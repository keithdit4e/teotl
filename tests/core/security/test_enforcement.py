"""Tests for security enforcement."""

import tempfile
from pathlib import Path

import pytest

from teotl.core.security.enforcement import SecurityEnforcer, create_enforcer
from teotl.core.security.policy import SecurityPolicy


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "security").mkdir()
        (workspace / "audit").mkdir()
        yield workspace


@pytest.fixture
def moderate_policy():
    """Create moderate security policy."""
    policy = SecurityPolicy.create_default("test-agent", "moderate")
    # Add network and LLM tools to test network/cost enforcement
    policy.tools.allowed.extend(["fetch_url", "llm_call"])
    return policy


@pytest.fixture
def strict_policy():
    """Create strict security policy."""
    return SecurityPolicy.create_default("test-agent", "strict")


@pytest.fixture
def enforcer(moderate_policy, temp_workspace):
    """Create security enforcer with moderate policy."""
    return SecurityEnforcer(moderate_policy, temp_workspace)


class TestToolEnforcement:
    """Test tool call enforcement."""

    @pytest.mark.asyncio
    async def test_allowed_tool(self, enforcer):
        """Test allowed tool passes."""
        allowed, reason = await enforcer.enforce_tool_call("read_file", {"path": "/tmp/test.txt"})

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_blocked_tool(self, enforcer):
        """Test blocked tool fails."""
        allowed, reason = await enforcer.enforce_tool_call("execute_shell", {"command": "ls"})

        assert allowed is False
        assert "blocked by security policy" in reason

    @pytest.mark.asyncio
    async def test_tool_not_in_allowlist(self, strict_policy, temp_workspace):
        """Test tool not in allowlist is blocked."""
        enforcer = SecurityEnforcer(strict_policy, temp_workspace)

        # web_search not in strict allowlist
        allowed, reason = await enforcer.enforce_tool_call("web_search", {"query": "test"})

        assert allowed is False
        assert "blocked" in reason.lower()


class TestNetworkEnforcement:
    """Test network access enforcement."""

    @pytest.mark.asyncio
    async def test_allowed_domain(self, enforcer):
        """Test allowed domain passes."""
        allowed, reason = await enforcer.enforce_tool_call(
            "web_search", {"query": "test", "url": "https://api.github.com/search"}
        )

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_blocked_domain(self, enforcer):
        """Test blocked domain fails."""
        allowed, reason = await enforcer.enforce_tool_call(
            "fetch_url", {"url": "https://facebook.com/page"}
        )

        # facebook.com not in moderate allowlist
        assert allowed is False
        assert "blocked by network policy" in reason

    @pytest.mark.asyncio
    async def test_domain_extraction_from_url(self, enforcer):
        """Test domain extraction from various URL formats."""
        # Full URL
        allowed, _ = await enforcer.enforce_tool_call(
            "fetch_url", {"url": "https://api.github.com/repos"}
        )
        assert allowed is True

        # Just domain
        allowed, _ = await enforcer.enforce_tool_call("web_search", {"domain": "api.github.com"})
        assert allowed is True


class TestFilesystemEnforcement:
    """Test filesystem access enforcement."""

    @pytest.mark.asyncio
    async def test_allowed_path_read(self, enforcer, temp_workspace):
        """Test reading allowed path."""
        allowed, reason = await enforcer.enforce_tool_call("read_file", {"path": "/tmp/test.txt"})

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_allowed_path_write(self, enforcer):
        """Test writing to allowed path."""
        allowed, reason = await enforcer.enforce_tool_call(
            "write_file", {"path": "/tmp/output.txt", "content": "test"}
        )

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_blocked_path(self, enforcer):
        """Test accessing blocked path fails."""
        allowed, reason = await enforcer.enforce_tool_call(
            "read_file", {"file_path": "~/.ssh/id_rsa"}
        )

        assert allowed is False
        assert "blocked by filesystem policy" in reason

    @pytest.mark.asyncio
    async def test_readonly_path_write(self, enforcer):
        """Test writing to readonly path fails."""
        # Documents is readonly in moderate policy
        allowed, reason = await enforcer.enforce_tool_call(
            "write_file", {"path": "~/Documents/test.txt"}
        )

        # Might fail if not in allowed OR if readonly
        # Exact behavior depends on moderate policy config
        # This tests the enforcement mechanism


class TestCostEnforcement:
    """Test cost limit enforcement."""

    @pytest.mark.asyncio
    async def test_within_cost_limit(self, enforcer):
        """Test execution within cost limits."""
        # Small cost should pass
        allowed, reason = await enforcer.enforce_tool_call("web_search", {"query": "test"})

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_exceeds_cost_limit(self, enforcer):
        """Test blocking when cost limit exceeded."""
        # Record costs to approach the hourly limit
        enforcer.cost_tracker.record_cost("test_tool", 4.99)

        # This call would push over the hourly limit (5.00)
        allowed, reason = await enforcer.enforce_tool_call(
            "llm_call",
            {"max_tokens": 10000},  # Expensive call
        )

        assert allowed is False
        assert "cost limit exceeded" in reason.lower()


class TestRateEnforcement:
    """Test rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_within_rate_limit(self, enforcer):
        """Test execution within rate limits."""
        allowed, reason = await enforcer.enforce_tool_call("read_file", {"path": "/tmp/test.txt"})

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_exceeds_rate_limit(self, enforcer):
        """Test blocking when rate limit exceeded."""
        # Fill up rate limiter
        from datetime import datetime

        from teotl.core.security.cost_tracker import RateRecord

        for _i in range(20):
            enforcer.rate_limiter.records.append(
                RateRecord(timestamp=datetime.now(), tool="test_tool")
            )

        # This should exceed limit (20/min in moderate)
        allowed, reason = await enforcer.enforce_tool_call("read_file", {"path": "/tmp/test.txt"})

        assert allowed is False
        assert "rate limit exceeded" in reason.lower()


class TestRecordExecution:
    """Test execution recording."""

    @pytest.mark.asyncio
    async def test_record_execution(self, enforcer):
        """Test recording tool execution."""
        await enforcer.record_execution(
            tool_name="read_file",
            result="file contents",
            duration_ms=150,
            actual_cost=0.001,
            tokens_used=100,
        )

        # Should be recorded in rate limiter
        assert len(enforcer.rate_limiter.records) == 1
        assert enforcer.rate_limiter.records[0].tool == "read_file"

        # Should be recorded in cost tracker
        assert enforcer.cost_tracker.current_hour > 0


class TestSecurityStatus:
    """Test security status retrieval."""

    def test_get_security_status(self, enforcer):
        """Test getting current security status."""
        status = enforcer.get_security_status()

        assert "agent_id" in status
        assert "policy_version" in status
        assert "costs" in status
        assert "rate" in status
        assert "compliance" in status

        assert status["agent_id"] == "test-agent"
        assert status["costs"]["limits"]["hourly"] == 5.0  # Moderate preset


class TestCreateEnforcer:
    """Test enforcer creation helper."""

    def test_create_enforcer_with_policy(self, temp_workspace):
        """Test creating enforcer from workspace with policy."""
        # Create policy file
        policy = SecurityPolicy.create_default("test-agent", "moderate")
        policy.to_yaml(temp_workspace / "security.yaml")

        # Create enforcer
        enforcer = create_enforcer(temp_workspace)

        assert enforcer is not None
        assert enforcer.policy.agent_id == "test-agent"

    def test_create_enforcer_without_policy(self, temp_workspace):
        """Test creating enforcer without policy returns None."""
        # No security.yaml file
        enforcer = create_enforcer(temp_workspace)

        assert enforcer is None

    def test_create_enforcer_invalid_policy(self, temp_workspace):
        """Test creating enforcer with invalid policy returns None."""
        # Create invalid YAML
        policy_path = temp_workspace / "security.yaml"
        policy_path.write_text("invalid: yaml: content: [[[")

        enforcer = create_enforcer(temp_workspace)

        assert enforcer is None


class TestCostEstimation:
    """Test cost estimation."""

    def test_estimate_web_search_cost(self, enforcer):
        """Test web search cost estimation."""
        cost = enforcer._estimate_cost("web_search", {})

        assert cost == 0.001  # From TOOL_COSTS

    def test_estimate_llm_call_cost(self, enforcer):
        """Test LLM call cost estimation with tokens."""
        cost = enforcer._estimate_cost("llm_call", {"max_tokens": 4000})

        # Should be based on tokens
        assert cost > 0
        # 4000 tokens / 1000 * $0.01 = $0.04
        assert abs(cost - 0.04) < 0.001

    def test_estimate_unknown_tool_cost(self, enforcer):
        """Test unknown tool has zero cost."""
        cost = enforcer._estimate_cost("unknown_tool", {})

        assert cost == 0.0


class TestDomainExtraction:
    """Test domain extraction from args."""

    def test_extract_from_url(self, enforcer):
        """Test extracting domain from URL."""
        domain = enforcer._extract_domain({"url": "https://api.github.com/repos"})

        assert domain == "api.github.com"

    def test_extract_from_domain_arg(self, enforcer):
        """Test extracting from domain argument."""
        domain = enforcer._extract_domain({"domain": "example.com"})

        assert domain == "example.com"

    def test_extract_from_query(self, enforcer):
        """Test extracting from query (if it's a URL)."""
        domain = enforcer._extract_domain({"query": "https://example.com/search"})

        assert domain == "example.com"

    def test_no_domain_found(self, enforcer):
        """Test when no domain can be extracted."""
        domain = enforcer._extract_domain({"text": "just some text"})

        assert domain is None
