"""Tests for credential store abstraction and backends."""

from unittest.mock import Mock, patch

import pytest

from teotl.primitives.integrations.credential_store import (
    AWSSecretsBackend,
    CredentialStore,
    EnvironmentBackend,
    FileBackend,
    LocalKeyringBackend,
)


class TestFileBackend:
    """Test file-based credential storage."""

    def test_save_and_load(self, tmp_path):
        backend = FileBackend(storage_path=tmp_path)

        # Save credential
        backend.save(
            "test_service",
            {
                "auth_type": "api_key",
                "api_key": "secret123",
            },
        )

        # Load credential
        cred = backend.load("test_service")
        assert cred["api_key"] == "secret123"
        assert cred["auth_type"] == "api_key"

    def test_credential_encrypted(self, tmp_path):
        """Verify credentials are not stored as plaintext."""
        backend = FileBackend(storage_path=tmp_path)

        backend.save("test", {"api_key": "secret123"})

        # Check file content is encrypted
        cred_file = tmp_path / "test.enc"
        content = cred_file.read_text()
        assert "secret123" not in content
        assert "api_key" not in content

    def test_file_permissions(self, tmp_path):
        """Verify files have restricted permissions."""
        backend = FileBackend(storage_path=tmp_path)

        backend.save("test", {"api_key": "secret"})

        cred_file = tmp_path / "test.enc"
        key_file = tmp_path / ".key"

        # Check permissions are 600 (owner read/write only)
        assert oct(cred_file.stat().st_mode)[-3:] == "600"
        assert oct(key_file.stat().st_mode)[-3:] == "600"

    def test_delete_credential(self, tmp_path):
        backend = FileBackend(storage_path=tmp_path)

        backend.save("test", {"api_key": "key"})
        assert backend.delete("test") is True

        # Verify deleted
        with pytest.raises(ValueError, match="No credential found"):
            backend.load("test")

    def test_list_services(self, tmp_path):
        backend = FileBackend(storage_path=tmp_path)

        backend.save("service1", {"api_key": "key1"})
        backend.save("service2", {"api_key": "key2"})

        services = backend.list_services()
        assert set(services) == {"service1", "service2"}

    def test_load_nonexistent(self, tmp_path):
        backend = FileBackend(storage_path=tmp_path)

        with pytest.raises(ValueError, match="No credential found"):
            backend.load("nonexistent")


class TestEnvironmentBackend:
    """Test environment variable-based credential storage."""

    def test_requires_explicit_enable(self):
        """Environment backend requires FORGE_ALLOW_ENV_AUTH=true."""
        with pytest.raises(RuntimeError, match="FORGE_ALLOW_ENV_AUTH"):
            EnvironmentBackend()

    def test_load_api_key(self, monkeypatch):
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
        monkeypatch.setenv("FORGE_GITHUB_API_KEY", "ghp_test123")

        backend = EnvironmentBackend()
        cred = backend.load("github")

        assert cred["auth_type"] == "api_key"
        assert cred["api_key"] == "ghp_test123"

    def test_load_token(self, monkeypatch):
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
        monkeypatch.setenv("FORGE_SLACK_TOKEN", "xoxb-test")

        backend = EnvironmentBackend()
        cred = backend.load("slack")

        assert cred["auth_type"] == "token"
        assert cred["token"] == "xoxb-test"

    def test_load_nonexistent(self, monkeypatch):
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")

        backend = EnvironmentBackend()

        with pytest.raises(ValueError, match="No credential found"):
            backend.load("nonexistent")

    def test_save_not_supported(self, monkeypatch):
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")

        backend = EnvironmentBackend()

        with pytest.raises(NotImplementedError, match="read-only"):
            backend.save("test", {"api_key": "key"})

    def test_list_services(self, monkeypatch):
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
        monkeypatch.setenv("FORGE_GITHUB_API_KEY", "key1")
        monkeypatch.setenv("FORGE_SLACK_TOKEN", "key2")
        monkeypatch.setenv("OTHER_VAR", "value")

        backend = EnvironmentBackend()
        services = backend.list_services()

        assert "github" in services
        assert "slack" in services
        assert len(services) == 2


def _keyring_available():
    """Check if keyring dependencies are available."""
    try:
        import cryptography
        import keyring

        return True
    except ImportError:
        return False


class TestLocalKeyringBackend:
    """Test OS keyring-based credential storage."""

    @pytest.mark.skipif(not _keyring_available(), reason="Keyring dependencies not available")
    def test_save_and_load(self):
        """Integration test with real keyring (if available)."""
        backend = LocalKeyringBackend()

        try:
            backend.save(
                "test_teotl_service",
                {
                    "auth_type": "api_key",
                    "api_key": "test123",
                },
            )

            cred = backend.load("test_teotl_service")
            assert cred["api_key"] == "test123"

        finally:
            # Cleanup
            backend.delete("test_teotl_service")

    @pytest.mark.skipif(_keyring_available(), reason="Test only runs when keyring is NOT available")
    def test_keyring_unavailable_error(self):
        """Test error when keyring dependencies missing."""
        with pytest.raises(ImportError, match="requires 'keyring'"):
            LocalKeyringBackend()


class TestAWSSecretsBackend:
    """Test AWS Secrets Manager backend."""

    def test_save_creates_secret(self):
        """Test saving credential creates AWS secret."""
        mock_client = Mock()

        # Create a proper exception class
        class MockResourceNotFound(Exception):
            pass

        mock_client.exceptions.ResourceNotFoundException = MockResourceNotFound
        mock_client.update_secret.side_effect = MockResourceNotFound("Not found")

        with patch("boto3.client", return_value=mock_client):
            backend = AWSSecretsBackend()
            backend.save("github", {"api_key": "ghp_test"})

            # Should create new secret
            mock_client.create_secret.assert_called_once()
            call_args = mock_client.create_secret.call_args
            assert call_args[1]["Name"] == "teotl/github"
            assert "ghp_test" in call_args[1]["SecretString"]

    def test_save_updates_existing(self):
        """Test saving credential updates existing secret."""
        mock_client = Mock()

        with patch("boto3.client", return_value=mock_client):
            backend = AWSSecretsBackend()
            backend.save("github", {"api_key": "ghp_test"})

            # Should update existing
            mock_client.update_secret.assert_called_once()
            assert not mock_client.create_secret.called

    def test_load_credential(self):
        """Test loading credential from AWS."""
        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": '{"api_key": "ghp_test"}'}

        with patch("boto3.client", return_value=mock_client):
            backend = AWSSecretsBackend()
            cred = backend.load("github")

            assert cred["api_key"] == "ghp_test"
            mock_client.get_secret_value.assert_called_with(SecretId="teotl/github")

    def test_load_nonexistent(self):
        """Test loading nonexistent credential raises error."""
        mock_client = Mock()

        # Create a proper exception class
        class MockResourceNotFound(Exception):
            pass

        mock_client.exceptions.ResourceNotFoundException = MockResourceNotFound
        mock_client.get_secret_value.side_effect = MockResourceNotFound("Not found")

        with patch("boto3.client", return_value=mock_client):
            backend = AWSSecretsBackend()

            with pytest.raises(ValueError, match="No credential found"):
                backend.load("nonexistent")

    def test_list_services(self):
        """Test listing services from AWS."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "SecretList": [
                    {"Name": "teotl/github"},
                    {"Name": "teotl/slack"},
                    {"Name": "other/secret"},  # Should be ignored
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_client):
            backend = AWSSecretsBackend()
            services = backend.list_services()

            assert set(services) == {"github", "slack"}


class TestCredentialStore:
    """Test credential store auto-detection and API."""

    def test_explicit_backend_selection(self, tmp_path):
        """Test explicitly choosing a backend."""
        store = CredentialStore.create(backend="file", storage_path=tmp_path)

        assert store.backend_name == "file"

    def test_auto_detect_environment(self, monkeypatch):
        """Test auto-detection prefers environment when enabled."""
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
        monkeypatch.setenv("FORGE_TEST_API_KEY", "key")

        store = CredentialStore.create()
        assert store.backend_name == "environment"

    def test_auto_detect_fallback_file(self, monkeypatch):
        """Test auto-detection falls back to file when others unavailable."""
        # Disable environment
        monkeypatch.delenv("FORGE_ALLOW_ENV_AUTH", raising=False)
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

        # The auto-detection will try keyring first, but if unavailable,
        # it will fallback to file backend
        store = CredentialStore.create()

        # Should be file backend (keyring might not be available in CI)
        assert store.backend_name in ["file", "keyring"]

    def test_save_and_load_api(self, tmp_path):
        """Test high-level save/load API."""
        store = CredentialStore.create(backend="file", storage_path=tmp_path)

        store.save_credential(
            "github",
            {
                "auth_type": "oauth2",
                "access_token": "gho_test123",
            },
        )

        cred = store.load_credential("github")
        assert cred["access_token"] == "gho_test123"

    def test_delete_credential_api(self, tmp_path):
        """Test high-level delete API."""
        store = CredentialStore.create(backend="file", storage_path=tmp_path)

        store.save_credential("test", {"api_key": "key"})
        assert store.delete_credential("test") is True

    def test_list_services_api(self, tmp_path):
        """Test high-level list API."""
        store = CredentialStore.create(backend="file", storage_path=tmp_path)

        store.save_credential("service1", {"api_key": "key1"})
        store.save_credential("service2", {"api_key": "key2"})

        services = store.list_services()
        assert set(services) == {"service1", "service2"}

    def test_invalid_backend_error(self):
        """Test error on invalid backend name."""
        with pytest.raises(ValueError, match="Unknown backend"):
            CredentialStore.create(backend="invalid")

    def test_no_backend_available_error(self, monkeypatch, tmp_path):
        """Test error when no backend can be initialized."""
        monkeypatch.delenv("FORGE_ALLOW_ENV_AUTH", raising=False)
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

        # Mock FileBackend to raise error (simulating cryptography not available)
        def mock_file_backend(*args, **kwargs):
            raise ImportError("cryptography not available")

        with patch(
            "teotl.primitives.integrations.credential_store.FileBackend",
            side_effect=mock_file_backend,
        ), patch(
            "teotl.primitives.integrations.credential_store.LocalKeyringBackend"
        ) as mock_keyring:
            mock_keyring.side_effect = ImportError("keyring not available")

            with pytest.raises(RuntimeError, match="No credential backend available"):
                CredentialStore.create()


class TestBackendIntegration:
    """Integration tests across backends."""

    def test_credential_portability(self, tmp_path):
        """Test credentials can be moved between backends."""
        # Save with file backend
        file_store = CredentialStore.create(backend="file", storage_path=tmp_path)
        file_store.save_credential(
            "github",
            {
                "auth_type": "api_key",
                "api_key": "ghp_test123",
            },
        )

        # Load with same backend
        cred = file_store.load_credential("github")
        assert cred["api_key"] == "ghp_test123"

        # Data structure is consistent
        assert "auth_type" in cred
        assert "api_key" in cred
