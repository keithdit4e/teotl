"""Runtime security enforcement.

Enforces security policies at runtime by checking all tool calls,
network requests, and file operations against configured policies.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from teotl.core.security.audit import AuditLogger
from teotl.core.security.cost_tracker import CostTracker, RateLimiter
from teotl.core.security.policy import SecurityPolicy
from teotl.core.security.sandbox import SandboxManager, SandboxViolation

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security policy blocks an operation."""

    pass


class SecurityEnforcer:
    """Enforces security policies at runtime.

    Checks tool calls against network, filesystem, tool, cost, and rate policies.
    Logs all security events for compliance.
    """

    # Estimated costs for common tools (USD)
    TOOL_COSTS = {
        "web_search": 0.001,
        "fetch_url": 0.0005,
        "read_file": 0.0,
        "write_file": 0.0,
        "list_directory": 0.0,
        "llm_call": 0.01,  # Varies by model
    }

    def __init__(
        self,
        policy: SecurityPolicy,
        workspace_dir: Path,
        sandbox: SandboxManager | None = None,
    ):
        """Initialize security enforcer.

        Args:
            policy: Security policy to enforce
            workspace_dir: Agent workspace directory
            sandbox: Sandbox manager for OS-level enforcement (optional)
        """
        self.policy = policy
        self.workspace_dir = workspace_dir
        self.sandbox = sandbox

        # Initialize audit logger
        self.audit = AuditLogger(policy, workspace_dir)

        # Initialize cost and rate tracking
        cost_file = workspace_dir / "security" / "costs.json"
        self.cost_tracker = CostTracker(policy.cost_limits, cost_file)
        self.rate_limiter = RateLimiter(policy.rate_limits)

        # Apply resource limits if sandbox enabled
        if self.sandbox:
            self.sandbox.apply_resource_limits()

        logger.info(f"Security enforcer initialized for agent: {policy.agent_id}")
        logger.info(
            f"Policy mode - Network: {policy.network.mode}, Filesystem: {policy.filesystem.mode}"
        )
        logger.info(f"Sandbox: {'enabled' if sandbox else 'disabled'}")

    async def enforce_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Check if tool call is allowed by policy.

        Args:
            tool_name: Name of tool being called
            args: Tool arguments

        Returns:
            (allowed, reason_if_blocked)
        """
        # 1. Check tool policy
        if not self.policy.tools.allows(tool_name):
            reason = f"Tool '{tool_name}' is blocked by security policy"
            await self.audit.log_violation("tool", tool_name, reason)
            logger.warning(f"Blocked tool call: {reason}")
            return False, reason

        # 2. Check network policy (for network tools)
        if tool_name in ["web_search", "fetch_url", "http_request"]:
            domain = self._extract_domain(args)
            if domain and not self.policy.network.allows(domain):
                reason = f"Domain '{domain}' is blocked by network policy"
                await self.audit.log_violation("network", domain, reason)
                logger.warning(f"Blocked network access: {reason}")
                return False, reason

        # 3. Check filesystem policy (for file tools)
        if tool_name in ["read_file", "write_file", "delete_file"]:
            path = args.get("path") or args.get("file_path") or args.get("filename")
            if path:
                is_write = tool_name in ["write_file", "delete_file"]
                if not self.policy.filesystem.allows(path, write=is_write):
                    reason = f"Path '{path}' is blocked by filesystem policy"
                    await self.audit.log_violation("filesystem", path, reason)
                    logger.warning(f"Blocked filesystem access: {reason}")
                    return False, reason

        # 4. Check cost limits
        estimated_cost = self._estimate_cost(tool_name, args)
        if not self.cost_tracker.would_allow(estimated_cost):
            remaining = self.cost_tracker.get_remaining()
            reason = f"Cost limit exceeded. Remaining: hourly=${remaining['hourly']:.2f}, daily=${remaining['daily']:.2f}"
            await self.audit.log_cost_limit(
                "combined",
                self.cost_tracker.current_hour,
                self.policy.cost_limits.max_per_hour,
                tool_name,
            )
            logger.warning(f"Blocked due to cost limit: {reason}")
            return False, reason

        # 5. Check rate limits
        if not self.rate_limiter.would_allow():
            current_rate = self.rate_limiter.get_current_rate()
            reason = f"Rate limit exceeded: {current_rate} calls/min (limit: {self.policy.rate_limits.max_api_calls_per_minute})"
            await self.audit.log_rate_limit(
                "per_minute",
                current_rate,
                self.policy.rate_limits.max_api_calls_per_minute,
                tool_name,
            )
            logger.warning(f"Blocked due to rate limit: {reason}")
            return False, reason

        # 6. Sandbox enforcement (OS-level validation)
        if self.sandbox:
            try:
                # Filesystem sandbox check
                if tool_name in ["read_file", "write_file", "delete_file"]:
                    path = args.get("path") or args.get("file_path") or args.get("filename")
                    if path:
                        operation = (
                            "write" if tool_name in ["write_file", "delete_file"] else "read"
                        )
                        self.sandbox.validate_file_operation(path, operation)

                # Network sandbox check
                if tool_name in ["web_search", "fetch_url", "http_request"]:
                    # Try URL first
                    url = args.get("url")
                    if url:
                        self.sandbox.validate_url(url)
                    else:
                        # Try domain/host
                        domain = self._extract_domain(args)
                        if domain:
                            self.sandbox.validate_network_connection(domain)

            except SandboxViolation as e:
                reason = f"Sandbox violation: {e}"
                await self.audit.log_violation("sandbox", tool_name, reason)
                logger.warning(f"Blocked by sandbox: {reason}")
                return False, reason

        # All checks passed
        await self.audit.log_tool_call(
            tool_name,
            args,
            allowed=True,
            cost=estimated_cost,
        )

        logger.debug(f"Allowed tool call: {tool_name}")
        return True, None

    async def record_execution(
        self,
        tool_name: str,
        result: Any,
        duration_ms: int,
        actual_cost: float | None = None,
        tokens_used: int | None = None,
    ) -> None:
        """Record successful tool execution.

        Args:
            tool_name: Name of tool executed
            result: Execution result
            duration_ms: Execution duration in milliseconds
            actual_cost: Actual cost (if known)
            tokens_used: Tokens used (if applicable)
        """
        # Record rate limit call
        self.rate_limiter.record_call(tool_name)

        # Record cost
        cost = actual_cost or self._estimate_cost(tool_name, {})
        if cost > 0:
            self.cost_tracker.record_cost(tool_name, cost, tokens_used)

        # Log result
        await self.audit.log_tool_result(tool_name, result, duration_ms, tokens_used)

    def _extract_domain(self, args: dict[str, Any]) -> str | None:
        """Extract domain from tool arguments.

        Args:
            args: Tool arguments

        Returns:
            Domain name or None
        """
        # Check common argument names
        for key in ["url", "domain", "host", "query"]:
            if key in args:
                value = args[key]
                if isinstance(value, str):
                    # Try to parse as URL
                    try:
                        parsed = urlparse(value)
                        if parsed.netloc:
                            return parsed.netloc
                        # Might be just a domain
                        if "." in value and " " not in value:
                            return value
                    except Exception:
                        pass

        return None

    def _estimate_cost(self, tool_name: str, args: dict[str, Any]) -> float:
        """Estimate cost of tool execution.

        Args:
            tool_name: Name of tool
            args: Tool arguments

        Returns:
            Estimated cost in USD
        """
        # Use predefined costs
        base_cost = self.TOOL_COSTS.get(tool_name, 0.0)

        # Adjust for LLM calls based on tokens (if provided in args)
        if tool_name == "llm_call":
            tokens = args.get("max_tokens", 4096)
            # Rough estimate: $0.01 per 1000 tokens
            base_cost = (tokens / 1000) * 0.01

        return base_cost

    def get_security_status(self) -> dict[str, Any]:
        """Get current security status.

        Returns:
            Dict with security status information
        """
        cost_current = self.cost_tracker.get_current()
        cost_remaining = self.cost_tracker.get_remaining()

        status = {
            "agent_id": self.policy.agent_id,
            "policy_version": self.policy.version,
            "log_level": self.policy.log_level.value,
            "costs": {
                "current": cost_current,
                "remaining": cost_remaining,
                "limits": {
                    "hourly": self.policy.cost_limits.max_per_hour,
                    "daily": self.policy.cost_limits.max_per_day,
                    "monthly": self.policy.cost_limits.max_per_month,
                },
            },
            "rate": {
                "current_per_minute": self.rate_limiter.get_current_rate(),
                "limit_per_minute": self.policy.rate_limits.max_api_calls_per_minute,
            },
            "compliance": {
                "gdpr": self.policy.compliance.gdpr_enabled,
                "soc2": self.policy.compliance.soc2_enabled,
                "hipaa": self.policy.compliance.hipaa_enabled,
            },
        }

        # Add sandbox status if enabled
        if self.sandbox:
            status["sandbox"] = self.sandbox.get_status()

        return status


def create_enforcer(
    workspace_dir: Path,
    policy_file: str = "security.yaml",
) -> SecurityEnforcer | None:
    """Create security enforcer from workspace.

    Args:
        workspace_dir: Agent workspace directory
        policy_file: Name of policy file (default: security.yaml)

    Returns:
        SecurityEnforcer if policy exists, None otherwise
    """
    policy_path = workspace_dir / policy_file

    if not policy_path.exists():
        logger.info(f"No security policy found at {policy_path}, security disabled")
        return None

    try:
        policy = SecurityPolicy.from_file(policy_path)

        # Create sandbox if enabled
        sandbox = None
        if policy.sandbox.enabled:
            from teotl.core.security.sandbox import (
                FilesystemSandbox,
                FilesystemSandboxConfig,
                NetworkSandbox,
                NetworkSandboxConfig,
                ResourceLimits,
                ResourceLimitsConfig,
                SandboxManager,
            )

            # Build filesystem sandbox
            filesystem = None
            if policy.sandbox.filesystem_enabled:
                fs_config = FilesystemSandboxConfig(
                    allowed_paths=policy.sandbox.allowed_paths,
                    max_file_size_mb=policy.sandbox.max_file_size_mb,
                    enforce=True,
                )
                filesystem = FilesystemSandbox(fs_config)

            # Build network sandbox
            network = None
            if policy.sandbox.network_enabled:
                net_config = NetworkSandboxConfig(
                    allowed_domains=policy.sandbox.allowed_domains,
                    block_private_networks=policy.sandbox.block_private_networks,
                    enforce=True,
                )
                network = NetworkSandbox(net_config)

            # Build resource limits
            resources = None
            if policy.sandbox.resources_enabled:
                res_config = ResourceLimitsConfig(
                    max_memory_mb=policy.sandbox.max_memory_mb,
                    max_cpu_seconds=policy.sandbox.max_cpu_seconds,
                    max_file_descriptors=policy.sandbox.max_file_descriptors,
                    enforce=True,
                )
                resources = ResourceLimits(res_config)

            # Create sandbox manager
            sandbox = SandboxManager(
                filesystem=filesystem,
                network=network,
                resources=resources,
            )

        return SecurityEnforcer(policy, workspace_dir, sandbox=sandbox)

    except Exception as e:
        logger.error(f"Failed to load security policy: {e}")
        return None
