"""Integration registry: manages service connections and auth."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from teotl.primitives.integrations.credential_store import CredentialStore

logger = logging.getLogger(__name__)


class IntegrationNotFound(Exception):
    pass


class NotConnected(Exception):
    pass


class AuthCredential:
    """Stored credential for a service."""

    def __init__(self, service: str, auth_type: str, data: dict[str, Any]) -> None:
        self.service = service
        self.auth_type = auth_type
        self.data = data

    @property
    def access_token(self) -> str:
        return self.data.get("access_token", "")

    @property
    def api_key(self) -> str:
        return self.data.get("api_key", "")


class IntegrationRegistry:
    """
    Manages service connections using secure credential storage.
    Skill scripts handle the actual API calls.
    """

    def __init__(
        self,
        credential_backend: str | None = None,
        storage_path: Path | None = None,
        **backend_kwargs,
    ) -> None:
        """
        Initialize integration registry with credential store.

        Args:
            credential_backend: Specific backend ("keyring", "file", "environment", "aws_secrets")
                              If None, auto-detects best available backend.
            storage_path: Path for file-based storage (only used with file backend)
            **backend_kwargs: Additional backend-specific options
        """
        # For file backend, use storage_path if provided
        if credential_backend == "file" or (credential_backend is None and storage_path):
            backend_kwargs["storage_path"] = storage_path or Path.home() / ".forge" / "auth"

        self.store = CredentialStore.create(backend=credential_backend, **backend_kwargs)
        self.connected: dict[str, AuthCredential] = {}
        self._load_credentials()

        logger.info(f"IntegrationRegistry using {self.store.backend_name} backend")

    def _load_credentials(self) -> None:
        """Load saved credentials from secure store."""
        try:
            services = self.store.list_services()
            for service in services:
                try:
                    cred_data = self.store.load_credential(service)
                    self.connected[service] = AuthCredential(
                        service=service,
                        auth_type=cred_data.get("auth_type", "api_key"),
                        data=cred_data,
                    )
                except Exception as e:
                    logger.warning(f"Failed to load credential for {service}: {e}")

            if self.connected:
                logger.info(f"Loaded credentials for: {list(self.connected.keys())}")
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")

    def _save_credential(self, service: str, cred: AuthCredential) -> None:
        """Save a single credential to secure store."""
        try:
            # Store the full credential data including auth_type
            data = {
                "auth_type": cred.auth_type,
                **cred.data,  # Merge in the credential data (api_key, access_token, etc.)
            }
            self.store.save_credential(service, data)
        except Exception as e:
            logger.error(f"Failed to save credential for {service}: {e}")

    async def connect_api_key(self, service: str, api_key: str) -> bool:
        """Connect a service using an API key."""
        cred = AuthCredential(
            service=service,
            auth_type="api_key",
            data={"api_key": api_key},
        )
        self.connected[service] = cred
        self._save_credential(service, cred)
        logger.info(f"Connected: {service} (api_key)")
        return True

    def is_connected(self, service: str) -> bool:
        """Check if a service is connected."""
        return service in self.connected

    def build_env(self, service: str) -> dict[str, str]:
        """
        Build environment variables for a service's CLI scripts.

        Auth tokens are injected as env vars, never in context.
        """
        cred = self.connected.get(service)
        if not cred:
            raise NotConnected(f"Service '{service}' is not connected. Run: forge auth {service}")

        env = os.environ.copy()
        prefix = f"FORGE_{service.upper()}"

        if cred.auth_type == "api_key":
            env[f"{prefix}_API_KEY"] = cred.api_key
        elif cred.auth_type == "oauth2":
            env[f"{prefix}_TOKEN"] = cred.access_token

        return env

    def list_connected(self) -> list[str]:
        """List all connected services."""
        return list(self.connected.keys())

    async def disconnect(self, service: str) -> bool:
        """Disconnect a service and remove credentials."""
        if service in self.connected:
            del self.connected[service]
            try:
                self.store.delete_credential(service)
                logger.info(f"Disconnected: {service}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete credential for {service}: {e}")
                return False
        return False
