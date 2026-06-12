"""Dry-run capabilities for previewing destructive actions.

Allows users to preview what would happen before actually executing changes,
reducing risk and building confidence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from teotl.primitives.harness.plan import ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)


@dataclass
class DryRunAction:
    """Single action that would be taken."""

    step_number: int
    action_type: str  # file_write, file_delete, file_modify, command, api_call
    description: str
    target: str  # File path, command, URL, etc.
    details: dict = field(default_factory=dict)
    risk_level: str = "low"  # low, medium, high, critical
    reversible: bool = True
    requires_approval: bool = False


@dataclass
class DryRunResult:
    """Result of dry-run analysis."""

    success: bool
    total_actions: int
    actions: list[DryRunAction] = field(default_factory=list)
    risk_summary: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    estimated_duration_seconds: float = 0.0
    estimated_cost: float = 0.0

    # Categorized actions
    file_writes: list[DryRunAction] = field(default_factory=list)
    file_deletes: list[DryRunAction] = field(default_factory=list)
    file_modifies: list[DryRunAction] = field(default_factory=list)
    commands: list[DryRunAction] = field(default_factory=list)
    api_calls: list[DryRunAction] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    user_approved: bool | None = None

    def get_high_risk_actions(self) -> list[DryRunAction]:
        """Get actions with high or critical risk level.

        Returns:
            List of high-risk actions
        """
        return [a for a in self.actions if a.risk_level in ("high", "critical")]

    def requires_approval(self) -> bool:
        """Check if any action requires approval.

        Returns:
            True if approval needed
        """
        return any(a.requires_approval for a in self.actions)

    def to_summary_text(self) -> str:
        """Generate human-readable summary.

        Returns:
            Formatted summary text
        """
        lines = [
            "=" * 70,
            "DRY-RUN PREVIEW",
            "=" * 70,
            "",
            f"Total Actions: {self.total_actions}",
            f"Estimated Duration: {self.estimated_duration_seconds:.1f}s",
            f"Estimated Cost: ${self.estimated_cost:.2f}",
            "",
        ]

        # Risk summary
        lines.append("Risk Breakdown:")
        for risk_level, count in self.risk_summary.items():
            lines.append(f"  {risk_level.upper()}: {count}")
        lines.append("")

        # Actions by type
        if self.file_writes:
            lines.append(f"File Writes ({len(self.file_writes)}):")
            for action in self.file_writes[:5]:
                lines.append(f"  • {action.target}")
            if len(self.file_writes) > 5:
                lines.append(f"  ... and {len(self.file_writes) - 5} more")
            lines.append("")

        if self.file_modifies:
            lines.append(f"File Modifications ({len(self.file_modifies)}):")
            for action in self.file_modifies[:5]:
                lines.append(f"  • {action.target}")
            if len(self.file_modifies) > 5:
                lines.append(f"  ... and {len(self.file_modifies) - 5} more")
            lines.append("")

        if self.file_deletes:
            lines.append(f"File Deletions ({len(self.file_deletes)}):")
            for action in self.file_deletes:
                lines.append(f"  • {action.target} [RISK: {action.risk_level.upper()}]")
            lines.append("")

        if self.commands:
            lines.append(f"Commands ({len(self.commands)}):")
            for action in self.commands[:5]:
                lines.append(f"  • {action.description}")
            if len(self.commands) > 5:
                lines.append(f"  ... and {len(self.commands) - 5} more")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("⚠️  Warnings:")
            for warning in self.warnings:
                lines.append(f"  • {warning}")
            lines.append("")

        # High-risk actions
        high_risk = self.get_high_risk_actions()
        if high_risk:
            lines.append(f"🚨 High-Risk Actions ({len(high_risk)}):")
            for action in high_risk:
                lines.append(
                    f"  • [{action.risk_level.upper()}] {action.description} → {action.target}"
                )
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


class DryRunAnalyzer:
    """Analyze execution plans to preview actions without executing.

    Usage:
        analyzer = DryRunAnalyzer(workspace_dir=Path("~/my-project"))

        # Analyze a plan
        result = analyzer.analyze_plan(plan)

        # Preview actions
        print(result.to_summary_text())

        # Check if safe
        if result.get_high_risk_actions():
            print("⚠️ High-risk actions detected!")

        # Get user approval
        if result.requires_approval():
            approved = input("Proceed? (y/n): ") == 'y'
            result.user_approved = approved

    Benefits:
    - Preview all changes before execution
    - Identify risky operations
    - Estimate costs and duration
    - Build user confidence
    - Catch potential issues early
    """

    def __init__(
        self,
        workspace_dir: Path,
        enable_risk_analysis: bool = True,
        enable_cost_estimation: bool = True,
    ):
        """Initialize dry-run analyzer.

        Args:
            workspace_dir: Project workspace directory
            enable_risk_analysis: Perform risk analysis on actions
            enable_cost_estimation: Estimate execution costs
        """
        self.workspace_dir = Path(workspace_dir).expanduser().resolve()
        self.enable_risk_analysis = enable_risk_analysis
        self.enable_cost_estimation = enable_cost_estimation

        logger.info(f"DryRun analyzer initialized: {self.workspace_dir}")

    def analyze_plan(self, plan: ExecutionPlan) -> DryRunResult:
        """Analyze execution plan and preview actions.

        Args:
            plan: Execution plan to analyze

        Returns:
            DryRunResult with action preview

        Example:
            result = analyzer.analyze_plan(plan)
            if not result.warnings:
                print("✅ Plan looks safe")
        """
        actions = []
        warnings = []

        # Analyze each step
        for step in plan.steps:
            step_actions = self._analyze_step(step)
            actions.extend(step_actions)

        # Categorize actions
        file_writes = [a for a in actions if a.action_type == "file_write"]
        file_deletes = [a for a in actions if a.action_type == "file_delete"]
        file_modifies = [a for a in actions if a.action_type == "file_modify"]
        commands = [a for a in actions if a.action_type == "command"]
        api_calls = [a for a in actions if a.action_type == "api_call"]

        # Risk analysis
        risk_summary = {}
        if self.enable_risk_analysis:
            risk_summary = self._calculate_risk_summary(actions)
            warnings.extend(self._generate_warnings(actions))

        # Cost estimation
        estimated_cost = 0.0
        estimated_duration = 0.0
        if self.enable_cost_estimation:
            estimated_cost = self._estimate_cost(plan, actions)
            estimated_duration = self._estimate_duration(plan, actions)

        return DryRunResult(
            success=True,
            total_actions=len(actions),
            actions=actions,
            risk_summary=risk_summary,
            warnings=warnings,
            estimated_duration_seconds=estimated_duration,
            estimated_cost=estimated_cost,
            file_writes=file_writes,
            file_deletes=file_deletes,
            file_modifies=file_modifies,
            commands=commands,
            api_calls=api_calls,
        )

    def _analyze_step(self, step: PlanStep) -> list[DryRunAction]:
        """Analyze a single plan step.

        Args:
            step: Plan step to analyze

        Returns:
            List of actions for this step
        """
        actions = []

        # Infer action type from step description and file_path
        description_lower = step.description.lower()

        # File operations
        if step.file_path:
            file_path = Path(step.file_path)

            # Determine operation type
            if "create" in description_lower or "write" in description_lower:
                action = DryRunAction(
                    step_number=step.number,
                    action_type="file_write",
                    description=f"Create/write file: {step.description}",
                    target=str(file_path),
                    risk_level=self._assess_file_write_risk(file_path),
                    reversible=True,
                )
                actions.append(action)

            elif "delete" in description_lower or "remove" in description_lower:
                action = DryRunAction(
                    step_number=step.number,
                    action_type="file_delete",
                    description=f"Delete file: {step.description}",
                    target=str(file_path),
                    risk_level="high",  # Deletes are always high-risk
                    reversible=False,
                    requires_approval=True,
                )
                actions.append(action)

            elif (
                "modify" in description_lower
                or "update" in description_lower
                or "edit" in description_lower
            ):
                action = DryRunAction(
                    step_number=step.number,
                    action_type="file_modify",
                    description=f"Modify file: {step.description}",
                    target=str(file_path),
                    risk_level=self._assess_file_modify_risk(file_path),
                    reversible=True,  # With git/checkpoints
                )
                actions.append(action)

        # Command execution (check for both keywords and actual shell commands)
        command_keywords = ["run", "execute", "command", "shell", "bash"]
        shell_commands = ["rm ", "mv ", "cp ", "dd ", "chmod ", "chown ", "kill ", "sudo "]

        is_command = any(kw in description_lower for kw in command_keywords) or any(
            cmd in description_lower for cmd in shell_commands
        )

        if is_command:
            action = DryRunAction(
                step_number=step.number,
                action_type="command",
                description=step.description,
                target="shell command",
                risk_level=self._assess_command_risk(step.description),
                reversible=False,
                requires_approval=self._command_requires_approval(step.description),
            )
            actions.append(action)

        # API calls
        if any(kw in description_lower for kw in ["api", "request", "http", "fetch", "post"]):
            action = DryRunAction(
                step_number=step.number,
                action_type="api_call",
                description=step.description,
                target="external API",
                risk_level="medium",
                reversible=False,
            )
            actions.append(action)

        # If no specific action detected, classify as general
        if not actions:
            action = DryRunAction(
                step_number=step.number,
                action_type="other",
                description=step.description,
                target="",
                risk_level="low",
                reversible=True,
            )
            actions.append(action)

        return actions

    def _assess_file_write_risk(self, file_path: Path) -> str:
        """Assess risk level for file write operation.

        Args:
            file_path: Path being written

        Returns:
            Risk level: low, medium, high, critical
        """
        path_str = str(file_path).lower()

        # Critical paths
        critical_patterns = [
            "/etc/",
            "/sys/",
            "/proc/",
            "sudoers",
            "shadow",
            "passwd",
        ]
        if any(pattern in path_str for pattern in critical_patterns):
            return "critical"

        # High-risk paths
        high_risk_patterns = [
            ".env",
            "config",
            "settings",
            "credentials",
            "secrets",
            ".git/",
        ]
        if any(pattern in path_str for pattern in high_risk_patterns):
            return "high"

        # Medium-risk paths
        medium_risk_patterns = ["__init__.py", "main.py", "app.py", "index"]
        if any(pattern in path_str for pattern in medium_risk_patterns):
            return "medium"

        return "low"

    def _assess_file_modify_risk(self, file_path: Path) -> str:
        """Assess risk level for file modification.

        Args:
            file_path: Path being modified

        Returns:
            Risk level
        """
        # Modifications slightly less risky than writes to same path
        write_risk = self._assess_file_write_risk(file_path)

        risk_map = {"critical": "high", "high": "medium", "medium": "low", "low": "low"}

        return risk_map.get(write_risk, "low")

    def _assess_command_risk(self, description: str) -> str:
        """Assess risk level for command execution.

        Args:
            description: Command description

        Returns:
            Risk level
        """
        description_lower = description.lower()

        # Critical commands
        critical_keywords = [
            "rm -rf",
            "sudo",
            "chmod",
            "chown",
            "dd",
            "format",
            "mkfs",
        ]
        if any(kw in description_lower for kw in critical_keywords):
            return "critical"

        # High-risk commands
        high_risk_keywords = [
            "delete",
            "remove",
            "drop",
            "truncate",
            "git reset --hard",
            "git push --force",
        ]
        if any(kw in description_lower for kw in high_risk_keywords):
            return "high"

        # Medium-risk commands
        medium_risk_keywords = ["install", "upgrade", "deploy", "publish", "commit"]
        if any(kw in description_lower for kw in medium_risk_keywords):
            return "medium"

        return "low"

    def _command_requires_approval(self, description: str) -> bool:
        """Check if command requires approval.

        Args:
            description: Command description

        Returns:
            True if approval required
        """
        risk = self._assess_command_risk(description)
        return risk in ("high", "critical")

    def _calculate_risk_summary(self, actions: list[DryRunAction]) -> dict:
        """Calculate risk summary across all actions.

        Args:
            actions: All actions

        Returns:
            Dictionary of risk counts
        """
        summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for action in actions:
            summary[action.risk_level] = summary.get(action.risk_level, 0) + 1

        return summary

    def _generate_warnings(self, actions: list[DryRunAction]) -> list[str]:
        """Generate warnings based on actions.

        Args:
            actions: All actions

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for critical actions
        critical_actions = [a for a in actions if a.risk_level == "critical"]
        if critical_actions:
            warnings.append(
                f"🚨 {len(critical_actions)} CRITICAL-risk actions detected! Review carefully."
            )

        # Check for deletions
        deletions = [a for a in actions if a.action_type == "file_delete"]
        if deletions:
            warnings.append(
                f"⚠️ {len(deletions)} file deletions - these cannot be undone without backups!"
            )

        # Check for irreversible actions
        irreversible = [a for a in actions if not a.reversible]
        if irreversible:
            warnings.append(
                f"⚠️ {len(irreversible)} irreversible actions - no automatic rollback available"
            )

        # Check for configuration changes
        config_changes = [
            a
            for a in actions
            if any(kw in a.target.lower() for kw in ["config", "settings", ".env", "credentials"])
        ]
        if config_changes:
            warnings.append(
                f"⚠️ {len(config_changes)} configuration file changes - may affect system behavior"
            )

        return warnings

    def _estimate_cost(self, plan: ExecutionPlan, actions: list[DryRunAction]) -> float:
        """Estimate execution cost.

        Args:
            plan: Execution plan
            actions: All actions

        Returns:
            Estimated cost in USD
        """
        # Simple estimation based on step count
        # Assume Haiku ($0.25 per 1M tokens, ~1000 tokens per step)
        cost_per_step = 0.00025
        return len(plan.steps) * cost_per_step

    def _estimate_duration(self, plan: ExecutionPlan, actions: list[DryRunAction]) -> float:
        """Estimate execution duration.

        Args:
            plan: Execution plan
            actions: All actions

        Returns:
            Estimated duration in seconds
        """
        # Simple estimation
        # File operations: 2s each
        # Commands: 5s each
        # API calls: 3s each

        duration = 0.0

        for action in actions:
            if action.action_type in ("file_write", "file_modify", "file_delete"):
                duration += 2.0
            elif action.action_type == "command":
                duration += 5.0
            elif action.action_type == "api_call":
                duration += 3.0
            else:
                duration += 1.0

        return duration

    def __repr__(self) -> str:
        """String representation."""
        return f"DryRunAnalyzer(workspace={self.workspace_dir})"
