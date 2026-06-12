"""
Credential storage abstraction with pluggable backends.

Supports multiple storage backends:
- LocalKeyringStore: OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- FileStore: Encrypted file-based storage (fallback)
- EnvironmentStore: Environment variables (CI/CD, containers)
- CloudSecretsStore: Cloud secrets managers (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)

Usage:
    # Auto-detect best backend
    store = CredentialStore.create()

    # Or explicitly choose
    store = CredentialStore.create(backend="keyring")
    store = CredentialStore.create(backend="aws_secrets")

    # Use the store
    store.save_credential("github", {"api_key": "ghp_..."})
    cred = store.load_credential("github")
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CredentialBackend(ABC):
    """Abstract base for credential storage backends."""

    @abstractmethod
    def save(self, service: str, data: dict[str, Any]) -> None:
        """Save credential data for a service."""
        pass

    @abstractmethod
    def load(self, service: str) -> dict[str, Any]:
        """Load credential data for a service."""
        pass

    @abstractmethod
    def delete(self, service: str) -> bool:
        """Delete credential for a service."""
        pass

    @abstractmethod
    def list_services(self) -> list[str]:
        """List all services with stored credentials."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging/debugging."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available in current environment."""
        pass


class LocalKeyringBackend(CredentialBackend):
    """
    Uses OS keyring for credential storage.

    - macOS: Keychain
    - Windows: Credential Manager
    - Linux: Secret Service (GNOME Keyring, KWallet)
    """

    def __init__(self):
        try:
            import keyring
            from cryptography.fernet import Fernet

            self._keyring = keyring
            self._fernet = Fernet
            self._cipher = self._get_or_create_cipher()
        except ImportError as e:
            raise ImportError(
                "LocalKeyringBackend requires 'keyring' and 'cryptography'. "
                "Install with: pip install keyring cryptography"
            ) from e

    def _get_or_create_cipher(self):
        """Get or create encryption cipher."""
        key = self._keyring.get_password("forge", "master_key")
        if not key:
            key = self._fernet.generate_key().decode()
            self._keyring.set_password("forge", "master_key", key)
            logger.info("Created new master encryption key in OS keyring")
        return self._fernet(key.encode())

    def save(self, service: str, data: dict[str, Any]) -> None:
        encrypted = self._cipher.encrypt(json.dumps(data).encode())
        self._keyring.set_password("forge", f"cred_{service}", encrypted.decode())
        logger.info(f"Saved credential for {service} to OS keyring")

    def load(self, service: str) -> dict[str, Any]:
        encrypted_str = self._keyring.get_password("forge", f"cred_{service}")
        if not encrypted_str:
            raise ValueError(f"No credential found for service: {service}")
        decrypted = self._cipher.decrypt(encrypted_str.encode())
        return json.loads(decrypted)

    def delete(self, service: str) -> bool:
        try:
            self._keyring.delete_password("forge", f"cred_{service}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credential for {service}: {e}")
            return False

    def list_services(self) -> list[str]:
        # Keyring doesn't provide list API - would need separate registry
        logger.warning("LocalKeyringBackend doesn't support listing services")
        return []

    @property
    def name(self) -> str:
        return "keyring"

    @property
    def is_available(self) -> bool:
        try:
            import keyring

            # Test if keyring is functional
            keyring.get_password("forge", "test")
            return True
        except Exception:
            return False


class FileBackend(CredentialBackend):
    """
    Encrypted file-based credential storage.

    Fallback when OS keyring is unavailable.
    Uses Fernet encryption with key stored in restricted file.
    """

    def __init__(self, storage_path: Path | None = None):
        try:
            from cryptography.fernet import Fernet

            self._fernet = Fernet
        except ImportError as e:
            raise ImportError(
                "FileBackend requires 'cryptography'. Install with: pip install cryptography"
            ) from e

        self.storage_path = storage_path or Path.home() / ".forge" / "auth"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.key_file = self.storage_path / ".key"
        self._cipher = self._get_or_create_cipher()

    def _get_or_create_cipher(self):
        """Get or create encryption key from file."""
        if self.key_file.exists():
            key = self.key_file.read_bytes()
        else:
            key = self._fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)
            logger.warning(
                f"Created encryption key file at {self.key_file}. "
                f"OS keyring is preferred for production."
            )
        return self._fernet(key)

    def save(self, service: str, data: dict[str, Any]) -> None:
        encrypted = self._cipher.encrypt(json.dumps(data).encode())
        cred_file = self.storage_path / f"{service}.enc"
        cred_file.write_bytes(encrypted)
        cred_file.chmod(0o600)
        logger.info(f"Saved credential for {service} to encrypted file")

    def load(self, service: str) -> dict[str, Any]:
        cred_file = self.storage_path / f"{service}.enc"
        if not cred_file.exists():
            raise ValueError(f"No credential found for service: {service}")
        encrypted = cred_file.read_bytes()
        decrypted = self._cipher.decrypt(encrypted)
        return json.loads(decrypted)

    def delete(self, service: str) -> bool:
        cred_file = self.storage_path / f"{service}.enc"
        if cred_file.exists():
            cred_file.unlink()
            return True
        return False

    def list_services(self) -> list[str]:
        return [f.stem for f in self.storage_path.glob("*.enc")]

    @property
    def name(self) -> str:
        return "file"

    @property
    def is_available(self) -> bool:
        try:
            from cryptography.fernet import Fernet

            return True
        except ImportError:
            return False


class EnvironmentBackend(CredentialBackend):
    """
    Environment variable-based credential storage.

    For CI/CD, containers, and automated environments.
    NOT recommended for local development (insecure).

    Requires FORGE_ALLOW_ENV_AUTH=true to enable.
    """

    def __init__(self):
        if os.getenv("FORGE_ALLOW_ENV_AUTH") != "true":
            raise RuntimeError(
                "EnvironmentBackend requires FORGE_ALLOW_ENV_AUTH=true. "
                "This is intentionally restricted as environment variables "
                "are less secure than keyring/file storage."
            )
        logger.warning(
            "Using EnvironmentBackend for credentials. "
            "This should only be used in CI/CD or containerized environments."
        )

    def save(self, service: str, data: dict[str, Any]) -> None:
        raise NotImplementedError(
            "EnvironmentBackend is read-only. Set credentials via environment variables."
        )

    def load(self, service: str) -> dict[str, Any]:
        prefix = f"FORGE_{service.upper()}"

        # Look for common credential patterns
        api_key = os.getenv(f"{prefix}_API_KEY")
        token = os.getenv(f"{prefix}_TOKEN")
        access_token = os.getenv(f"{prefix}_ACCESS_TOKEN")

        if api_key:
            return {"auth_type": "api_key", "api_key": api_key}
        elif token:
            return {"auth_type": "token", "token": token}
        elif access_token:
            return {"auth_type": "oauth2", "access_token": access_token}
        else:
            raise ValueError(
                f"No credential found in environment for {service}. "
                f"Expected {prefix}_API_KEY, {prefix}_TOKEN, or {prefix}_ACCESS_TOKEN"
            )

    def delete(self, service: str) -> bool:
        raise NotImplementedError(
            "EnvironmentBackend is read-only. Cannot delete environment variables."
        )

    def list_services(self) -> list[str]:
        # Scan environment for FORGE_*_API_KEY or FORGE_*_TOKEN patterns
        services = set()
        for key in os.environ:
            if key.startswith("FORGE_"):
                # Extract service name (e.g., FORGE_GITHUB_API_KEY -> github)
                if key.endswith("_API_KEY"):
                    # Remove FORGE_ prefix and _API_KEY suffix
                    service = key[6:-8].lower()
                    if service:
                        services.add(service)
                elif key.endswith("_TOKEN"):
                    # Remove FORGE_ prefix and _TOKEN suffix
                    service = key[6:-6].lower()
                    if service:
                        services.add(service)
                elif key.endswith("_ACCESS_TOKEN"):
                    # Remove FORGE_ prefix and _ACCESS_TOKEN suffix
                    service = key[6:-13].lower()
                    if service:
                        services.add(service)
        return list(services)

    @property
    def name(self) -> str:
        return "environment"

    @property
    def is_available(self) -> bool:
        return os.getenv("FORGE_ALLOW_ENV_AUTH") == "true"


class AWSSecretsBackend(CredentialBackend):
    """
    AWS Secrets Manager backend.

    Requires:
    - boto3 installed
    - AWS credentials configured
    - AWS_REGION set (or default region)
    """

    def __init__(self, region: str | None = None):
        try:
            import boto3

            self.region = region or os.getenv("AWS_REGION", "us-east-1")
            self.client = boto3.client("secretsmanager", region_name=self.region)
            logger.info(f"Using AWS Secrets Manager in {self.region}")
        except ImportError as e:
            raise ImportError(
                "AWSSecretsBackend requires 'boto3'. Install with: pip install boto3"
            ) from e

    def save(self, service: str, data: dict[str, Any]) -> None:
        secret_name = f"forge/{service}"
        secret_value = json.dumps(data)

        try:
            # Try to update existing secret
            self.client.update_secret(SecretId=secret_name, SecretString=secret_value)
            logger.info(f"Updated secret {secret_name} in AWS Secrets Manager")
        except self.client.exceptions.ResourceNotFoundException:
            # Create new secret
            self.client.create_secret(
                Name=secret_name,
                SecretString=secret_value,
                Description=f"Forge credential for {service}",
            )
            logger.info(f"Created secret {secret_name} in AWS Secrets Manager")

    def load(self, service: str) -> dict[str, Any]:
        secret_name = f"forge/{service}"

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except self.client.exceptions.ResourceNotFoundException:
            raise ValueError(f"No credential found for service: {service}")

    def delete(self, service: str) -> bool:
        secret_name = f"forge/{service}"

        try:
            self.client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=False,  # Allows recovery within 7-30 days
            )
            logger.info(f"Scheduled deletion of secret {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name}: {e}")
            return False

    def list_services(self) -> list[str]:
        try:
            paginator = self.client.get_paginator("list_secrets")
            services = []

            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret["Name"]
                    if name.startswith("forge/"):
                        service = name.replace("forge/", "")
                        services.append(service)

            return services
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []

    @property
    def name(self) -> str:
        return "aws_secrets"

    @property
    def is_available(self) -> bool:
        try:
            import boto3

            # Quick check if AWS credentials are configured
            client = boto3.client("secretsmanager", region_name=self.region)
            client.list_secrets(MaxResults=1)
            return True
        except Exception:
            return False


# Backend registry
BACKENDS = {
    "keyring": LocalKeyringBackend,
    "file": FileBackend,
    "environment": EnvironmentBackend,
    "aws_secrets": AWSSecretsBackend,
}


class CredentialStore:
    """
    Credential storage with automatic backend selection.

    Auto-detects best available backend:
    1. Environment variables (if FORGE_ALLOW_ENV_AUTH=true)
    2. Cloud secrets (if in cloud environment)
    3. OS keyring (if available)
    4. Encrypted file (fallback)
    """

    def __init__(self, backend: CredentialBackend):
        self.backend = backend
        logger.info(f"Using credential backend: {backend.name}")

    @classmethod
    def create(cls, backend: str | None = None, **kwargs) -> CredentialStore:
        """
        Create credential store with auto-detected or specified backend.

        Args:
            backend: Specific backend name ("keyring", "file", "environment", "aws_secrets")
                    If None, auto-detects best available backend.
            **kwargs: Backend-specific options (e.g., region for AWS)

        Returns:
            CredentialStore instance
        """
        if backend:
            # Use specified backend
            if backend not in BACKENDS:
                raise ValueError(f"Unknown backend: {backend}. Available: {list(BACKENDS.keys())}")

            backend_class = BACKENDS[backend]
            try:
                backend_instance = backend_class(**kwargs)
                return cls(backend_instance)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize {backend} backend: {e}") from e

        # Auto-detect best backend
        # Priority: environment > cloud > keyring > file

        # 1. Check environment (CI/CD, containers)
        if os.getenv("FORGE_ALLOW_ENV_AUTH") == "true":
            try:
                backend_instance = EnvironmentBackend()
                return cls(backend_instance)
            except Exception as e:
                logger.debug(f"EnvironmentBackend not available: {e}")

        # 2. Check cloud secrets (AWS first, can add GCP/Azure)
        if os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"):
            try:
                backend_instance = AWSSecretsBackend()
                if backend_instance.is_available:
                    return cls(backend_instance)
            except Exception as e:
                logger.debug(f"AWSSecretsBackend not available: {e}")

        # 3. Try OS keyring
        try:
            backend_instance = LocalKeyringBackend()
            if backend_instance.is_available:
                return cls(backend_instance)
        except Exception as e:
            logger.debug(f"LocalKeyringBackend not available: {e}")

        # 4. Fallback to encrypted file
        try:
            backend_instance = FileBackend()
            return cls(backend_instance)
        except Exception as e:
            raise RuntimeError(
                "No credential backend available. Install 'cryptography': pip install cryptography"
            ) from e

    def save_credential(self, service: str, data: dict[str, Any]) -> None:
        """Save credential for a service."""
        self.backend.save(service, data)

    def load_credential(self, service: str) -> dict[str, Any]:
        """Load credential for a service."""
        return self.backend.load(service)

    def delete_credential(self, service: str) -> bool:
        """Delete credential for a service."""
        return self.backend.delete(service)

    def list_services(self) -> list[str]:
        """List all services with stored credentials."""
        return self.backend.list_services()

    @property
    def backend_name(self) -> str:
        """Get current backend name."""
        return self.backend.name
