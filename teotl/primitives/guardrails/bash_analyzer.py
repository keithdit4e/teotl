"""Structural bash command analysis. Beyond regex."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path

from teotl.core.types import ActionType, RiskLevel

# Commands that indicate network access
NETWORK_COMMANDS = {"curl", "wget", "ssh", "scp", "rsync", "nc", "ncat", "telnet", "ftp", "sftp"}

# Commands that are destructive
DESTRUCTIVE_COMMANDS = {"rm", "rmdir", "shred", "dd", "mkfs", "fdisk", "parted"}

# Commands that modify permissions / ownership
PERMISSION_COMMANDS = {"chmod", "chown", "chgrp"}

# Commands that modify system state
SYSTEM_COMMANDS = {"sudo", "su", "systemctl", "service", "mount", "umount", "reboot", "shutdown"}

# Package managers
PACKAGE_COMMANDS = {"pip", "pip3", "npm", "yarn", "pnpm", "apt", "apt-get", "brew", "cargo"}

# Sensitive paths
SENSITIVE_PATHS = {
    "~/.ssh",
    "~/.aws",
    "~/.gnupg",
    "~/.config/gcloud",
    "~/.kube",
    "~/.docker",
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "~/.env",
    ".env",
}


@dataclass
class BashAnalysis:
    """Result of analyzing a bash command."""

    primary_command: str = ""
    primary_target: str = ""
    action_type: ActionType = ActionType.EXECUTE
    risk_level: RiskLevel = RiskLevel.LOW
    has_pipe: bool = False
    has_redirect: bool = False
    has_subshell: bool = False
    accesses_network: bool = False
    accesses_sensitive: bool = False
    all_commands: list[str] = field(default_factory=list)


class BashAnalyzer:
    """
    Structural bash command analyzer.

    Uses shlex for tokenization and pattern matching for classification.
    Detects: pipes, redirects, subshells, network access, destructive ops,
    sensitive path access, pipe-to-bash patterns.
    """

    @classmethod
    def analyze(cls, command: str) -> BashAnalysis:
        """Analyze a bash command string."""
        result = BashAnalysis()

        if not command.strip():
            return result

        # Detect structural patterns before tokenization
        result.has_pipe = "|" in command
        result.has_redirect = any(op in command for op in [">", ">>", "<", "2>"])
        result.has_subshell = "$(" in command or "`" in command or "(" in command

        # Tokenize (best-effort — complex bash may fail)
        try:
            tokens = shlex.split(command)
        except ValueError:
            # Malformed command — treat as high risk
            tokens = command.split()
            result.risk_level = RiskLevel.HIGH

        if not tokens:
            return result

        # Extract primary command (first token, possibly after env vars)
        result.primary_command = cls._extract_primary_command(tokens)
        result.all_commands = cls._extract_all_commands(command)

        # Classify action type
        result.action_type = cls._classify_action_type(result)

        # Check for network access
        result.accesses_network = any(cmd in NETWORK_COMMANDS for cmd in result.all_commands)

        # Check for sensitive path access
        result.accesses_sensitive = cls._check_sensitive_paths(tokens)

        # Determine risk level
        result.risk_level = cls._assess_risk(result, command)

        # Determine primary target
        result.primary_target = cls._extract_target(tokens, result.primary_command)

        return result

    @classmethod
    def _extract_primary_command(cls, tokens: list[str]) -> str:
        """Extract the primary command, skipping env var assignments."""
        for token in tokens:
            if "=" in token and not token.startswith("-"):
                continue  # Skip env var assignments like FOO=bar
            # Strip path prefix
            return Path(token).name
        return tokens[0] if tokens else ""

    @classmethod
    def _extract_all_commands(cls, command: str) -> list[str]:
        """Extract all command names from a pipeline."""
        commands = []
        # Split on pipe, semicolon, &&, ||
        parts = command.replace("&&", "|").replace("||", "|").replace(";", "|").split("|")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                tokens = shlex.split(part)
                if tokens:
                    cmd = Path(tokens[0]).name
                    commands.append(cmd)
            except ValueError:
                parts_split = part.split()
                if parts_split:
                    commands.append(parts_split[0])
        return commands

    @classmethod
    def _classify_action_type(cls, analysis: BashAnalysis) -> ActionType:
        """Classify the overall action type."""
        cmd = analysis.primary_command

        if cmd in DESTRUCTIVE_COMMANDS:
            return ActionType.DESTRUCTIVE
        if cmd in NETWORK_COMMANDS or analysis.accesses_network:
            return ActionType.NETWORK
        if cmd in ("cat", "ls", "head", "tail", "find", "grep", "wc", "file", "stat"):
            return ActionType.READ
        if cmd in ("cp", "mv", "tee", "sed", "awk") or analysis.has_redirect:
            return ActionType.WRITE

        return ActionType.EXECUTE

    @classmethod
    def _check_sensitive_paths(cls, tokens: list[str]) -> bool:
        """Check if any tokens reference sensitive paths."""
        for token in tokens:
            try:
                expanded = str(Path(token).expanduser()) if token.startswith("~") else token
            except RuntimeError:
                # HOME not set - use token as-is
                expanded = token

            for sensitive in SENSITIVE_PATHS:
                try:
                    sensitive_expanded = str(Path(sensitive).expanduser())
                except RuntimeError:
                    sensitive_expanded = sensitive

                if expanded.startswith(sensitive_expanded) or token.startswith(sensitive):
                    return True
        return False

    @classmethod
    def _assess_risk(cls, analysis: BashAnalysis, raw_command: str) -> RiskLevel:
        """Assess overall risk level."""
        cmd = analysis.primary_command

        # Critical: pipe-to-shell patterns
        pipe_to_shell = any(
            f"| {shell}" in raw_command or f"|{shell}" in raw_command
            for shell in ["bash", "sh", "zsh", "eval", "python", "python3", "node"]
        )
        if pipe_to_shell and analysis.accesses_network:
            return RiskLevel.CRITICAL

        # Critical: fork bombs, disk wipers
        if ":()" in raw_command or cmd == "dd" or (cmd == "rm" and "-rf /" in raw_command):
            return RiskLevel.CRITICAL

        # High: destructive, system, sudo
        if cmd in DESTRUCTIVE_COMMANDS or cmd in SYSTEM_COMMANDS:
            return RiskLevel.HIGH

        # High: sensitive path access
        if analysis.accesses_sensitive:
            return RiskLevel.HIGH

        # Medium: writes, network, package installs
        if analysis.action_type in (ActionType.WRITE, ActionType.NETWORK):
            return RiskLevel.MEDIUM
        if cmd in PACKAGE_COMMANDS:
            return RiskLevel.MEDIUM

        # Medium: pipes (could be chaining something dangerous)
        if analysis.has_pipe and len(analysis.all_commands) > 2:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    @classmethod
    def _extract_target(cls, tokens: list[str], primary_cmd: str) -> str:
        """Extract the primary target (file/URL/host) from tokens."""
        # Skip the command itself and flags
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            return token
        return primary_cmd
