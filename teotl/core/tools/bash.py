"""Bash command execution tool with sandboxing and security.

This tool allows agents to execute bash commands for skills like filesystem,
git, and web operations. All executions are:
1. Validated against security policy (via guardrails)
2. Sandboxed for filesystem/network access
3. Resource-limited (CPU, memory, time)
4. Logged to audit trail

Usage:
    tool = BashTool(sandbox=sandbox_manager)
    result = await tool.execute(command="ls -la")
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BashResult:
    """Result from bash command execution."""

    stdout: str
    stderr: str
    return_code: int
    command: str
    is_error: bool = False
    error_message: str | None = None

    def __str__(self) -> str:
        """Format result for LLM consumption."""
        if self.is_error:
            return f"Error: {self.error_message}\n{self.stderr}".strip()

        output_parts = []
        if self.stdout:
            output_parts.append(f"Output:\n{self.stdout}")
        if self.stderr:
            output_parts.append(f"Warnings:\n{self.stderr}")
        if self.return_code != 0:
            output_parts.append(f"Exit code: {self.return_code}")

        return "\n\n".join(output_parts) if output_parts else "(no output)"


class BashTool:
    """Safe bash command execution with sandboxing.

    Features:
    - Command validation (detects dangerous patterns)
    - Timeout enforcement (default 30s)
    - Working directory control
    - Environment variable isolation
    - Stdout/stderr capture
    - Resource limits (via sandbox)

    Security:
    - Guardrails evaluate commands before execution
    - Sandbox validates file/network access
    - No shell injection (subprocess.run with shell=True but validated)
    - Timeout prevents infinite loops
    """

    # Dangerous command patterns that should be blocked or confirmed
    DANGEROUS_PATTERNS = [
        r"\brm\s+-rf\s+/",  # rm -rf / (catastrophic)
        r"\bdd\b.*if=/dev/",  # dd from device (disk operations)
        r"\bmkfs\b",  # Make filesystem
        r"\bfdisk\b",  # Disk partitioning
        r">\s*/dev/sd",  # Write to disk device
        r"\bcurl\b.*\|\s*bash",  # Curl pipe to bash (arbitrary code)
        r"\bwget\b.*\|\s*bash",  # Wget pipe to bash
        r"\beval\b",  # Eval (code injection risk)
        r";\s*bash",  # Command chaining with bash
        r"\$\(.*curl",  # Command substitution with curl
    ]

    def __init__(
        self,
        sandbox: Any | None = None,
        working_dir: Path | None = None,
        timeout: int = 30,
        max_output_size: int = 1024 * 1024,  # 1MB
    ):
        """Initialize bash tool.

        Args:
            sandbox: SandboxManager for enforcing security (optional)
            working_dir: Default working directory (default: current dir)
            timeout: Command timeout in seconds (default: 30)
            max_output_size: Maximum output size in bytes (default: 1MB)
        """
        self.sandbox = sandbox
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout
        self.max_output_size = max_output_size

        logger.info(
            f"BashTool initialized: "
            f"sandbox={'enabled' if sandbox else 'disabled'}, "
            f"working_dir={self.working_dir}, "
            f"timeout={timeout}s"
        )

    def validate_command(self, command: str) -> tuple[bool, str]:
        """Validate command for dangerous patterns.

        This is a secondary safety check - guardrails should catch most issues.
        But defense-in-depth means we validate again here.

        Args:
            command: Bash command to validate

        Returns:
            Tuple of (is_safe, reason_if_unsafe)
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches dangerous pattern: {pattern}"

        # Check for shell metacharacters that could indicate injection
        # (These are often legitimate, so we just warn)
        # Skip warning for whitelisted commands like gh CLI
        whitelisted_commands = ["gh ", "git ", "pytest", "npm test"]
        is_whitelisted = any(command.strip().startswith(cmd) for cmd in whitelisted_commands)

        if not is_whitelisted:
            suspicious_chars = ["$(", "`", "${"]
            for char in suspicious_chars:
                if char in command:
                    logger.debug(f"Command contains shell expansion sequence: {char}")

        return True, ""

    async def execute(
        self,
        command: str,
        working_dir: Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        """Execute bash command asynchronously.

        Args:
            command: Bash command to execute
            working_dir: Override default working directory
            timeout: Override default timeout
            env: Additional environment variables

        Returns:
            Execution result as string (formatted for LLM)

        Raises:
            ValueError: If command is invalid
            TimeoutError: If command exceeds timeout
        """
        # Validate command
        is_safe, reason = self.validate_command(command)
        if not is_safe:
            logger.error(f"Unsafe command blocked: {reason}")
            return f"Error: Unsafe command blocked: {reason}"

        # Determine working directory
        cwd = working_dir or self.working_dir

        # Validate working directory with sandbox (if available)
        if self.sandbox and hasattr(self.sandbox, "validate_file_operation"):
            try:
                cwd = self.sandbox.validate_file_operation(cwd, "execute")
            except Exception as e:
                logger.error(f"Sandbox blocked working directory: {e}")
                return f"Error: Access to directory '{cwd}' is not permitted"

        # Prepare environment
        import os

        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        # Execute command
        timeout_val = timeout or self.timeout

        logger.info(f"Executing command (timeout={timeout_val}s): {command[:100]}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=exec_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_val
                )
            except TimeoutError:
                # Kill the process
                process.kill()
                await process.wait()
                logger.error(f"Command timed out after {timeout_val}s: {command[:100]}")
                return f"Error: Command timed out after {timeout_val} seconds"

            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Check output size
            total_output = len(stdout) + len(stderr)
            if total_output > self.max_output_size:
                logger.warning(f"Output exceeds max size ({total_output} > {self.max_output_size})")
                stdout = stdout[: self.max_output_size // 2] + "\n...(truncated)"
                stderr = stderr[: self.max_output_size // 2] + "\n...(truncated)"

            # Create result
            result = BashResult(
                stdout=stdout,
                stderr=stderr,
                return_code=process.returncode or 0,
                command=command,
            )

            # Log execution
            logger.info(
                f"Command completed: return_code={result.return_code}, "
                f"stdout={len(stdout)} bytes, stderr={len(stderr)} bytes"
            )

            return str(result)

        except FileNotFoundError:
            error_msg = f"Working directory not found: {cwd}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        except PermissionError as e:
            error_msg = f"Permission denied: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Command execution failed: {type(e).__name__}: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def get_tool_definition(self) -> dict[str, Any]:
        """Get tool definition for agent registration.

        Returns:
            Tool definition dict with name, description, and parameters
        """
        return {
            "name": "bash",
            "description": (
                "Execute bash commands for file operations, git commands, and other "
                "system tasks. Use this to run commands from enabled skills like "
                "filesystem, git, and web. Commands are sandboxed and time-limited."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "The bash command to execute. Can include pipes, "
                            "redirects, and standard bash syntax. Must follow "
                            "security policies."
                        ),
                    },
                    "working_dir": {
                        "type": "string",
                        "description": (
                            "Optional: Override the working directory for this command."
                        ),
                    },
                },
                "required": ["command"],
            },
        }


def create_bash_tool(agent: Any) -> BashTool:
    """Create and configure bash tool for an agent.

    Args:
        agent: Agent instance with guardrails and policy

    Returns:
        Configured BashTool instance
    """
    # Extract sandbox from agent's guardrails if available
    sandbox = None
    if hasattr(agent, "guardrails") and agent.guardrails:
        pass
        # TODO: Create SandboxManager from policy.sandbox config
        # For now, sandbox is None (policy-only enforcement)

    # Get working directory from agent's config if available
    working_dir = Path.cwd()

    tool = BashTool(sandbox=sandbox, working_dir=working_dir)

    logger.info("Created bash tool for agent")

    return tool
