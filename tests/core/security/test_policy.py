"""Tests for security policy system."""

import tempfile
from pathlib import Path

import pytest

from teotl.core.security.policy import (
    Compliance,
    CostLimits,
    DataPrivacy,
    FilesystemPolicy,
    NetworkPolicy,
    PolicyMode,
    RateLimits,
    SecurityPolicy,
    ToolPolicy,
)


class TestNetworkPolicy:
    """Test network policy enforcement."""

    def test_allowlist_mode(self):
        """Test allowlist mode blocks unlisted domains."""
        policy = NetworkPolicy(
            mode=PolicyMode.ALLOWLIST,
            allowed_domains=["github.com", "*.google.com"],
        )

        assert policy.allows("github.com")
        assert policy.allows("api.google.com")
        assert policy.allows("mail.google.com")
        assert not policy.allows("facebook.com")

    def test_denylist_mode(self):
        """Test denylist mode allows unlisted domains."""
        policy = NetworkPolicy(
            mode=PolicyMode.DENYLIST,
            blocked_domains=["facebook.com", "*.twitter.com"],
        )

        assert policy.allows("github.com")
        assert policy.allows("google.com")
        assert not policy.allows("facebook.com")
        assert not policy.allows("api.twitter.com")

    def test_permissive_mode(self):
        """Test permissive mode allows everything."""
        policy = NetworkPolicy(
            mode=PolicyMode.PERMISSIVE,
            blocked_domains=["facebook.com"],  # Even blocklist ignored
        )

        assert policy.allows("anything.com")
        assert policy.allows("facebook.com")  # Still allowed in permissive

    def test_wildcard_patterns(self):
        """Test wildcard domain matching."""
        policy = NetworkPolicy(
            mode=PolicyMode.ALLOWLIST,
            allowed_domains=["*.github.com", "example.*"],
        )

        assert policy.allows("api.github.com")
        assert policy.allows("raw.githubusercontent.com") is False
        assert policy.allows("example.com")
        assert policy.allows("example.org")

    def test_requires_approval(self):
        """Test approval requirement check."""
        policy = NetworkPolicy(
            require_approval=["*.amazonaws.com"],
        )

        assert policy.requires_approval("s3.amazonaws.com")
        assert not policy.requires_approval("github.com")


class TestFilesystemPolicy:
    """Test filesystem policy enforcement."""

    def test_allowed_paths(self):
        """Test allowed paths checking."""
        policy = FilesystemPolicy(
            mode=PolicyMode.RESTRICTED,
            allowed_paths=["/tmp/**", "~/.teotl/**"],
        )

        assert policy.allows("/tmp/test.txt")
        assert policy.allows("/tmp/subdir/file.txt")
        assert policy.allows(str(Path("~/.teotl/data/file.txt").expanduser()))
        assert not policy.allows("/etc/passwd")

    def test_readonly_paths(self):
        """Test readonly path restrictions."""
        policy = FilesystemPolicy(
            mode=PolicyMode.RESTRICTED,
            allowed_paths=["~/.teotl/**"],
            readonly_paths=["~/Documents/**"],
        )

        # Read access allowed
        assert policy.allows("~/Documents/file.txt", write=False)

        # Write access denied
        assert not policy.allows("~/Documents/file.txt", write=True)

    def test_blocked_paths(self):
        """Test blocked paths override allowed."""
        policy = FilesystemPolicy(
            mode=PolicyMode.RESTRICTED,
            allowed_paths=["~/**"],
            blocked_paths=["~/.ssh/**", "~/.aws/**"],
        )

        assert policy.allows("~/projects/file.txt")
        assert not policy.allows("~/.ssh/id_rsa")
        assert not policy.allows("~/.aws/credentials")

    def test_path_resolution(self):
        """Test path expansion and resolution."""
        policy = FilesystemPolicy(
            mode=PolicyMode.RESTRICTED,
            allowed_paths=["~/.teotl/**"],
        )

        # Should expand ~ and resolve to absolute path
        home_teotl = Path("~/.teotl/test.txt").expanduser().resolve()
        assert policy.allows(str(home_teotl))


class TestToolPolicy:
    """Test tool policy enforcement."""

    def test_allowlist(self):
        """Test tool allowlist."""
        policy = ToolPolicy(
            allowed=["read_file", "write_file"],
        )

        assert policy.allows("read_file")
        assert policy.allows("write_file")
        assert not policy.allows("execute_shell")

    def test_blocklist(self):
        """Test tool blocklist."""
        policy = ToolPolicy(
            blocked=["execute_shell", "delete_file"],
        )

        assert policy.allows("read_file")
        assert not policy.allows("execute_shell")
        assert not policy.allows("delete_file")

    def test_empty_allowlist_allows_all(self):
        """Test empty allowlist allows all except blocked."""
        policy = ToolPolicy(
            allowed=[],  # Empty
            blocked=["execute_shell"],
        )

        assert policy.allows("read_file")
        assert policy.allows("web_search")
        assert not policy.allows("execute_shell")

    def test_requires_approval(self):
        """Test approval requirement."""
        policy = ToolPolicy(
            require_approval=["send_email", "create_pr"],
        )

        assert policy.requires_approval("send_email")
        assert not policy.requires_approval("read_file")


class TestSecurityPolicy:
    """Test complete security policy."""

    def test_from_dict(self):
        """Test policy creation from dict."""
        config = {
            "version": "1.0",
            "agent_id": "test-agent",
            "log_level": "standard",
            "network": {
                "mode": "allowlist",
                "allowed_domains": ["github.com"],
            },
            "filesystem": {
                "mode": "restricted",
                "allowed_paths": ["/tmp/**"],
            },
            "tools": {
                "allowed": ["read_file"],
                "blocked": ["execute_shell"],
            },
            "cost_limits": {
                "max_per_hour": 1.0,
                "max_per_day": 10.0,
                "max_per_month": 100.0,
            },
            "rate_limits": {
                "max_api_calls_per_minute": 10,
            },
            "data_privacy": {
                "redact_pii": True,
                "retention_days": 90,
            },
            "compliance": {
                "gdpr_enabled": True,
                "soc2_enabled": False,
                "hipaa_enabled": False,
            },
        }

        policy = SecurityPolicy.from_dict(config)

        assert policy.agent_id == "test-agent"
        assert policy.network.mode == PolicyMode.ALLOWLIST
        assert policy.filesystem.mode == PolicyMode.RESTRICTED
        assert policy.cost_limits.max_per_hour == 1.0
        assert policy.compliance.gdpr_enabled is True

    def test_to_yaml_and_from_file(self):
        """Test policy serialization round-trip."""
        # Create policy
        policy = SecurityPolicy.create_default("test-agent", "moderate")

        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_path = Path(tmpdir) / "security.yaml"
            policy.to_yaml(policy_path)

            # Load back
            loaded = SecurityPolicy.from_file(policy_path)

            assert loaded.agent_id == policy.agent_id
            assert loaded.network.mode == policy.network.mode
            assert loaded.filesystem.mode == policy.filesystem.mode
            assert loaded.cost_limits.max_per_hour == policy.cost_limits.max_per_hour

    def test_create_default_strict(self):
        """Test strict preset creation."""
        policy = SecurityPolicy.create_default("test-agent", "strict")

        assert policy.agent_id == "test-agent"
        assert policy.network.mode == PolicyMode.ALLOWLIST
        assert len(policy.network.allowed_domains) <= 3  # Minimal domains
        assert "execute_shell" in policy.tools.blocked
        assert policy.cost_limits.max_per_hour == 1.0
        assert policy.cost_limits.max_per_day == 10.0

    def test_create_default_moderate(self):
        """Test moderate preset creation."""
        policy = SecurityPolicy.create_default("test-agent", "moderate")

        assert policy.network.mode == PolicyMode.ALLOWLIST
        assert len(policy.network.allowed_domains) >= 5  # Common domains
        assert "read_file" in policy.tools.allowed
        assert "web_search" in policy.tools.allowed
        assert policy.cost_limits.max_per_hour == 5.0
        assert policy.cost_limits.max_per_day == 50.0

    def test_create_default_permissive(self):
        """Test permissive preset creation."""
        policy = SecurityPolicy.create_default("test-agent", "permissive")

        assert policy.network.mode == PolicyMode.PERMISSIVE
        assert policy.filesystem.mode == PolicyMode.PERMISSIVE
        assert "execute_shell" in policy.tools.blocked  # Still some safety
        assert policy.cost_limits.max_per_hour == 10.0
        assert policy.cost_limits.max_per_day == 100.0

    def test_invalid_preset(self):
        """Test invalid preset raises error."""
        with pytest.raises(ValueError, match="Unknown preset"):
            SecurityPolicy.create_default("test-agent", "invalid")

    def test_file_not_found(self):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            SecurityPolicy.from_file(Path("/nonexistent/security.yaml"))


class TestCostLimits:
    """Test cost limit configuration."""

    def test_defaults(self):
        """Test default cost limits."""
        limits = CostLimits()

        assert limits.max_per_hour == 5.0
        assert limits.max_per_day == 50.0
        assert limits.max_per_month == 500.0
        assert limits.currency == "USD"


class TestRateLimits:
    """Test rate limit configuration."""

    def test_defaults(self):
        """Test default rate limits."""
        limits = RateLimits()

        assert limits.max_api_calls_per_minute == 20
        assert limits.max_tokens_per_hour == 100_000


class TestDataPrivacy:
    """Test data privacy configuration."""

    def test_defaults(self):
        """Test default privacy settings."""
        privacy = DataPrivacy()

        assert privacy.redact_pii is True
        assert privacy.encrypt_logs is False
        assert privacy.retention_days == 90


class TestCompliance:
    """Test compliance configuration."""

    def test_defaults(self):
        """Test default compliance settings."""
        compliance = Compliance()

        assert compliance.gdpr_enabled is False
        assert compliance.soc2_enabled is False
        assert compliance.hipaa_enabled is False

    def test_enable_all(self):
        """Test enabling all compliance features."""
        compliance = Compliance(
            gdpr_enabled=True,
            soc2_enabled=True,
            hipaa_enabled=True,
        )

        assert compliance.gdpr_enabled is True
        assert compliance.soc2_enabled is True
        assert compliance.hipaa_enabled is True
