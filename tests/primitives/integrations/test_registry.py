"""Tests for IntegrationRegistry with secure credential storage."""

import pytest

from teotl.primitives.integrations.registry import (
    AuthCredential,
    IntegrationRegistry,
    NotConnected,
)


class TestIntegrationRegistry:
    """Test IntegrationRegistry with credential store backends."""

    @pytest.mark.asyncio
    async def test_connect_api_key_file_backend(self, tmp_path):
        """Test connecting a service with API key using file backend."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        # Connect a service
        result = await registry.connect_api_key("github", "ghp_test123")
        assert result is True

        # Verify it's in connected services
        assert registry.is_connected("github")
        assert "github" in registry.list_connected()

        # Verify credential data
        cred = registry.connected["github"]
        assert cred.service == "github"
        assert cred.auth_type == "api_key"
        assert cred.api_key == "ghp_test123"

    @pytest.mark.asyncio
    async def test_credentials_persist_across_instances(self, tmp_path):
        """Test credentials persist when creating new registry instances."""
        # Create first registry and connect
        registry1 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)
        await registry1.connect_api_key("github", "ghp_test123")

        # Create second registry - should load existing credentials
        registry2 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        assert registry2.is_connected("github")
        cred = registry2.connected["github"]
        assert cred.api_key == "ghp_test123"

    @pytest.mark.asyncio
    async def test_disconnect_removes_credential(self, tmp_path):
        """Test disconnecting removes credential from store."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        await registry.connect_api_key("github", "ghp_test123")
        assert registry.is_connected("github")

        # Disconnect
        result = await registry.disconnect("github")
        assert result is True
        assert not registry.is_connected("github")

        # Verify it's gone from store
        registry2 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)
        assert not registry2.is_connected("github")

    @pytest.mark.asyncio
    async def test_build_env_with_api_key(self, tmp_path):
        """Test building environment variables for API key auth."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        await registry.connect_api_key("github", "ghp_test123")

        env = registry.build_env("github")
        assert "FORGE_GITHUB_API_KEY" in env
        assert env["FORGE_GITHUB_API_KEY"] == "ghp_test123"

    def test_build_env_not_connected_raises(self, tmp_path):
        """Test build_env raises NotConnected for unconnected service."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        with pytest.raises(NotConnected, match="not connected"):
            registry.build_env("nonexistent")

    @pytest.mark.asyncio
    async def test_auto_detect_backend(self, tmp_path):
        """Test auto-detection of backend when not specified."""
        # Should auto-detect and use file backend as fallback
        registry = IntegrationRegistry(storage_path=tmp_path)

        await registry.connect_api_key("test", "key123")
        assert registry.is_connected("test")

    @pytest.mark.asyncio
    async def test_environment_backend(self, monkeypatch):
        """Test using environment backend for credentials."""
        monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
        monkeypatch.setenv("FORGE_GITHUB_API_KEY", "ghp_test123")

        registry = IntegrationRegistry(credential_backend="environment")

        # Environment backend should load GitHub credential
        assert registry.is_connected("github")
        cred = registry.connected["github"]
        assert cred.api_key == "ghp_test123"

    def test_list_connected_services(self, tmp_path):
        """Test listing all connected services."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        # Initially empty
        assert registry.list_connected() == []

        # Add some services
        import asyncio

        asyncio.run(registry.connect_api_key("github", "key1"))
        asyncio.run(registry.connect_api_key("slack", "key2"))

        services = registry.list_connected()
        assert set(services) == {"github", "slack"}

    @pytest.mark.asyncio
    async def test_oauth2_credential_structure(self, tmp_path):
        """Test OAuth2 credentials can be stored and retrieved."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        # Manually create OAuth2 credential
        cred = AuthCredential(
            service="gmail",
            auth_type="oauth2",
            data={
                "access_token": "ya29.test",
                "refresh_token": "1//test",
                "expires_at": 1234567890,
            },
        )
        registry.connected["gmail"] = cred
        registry._save_credential("gmail", cred)

        # Reload and verify
        registry2 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        assert registry2.is_connected("gmail")
        loaded_cred = registry2.connected["gmail"]
        assert loaded_cred.auth_type == "oauth2"
        assert loaded_cred.access_token == "ya29.test"
        assert loaded_cred.data["refresh_token"] == "1//test"

    def test_backend_name_logging(self, tmp_path, caplog):
        """Test that backend name is logged on initialization."""
        import logging

        caplog.set_level(logging.INFO)

        IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        assert "using file backend" in caplog.text.lower()


class TestAuthCredential:
    """Test AuthCredential data structure."""

    def test_api_key_property(self):
        """Test api_key property accessor."""
        cred = AuthCredential(
            service="github", auth_type="api_key", data={"api_key": "ghp_test123"}
        )

        assert cred.api_key == "ghp_test123"

    def test_access_token_property(self):
        """Test access_token property accessor."""
        cred = AuthCredential(
            service="gmail", auth_type="oauth2", data={"access_token": "ya29.test"}
        )

        assert cred.access_token == "ya29.test"

    def test_missing_keys_return_empty_string(self):
        """Test properties return empty string for missing keys."""
        cred = AuthCredential(service="test", auth_type="api_key", data={})

        assert cred.api_key == ""
        assert cred.access_token == ""


class TestIntegrationRegistryErrorHandling:
    """Test error handling in IntegrationRegistry."""

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_service(self, tmp_path):
        """Test disconnecting a service that doesn't exist."""
        registry = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        result = await registry.disconnect("nonexistent")
        assert result is False

    def test_corrupted_credential_load_continues(self, tmp_path, caplog):
        """Test that loading continues if one credential is corrupted."""
        import logging

        caplog.set_level(logging.WARNING)

        # Create registry and add valid credential
        registry1 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)
        import asyncio

        asyncio.run(registry1.connect_api_key("github", "key1"))

        # Manually corrupt a credential file
        (tmp_path / "corrupted.enc").write_text("invalid data")

        # Create new registry - should load valid credential despite corruption
        registry2 = IntegrationRegistry(credential_backend="file", storage_path=tmp_path)

        # Valid credential should still be loaded
        assert registry2.is_connected("github")

        # Should log warning about corruption
        assert "failed to load" in caplog.text.lower()
