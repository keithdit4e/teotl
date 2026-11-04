"""Structural bash command analysis. Beyond regex."""

from __future__ import annotations

import re
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

# Interpreters: running code through them can do anything the code does, which
# the guardrails can't see. Inline code and scripts are high risk (ask first).
INTERPRETERS = {
    "python",
    "python3",
    "node",
    "deno",
    "bun",
    "ruby",
    "perl",
    "php",
    "bash",
    "sh",
    "zsh",
    "fish",
    "osascript",
    "lua",
    "Rscript",
}
INLINE_CODE_FLAGS = {"-c", "-e", "-E", "--eval", "-p", "--print", "-r", "eval", "-x"}
# Build and task runners execute project-defined code
TASK_RUNNERS = {"make", "gmake", "just", "rake", "npx", "invoke", "nox", "tox"}
# Test runners: also run project code, but checking work is what agents must do;
# kept low risk so an unattended worker can verify its steps
TEST_COMMANDS = {"pytest", "py.test"}
TEST_MODULES = {"pytest", "unittest"}
DELETING_COMMANDS = {"rm", "rmdir", "shred", "unlink"}

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
    # Files written by output redirects (> or >>), e.g. "cat > notes.txt"
    redirect_targets: list[str] = field(default_factory=list)
    deletes: bool = False  # find -delete / -exec, xargs rm


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
        result.redirect_targets = cls._output_redirect_targets(command)
        result.deletes = cls._deletes_via_helper(command)

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

        # Determine primary target (the redirected-to file for "cmd > file")
        result.primary_target = (
            result.redirect_targets[0]
            if result.redirect_targets
            else cls._extract_target(tokens, result.primary_command)
        )

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
        # Output redirects write files even when the command itself only reads
        # ("cat > ~/.bashrc << EOF", "ls > out.txt")
        if analysis.redirect_targets:
            return ActionType.WRITE
        if cmd in ("find", "xargs") and analysis.deletes:
            return ActionType.DESTRUCTIVE
        if cmd in ("cat", "ls", "head", "tail", "find", "grep", "wc", "file", "stat"):
            return ActionType.READ
        if cmd in ("cp", "mv", "tee", "sed", "awk"):
            return ActionType.WRITE

        return ActionType.EXECUTE

    _HARMLESS_REDIRECTS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})

    @classmethod
    def _output_redirect_targets(cls, command: str) -> list[str]:
        """Files an output redirect writes to: `> f`, `>> f`, `1> f`, `&> f`.

        Ignores stderr-to-stdout (`2>&1`), heredocs (`<<`), and /dev/null.
        Only the first line is scanned, since heredoc bodies are data.
        """
        first_line = command.split("\n", 1)[0]
        # Hide quoted text so "print(1 > 0)" isn't read as a redirect; keep it for targets
        quoted: list[str] = []

        def hide(match: re.Match) -> str:
            quoted.append(match.group(0)[1:-1])
            return f"\x00{len(quoted) - 1}\x00"

        line = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", hide, first_line)
        targets = []
        for match in re.finditer(r"(?<![<>\d&])(?:&|1)?>>?(?!&)\s*([^\s;&|<>]+)", line):
            target = re.sub(r"\x00(\d+)\x00", lambda m: quoted[int(m.group(1))], match.group(1))
            if target and target not in cls._HARMLESS_REDIRECTS:
                targets.append(target)
        return targets

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

    # Targets whose recursive deletion is never a reasonable agent action
    _CRITICAL_RM_TARGETS = frozenset(
        {"/", "/*", "~", "~/", "~/*", "..", "../"}
        | {"$HOME", "$HOME/", "$HOME/*", "${HOME}", "${HOME}/"}
    )

    @classmethod
    def _wipes_root_or_home(cls, raw_command: str) -> bool:
        """True for `rm -r`/`-rf` (any flag order) aimed at /, ~, $HOME or the parent dir."""
        import shlex

        for segment in re.split(r"&&|\|\||;|\|", raw_command):
            try:
                tokens = shlex.split(segment, posix=True)
            except ValueError:
                tokens = segment.split()
            if tokens[:1] == ["sudo"]:
                tokens = tokens[1:]
            if not tokens or tokens[0] != "rm":
                continue
            flags = [t for t in tokens[1:] if t.startswith("-")]
            recursive = any(
                f in ("--recursive", "-r", "-R")
                or (not f.startswith("--") and ("r" in f or "R" in f))
                for f in flags
            )
            targets = [t for t in tokens[1:] if not t.startswith("-")]
            if recursive and any(t in cls._CRITICAL_RM_TARGETS for t in targets):
                return True
        return False

    @classmethod
    def _segments(cls, raw_command: str) -> list[list[str]]:
        segments = []
        for part in re.split(r"&&|\|\||;|\|", raw_command.split("\n", 1)[0]):
            try:
                words = shlex.split(part)
            except ValueError:
                words = part.split()
            while words and "=" in words[0] and not words[0].startswith("-"):
                words = words[1:]
            if words and words[0] in ("sudo", "env", "nohup", "time", "exec"):
                words = words[1:]
            if words:
                words[0] = Path(words[0]).name
                segments.append(words)
        return segments

    @classmethod
    def _runs_code(cls, raw_command: str) -> bool:
        """Inline code, a script through an interpreter, `./script`, or a task runner."""
        for words in cls._segments(raw_command):
            cmd, args = words[0], words[1:]
            if cmd in TEST_COMMANDS:
                continue
            if cmd in TASK_RUNNERS:
                return True
            if cmd in ("npm", "pnpm", "yarn", "bun") and args[:1] in (["run"], ["exec"], ["x"]):
                return True
            if words[0] != Path(words[0]).name or raw_command.lstrip().startswith("./"):
                return True
            if cmd in INTERPRETERS or re.fullmatch(r"python\d(\.\d+)?", cmd):
                if not args:
                    continue  # bare interpreter (interactive) - nothing to run
                if args[0] == "-m" and len(args) > 1 and args[1] in TEST_MODULES:
                    continue
                if args[0] in ("--version", "-V", "--help", "-h"):
                    continue
                return True
        return False

    @classmethod
    def _deletes_via_helper(cls, raw_command: str) -> bool:
        """`find ... -delete` / `-exec rm`, or `xargs rm`."""
        for words in cls._segments(raw_command):
            if words[0] == "find" and any(
                a in ("-delete", "-exec", "-execdir", "-ok") for a in words[1:]
            ):
                return True
            if words[0] == "xargs" and any(Path(a).name in DELETING_COMMANDS for a in words[1:]):
                return True
        return False

    _UPLOAD_PATTERNS = (
        r"(?:-F|--form)\s+\S*?=@(\S+)",
        r"(?:-d|--data|--data-binary|--data-raw|--data-urlencode)\s+\S*?@(\S+)",
        r"(?:-T|--upload-file)\s+(\S+)",
    )

    @classmethod
    def _uploads_sensitive_file(cls, raw_command: str) -> bool:
        for pattern in cls._UPLOAD_PATTERNS:
            for match in re.finditer(pattern, raw_command):
                path = match.group(1).strip("'\"")
                path = re.sub(r"^\$\{?HOME\}?", "~", path)
                if cls._check_sensitive_paths([path]):
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

        # Critical: fork bombs, disk wipers, recursive deletes of / or the home folder
        if ":()" in raw_command or cmd == "dd" or (cmd == "rm" and "-rf /" in raw_command):
            return RiskLevel.CRITICAL
        if cls._wipes_root_or_home(raw_command):
            return RiskLevel.CRITICAL
        # Critical: uploading secrets (curl -F file=@~/.ssh/...), deleting ~ or / via find
        if analysis.accesses_network and cls._uploads_sensitive_file(raw_command):
            return RiskLevel.CRITICAL
        if cls._deletes_via_helper(raw_command) and re.search(
            r"(?:^|\s)(?:~|\$HOME|\$\{HOME\}|/)/?(?:\s|$)", raw_command
        ):
            return RiskLevel.CRITICAL

        # High: running code the guardrails can't inspect, or deleting via find/xargs
        if cls._runs_code(raw_command) or cls._deletes_via_helper(raw_command):
            return RiskLevel.HIGH

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
