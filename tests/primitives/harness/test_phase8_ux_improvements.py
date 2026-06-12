"""Integration tests for Phase 8 UX improvements.

Tests the following Phase 8 capabilities:
1. Read-only exploration mode
2. Dry-run capabilities
3. Enhanced step verification
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from teotl.primitives.harness.dryrun import DryRunAction, DryRunAnalyzer
from teotl.primitives.harness.explorer import ExplorationMode
from teotl.primitives.harness.plan import ExecutionPlan, PlanStep
from teotl.primitives.harness.verification import StepVerifier, VerificationResult


class TestExplorationMode:
    """Test read-only exploration mode."""

    @pytest.mark.asyncio
    async def test_exploration_initialization(self, tmp_path):
        """Test ExplorationMode initialization."""
        # Create mock provider
        mock_provider = Mock()

        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
            exploration_depth="thorough",
        )

        assert explorer.workspace_dir == tmp_path
        assert explorer.exploration_depth == "thorough"
        assert explorer.max_files_to_read == 50
        assert explorer.max_turns == 10

    @pytest.mark.asyncio
    async def test_explorer_system_prompt_generation(self, tmp_path):
        """Test exploration agent system prompt."""
        mock_provider = Mock()
        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        prompt = explorer._get_explorer_system_prompt()

        assert "READ-ONLY mode" in prompt
        assert str(tmp_path) in prompt
        assert "NO file modifications" in prompt
        assert "read_file" in prompt

    def test_build_exploration_prompt(self, tmp_path):
        """Test exploration prompt building."""
        mock_provider = Mock()
        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        prompt = explorer._build_exploration_prompt(
            goal="Understand authentication",
            questions=["Where is login handled?", "What session management is used?"],
            focus_areas=["auth", "users"],
        )

        assert "Understand authentication" in prompt
        assert "Where is login handled?" in prompt
        assert "What session management is used?" in prompt
        assert "auth, users" in prompt

    def test_extract_findings(self, tmp_path):
        """Test findings extraction from response."""
        mock_provider = Mock()
        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        response = """
        Here are my findings:
        - Authentication is handled in auth/login.py
        - Sessions use JWT tokens
        - Database is PostgreSQL

        Additional notes:
        1. Login endpoint is /api/auth/login
        2. Tokens expire after 24 hours
        3. Refresh tokens are supported
        """

        findings = explorer._extract_findings(response)

        assert len(findings) >= 5
        assert any("auth/login.py" in f for f in findings)
        assert any("JWT" in f for f in findings)

    def test_extract_file_mentions(self, tmp_path):
        """Test file path extraction from response."""
        mock_provider = Mock()
        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        response = """
        I found authentication in these files:
        - src/auth/login.py
        - src/auth/session.py
        - config/settings.json
        - tests/test_auth.py
        """

        files = explorer._extract_file_mentions(response)

        assert len(files) >= 3
        assert any("login.py" in f for f in files)
        assert any("session.py" in f for f in files)

    def test_identify_patterns(self, tmp_path):
        """Test pattern identification."""
        mock_provider = Mock()
        explorer = ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        findings = [
            "Found MVC architecture with controllers and models",
            "Services use repository pattern",
            "Authentication uses JWT tokens",
        ]

        patterns = explorer._identify_patterns(findings)

        assert len(patterns) >= 2
        # Should detect MVC and JWT patterns


class TestDryRunAnalyzer:
    """Test dry-run capabilities."""

    def test_dryrun_initialization(self, tmp_path):
        """Test DryRunAnalyzer initialization."""
        analyzer = DryRunAnalyzer(
            workspace_dir=tmp_path,
            enable_risk_analysis=True,
            enable_cost_estimation=True,
        )

        assert analyzer.workspace_dir == tmp_path
        assert analyzer.enable_risk_analysis is True
        assert analyzer.enable_cost_estimation is True

    def test_analyze_file_write_step(self, tmp_path):
        """Test analysis of file write operation."""
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Create new authentication module",
            file_path="src/auth/login.py",
        )

        actions = analyzer._analyze_step(step)

        assert len(actions) == 1
        assert actions[0].action_type == "file_write"
        assert "login.py" in actions[0].target
        assert actions[0].reversible is True

    def test_analyze_file_delete_step(self, tmp_path):
        """Test analysis of file deletion."""
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Delete old config file",
            file_path="config/old_settings.json",
        )

        actions = analyzer._analyze_step(step)

        assert len(actions) == 1
        assert actions[0].action_type == "file_delete"
        assert actions[0].risk_level == "high"
        assert actions[0].reversible is False
        assert actions[0].requires_approval is True

    def test_analyze_command_step(self, tmp_path):
        """Test analysis of command execution."""
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Run database migrations",
        )

        actions = analyzer._analyze_step(step)

        # Should detect command operation
        assert len(actions) >= 1

    def test_risk_assessment_critical_path(self, tmp_path):
        """Test risk assessment for critical paths."""
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        # Test critical path
        risk = analyzer._assess_file_write_risk(Path("/etc/passwd"))
        assert risk == "critical"

        # Test .env file
        risk = analyzer._assess_file_write_risk(Path(".env"))
        assert risk == "high"

        # Test normal file
        risk = analyzer._assess_file_write_risk(Path("src/utils.py"))
        assert risk in ("low", "medium")

    def test_risk_assessment_commands(self, tmp_path):
        """Test command risk assessment."""
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        # Critical command
        risk = analyzer._assess_command_risk("rm -rf /var/www")
        assert risk == "critical"

        # High-risk command
        risk = analyzer._assess_command_risk("git push --force origin main")
        assert risk == "high"

        # Medium-risk command
        risk = analyzer._assess_command_risk("npm install package")
        assert risk == "medium"

        # Low-risk command
        risk = analyzer._assess_command_risk("echo 'hello'")
        assert risk == "low"

    def test_analyze_plan(self, tmp_path):
        """Test analyzing full execution plan."""
        from datetime import datetime

        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        steps = [
            PlanStep(
                number=1,
                description="Create new auth module",
                file_path="src/auth/new_auth.py",
            ),
            PlanStep(
                number=2,
                description="Update main app",
                file_path="src/app.py",
            ),
            PlanStep(
                number=3,
                description="Delete old auth file",
                file_path="src/old_auth.py",
            ),
        ]
        plan = ExecutionPlan(
            goals="Refactor authentication",
            steps=steps,
            created_at=datetime.now(),
            created_by="test-model",
            total_steps=len(steps),
        )

        result = analyzer.analyze_plan(plan)

        assert result.success is True
        assert result.total_actions == 3
        assert len(result.file_writes) >= 1
        assert len(result.file_modifies) >= 1
        assert len(result.file_deletes) >= 1
        assert result.estimated_cost > 0.0
        assert result.estimated_duration_seconds > 0.0

    def test_dry_run_result_summary(self, tmp_path):
        """Test dry-run result summary generation."""
        from datetime import datetime

        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)

        steps = [
            PlanStep(number=1, description="Create file", file_path="test.py"),
            PlanStep(number=2, description="Delete file", file_path="old.py"),
        ]
        plan = ExecutionPlan(
            goals="Test plan",
            steps=steps,
            created_at=datetime.now(),
            created_by="test-model",
            total_steps=len(steps),
        )

        result = analyzer.analyze_plan(plan)
        summary = result.to_summary_text()

        assert "DRY-RUN PREVIEW" in summary
        assert "Total Actions:" in summary
        assert "Estimated Duration:" in summary

    def test_high_risk_actions_detection(self, tmp_path):
        """Test detection of high-risk actions."""
        result = DryRunAction(
            step_number=1,
            action_type="command",
            description="Force delete database",
            target="DROP DATABASE production",
            risk_level="critical",
            reversible=False,
            requires_approval=True,
        )

        from teotl.primitives.harness.dryrun import DryRunResult

        dry_run_result = DryRunResult(
            success=True,
            total_actions=1,
            actions=[result],
        )

        high_risk = dry_run_result.get_high_risk_actions()
        assert len(high_risk) == 1
        assert high_risk[0].risk_level == "critical"

    def test_requires_approval_detection(self, tmp_path):
        """Test approval requirement detection."""
        from teotl.primitives.harness.dryrun import DryRunResult

        # Action requiring approval
        action1 = DryRunAction(
            step_number=1,
            action_type="file_delete",
            description="Delete config",
            target="config.json",
            requires_approval=True,
        )

        # Action not requiring approval
        action2 = DryRunAction(
            step_number=2,
            action_type="file_write",
            description="Create file",
            target="test.py",
            requires_approval=False,
        )

        result = DryRunResult(
            success=True,
            total_actions=2,
            actions=[action1, action2],
        )

        assert result.requires_approval() is True


class TestStepVerifier:
    """Test enhanced step verification."""

    def test_verifier_initialization(self, tmp_path):
        """Test StepVerifier initialization."""
        verifier = StepVerifier(
            workspace_dir=tmp_path,
            enable_pattern_matching=True,
            enable_path_validation=True,
            strict_mode=True,
        )

        assert verifier.workspace_dir == tmp_path
        assert verifier.enable_pattern_matching is True
        assert verifier.strict_mode is True

    def test_verify_safe_step(self, tmp_path):
        """Test verification of safe step."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Create utility function for string formatting",
            file_path="src/utils/formatting.py",
        )

        result = verifier.verify_step(step)

        assert result.safe is True
        assert result.risk_level == "low"
        assert result.requires_approval is False

    def test_detect_recursive_delete(self, tmp_path):
        """Test detection of rm -rf pattern."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Run rm -rf /tmp/old_data to clean up",
        )

        result = verifier.verify_step(step)

        assert "recursive_delete" in result.detected_patterns
        assert result.risk_level in ("high", "critical")
        assert result.requires_approval is True
        assert len(result.warnings) > 0

    def test_detect_force_git_push(self, tmp_path):
        """Test detection of git push --force."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Execute git push --force origin main",
        )

        result = verifier.verify_step(step)

        assert "force_git_operations" in result.detected_patterns
        assert result.risk_level == "high"
        assert result.requires_approval is True

    def test_detect_database_drop(self, tmp_path):
        """Test detection of DROP DATABASE."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="DROP DATABASE old_test_db",
        )

        result = verifier.verify_step(step)

        assert "database_drop" in result.detected_patterns
        assert result.risk_level == "critical"
        assert result.requires_approval is True

    def test_detect_chmod_777(self, tmp_path):
        """Test detection of overly permissive chmod."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="chmod 777 /var/www/uploads",
        )

        result = verifier.verify_step(step)

        assert "chmod_777" in result.detected_patterns
        assert result.risk_level == "high"
        assert len(result.suggestions) > 0

    def test_validate_sensitive_file_path(self, tmp_path):
        """Test validation of sensitive file paths."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Update environment variables",
            file_path=".env",
        )

        result = verifier.verify_step(step)

        assert result.risk_level in ("high", "critical")
        assert result.requires_approval is True
        assert any("Sensitive file" in w for w in result.warnings)

    def test_validate_critical_system_path(self, tmp_path):
        """Test validation of critical system paths."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Modify system configuration",
            file_path="/etc/passwd",
        )

        result = verifier.verify_step(step)

        assert result.risk_level == "critical"
        assert result.requires_approval is True
        assert any("Critical system path" in w for w in result.warnings)

    def test_detect_vague_description(self, tmp_path):
        """Test detection of vague step descriptions."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description="Fix bug",
        )

        result = verifier.verify_step(step)

        assert "vague_description" in result.detected_patterns
        assert any("vague" in w.lower() for w in result.warnings)
        assert any("specific" in s.lower() for s in result.suggestions)

    def test_detect_hardcoded_credentials(self, tmp_path):
        """Test detection of hardcoded credentials."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        step = PlanStep(
            number=1,
            description='Set API_KEY = "sk-1234567890abcdef" in config',
        )

        result = verifier.verify_step(step)

        assert "hardcoded_credential" in result.detected_patterns
        assert result.risk_level == "high"
        assert any("environment variable" in s.lower() for s in result.suggestions)

    def test_strict_mode_blocks_critical(self, tmp_path):
        """Test strict mode blocks critical operations."""
        verifier = StepVerifier(workspace_dir=tmp_path, strict_mode=True)

        step = PlanStep(
            number=1,
            description="DROP DATABASE production",
        )

        result = verifier.verify_step(step)

        assert result.safe is False
        assert result.risk_level == "critical"
        assert "blocked in strict mode" in result.reason

    def test_verify_entire_plan(self, tmp_path):
        """Test verifying entire execution plan."""
        from datetime import datetime

        verifier = StepVerifier(workspace_dir=tmp_path)

        steps = [
            PlanStep(
                number=1,
                description="Create new module",
                file_path="src/new_module.py",
            ),
            PlanStep(
                number=2,
                description="Update imports",
                file_path="src/main.py",
            ),
            PlanStep(
                number=3,
                description="Delete old module",
                file_path="src/old_module.py",
            ),
        ]
        plan = ExecutionPlan(
            goals="Refactor code",
            steps=steps,
            created_at=datetime.now(),
            created_by="test-model",
            total_steps=len(steps),
        )

        results = verifier.verify_plan(plan)

        assert len(results) == 3
        assert all(isinstance(r, VerificationResult) for r in results)

    def test_confidence_calculation(self, tmp_path):
        """Test confidence score calculation."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        # High confidence - no warnings
        confidence = verifier._calculate_confidence(warnings=[], patterns=[])
        assert confidence == 1.0

        # Medium confidence - few warnings
        confidence = verifier._calculate_confidence(
            warnings=["Warning 1", "Warning 2"], patterns=["pattern1"]
        )
        assert 0.5 <= confidence < 1.0

        # Low confidence - many warnings
        confidence = verifier._calculate_confidence(
            warnings=["W1", "W2", "W3", "W4", "W5"],
            patterns=["P1", "P2", "P3"],
        )
        assert 0.0 <= confidence <= 0.6

    def test_max_risk_level(self, tmp_path):
        """Test maximum risk level calculation."""
        verifier = StepVerifier(workspace_dir=tmp_path)

        assert verifier._max_risk_level("low", "medium") == "medium"
        assert verifier._max_risk_level("high", "medium") == "high"
        assert verifier._max_risk_level("critical", "high") == "critical"
        assert verifier._max_risk_level("low", "low") == "low"


class TestPhase8Integration:
    """Integration tests combining Phase 8 features."""

    def test_exploration_then_dryrun_workflow(self, tmp_path):
        """Test workflow: explore codebase, then dry-run changes."""
        from datetime import datetime

        # Phase 1: Explore
        mock_provider = Mock()
        ExplorationMode(
            workspace_dir=tmp_path,
            provider=mock_provider,
        )

        # Phase 2: Create plan based on exploration
        steps = [
            PlanStep(
                number=1,
                description="Create new auth module",
                file_path="src/auth/new_auth.py",
            ),
        ]
        plan = ExecutionPlan(
            goals="Based on exploration, refactor auth",
            steps=steps,
            created_at=datetime.now(),
            created_by="test-model",
            total_steps=len(steps),
        )

        # Phase 3: Dry-run the plan
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)
        dry_run_result = analyzer.analyze_plan(plan)

        assert dry_run_result.success is True
        assert dry_run_result.total_actions >= 1

    def test_verify_then_dryrun_workflow(self, tmp_path):
        """Test workflow: verify steps, then dry-run if safe."""
        from datetime import datetime

        steps = [
            PlanStep(
                number=1,
                description="Create utility function",
                file_path="src/utils.py",
            ),
        ]
        plan = ExecutionPlan(
            goals="Safe refactoring",
            steps=steps,
            created_at=datetime.now(),
            created_by="test-model",
            total_steps=len(steps),
        )

        # Phase 1: Verify each step
        verifier = StepVerifier(workspace_dir=tmp_path)
        verification_results = verifier.verify_plan(plan)

        # All steps should be safe
        assert all(r.safe for r in verification_results)

        # Phase 2: If safe, dry-run
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)
        dry_run_result = analyzer.analyze_plan(plan)

        assert dry_run_result.success is True

    def test_dangerous_operation_caught_by_multiple_checks(self, tmp_path):
        """Test that dangerous operation is caught by both verifier and dry-run."""
        dangerous_step = PlanStep(
            number=1,
            description="rm -rf /important/data",
        )

        # Verification should detect danger
        verifier = StepVerifier(workspace_dir=tmp_path)
        verify_result = verifier.verify_step(dangerous_step)

        assert verify_result.risk_level in ("high", "critical")
        assert verify_result.requires_approval is True

        # Dry-run should also detect danger
        analyzer = DryRunAnalyzer(workspace_dir=tmp_path)
        actions = analyzer._analyze_step(dangerous_step)

        assert any(a.risk_level in ("high", "critical") for a in actions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
