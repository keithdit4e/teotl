"""Action classification for tool calls."""

from __future__ import annotations

from teotl.core.types import Action, ActionType, RiskLevel, ToolCall


def classify(tool_call: ToolCall) -> Action:
    """
    Classify a tool call into an Action with type and risk level.

    This is the entry point for the guardrails system. Every tool call
    goes through classification before policy evaluation.
    """
    if tool_call.name == "bash":
        return classify_bash(tool_call.args.get("command", ""))
    elif tool_call.name in ("write_file", "create_file", "str_replace"):
        return Action(
            type=ActionType.WRITE,
            target=tool_call.args.get("path", ""),
            risk=RiskLevel.MEDIUM,
            details={"tool": tool_call.name},
        )
    elif tool_call.name in ("read_file", "view"):
        return Action(
            type=ActionType.READ,
            target=tool_call.args.get("path", ""),
            risk=RiskLevel.LOW,
            details={"tool": tool_call.name},
        )
    else:
        return Action(
            type=ActionType.EXECUTE,
            target=tool_call.name,
            risk=RiskLevel.LOW,
            details={"tool": tool_call.name, "args": tool_call.args},
        )


def classify_bash(command: str) -> Action:
    """
    Structural analysis of a bash command.

    Uses shlex for tokenization and pattern matching for classification.
    Not just regex — understands pipes, redirects, and subshells.
    """
    from teotl.primitives.guardrails.bash_analyzer import BashAnalyzer

    analysis = BashAnalyzer.analyze(command)
    return Action(
        type=analysis.action_type,
        target=analysis.primary_target,
        risk=analysis.risk_level,
        details={
            "command": command,
            "primary_command": analysis.primary_command,
            "has_pipe": analysis.has_pipe,
            "has_redirect": analysis.has_redirect,
            "has_subshell": analysis.has_subshell,
            "accesses_network": analysis.accesses_network,
            "accesses_sensitive": analysis.accesses_sensitive,
        },
    )
