"""Tests for sandboxing system.

Tests filesystem, network, and resource sandboxes to ensure proper isolation.
"""

import socket
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from teotl.core.security.sandbox import (
    FilesystemSandbox,
    FilesystemSandboxConfig,
    NetworkSandbox,
    NetworkSandboxConfig,
    ResourceLimits,
    ResourceLimitsConfig,
    SandboxManager,
    SandboxViolation,
)


class TestFilesystemSandbox:
    """Test filesystem sandbox isolation."""

    def test_path_within_allowed(self):
        """Test path within allowed directory is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[],
                enforce=True,
            )
            sandbox = FilesystemSandbox(config)

            # Should succeed
            test_path = Path(tmpdir) / "test.txt"
            result = sandbox.validate_path(test_path, "read")
            assert result.is_absolute()
            assert str(result).startswith(str(Path(tmpdir).resolve()))

    def test_path_outside_allowed(self):
        """Test path outside allowed directory is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[],
                enforce=True,
            )
            sandbox = FilesystemSandbox(config)

            # Should raise
            with pytest.raises(SandboxViolation, match="not permitted"):
                sandbox.validate_path("/etc/passwd", "read")

    def test_blocked_pattern_wildcard_recursive(self):
        """Test blocked pattern with ** (recursive wildcard)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[f"{tmpdir}/blocked/**"],
                enforce=True,
            )
            sandbox = FilesystemSandbox(config)

            # Create test directory structure
            blocked_dir = Path(tmpdir) / "blocked"
            blocked_dir.mkdir()
            nested = blocked_dir / "nested" / "file.txt"

            # Should raise for blocked path
            with pytest.raises(SandboxViolation, match="blocked by pattern"):
                sandbox.validate_path(nested, "read")

    def test_blocked_pattern_wildcard_single(self):
        """Test blocked pattern with * (single-level wildcard)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[f"{tmpdir}/*.secret"],
                enforce=True,
            )
            sandbox = FilesystemSandbox(config)

            # Should raise for matching pattern
            with pytest.raises(SandboxViolation, match="blocked by pattern"):
                sandbox.validate_path(f"{tmpdir}/test.secret", "read")

    def test_blocked_pattern_exact(self):
        """Test blocked pattern with exact path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[f"{tmpdir}/blocked.txt"],
                enforce=True,
            )
            sandbox = FilesystemSandbox(config)

            # Should raise for exact match
            with pytest.raises(SandboxViolation, match="explicitly blocked"):
                sandbox.validate_path(f"{tmpdir}/blocked.txt", "read")

    def test_no_allowed_paths_configured(self):
        """Test that empty allowed_paths allows everything (except blocked)."""
        config = FilesystemSandboxConfig(
            allowed_paths=[],
            blocked_patterns=["~/.ssh/**"],
            enforce=True,
        )
        sandbox = FilesystemSandbox(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Should succeed (no allowlist)
            result = sandbox.validate_path(tmpdir, "read")
            assert result.is_absolute()

    def test_enforce_false_logs_only(self):
        """Test that enforce=False logs violations but doesn't raise."""
        config = FilesystemSandboxConfig(
            allowed_paths=["/tmp"],
            blocked_patterns=[],
            enforce=False,  # Don't enforce, only log
        )
        sandbox = FilesystemSandbox(config)

        # Should succeed (only logs warning)
        result = sandbox.validate_path("/etc/passwd", "read")
        assert result == Path("/etc/passwd").resolve()

    def test_file_size_check_within_limit(self):
        """Test file size check passes for files under limit."""
        config = FilesystemSandboxConfig(max_file_size_mb=10, enforce=True)
        sandbox = FilesystemSandbox(config)

        # 5MB - should succeed
        sandbox.check_file_size(5 * 1024 * 1024)

    def test_file_size_check_exceeds_limit(self):
        """Test file size check fails for files over limit."""
        config = FilesystemSandboxConfig(max_file_size_mb=10, enforce=True)
        sandbox = FilesystemSandbox(config)

        # 15MB - should raise
        with pytest.raises(SandboxViolation, match="exceeds limit"):
            sandbox.check_file_size(15 * 1024 * 1024)

    def test_expanduser_in_paths(self):
        """Test that ~ is properly expanded in paths."""
        config = FilesystemSandboxConfig(
            allowed_paths=["~/test"],
            blocked_patterns=["~/.ssh/**"],
            enforce=True,
        )
        sandbox = FilesystemSandbox(config)

        # Paths should be expanded
        assert all(not str(p).startswith("~") for p in sandbox.allowed_paths)
        assert all(
            "~" not in pattern or Path(pattern.split("/**")[0]).expanduser()
            for pattern in sandbox.blocked_patterns
        )


class TestNetworkSandbox:
    """Test network sandbox isolation."""

    def test_allowed_domain_exact_match(self):
        """Test connection to allowed domain succeeds."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        # Should succeed (no exception)
        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            sandbox.validate_connection("example.com", 443, "https")

    def test_allowed_domain_wildcard(self):
        """Test connection to wildcard domain succeeds."""
        config = NetworkSandboxConfig(
            allowed_domains=["*.example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            # Should succeed
            sandbox.validate_connection("api.example.com", 443, "https")

    def test_disallowed_domain(self):
        """Test connection to disallowed domain fails."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        # Should raise
        with pytest.raises(SandboxViolation, match="not permitted"):
            sandbox.validate_connection("evil.com", 443, "https")

    def test_blocked_ip_range(self):
        """Test connection to blocked IP range fails."""
        config = NetworkSandboxConfig(
            allowed_domains=[],  # No domain restrictions
            blocked_ip_ranges=["192.168.0.0/16"],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            with pytest.raises(SandboxViolation, match="blocked"):
                sandbox.validate_connection("internal.local", 80, "http")

    def test_block_private_networks(self):
        """Test blocking private networks (10.x, 172.16.x, 192.168.x)."""
        config = NetworkSandboxConfig(
            allowed_domains=[],
            blocked_ip_ranges=[],
            block_private_networks=True,
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        # Test 10.x network
        with patch("socket.gethostbyname", return_value="10.0.0.1"):
            with pytest.raises(SandboxViolation, match="blocked"):
                sandbox.validate_connection("internal1.local", 80, "http")

        # Test 172.16.x network
        with patch("socket.gethostbyname", return_value="172.16.0.1"):
            with pytest.raises(SandboxViolation, match="blocked"):
                sandbox.validate_connection("internal2.local", 80, "http")

        # Test 192.168.x network
        with patch("socket.gethostbyname", return_value="192.168.0.1"):
            with pytest.raises(SandboxViolation, match="blocked"):
                sandbox.validate_connection("internal3.local", 80, "http")

    def test_loopback_allowed(self):
        """Test loopback connections are allowed when configured."""
        config = NetworkSandboxConfig(
            allowed_domains=[],
            blocked_ip_ranges=[],
            allow_loopback=True,
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            # Should succeed
            sandbox.validate_connection("localhost", 8080, "http")

    def test_loopback_blocked(self):
        """Test loopback connections are blocked when configured."""
        config = NetworkSandboxConfig(
            allowed_domains=[],
            blocked_ip_ranges=[],
            allow_loopback=False,
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            with pytest.raises(SandboxViolation, match="Loopback"):
                sandbox.validate_connection("localhost", 8080, "http")

    def test_dns_resolution_failure(self):
        """Test that DNS resolution failures are logged but don't raise."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        # Should not raise (DNS failure is logged as warning)
        with patch("socket.gethostbyname", side_effect=socket.gaierror("DNS failed")):
            sandbox.validate_connection("example.com", 443, "https")

    def test_validate_url(self):
        """Test URL validation extracts host and validates."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            # Should succeed
            sandbox.validate_url("https://example.com/path")

    def test_validate_url_blocked(self):
        """Test URL validation blocks disallowed domains."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=True,
        )
        sandbox = NetworkSandbox(config)

        # Should raise
        with pytest.raises(SandboxViolation, match="not permitted"):
            sandbox.validate_url("https://evil.com/path")

    def test_enforce_false_logs_only(self):
        """Test that enforce=False logs violations but doesn't raise."""
        config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            blocked_ip_ranges=[],
            enforce=False,
        )
        sandbox = NetworkSandbox(config)

        # Should succeed (only logs)
        sandbox.validate_connection("evil.com", 443, "https")


class TestResourceLimits:
    """Test resource limit enforcement."""

    def test_apply_limits(self):
        """Test applying resource limits to process."""
        config = ResourceLimitsConfig(
            max_memory_mb=512,
            max_cpu_seconds=60,
            max_file_descriptors=128,
            max_file_size_mb=50,
            enforce=True,
        )
        limits = ResourceLimits(config)

        # Should not raise (might log warnings on some platforms)
        limits.apply()

    def test_apply_limits_enforce_false(self):
        """Test that enforce=False doesn't apply limits."""
        config = ResourceLimitsConfig(
            max_memory_mb=512,
            max_cpu_seconds=60,
            max_file_descriptors=128,
            enforce=False,
        )
        limits = ResourceLimits(config)

        # Should succeed without applying limits
        limits.apply()

    def test_get_current_usage(self):
        """Test getting current resource usage."""
        config = ResourceLimitsConfig(enforce=True)
        limits = ResourceLimits(config)

        usage = limits.get_current_usage()

        # Should return dict with keys
        assert "cpu_time_seconds" in usage
        assert "memory_mb" in usage
        assert "file_descriptors" in usage

        # CPU time should be non-negative
        assert usage["cpu_time_seconds"] >= 0


class TestSandboxManager:
    """Test sandbox manager coordination."""

    def test_manager_with_all_sandboxes(self):
        """Test manager coordinates all sandbox types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs_config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                enforce=True,
            )
            filesystem = FilesystemSandbox(fs_config)

            net_config = NetworkSandboxConfig(
                allowed_domains=["example.com"],
                enforce=True,
            )
            network = NetworkSandbox(net_config)

            res_config = ResourceLimitsConfig(enforce=True)
            resources = ResourceLimits(res_config)

            manager = SandboxManager(
                filesystem=filesystem,
                network=network,
                resources=resources,
            )

            # Verify all components are present
            assert manager.filesystem is not None
            assert manager.network is not None
            assert manager.resources is not None

    def test_manager_with_partial_sandboxes(self):
        """Test manager works with only some sandboxes enabled."""
        # Only filesystem sandbox
        fs_config = FilesystemSandboxConfig(
            allowed_paths=["/tmp"],
            enforce=True,
        )
        filesystem = FilesystemSandbox(fs_config)

        manager = SandboxManager(filesystem=filesystem)

        assert manager.filesystem is not None
        assert manager.network is None
        assert manager.resources is None

    def test_validate_file_operation(self):
        """Test file operation validation through manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs_config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=[],  # Clear default blocked patterns for test
                enforce=True,
            )
            filesystem = FilesystemSandbox(fs_config)
            manager = SandboxManager(filesystem=filesystem)

            # Should succeed
            test_path = Path(tmpdir) / "test.txt"
            result = manager.validate_file_operation(test_path, "write")
            assert result.is_absolute()

            # Should fail
            with pytest.raises(SandboxViolation):
                manager.validate_file_operation("/etc/passwd", "read")

    def test_validate_file_operation_no_filesystem_sandbox(self):
        """Test file operation validation with no filesystem sandbox."""
        manager = SandboxManager()

        # Should succeed (no sandbox = allow)
        result = manager.validate_file_operation("/etc/passwd", "read")
        assert result.is_absolute()

    def test_validate_network_connection(self):
        """Test network connection validation through manager."""
        net_config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            enforce=True,
        )
        network = NetworkSandbox(net_config)
        manager = SandboxManager(network=network)

        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            # Should succeed
            manager.validate_network_connection("example.com", 443)

        # Should fail
        with pytest.raises(SandboxViolation):
            manager.validate_network_connection("evil.com", 443)

    def test_validate_network_connection_no_network_sandbox(self):
        """Test network connection validation with no network sandbox."""
        manager = SandboxManager()

        # Should succeed (no sandbox = allow)
        manager.validate_network_connection("anything.com", 443)

    def test_validate_url(self):
        """Test URL validation through manager."""
        net_config = NetworkSandboxConfig(
            allowed_domains=["example.com"],
            enforce=True,
        )
        network = NetworkSandbox(net_config)
        manager = SandboxManager(network=network)

        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            # Should succeed
            manager.validate_url("https://example.com/path")

        # Should fail
        with pytest.raises(SandboxViolation):
            manager.validate_url("https://evil.com/path")

    def test_validate_url_no_network_sandbox(self):
        """Test URL validation with no network sandbox."""
        manager = SandboxManager()

        # Should succeed (no sandbox = allow)
        manager.validate_url("https://anything.com/path")

    def test_apply_resource_limits(self):
        """Test applying resource limits through manager."""
        res_config = ResourceLimitsConfig(
            max_memory_mb=512,
            max_cpu_seconds=60,
            enforce=True,
        )
        resources = ResourceLimits(res_config)
        manager = SandboxManager(resources=resources)

        # Should not raise
        manager.apply_resource_limits()

    def test_apply_resource_limits_no_resources(self):
        """Test applying resource limits with no resource sandbox."""
        manager = SandboxManager()

        # Should succeed (no-op)
        manager.apply_resource_limits()

    def test_get_status(self):
        """Test getting sandbox status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs_config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                enforce=True,
            )
            filesystem = FilesystemSandbox(fs_config)

            net_config = NetworkSandboxConfig(
                allowed_domains=["example.com"],
                enforce=True,
            )
            network = NetworkSandbox(net_config)

            res_config = ResourceLimitsConfig(enforce=True)
            resources = ResourceLimits(res_config)

            manager = SandboxManager(
                filesystem=filesystem,
                network=network,
                resources=resources,
            )

            status = manager.get_status()

            # Check structure
            assert "enabled" in status
            assert status["enabled"]["filesystem"] is True
            assert status["enabled"]["network"] is True
            assert status["enabled"]["resources"] is True
            assert "resource_usage" in status

    def test_get_status_partial_sandboxes(self):
        """Test status with only some sandboxes enabled."""
        fs_config = FilesystemSandboxConfig(
            allowed_paths=["/tmp"],
            enforce=True,
        )
        filesystem = FilesystemSandbox(fs_config)

        manager = SandboxManager(filesystem=filesystem)

        status = manager.get_status()

        assert status["enabled"]["filesystem"] is True
        assert status["enabled"]["network"] is False
        assert status["enabled"]["resources"] is False
        assert "resource_usage" not in status


class TestSandboxIntegration:
    """Integration tests combining multiple sandbox components."""

    def test_defense_in_depth(self):
        """Test multiple sandboxes working together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create restrictive sandbox
            fs_config = FilesystemSandboxConfig(
                allowed_paths=[tmpdir],
                blocked_patterns=["**/.ssh/**"],
                enforce=True,
            )
            filesystem = FilesystemSandbox(fs_config)

            net_config = NetworkSandboxConfig(
                allowed_domains=["api.example.com"],
                block_private_networks=True,
                enforce=True,
            )
            network = NetworkSandbox(net_config)

            res_config = ResourceLimitsConfig(
                max_memory_mb=256,
                max_cpu_seconds=30,
                enforce=True,
            )
            resources = ResourceLimits(res_config)

            manager = SandboxManager(
                filesystem=filesystem,
                network=network,
                resources=resources,
            )

            # Apply resource limits
            manager.apply_resource_limits()

            # Valid file operation should succeed
            valid_path = Path(tmpdir) / "data.txt"
            result = manager.validate_file_operation(valid_path, "write")
            assert result.is_absolute()

            # Blocked file operation should fail
            with pytest.raises(SandboxViolation):
                manager.validate_file_operation("~/.ssh/id_rsa", "read")

            # Valid network connection should succeed
            with patch("socket.gethostbyname", return_value="93.184.216.34"):
                manager.validate_network_connection("api.example.com", 443)

            # Invalid network connection should fail
            with pytest.raises(SandboxViolation):
                manager.validate_url("https://evil.com/malware")

            # Private network should fail
            with patch("socket.gethostbyname", return_value="10.0.0.1"):
                with pytest.raises(SandboxViolation):
                    manager.validate_network_connection("internal.corp", 80)

    def test_permissive_mode(self):
        """Test permissive sandbox configuration."""
        # Permissive: Only resource limits, no file/network restrictions
        res_config = ResourceLimitsConfig(
            max_memory_mb=2048,
            max_cpu_seconds=600,
            enforce=True,
        )
        resources = ResourceLimits(res_config)

        manager = SandboxManager(resources=resources)

        # File operations allowed (no filesystem sandbox)
        result = manager.validate_file_operation("/any/path", "read")
        assert result.is_absolute()

        # Network connections allowed (no network sandbox)
        manager.validate_network_connection("any-domain.com", 443)

        # But resource limits still applied
        manager.apply_resource_limits()
        status = manager.get_status()
        assert "resource_usage" in status
