"""Enhanced step verification with pattern matching for destructive operations.

Provides sophisticated safety checks beyond basic policy enforcement,
detecting dangerous patterns and anti-patterns in planned steps.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from teotl.primitives.harness.plan import PlanStep

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of step verification."""

    safe: bool
    confidence: float = 1.0  # 0.0 to 1.0
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    requires_approval: bool = False
    metadata: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow using result in boolean context.

        Returns:
            True if safe
        """
        return self.safe


@dataclass
class DestructivePattern:
    """Pattern for detecting destructive operations."""

    name: str
    pattern: str  # Regex pattern
    risk_level: str
    requires_approval: bool
    description: str
    suggestion: str = ""


class StepVerifier:
    """Enhanced step verification with pattern matching.

    Usage:
        verifier = StepVerifier(
            workspace_dir=Path("~/my-project"),
            enable_pattern_matching=True,
        )

        # Verify a step
        result = verifier.verify_step(step)

        if not result.safe:
            print(f"⚠️ Unsafe step: {result.reason}")
            for warning in result.warnings:
                print(f"  • {warning}")

        if result.requires_approval:
            approved = get_user_approval(step, result)
            if not approved:
                raise StepRejectedError()

    Benefits:
    - Detect dangerous patterns before execution
    - Provide actionable suggestions
    - Catch anti-patterns and code smells
    - Reduce risk of data loss or corruption
    - Build user confidence through transparency
    """

    # Destructive patterns database
    DESTRUCTIVE_PATTERNS = [
        DestructivePattern(
            name="recursive_delete",
            pattern=r"rm\s+-rf?\s+",
            risk_level="critical",
            requires_approval=True,
            description="Recursive file deletion detected",
            suggestion="Consider deleting specific files instead of entire directories",
        ),
        DestructivePattern(
            name="force_git_operations",
            pattern=r"git\s+(push|reset)\s+--force",
            risk_level="high",
            requires_approval=True,
            description="Force git operation detected",
            suggestion="Use --force-with-lease instead of --force for safer pushes",
        ),
        DestructivePattern(
            name="database_drop",
            pattern=r"DROP\s+(DATABASE|TABLE|SCHEMA)",
            risk_level="critical",
            requires_approval=True,
            description="Database drop operation detected",
            suggestion="Consider backing up data before dropping",
        ),
        DestructivePattern(
            name="truncate_table",
            pattern=r"TRUNCATE\s+TABLE",
            risk_level="high",
            requires_approval=True,
            description="Table truncation detected",
            suggestion="Use DELETE with WHERE clause for safer data removal",
        ),
        DestructivePattern(
            name="delete_without_where",
            pattern=r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",
            risk_level="high",
            requires_approval=True,
            description="DELETE without WHERE clause detected",
            suggestion="Add WHERE clause to avoid deleting all records",
        ),
        DestructivePattern(
            name="chmod_777",
            pattern=r"chmod\s+777",
            risk_level="high",
            requires_approval=True,
            description="Overly permissive file permissions (777)",
            suggestion="Use more restrictive permissions (e.g., 644 for files, 755 for dirs)",
        ),
        DestructivePattern(
            name="sudo_command",
            pattern=r"sudo\s+",
            risk_level="high",
            requires_approval=True,
            description="Elevated privileges (sudo) detected",
            suggestion="Ensure command absolutely requires root privileges",
        ),
        DestructivePattern(
            name="format_disk",
            pattern=r"(mkfs|format)\s+",
            risk_level="critical",
            requires_approval=True,
            description="Disk formatting operation detected",
            suggestion="Verify target device carefully before proceeding",
        ),
        DestructivePattern(
            name="overwrite_config",
            pattern=r">\s*(/etc/|\.env|config\.|settings\.)",
            risk_level="medium",
            requires_approval=True,
            description="Configuration file overwrite detected",
            suggestion="Consider backing up configuration before overwriting",
        ),
        DestructivePattern(
            name="drop_production",
            pattern=r"(production|prod|live).*DROP",
            risk_level="critical",
            requires_approval=True,
            description="Production database operation detected",
            suggestion="Never drop production databases without explicit approval",
        ),
    ]

    # Sensitive file patterns
    SENSITIVE_FILE_PATTERNS = [
        r"\.env$",
        r"\.env\.",
        r"credentials",
        r"secrets",
        r"password",
        r"private[_-]?key",
        r"id_rsa",
        r"\.pem$",
        r"\.key$",
        r"\.p12$",
        r"\.pfx$",
        r"auth[_-]?token",
        r"api[_-]?key",
    ]

    # Critical system paths
    CRITICAL_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/etc/ssh",
        "/etc/fstab",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
    ]

    def __init__(
        self,
        workspace_dir: Path,
        enable_pattern_matching: bool = True,
        enable_path_validation: bool = True,
        enable_content_analysis: bool = True,
        strict_mode: bool = False,
    ):
        """Initialize step verifier.

        Args:
            workspace_dir: Project workspace directory
            enable_pattern_matching: Enable destructive pattern detection
            enable_path_validation: Validate file paths
            enable_content_analysis: Analyze step content for risks
            strict_mode: Stricter verification (more false positives)
        """
        self.workspace_dir = Path(workspace_dir).expanduser().resolve()
        self.enable_pattern_matching = enable_pattern_matching
        self.enable_path_validation = enable_path_validation
        self.enable_content_analysis = enable_content_analysis
        self.strict_mode = strict_mode

        logger.info(f"StepVerifier initialized: {self.workspace_dir}")

    def verify_step(self, step: PlanStep) -> VerificationResult:
        """Verify step safety with pattern matching.

        Args:
            step: Plan step to verify

        Returns:
            VerificationResult with safety assessment

        Example:
            result = verifier.verify_step(step)
            if not result:
                raise StepRejectedError(result.reason)
        """
        warnings = []
        suggestions = []
        detected_patterns = []
        risk_level = "low"
        requires_approval = False

        # Pattern matching
        if self.enable_pattern_matching:
            pattern_result = self._check_destructive_patterns(step)
            if pattern_result:
                warnings.extend(pattern_result.get("warnings", []))
                suggestions.extend(pattern_result.get("suggestions", []))
                detected_patterns.extend(pattern_result.get("patterns", []))
                risk_level = self._max_risk_level(
                    risk_level, pattern_result.get("risk_level", "low")
                )
                requires_approval = requires_approval or pattern_result.get(
                    "requires_approval", False
                )

        # Path validation
        if self.enable_path_validation and step.file_path:
            path_result = self._validate_file_path(step.file_path, step.description)
            if path_result:
                warnings.extend(path_result.get("warnings", []))
                suggestions.extend(path_result.get("suggestions", []))
                risk_level = self._max_risk_level(risk_level, path_result.get("risk_level", "low"))
                requires_approval = requires_approval or path_result.get("requires_approval", False)

        # Content analysis
        if self.enable_content_analysis:
            content_result = self._analyze_step_content(step)
            if content_result:
                warnings.extend(content_result.get("warnings", []))
                suggestions.extend(content_result.get("suggestions", []))
                detected_patterns.extend(content_result.get("patterns", []))
                risk_level = self._max_risk_level(
                    risk_level, content_result.get("risk_level", "low")
                )

        # Determine safety
        safe = True
        reason = ""

        if risk_level == "critical":
            if self.strict_mode:
                safe = False
                reason = "Critical risk detected - step blocked in strict mode"
            else:
                requires_approval = True

        # Build result
        result = VerificationResult(
            safe=safe,
            confidence=self._calculate_confidence(warnings, detected_patterns),
            reason=reason,
            warnings=warnings,
            suggestions=suggestions,
            detected_patterns=detected_patterns,
            risk_level=risk_level,
            requires_approval=requires_approval,
            metadata={
                "step_number": step.number,
                "step_description": step.description,
            },
        )

        return result

    def _check_destructive_patterns(self, step: PlanStep) -> dict | None:
        """Check for destructive patterns in step.

        Args:
            step: Plan step

        Returns:
            Dictionary with warnings and suggestions, or None
        """
        warnings = []
        suggestions = []
        patterns_found = []
        max_risk = "low"
        requires_approval = False

        # Check step description and file_path
        text_to_check = f"{step.description} {step.file_path or ''}"

        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern.pattern, text_to_check, re.IGNORECASE):
                patterns_found.append(pattern.name)
                warnings.append(f"⚠️ {pattern.description}")

                if pattern.suggestion:
                    suggestions.append(f"💡 {pattern.suggestion}")

                max_risk = self._max_risk_level(max_risk, pattern.risk_level)
                requires_approval = requires_approval or pattern.requires_approval

        if patterns_found:
            return {
                "warnings": warnings,
                "suggestions": suggestions,
                "patterns": patterns_found,
                "risk_level": max_risk,
                "requires_approval": requires_approval,
            }

        return None

    def _validate_file_path(self, file_path: str, description: str) -> dict | None:
        """Validate file path for safety.

        Args:
            file_path: File path from step
            description: Step description

        Returns:
            Dictionary with validation results, or None
        """
        warnings = []
        suggestions = []
        risk_level = "low"
        requires_approval = False

        # Check both original and resolved paths for pattern matching
        # For relative paths, resolve relative to workspace_dir
        original_path = Path(file_path).expanduser()
        if original_path.is_absolute():
            resolved_path = original_path.resolve()
        else:
            # Relative paths should be resolved relative to workspace
            resolved_path = (self.workspace_dir / original_path).resolve()
        original_str = str(original_path).lower()
        resolved_str = str(resolved_path).lower()

        # Check critical paths (check both original and resolved for symlink compatibility)
        for critical_path in self.CRITICAL_PATHS:
            critical_lower = critical_path.lower()
            if original_str.startswith(critical_lower) or resolved_str.startswith(critical_lower):
                warnings.append(f"🚨 Critical system path: {critical_path}")
                suggestions.append("Verify this operation is absolutely necessary and approved")
                risk_level = "critical"
                requires_approval = True
                break

        # Check sensitive files
        for pattern in self.SENSITIVE_FILE_PATTERNS:
            if re.search(pattern, resolved_str, re.IGNORECASE):
                warnings.append(f"🔐 Sensitive file pattern detected: {pattern}")
                suggestions.append(
                    "Ensure credentials/secrets are not committed to version control"
                )
                risk_level = self._max_risk_level(risk_level, "high")
                requires_approval = True
                break

        # Check if path exists (for deletions)
        if any(kw in description.lower() for kw in ["delete", "remove", "unlink", "rm"]):
            if resolved_path.exists():
                if resolved_path.is_dir():
                    file_count = sum(1 for _ in resolved_path.rglob("*"))
                    warnings.append(f"📁 Deleting directory with {file_count} files/subdirectories")
                    suggestions.append("Consider moving to trash instead of permanent deletion")
                    risk_level = self._max_risk_level(risk_level, "high")
                    requires_approval = True
                else:
                    warnings.append(f"🗑️ Deleting file: {resolved_path.name}")
                    risk_level = self._max_risk_level(risk_level, "medium")

        # Check if outside workspace (use resolved paths for accurate comparison)
        try:
            resolved_path.relative_to(self.workspace_dir.resolve())
        except ValueError:
            # Only flag as outside workspace if it's not a relative path in workspace
            # Relative paths like "src/utils/formatting.py" shouldn't trigger this
            if resolved_path.is_absolute() or str(original_path).startswith("/"):
                warnings.append(f"⚠️ Path outside workspace: {resolved_path}")
                suggestions.append("Verify path is correct and operation is authorized")
                risk_level = self._max_risk_level(risk_level, "high")
                requires_approval = True

        if warnings:
            return {
                "warnings": warnings,
                "suggestions": suggestions,
                "risk_level": risk_level,
                "requires_approval": requires_approval,
            }

        return None

    def _analyze_step_content(self, step: PlanStep) -> dict | None:
        """Analyze step content for risks.

        Args:
            step: Plan step

        Returns:
            Dictionary with analysis results, or None
        """
        warnings = []
        suggestions = []
        patterns = []
        risk_level = "low"

        description_lower = step.description.lower()

        # Check for vague descriptions
        vague_keywords = ["fix", "update", "change", "modify", "refactor"]
        if any(kw in description_lower for kw in vague_keywords):
            if len(step.description.split()) < 5:
                warnings.append("⚠️ Step description is vague")
                suggestions.append("More specific descriptions help verify step correctness")
                patterns.append("vague_description")

        # Check for multiple operations in one step
        multi_op_keywords = ["and then", "after that", "also", "as well as"]
        if any(kw in description_lower for kw in multi_op_keywords):
            warnings.append("⚠️ Step appears to contain multiple operations")
            suggestions.append("Consider splitting into separate steps for better control")
            patterns.append("multi_operation")

        # Check for missing file path when needed
        file_keywords = ["create", "write", "modify", "delete", "update"]
        if any(kw in description_lower for kw in file_keywords) and not step.file_path:
            warnings.append("⚠️ File operation without specified file path")
            suggestions.append("Add file_path to step for clarity")
            patterns.append("missing_file_path")

        # Check for hardcoded credentials
        credential_patterns = [
            r"password\s*=\s*[\"']",
            r"api[_-]?key\s*=\s*[\"']",
            r"secret\s*=\s*[\"']",
            r"token\s*=\s*[\"']",
        ]
        for pattern in credential_patterns:
            if re.search(pattern, step.description, re.IGNORECASE):
                warnings.append("🔐 Possible hardcoded credential in description")
                suggestions.append("Use environment variables for sensitive data")
                risk_level = self._max_risk_level(risk_level, "high")
                patterns.append("hardcoded_credential")
                break

        if warnings:
            return {
                "warnings": warnings,
                "suggestions": suggestions,
                "patterns": patterns,
                "risk_level": risk_level,
            }

        return None

    def _max_risk_level(self, level1: str, level2: str) -> str:
        """Get maximum risk level between two levels.

        Args:
            level1: First risk level
            level2: Second risk level

        Returns:
            Maximum risk level
        """
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        score1 = risk_order.get(level1, 0)
        score2 = risk_order.get(level2, 0)

        max_score = max(score1, score2)

        for level, score in risk_order.items():
            if score == max_score:
                return level

        return "low"

    def _calculate_confidence(self, warnings: list[str], patterns: list[str]) -> float:
        """Calculate confidence score.

        Args:
            warnings: List of warnings
            patterns: List of detected patterns

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Start with high confidence
        confidence = 1.0

        # Reduce confidence for each warning
        confidence -= len(warnings) * 0.1

        # Reduce confidence for detected patterns
        confidence -= len(patterns) * 0.05

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def verify_plan(self, plan) -> list[VerificationResult]:
        """Verify entire execution plan.

        Args:
            plan: Execution plan

        Returns:
            List of verification results (one per step)
        """
        results = []

        for step in plan.steps:
            result = self.verify_step(step)
            results.append(result)

        return results

    def __repr__(self) -> str:
        """String representation."""
        return f"StepVerifier(workspace={self.workspace_dir}, strict={self.strict_mode})"
