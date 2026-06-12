"""Sandboxing and isolation for agent execution.

Provides OS-level enforcement to complement policy-based access control.
This creates a defense-in-depth security model where:
1. SecurityPolicy defines intent (what SHOULD be allowed)
2. Sandbox enforces limits (what CAN be done at OS level)

Phase 1: Basic Isolation
- Filesystem sandbox (path validation)
- Network sandbox (domain/IP filtering)
- Resource limits (CPU, memory, file descriptors)
"""

from __future__ import annotations

import fnmatch
import ipaddress
import logging
import resource
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SandboxViolation(Exception):
    """Raised when sandbox detects unauthorized operation."""

    pass


@dataclass
class FilesystemSandboxConfig:
    """Filesystem sandbox configuration."""

    allowed_paths: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(
        default_factory=lambda: [
            "/etc/**",
            "/var/**",
            "/usr/**",
            "/boot/**",
            "~/.ssh/**",
            "~/.gnupg/**",
            "~/.aws/**",
            "~/.config/**",
        ]
    )
    max_file_size_mb: int = 100
    enforce: bool = True  # If False, only log violations


@dataclass
class NetworkSandboxConfig:
    """Network sandbox configuration."""

    allowed_domains: list[str] = field(default_factory=list)
    blocked_ip_ranges: list[str] = field(
        default_factory=lambda: [
            "169.254.0.0/16",  # Link-local
        ]
    )
    block_private_networks: bool = False  # Block 10.x, 172.16.x, 192.168.x
    allow_loopback: bool = True  # Allow 127.0.0.1
    enforce: bool = True


@dataclass
class ResourceLimitsConfig:
    """Resource limit configuration."""

    max_memory_mb: int = 1024  # 1GB
    max_cpu_seconds: int = 300  # 5 minutes
    max_file_descriptors: int = 256
    max_file_size_mb: int = 100
    enforce: bool = True


class FilesystemSandbox:
    """Restricts agent filesystem access.

    Validates all file operations against allowed paths and blocked patterns.
    Works in conjunction with SecurityPolicy for defense-in-depth.
    """

    def __init__(self, config: FilesystemSandboxConfig):
        """Initialize filesystem sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config

        # Resolve and normalize paths
        self.allowed_paths = [Path(p).expanduser().resolve() for p in config.allowed_paths]

        # Pre-compile patterns for performance
        self.blocked_patterns = config.blocked_patterns

        logger.info(
            f"Filesystem sandbox initialized: {len(self.allowed_paths)} allowed paths, "
            f"{len(self.blocked_patterns)} blocked patterns, "
            f"enforce={config.enforce}"
        )

    def validate_path(self, path: str | Path, operation: str = "access") -> Path:
        """Validate path is accessible by sandbox.

        Args:
            path: Path to validate
            operation: Operation type (for logging): 'read', 'write', 'execute'

        Returns:
            Resolved path if valid

        Raises:
            SandboxViolation: If path is not allowed
        """
        try:
            resolved = Path(path).expanduser().resolve()
        except Exception as e:
            raise SandboxViolation(f"Invalid path '{path}': {e}")

        # Check blocked patterns first (highest priority)
        for pattern in self.blocked_patterns:
            pattern_path = Path(pattern).expanduser()
            pattern_str = str(pattern_path)

            # Handle ** (recursive match)
            if "**" in pattern_str:
                # Convert to parent directory check
                parent = pattern_str.split("/**")[0]
                parent_path = Path(parent).resolve()
                try:
                    if resolved.is_relative_to(parent_path):
                        msg = f"Access to '{path}' blocked by pattern '{pattern}'"
                        if self.config.enforce:
                            raise SandboxViolation(msg)
                        else:
                            logger.warning(f"Sandbox violation (not enforced): {msg}")
                            return resolved
                except ValueError:
                    # Not relative to parent
                    pass

            # Handle * (single-level wildcard)
            elif "*" in pattern_str:
                # Resolve the directory part of the pattern to handle symlinks
                pattern_parts = pattern_str.split("/")
                # Find the first part with a wildcard
                non_wild_parts = []
                wild_parts = []
                found_wildcard = False
                for part in pattern_parts:
                    if not found_wildcard and "*" not in part:
                        non_wild_parts.append(part)
                    else:
                        found_wildcard = True
                        wild_parts.append(part)

                # Resolve the non-wildcard part and reconstruct pattern
                if non_wild_parts:
                    base_path = Path("/".join(non_wild_parts)).resolve()
                    resolved_pattern = str(base_path) + "/" + "/".join(wild_parts)
                else:
                    resolved_pattern = pattern_str

                if fnmatch.fnmatch(str(resolved), resolved_pattern):
                    msg = f"Access to '{path}' blocked by pattern '{pattern}'"
                    if self.config.enforce:
                        raise SandboxViolation(msg)
                    else:
                        logger.warning(f"Sandbox violation (not enforced): {msg}")
                        return resolved

            # Exact path match
            else:
                try:
                    pattern_resolved = pattern_path.resolve()
                    if resolved == pattern_resolved or resolved.is_relative_to(pattern_resolved):
                        msg = f"Access to '{path}' is explicitly blocked"
                        if self.config.enforce:
                            raise SandboxViolation(msg)
                        else:
                            logger.warning(f"Sandbox violation (not enforced): {msg}")
                            return resolved
                except ValueError:
                    pass

        # Check if within allowed paths
        if not self.allowed_paths:
            # No allowed paths configured - allow everything not blocked
            logger.debug(f"Path '{path}' allowed (no allowlist configured)")
            return resolved

        for allowed in self.allowed_paths:
            try:
                if resolved.is_relative_to(allowed):
                    logger.debug(f"Path '{path}' allowed (within {allowed})")
                    return resolved
            except ValueError:
                # Not relative to this allowed path
                continue

        # Not in any allowed path
        msg = (
            f"Access to '{path}' not permitted. "
            f"Allowed paths: {', '.join(str(p) for p in self.allowed_paths)}"
        )
        if self.config.enforce:
            raise SandboxViolation(msg)
        else:
            logger.warning(f"Sandbox violation (not enforced): {msg}")
            return resolved

    def check_file_size(self, size_bytes: int) -> None:
        """Check if file size is within limits.

        Args:
            size_bytes: File size in bytes

        Raises:
            SandboxViolation: If file exceeds size limit
        """
        max_bytes = self.config.max_file_size_mb * 1024 * 1024

        if size_bytes > max_bytes:
            msg = (
                f"File size {size_bytes / 1024 / 1024:.2f}MB exceeds limit "
                f"of {self.config.max_file_size_mb}MB"
            )
            if self.config.enforce:
                raise SandboxViolation(msg)
            else:
                logger.warning(f"Sandbox violation (not enforced): {msg}")


class NetworkSandbox:
    """Restricts agent network access.

    Validates network connections against domain allowlists and IP blocklists.
    Works in conjunction with SecurityPolicy for defense-in-depth.
    """

    def __init__(self, config: NetworkSandboxConfig):
        """Initialize network sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config

        # Parse IP ranges
        self.blocked_networks = [ipaddress.ip_network(cidr) for cidr in config.blocked_ip_ranges]

        if config.block_private_networks:
            self.blocked_networks.extend(
                [
                    ipaddress.ip_network("10.0.0.0/8"),
                    ipaddress.ip_network("172.16.0.0/12"),
                    ipaddress.ip_network("192.168.0.0/16"),
                ]
            )

        logger.info(
            f"Network sandbox initialized: {len(config.allowed_domains)} allowed domains, "
            f"{len(self.blocked_networks)} blocked networks, "
            f"enforce={config.enforce}"
        )

    def validate_connection(
        self, host: str, port: int | None = None, protocol: str = "tcp"
    ) -> None:
        """Validate network connection is allowed.

        Args:
            host: Hostname or IP address
            port: Port number (optional)
            protocol: Protocol type (for logging)

        Raises:
            SandboxViolation: If connection is not allowed
        """
        # Check domain allowlist (if configured)
        if self.config.allowed_domains:
            allowed = any(
                host.endswith(domain) or fnmatch.fnmatch(host, domain)
                for domain in self.config.allowed_domains
            )

            if not allowed:
                msg = (
                    f"Connection to '{host}' not permitted. "
                    f"Allowed domains: {', '.join(self.config.allowed_domains)}"
                )
                if self.config.enforce:
                    raise SandboxViolation(msg)
                else:
                    logger.warning(f"Sandbox violation (not enforced): {msg}")
                    return

        # Resolve to IP and check blocklists
        try:
            ip_str = socket.gethostbyname(host)
            ip = ipaddress.ip_address(ip_str)

            # Check loopback
            if ip.is_loopback and not self.config.allow_loopback:
                msg = f"Loopback connections not allowed: {host} ({ip})"
                if self.config.enforce:
                    raise SandboxViolation(msg)
                else:
                    logger.warning(f"Sandbox violation (not enforced): {msg}")
                    return

            # Check blocked networks
            for network in self.blocked_networks:
                if ip in network:
                    msg = f"Connection to {host} ({ip}) blocked (in network {network})"
                    if self.config.enforce:
                        raise SandboxViolation(msg)
                    else:
                        logger.warning(f"Sandbox violation (not enforced): {msg}")
                        return

        except socket.gaierror as e:
            # DNS resolution failed - allow but log
            logger.warning(f"Could not resolve {host} for IP validation: {e}")

        logger.debug(f"Connection to {host}:{port} allowed")

    def validate_url(self, url: str) -> None:
        """Validate URL is allowed.

        Args:
            url: URL to validate

        Raises:
            SandboxViolation: If URL is not allowed
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.netloc:
            # Extract host and port
            host = parsed.hostname or parsed.netloc
            port = parsed.port

            self.validate_connection(host, port, parsed.scheme)


class ResourceLimits:
    """Enforces resource limits on agent process.

    Uses OS-level rlimit to restrict CPU, memory, and file descriptors.
    Platform-specific (works best on Unix-like systems).
    """

    def __init__(self, config: ResourceLimitsConfig):
        """Initialize resource limits.

        Args:
            config: Resource limit configuration
        """
        self.config = config

        logger.info(
            f"Resource limits initialized: "
            f"memory={config.max_memory_mb}MB, "
            f"cpu={config.max_cpu_seconds}s, "
            f"fds={config.max_file_descriptors}, "
            f"enforce={config.enforce}"
        )

    def apply(self) -> None:
        """Apply resource limits to current process.

        Note: Should be called early in process initialization.
        Some limits may require elevated privileges to set.
        """
        if not self.config.enforce:
            logger.info("Resource limits configured but not enforced")
            return

        try:
            # Memory limit (address space)
            max_memory = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
            logger.info(f"Set memory limit: {self.config.max_memory_mb}MB")

        except (ValueError, OSError) as e:
            logger.warning(f"Could not set memory limit: {e}")

        try:
            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU, (self.config.max_cpu_seconds, self.config.max_cpu_seconds)
            )
            logger.info(f"Set CPU time limit: {self.config.max_cpu_seconds}s")

        except (ValueError, OSError) as e:
            logger.warning(f"Could not set CPU limit: {e}")

        try:
            # File descriptor limit
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.config.max_file_descriptors, self.config.max_file_descriptors),
            )
            logger.info(f"Set file descriptor limit: {self.config.max_file_descriptors}")

        except (ValueError, OSError) as e:
            logger.warning(f"Could not set file descriptor limit: {e}")

        try:
            # File size limit
            max_file_size = self.config.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (max_file_size, max_file_size))
            logger.info(f"Set file size limit: {self.config.max_file_size_mb}MB")

        except (ValueError, OSError) as e:
            logger.warning(f"Could not set file size limit: {e}")

    def get_current_usage(self) -> dict[str, Any]:
        """Get current resource usage.

        Returns:
            Dict with current usage statistics
        """
        usage = resource.getrusage(resource.RUSAGE_SELF)

        return {
            "cpu_time_seconds": usage.ru_utime + usage.ru_stime,
            "memory_mb": usage.ru_maxrss / 1024,  # Convert KB to MB (on Linux)
            "file_descriptors": self._count_open_fds(),
        }

    def _count_open_fds(self) -> int:
        """Count currently open file descriptors.

        Returns:
            Number of open file descriptors
        """
        try:
            # Linux/Unix: Count entries in /proc/self/fd
            fd_dir = Path("/proc/self/fd")
            if fd_dir.exists():
                return len(list(fd_dir.iterdir()))
        except Exception:
            pass

        # Fallback: Can't determine on this platform
        return -1


class SandboxManager:
    """Coordinates all sandbox components.

    Provides unified interface for filesystem, network, and resource sandboxing.
    """

    def __init__(
        self,
        filesystem: FilesystemSandbox | None = None,
        network: NetworkSandbox | None = None,
        resources: ResourceLimits | None = None,
    ):
        """Initialize sandbox manager.

        Args:
            filesystem: Filesystem sandbox (optional)
            network: Network sandbox (optional)
            resources: Resource limits (optional)
        """
        self.filesystem = filesystem
        self.network = network
        self.resources = resources

        logger.info(
            f"Sandbox manager initialized: "
            f"filesystem={'enabled' if filesystem else 'disabled'}, "
            f"network={'enabled' if network else 'disabled'}, "
            f"resources={'enabled' if resources else 'disabled'}"
        )

    def apply_resource_limits(self) -> None:
        """Apply resource limits (should be called early)."""
        if self.resources:
            self.resources.apply()

    def validate_file_operation(self, path: str | Path, operation: str = "access") -> Path:
        """Validate file operation.

        Args:
            path: File path
            operation: Operation type ('read', 'write', 'execute')

        Returns:
            Resolved path if allowed

        Raises:
            SandboxViolation: If operation not allowed
        """
        if self.filesystem:
            return self.filesystem.validate_path(path, operation)
        else:
            # No filesystem sandbox - allow
            return Path(path).expanduser().resolve()

    def validate_network_connection(self, host: str, port: int | None = None) -> None:
        """Validate network connection.

        Args:
            host: Hostname or IP
            port: Port number (optional)

        Raises:
            SandboxViolation: If connection not allowed
        """
        if self.network:
            self.network.validate_connection(host, port)

    def validate_url(self, url: str) -> None:
        """Validate URL access.

        Args:
            url: URL to validate

        Raises:
            SandboxViolation: If URL not allowed
        """
        if self.network:
            self.network.validate_url(url)

    def get_status(self) -> dict[str, Any]:
        """Get sandbox status and resource usage.

        Returns:
            Dict with sandbox status
        """
        status = {
            "enabled": {
                "filesystem": self.filesystem is not None,
                "network": self.network is not None,
                "resources": self.resources is not None,
            }
        }

        if self.resources:
            status["resource_usage"] = self.resources.get_current_usage()

        return status
