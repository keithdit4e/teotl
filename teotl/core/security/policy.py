"""Security policy definitions and loading.

Defines security policies for network access, filesystem operations,
tool usage, cost limits, and compliance requirements.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class PolicyMode(StrEnum):
    """Policy enforcement modes."""

    ALLOWLIST = "allowlist"  # Only explicitly allowed
    DENYLIST = "denylist"  # Block explicitly denied
    PERMISSIVE = "permissive"  # Allow everything
    RESTRICTED = "allowlist"  # Alias for ALLOWLIST (backward compatibility)


def _normalize_policy_mode(mode_str: str) -> str:
    """Normalize policy mode string for backward compatibility.

    Args:
        mode_str: Mode string from config

    Returns:
        Normalized mode string compatible with PolicyMode enum
    """
    # Map "restricted" to "allowlist" for backward compatibility
    if mode_str == "restricted":
        return "allowlist"
    return mode_str


@dataclass
class NetworkPolicy:
    """Network access policy."""

    mode: PolicyMode = PolicyMode.ALLOWLIST
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)

    def allows(self, domain: str) -> bool:
        """Check if domain is allowed by policy.

        Args:
            domain: Domain to check (e.g., "api.github.com")

        Returns:
            True if allowed, False otherwise
        """
        if self.mode == PolicyMode.PERMISSIVE:
            return True

        # Check blocklist first
        if self._matches_pattern(domain, self.blocked_domains):
            return False

        # Check allowlist
        if self.mode == PolicyMode.ALLOWLIST:
            return self._matches_pattern(domain, self.allowed_domains)

        # Denylist mode - allow if not blocked
        return True

    def requires_approval(self, domain: str) -> bool:
        """Check if domain requires user approval.

        Args:
            domain: Domain to check

        Returns:
            True if approval required
        """
        return self._matches_pattern(domain, self.require_approval)

    @staticmethod
    def _matches_pattern(domain: str, patterns: list[str]) -> bool:
        """Check if domain matches any pattern.

        Supports wildcards:
        - *.example.com matches api.example.com, www.example.com
        - example.* matches example.com, example.org
        """
        return any(fnmatch.fnmatch(domain, pattern) for pattern in patterns)


@dataclass
class FilesystemPolicy:
    """Filesystem access policy."""

    mode: PolicyMode = PolicyMode.RESTRICTED
    allowed_paths: list[str] = field(default_factory=list)
    readonly_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    max_file_size_mb: int = 10

    def allows(self, path: str, write: bool = False) -> bool:
        """Check if file operation is allowed.

        Args:
            path: File path to check
            write: True for write operations, False for read

        Returns:
            True if allowed, False otherwise
        """
        path = Path(path).expanduser().resolve()

        # Check blocklist first
        if self._matches_path(path, self.blocked_paths):
            return False

        # For write operations, check readonly list
        if write and self._matches_path(path, self.readonly_paths):
            return False

        # Check allowlist
        if self.mode == PolicyMode.RESTRICTED:
            # Must be in allowed paths
            allowed = self._matches_path(path, self.allowed_paths)
            # Or readonly (for read operations)
            if not write:
                allowed = allowed or self._matches_path(path, self.readonly_paths)
            return allowed

        # Permissive mode - allow if not blocked
        return True

    @staticmethod
    def _matches_path(path: Path, patterns: list[str]) -> bool:
        """Check if path matches any pattern.

        Supports:
        - Exact paths: /tmp/file.txt
        - Wildcards: /tmp/**/*.txt
        - Home dir: ~/.forge/**
        """
        for pattern in patterns:
            pattern_path = Path(pattern).expanduser().resolve()
            pattern_str = str(pattern_path)

            # Handle ** (recursive match)
            if "**" in pattern_str:
                regex = pattern_str.replace("**", ".*").replace("*", "[^/]*")
                if re.match(regex, str(path)):
                    return True
            # Handle * (single-level match)
            elif "*" in pattern_str:
                if fnmatch.fnmatch(str(path), pattern_str):
                    return True
            # Exact match
            elif path == pattern_path or path.is_relative_to(pattern_path):
                return True

        return False


@dataclass
class ToolPolicy:
    """Tool usage policy."""

    allowed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)

    def allows(self, tool_name: str) -> bool:
        """Check if tool is allowed.

        Args:
            tool_name: Name of tool to check

        Returns:
            True if allowed, False otherwise
        """
        # Check blocklist first
        if tool_name in self.blocked:
            return False

        # If allowlist is empty, allow all (except blocked)
        if not self.allowed:
            return True

        # Check allowlist
        return tool_name in self.allowed

    def requires_approval(self, tool_name: str) -> bool:
        """Check if tool requires approval.

        Args:
            tool_name: Name of tool to check

        Returns:
            True if approval required
        """
        return tool_name in self.require_approval


@dataclass
class CostLimits:
    """Cost limiting configuration."""

    max_per_hour: float = 5.0
    max_per_day: float = 50.0
    max_per_month: float = 500.0
    currency: str = "USD"


@dataclass
class RateLimits:
    """Rate limiting configuration."""

    max_api_calls_per_minute: int = 20
    max_tokens_per_hour: int = 100_000


@dataclass
class DataPrivacy:
    """Data privacy configuration."""

    redact_pii: bool = True
    encrypt_logs: bool = False
    retention_days: int = 90


@dataclass
class Compliance:
    """Compliance configuration."""

    gdpr_enabled: bool = False
    soc2_enabled: bool = False
    hipaa_enabled: bool = False


@dataclass
class SandboxConfig:
    """Sandbox configuration for OS-level enforcement."""

    enabled: bool = True  # Enable sandboxing
    filesystem_enabled: bool = True
    network_enabled: bool = True
    resources_enabled: bool = True

    # Filesystem sandbox
    allowed_paths: list[str] = field(default_factory=list)
    max_file_size_mb: int = 100

    # Network sandbox
    allowed_domains: list[str] = field(default_factory=list)
    block_private_networks: bool = False

    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_seconds: int = 300
    max_file_descriptors: int = 256


class LogLevel(StrEnum):
    """Audit log detail levels."""

    MINIMAL = "minimal"  # Only violations
    STANDARD = "standard"  # Violations + tool calls + costs
    DETAILED = "detailed"  # Standard + LLM prompts (PII redacted)
    PARANOID = "paranoid"  # Everything including full prompts


@dataclass
class SecurityPolicy:
    """Complete security policy for an agent.

    Loaded from security.yaml in agent workspace.
    """

    version: str = "1.0"
    agent_id: str = ""
    log_level: LogLevel = LogLevel.STANDARD

    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    filesystem: FilesystemPolicy = field(default_factory=FilesystemPolicy)
    tools: ToolPolicy = field(default_factory=ToolPolicy)
    cost_limits: CostLimits = field(default_factory=CostLimits)
    rate_limits: RateLimits = field(default_factory=RateLimits)
    data_privacy: DataPrivacy = field(default_factory=DataPrivacy)
    compliance: Compliance = field(default_factory=Compliance)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    @classmethod
    def from_file(cls, path: Path) -> SecurityPolicy:
        """Load policy from YAML file.

        Args:
            path: Path to security.yaml

        Returns:
            Loaded SecurityPolicy

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Security policy not found: {path}")

        with open(path) as f:
            config = yaml.safe_load(f)

        return cls.from_dict(config)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> SecurityPolicy:
        """Create policy from dict.

        Args:
            config: Policy configuration dict

        Returns:
            SecurityPolicy instance
        """
        return cls(
            version=config.get("version", "1.0"),
            agent_id=config.get("agent_id", ""),
            log_level=LogLevel(config.get("log_level", "standard")),
            network=NetworkPolicy(
                mode=PolicyMode(
                    _normalize_policy_mode(config.get("network", {}).get("mode", "allowlist"))
                ),
                allowed_domains=config.get("network", {}).get("allowed_domains", []),
                blocked_domains=config.get("network", {}).get("blocked_domains", []),
                require_approval=config.get("network", {}).get("require_approval", []),
            ),
            filesystem=FilesystemPolicy(
                mode=PolicyMode(
                    _normalize_policy_mode(config.get("filesystem", {}).get("mode", "allowlist"))
                ),
                allowed_paths=config.get("filesystem", {}).get("allowed_paths", []),
                readonly_paths=config.get("filesystem", {}).get("readonly_paths", []),
                blocked_paths=config.get("filesystem", {}).get("blocked_paths", []),
                max_file_size_mb=config.get("filesystem", {}).get("max_file_size_mb", 10),
            ),
            tools=ToolPolicy(
                allowed=config.get("tools", {}).get("allowed", []),
                blocked=config.get("tools", {}).get("blocked", []),
                require_approval=config.get("tools", {}).get("require_approval", []),
            ),
            cost_limits=CostLimits(
                max_per_hour=config.get("cost_limits", {}).get("max_per_hour", 5.0),
                max_per_day=config.get("cost_limits", {}).get("max_per_day", 50.0),
                max_per_month=config.get("cost_limits", {}).get("max_per_month", 500.0),
                currency=config.get("cost_limits", {}).get("currency", "USD"),
            ),
            rate_limits=RateLimits(
                max_api_calls_per_minute=config.get("rate_limits", {}).get(
                    "max_api_calls_per_minute", 20
                ),
                max_tokens_per_hour=config.get("rate_limits", {}).get(
                    "max_tokens_per_hour", 100_000
                ),
            ),
            data_privacy=DataPrivacy(
                redact_pii=config.get("data_privacy", {}).get("redact_pii", True),
                encrypt_logs=config.get("data_privacy", {}).get("encrypt_logs", False),
                retention_days=config.get("data_privacy", {}).get("retention_days", 90),
            ),
            compliance=Compliance(
                gdpr_enabled=config.get("compliance", {}).get("gdpr_enabled", False),
                soc2_enabled=config.get("compliance", {}).get("soc2_enabled", False),
                hipaa_enabled=config.get("compliance", {}).get("hipaa_enabled", False),
            ),
            sandbox=SandboxConfig(
                enabled=config.get("sandbox", {}).get("enabled", True),
                filesystem_enabled=config.get("sandbox", {}).get("filesystem_enabled", True),
                network_enabled=config.get("sandbox", {}).get("network_enabled", True),
                resources_enabled=config.get("sandbox", {}).get("resources_enabled", True),
                allowed_paths=config.get("sandbox", {}).get("allowed_paths", []),
                max_file_size_mb=config.get("sandbox", {}).get("max_file_size_mb", 100),
                allowed_domains=config.get("sandbox", {}).get("allowed_domains", []),
                block_private_networks=config.get("sandbox", {}).get(
                    "block_private_networks", False
                ),
                max_memory_mb=config.get("sandbox", {}).get("max_memory_mb", 1024),
                max_cpu_seconds=config.get("sandbox", {}).get("max_cpu_seconds", 300),
                max_file_descriptors=config.get("sandbox", {}).get("max_file_descriptors", 256),
            ),
        )

    @classmethod
    def create_default(cls, agent_id: str, preset: str = "moderate") -> SecurityPolicy:
        """Create default policy with preset.

        Args:
            agent_id: Agent ID for policy
            preset: Security preset (strict, moderate, permissive, autonomous-dev)

        Returns:
            SecurityPolicy with preset configuration
        """
        if preset == "strict":
            return cls._create_strict(agent_id)
        elif preset == "moderate":
            return cls._create_moderate(agent_id)
        elif preset == "permissive":
            return cls._create_permissive(agent_id)
        elif preset == "autonomous-dev":
            return cls._create_autonomous_dev(agent_id)
        else:
            raise ValueError(f"Unknown preset: {preset}")

    @classmethod
    def _create_strict(cls, agent_id: str) -> SecurityPolicy:
        """Create strict security policy."""
        return cls(
            agent_id=agent_id,
            log_level=LogLevel.DETAILED,
            network=NetworkPolicy(
                mode=PolicyMode.ALLOWLIST,
                allowed_domains=["*.anthropic.com", "*.openai.com"],
            ),
            filesystem=FilesystemPolicy(
                mode=PolicyMode.RESTRICTED,
                allowed_paths=[f"~/.forge/agents/{agent_id}/**", "/tmp/**"],
                blocked_paths=["~/.ssh/**", "~/.aws/**", "/etc/**", "~/.config/**"],
            ),
            tools=ToolPolicy(
                allowed=["read_file", "write_file", "list_directory"],
                blocked=["execute_shell", "run_command"],
            ),
            cost_limits=CostLimits(max_per_hour=1.0, max_per_day=10.0),
            sandbox=SandboxConfig(
                enabled=True,
                allowed_paths=[f"~/.forge/agents/{agent_id}/**", "/tmp/**"],
                allowed_domains=["*.anthropic.com", "*.openai.com"],
                max_memory_mb=512,  # Lower memory limit for strict
                max_cpu_seconds=180,  # 3 minutes
            ),
        )

    @classmethod
    def _create_moderate(cls, agent_id: str) -> SecurityPolicy:
        """Create moderate security policy (recommended)."""
        return cls(
            agent_id=agent_id,
            log_level=LogLevel.STANDARD,
            network=NetworkPolicy(
                mode=PolicyMode.ALLOWLIST,
                allowed_domains=[
                    "*.anthropic.com",
                    "*.openai.com",
                    "api.github.com",
                    "*.google.com",
                    "*.wikipedia.org",
                ],
            ),
            filesystem=FilesystemPolicy(
                mode=PolicyMode.RESTRICTED,
                allowed_paths=[f"~/.forge/agents/{agent_id}/**", "/tmp/**"],
                readonly_paths=["~/Documents/**"],
                blocked_paths=["~/.ssh/**", "~/.aws/**", "/etc/**"],
            ),
            tools=ToolPolicy(
                allowed=["read_file", "write_file", "web_search", "list_directory"],
                blocked=["execute_shell"],
            ),
            cost_limits=CostLimits(max_per_hour=5.0, max_per_day=50.0),
            sandbox=SandboxConfig(
                enabled=True,
                allowed_paths=[f"~/.forge/agents/{agent_id}/**", "/tmp/**", "~/Documents/**"],
                allowed_domains=[
                    "*.anthropic.com",
                    "*.openai.com",
                    "api.github.com",
                    "*.google.com",
                    "*.wikipedia.org",
                ],
                max_memory_mb=1024,  # 1GB
                max_cpu_seconds=300,  # 5 minutes
            ),
        )

    @classmethod
    def _create_permissive(cls, agent_id: str) -> SecurityPolicy:
        """Create permissive security policy."""
        return cls(
            agent_id=agent_id,
            log_level=LogLevel.MINIMAL,
            network=NetworkPolicy(mode=PolicyMode.PERMISSIVE),
            filesystem=FilesystemPolicy(
                mode=PolicyMode.PERMISSIVE,
                blocked_paths=["~/.ssh/**", "~/.aws/**"],  # Still block sensitive paths
            ),
            tools=ToolPolicy(
                blocked=["execute_shell"],  # Still block dangerous tools
            ),
            cost_limits=CostLimits(max_per_hour=10.0, max_per_day=100.0),
            sandbox=SandboxConfig(
                enabled=True,
                filesystem_enabled=False,  # Less restrictive
                network_enabled=False,  # Less restrictive
                resources_enabled=True,  # Still limit resources
                max_memory_mb=2048,  # 2GB
                max_cpu_seconds=600,  # 10 minutes
            ),
        )

    @classmethod
    def _create_autonomous_dev(cls, agent_id: str) -> SecurityPolicy:
        """Create autonomous development security policy.

        Designed for autonomous development agents that:
        - Commit code changes automatically
        - Run tests and iterate
        - Work without human confirmation

        Safety guarantees:
        - Tests must pass before commit
        - No force push allowed
        - Full audit trail
        - Scoped to workspace directory
        - Extended timeouts for test execution
        """
        return cls(
            agent_id=agent_id,
            log_level=LogLevel.DETAILED,
            network=NetworkPolicy(
                mode=PolicyMode.ALLOWLIST,
                allowed_domains=["*.anthropic.com", "*.openai.com"],
            ),
            filesystem=FilesystemPolicy(
                mode=PolicyMode.RESTRICTED,
                allowed_paths=[
                    f"~/.forge/agents/{agent_id}/**",
                    "~/Documents/**",
                    "~/workspace/**",
                ],
                blocked_paths=[
                    "~/.ssh/**",
                    "~/.aws/**",
                    "/etc/**",
                    "**/*secret*",
                    "**/*credential*",
                ],
            ),
            tools=ToolPolicy(
                allowed=["read_file", "write_file", "execute_shell", "git"],
                blocked=[],  # Autonomous needs full tool access
            ),
            cost_limits=CostLimits(max_per_hour=5.0, max_per_day=25.0),
            sandbox=SandboxConfig(
                enabled=True,
                allowed_paths=[
                    f"~/.forge/agents/{agent_id}/**",
                    "~/Documents/**",
                    "~/workspace/**",
                ],
                allowed_domains=["*.anthropic.com", "*.openai.com"],
                max_memory_mb=1024,
                max_cpu_seconds=600,  # 10 minutes for test execution
            ),
        )

    def to_yaml(self, path: Path) -> None:
        """Save policy to YAML file.

        Args:
            path: Path to write security.yaml
        """
        config = {
            "version": self.version,
            "agent_id": self.agent_id,
            "log_level": self.log_level.value,
            "network": {
                "mode": self.network.mode.value,
                "allowed_domains": self.network.allowed_domains,
                "blocked_domains": self.network.blocked_domains,
                "require_approval": self.network.require_approval,
            },
            "filesystem": {
                "mode": self.filesystem.mode.value,
                "allowed_paths": self.filesystem.allowed_paths,
                "readonly_paths": self.filesystem.readonly_paths,
                "blocked_paths": self.filesystem.blocked_paths,
                "max_file_size_mb": self.filesystem.max_file_size_mb,
            },
            "tools": {
                "allowed": self.tools.allowed,
                "blocked": self.tools.blocked,
                "require_approval": self.tools.require_approval,
            },
            "cost_limits": {
                "max_per_hour": self.cost_limits.max_per_hour,
                "max_per_day": self.cost_limits.max_per_day,
                "max_per_month": self.cost_limits.max_per_month,
                "currency": self.cost_limits.currency,
            },
            "rate_limits": {
                "max_api_calls_per_minute": self.rate_limits.max_api_calls_per_minute,
                "max_tokens_per_hour": self.rate_limits.max_tokens_per_hour,
            },
            "data_privacy": {
                "redact_pii": self.data_privacy.redact_pii,
                "encrypt_logs": self.data_privacy.encrypt_logs,
                "retention_days": self.data_privacy.retention_days,
            },
            "compliance": {
                "gdpr_enabled": self.compliance.gdpr_enabled,
                "soc2_enabled": self.compliance.soc2_enabled,
                "hipaa_enabled": self.compliance.hipaa_enabled,
            },
            "sandbox": {
                "enabled": self.sandbox.enabled,
                "filesystem_enabled": self.sandbox.filesystem_enabled,
                "network_enabled": self.sandbox.network_enabled,
                "resources_enabled": self.sandbox.resources_enabled,
                "allowed_paths": self.sandbox.allowed_paths,
                "max_file_size_mb": self.sandbox.max_file_size_mb,
                "allowed_domains": self.sandbox.allowed_domains,
                "block_private_networks": self.sandbox.block_private_networks,
                "max_memory_mb": self.sandbox.max_memory_mb,
                "max_cpu_seconds": self.sandbox.max_cpu_seconds,
                "max_file_descriptors": self.sandbox.max_file_descriptors,
            },
        }

        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
