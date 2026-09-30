"""Tests for the data directory and the Forge -> Teotl rename compatibility."""

import pytest

from teotl.core import paths


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.delenv("TEOTL_HOME", raising=False)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_teotl_home_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TEOTL_HOME", str(tmp_path / "custom"))
    assert paths.teotl_home() == tmp_path / "custom"


def test_default_is_dot_teotl(fake_home):
    assert paths.teotl_home() == fake_home / ".teotl"
    assert paths.teotl_home_display() == "~/.teotl"


def test_legacy_forge_dir_used_when_only_it_exists(fake_home):
    (fake_home / ".forge").mkdir()
    assert paths.teotl_home() == fake_home / ".forge"
    assert paths.teotl_home_display() == "~/.forge"


def test_new_dir_wins_when_both_exist(fake_home):
    (fake_home / ".forge").mkdir()
    (fake_home / ".teotl").mkdir()
    assert paths.teotl_home() == fake_home / ".teotl"


def test_getenv_prefers_teotl(monkeypatch):
    monkeypatch.setenv("FORGE_X_TEST", "old")
    assert paths.getenv("X_TEST") == "old"
    monkeypatch.setenv("TEOTL_X_TEST", "new")
    assert paths.getenv("X_TEST") == "new"


def test_env_backend_accepts_legacy_names(monkeypatch):
    from teotl.primitives.integrations.credential_store import EnvironmentBackend

    monkeypatch.delenv("TEOTL_ALLOW_ENV_AUTH", raising=False)
    monkeypatch.setenv("FORGE_ALLOW_ENV_AUTH", "true")
    monkeypatch.setenv("FORGE_LEGACYSVC_API_KEY", "k1")
    backend = EnvironmentBackend()
    assert backend.load("legacysvc")["api_key"] == "k1"
    assert "legacysvc" in backend.list_services()


def test_env_backend_lists_access_token_services(monkeypatch):
    from teotl.primitives.integrations.credential_store import EnvironmentBackend

    monkeypatch.setenv("TEOTL_ALLOW_ENV_AUTH", "true")
    monkeypatch.setenv("TEOTL_OAUTHSVC_ACCESS_TOKEN", "t")
    services = EnvironmentBackend().list_services()
    assert "oauthsvc" in services
    assert "oauthsvc_access" not in services
    assert "allow_env_auth" not in services


def test_keyring_copies_legacy_master_key(monkeypatch):
    pytest.importorskip("keyring")
    pytest.importorskip("cryptography")
    import json

    from cryptography.fernet import Fernet

    from teotl.primitives.integrations import credential_store as cs

    store = {}

    class FakeKeyring:
        @staticmethod
        def get_password(service, name):
            return store.get((service, name))

        @staticmethod
        def set_password(service, name, value):
            store[(service, name)] = value

        @staticmethod
        def delete_password(service, name):
            del store[(service, name)]

    legacy_key = Fernet.generate_key().decode()
    store[("forge", "master_key")] = legacy_key
    token = Fernet(legacy_key.encode()).encrypt(json.dumps({"token": "abc"}).encode()).decode()
    store[("forge", "cred_github")] = token

    monkeypatch.setitem(__import__("sys").modules, "keyring", FakeKeyring)
    backend = cs.LocalKeyringBackend()

    assert store[("teotl", "master_key")] == legacy_key  # copied
    assert store[("forge", "master_key")] == legacy_key  # not moved
    assert backend.load("github") == {"token": "abc"}  # legacy credential still readable

    backend.save("slack", {"token": "x"})
    assert ("teotl", "cred_slack") in store
    assert backend.delete("github") is True
