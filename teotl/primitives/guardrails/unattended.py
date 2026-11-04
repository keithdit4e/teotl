"""What to do with "ask first" actions when nobody is watching.

Interactive runs ask a person. Unattended runs (no UI: headless `agent.run()`,
the planner-worker harness, the daemon) use one of three modes:

- ``safe_zone`` (default): allow the action only if it is a plain file operation
  whose every path is inside the agent's safe zone (its project folder);
  refuse everything else.
- ``refuse``: refuse every action that would need confirmation.
- ``approve``: approve everything that isn't blocked (the pre-0.2.9 behavior).
  Logged loudly; not recommended.

Blocked actions stay blocked in every mode.
"""

from __future__ import annotations

import logging
import os
import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

MODES = ("safe_zone", "refuse", "approve")

# Commands whose effect is limited to the files named in their arguments
_FILE_COMMANDS = frozenset(
    {
        "rm",
        "rmdir",
        "mv",
        "cp",
        "mkdir",
        "touch",
        "tee",
        "echo",
        "printf",
        "cat",
        "sed",
        "ls",
        "pwd",
    }
)
# Commands that only read or report (arguments may be anything); fine to chain
_NEUTRAL_COMMANDS = frozenset({"true", "echo", "printf", "pwd", "ls"})
_FILE_TOOLS = frozenset({"write_file", "create_file", "str_replace", "read_file", "view"})


def validate_mode(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"Invalid unattended mode {mode!r}: use one of {', '.join(MODES)}")
    return mode


def resolve_safe_zone(zones: Iterable[str | Path] | None, cwd: Path | None = None) -> list[Path]:
    """Resolve safe-zone folders, dropping (with a warning) any that would cover too much.

    With no folders given, the safe zone is the current working directory.
    A safe zone of `/`, the home folder, or a folder containing the home folder
    would make "inside the safe zone" mean "almost anywhere", so it's ignored.
    """
    home = Path.home().resolve()
    candidates = list(zones) if zones else [cwd or Path.cwd()]
    resolved: list[Path] = []
    for zone in candidates:
        path = Path(os.path.expanduser(str(zone))).resolve()
        if path == Path(path.anchor) or path == home or home.is_relative_to(path):
            logger.warning(
                f"Ignoring safe zone {path}: it would cover your whole home folder or disk. "
                "Pass safe_zone=[...] with a specific project folder."
            )
            continue
        resolved.append(path)
    return resolved


def _inside(path: Path, zones: list[Path]) -> bool:
    return any(path == zone or path.is_relative_to(zone) for zone in zones)


def _resolve(arg: str, cwd: Path) -> Path | None:
    """Resolve a path argument; None if it can't be known statically."""
    if not arg or "$" in arg or "`" in arg:
        expanded = arg.replace("${HOME}", "~").replace("$HOME", "~")
        if "$" in expanded or "`" in expanded:
            return None
        arg = expanded
    path = Path(os.path.expanduser(arg))
    if not path.is_absolute():
        path = cwd / path
    # Resolve "..", symlinks, and glob parents ("build/*" -> "build")
    parts = []
    for part in path.parts:
        if any(c in part for c in "*?["):
            break
        parts.append(part)
    return Path(*parts).resolve() if parts else None


def _strip_heredoc(command: str) -> str:
    """Drop heredoc bodies: only the first line names files ("cat > f << 'EOF'")."""
    match = re.search(r"<<-?\s*(['\"]?)(\w+)\1", command)
    if not match:
        return command
    first_line = command.split("\n", 1)[0]
    return (
        first_line[: match.start()] + first_line[match.end() :]
        if match.start() < len(first_line)
        else first_line
    )


def _bash_inside_safe_zone(command: str, zones: list[Path], cwd: Path) -> tuple[bool, str]:
    command = _strip_heredoc(command)
    if "\n" in command.strip():
        return (False, "multi-line command can't be checked")
    if "$(" in command or "`" in command:
        return (False, "command substitution can't be checked")
    cwd_now = cwd
    segments = [s.strip() for s in re.split(r"&&|\|\||;|\|", command) if s.strip()]
    for segment in segments:
        try:
            tokens = shlex.split(segment)
        except ValueError:
            return (False, "command couldn't be parsed")
        if not tokens:
            continue
        name = Path(tokens[0]).name
        if name == "cd":
            target = _resolve(tokens[1] if len(tokens) > 1 else "~", cwd_now)
            if target is None:
                return (False, "cd target can't be determined")
            cwd_now = target
            continue
        if name not in _FILE_COMMANDS:
            return (False, f"`{name}` isn't a plain file operation")
        paths: list[str] = []
        args = tokens[1:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in (">", ">>", "2>", "&>", "<"):
                if i + 1 < len(args):
                    paths.append(args[i + 1])
                i += 2
                continue
            if re.match(r"^(\d?>>?|&>|<)(.+)$", arg):
                paths.append(re.sub(r"^(\d?>>?|&>|<)", "", arg))
            elif not arg.startswith("-") and name not in _NEUTRAL_COMMANDS:
                if name == "sed" and not paths and not any(a.startswith("-i") for a in args):
                    return (False, "sed without -i doesn't change files")
                paths.append(arg)
            i += 1
        if name == "sed":
            paths = paths[1:]  # first non-flag argument is the expression
        for raw in paths:
            path = _resolve(raw, cwd_now)
            if path is None:
                return (False, f"path {raw!r} can't be determined")
            if not _inside(path, zones):
                return (False, f"{path} is outside the safe zone")
    return (True, "")


def inside_safe_zone(tool_name: str, args: dict[str, Any], zones: list[Path]) -> tuple[bool, str]:
    """Is this tool call a file operation confined to the safe zone?

    Returns (inside, reason it isn't). Anything not understood is "not inside".
    """
    if not zones:
        return (False, "no safe zone is set")
    cwd = Path.cwd().resolve()
    if tool_name == "bash":
        return _bash_inside_safe_zone(str(args.get("command", "")), zones, cwd)
    if tool_name in _FILE_TOOLS:
        path = _resolve(str(args.get("path", "")), cwd)
        if path is None:
            return (False, "path can't be determined")
        if not _inside(path, zones):
            return (False, f"{path} is outside the safe zone")
        return (True, "")
    return (False, f"`{tool_name}` isn't a file operation")
