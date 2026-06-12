"""Security and compliance system for Forge agents.

Provides:
- Policy-based access control
- OS-level sandboxing (filesystem, network, resources)
- Audit logging for compliance (GDPR, SOC2, HIPAA)
- Cost and rate limiting
- Runtime enforcement

Usage:
    from teotl.core.security import SecurityPolicy, SecurityEnforcer, SandboxManager

    # Load policy
    policy = SecurityPolicy.from_file("security.yaml")

    # Create sandbox (optional, recommended)
    from teotl.core.security.sandbox import (
        FilesystemSandbox, NetworkSandbox, ResourceLimits,
        FilesystemSandboxConfig, NetworkSandboxConfig, ResourceLimitsConfig
    )

    sandbox = SandboxManager(
        filesystem=FilesystemSandbox(FilesystemSandboxConfig(...)),
        network=NetworkSandbox(NetworkSandboxConfig(...)),
        resources=ResourceLimits(ResourceLimitsConfig(...)),
    )

    # Create enforcer with sandbox
    enforcer = SecurityEnforcer(policy, workspace_dir, sandbox=sandbox)

    # Check if action allowed (checks both policy AND sandbox)
    allowed, reason = await enforcer.enforce_tool_call("web_search", {"query": "..."})
"""

from teotl.core.security.audit import AuditEntry, AuditLogger, LogLevel
from teotl.core.security.enforcement import SecurityEnforcer, SecurityError
from teotl.core.security.policy import SecurityPolicy
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

__all__ = [
    "SecurityPolicy",
    "SecurityEnforcer",
    "SecurityError",
    "AuditLogger",
    "AuditEntry",
    "LogLevel",
    "SandboxManager",
    "FilesystemSandbox",
    "FilesystemSandboxConfig",
    "NetworkSandbox",
    "NetworkSandboxConfig",
    "ResourceLimits",
    "ResourceLimitsConfig",
    "SandboxViolation",
]
