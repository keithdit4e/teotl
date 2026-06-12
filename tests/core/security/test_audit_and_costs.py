"""Tests for audit logging and cost tracking."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from teotl.core.security.audit import AuditEntry, AuditLogger, LogLevel
from teotl.core.security.cost_tracker import CostRecord, CostTracker, RateLimiter
from teotl.core.security.policy import CostLimits, RateLimits, SecurityPolicy


class TestAuditEntry:
    """Test audit entry data structure."""

    def test_to_json(self):
        """Test serialization to JSON."""
        entry = AuditEntry(
            timestamp="2026-03-26T14:30:00Z",
            agent_id="test-agent",
            event_type="tool_call",
            tool="read_file",
            allowed=True,
            cost=0.001,
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        assert data["timestamp"] == "2026-03-26T14:30:00Z"
        assert data["agent_id"] == "test-agent"
        assert data["event_type"] == "tool_call"
        assert data["tool"] == "read_file"
        assert data["allowed"] is True
        assert data["cost"] == 0.001

    def test_from_json(self):
        """Test deserialization from JSON."""
        json_str = '{"timestamp":"2026-03-26T14:30:00Z","agent_id":"test-agent","event_type":"tool_call","tool":"read_file","allowed":true,"cost":0.001}'

        entry = AuditEntry.from_json(json_str)

        assert entry.timestamp == "2026-03-26T14:30:00Z"
        assert entry.agent_id == "test-agent"
        assert entry.event_type == "tool_call"
        assert entry.tool == "read_file"
        assert entry.allowed is True
        assert entry.cost == 0.001

    def test_none_values_omitted(self):
        """Test None values are omitted from JSON."""
        entry = AuditEntry(
            timestamp="2026-03-26T14:30:00Z",
            agent_id="test-agent",
            event_type="tool_call",
            tool=None,  # Will be omitted
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        assert "tool" not in data  # None value omitted


class TestAuditLogger:
    """Test audit logger."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            yield workspace

    @pytest.fixture
    def policy(self):
        """Create test policy."""
        return SecurityPolicy.create_default("test-agent", "moderate")

    @pytest.fixture
    def logger(self, policy, temp_workspace):
        """Create audit logger."""
        return AuditLogger(policy, temp_workspace)

    def test_log_file_creation(self, logger, temp_workspace):
        """Test log file is created."""
        audit_dir = temp_workspace / "audit"

        assert audit_dir.exists()

    def test_log_file_naming(self, logger):
        """Test log file uses YYYY-MM.jsonl format."""
        log_file = logger._get_current_log_file()

        now = datetime.now()
        expected = logger.audit_dir / f"{now.year}-{now.month:02d}.jsonl"

        assert log_file == expected

    @pytest.mark.asyncio
    async def test_log_tool_call(self, logger, temp_workspace):
        """Test logging tool call."""
        await logger.log_tool_call(
            tool_name="read_file",
            args={"path": "/tmp/test.txt"},
            allowed=True,
            cost=0.001,
        )

        # Check log file exists and has entry
        log_file = logger.current_file
        assert log_file.exists()

        with open(log_file) as f:
            line = f.readline()
            entry = AuditEntry.from_json(line.strip())

            assert entry.tool == "read_file"
            assert entry.allowed is True
            assert entry.cost == 0.001

    @pytest.mark.asyncio
    async def test_log_violation(self, logger, temp_workspace):
        """Test logging policy violation."""
        await logger.log_violation(
            policy_type="network",
            tool_or_resource="facebook.com",
            reason="Domain blocked",
        )

        with open(logger.current_file) as f:
            line = f.readline()
            entry = AuditEntry.from_json(line.strip())

            assert entry.event_type == "policy_violation"
            assert entry.policy_violated == "network"
            assert entry.allowed is False

    @pytest.mark.asyncio
    async def test_pii_redaction(self, logger):
        """Test PII redaction in logs."""
        args_with_pii = {
            "email": "user@example.com",
            "ssn": "123-45-6789",
            "phone": "555-123-4567",
        }

        await logger.log_tool_call(
            tool_name="test_tool",
            args=args_with_pii,
            allowed=True,
        )

        with open(logger.current_file) as f:
            line = f.readline()
            entry = AuditEntry.from_json(line.strip())

            # Email should be redacted
            assert "[EMAIL]" in str(entry.args)
            assert "user@example.com" not in str(entry.args)

            # SSN should be redacted
            assert "***-**-****" in str(entry.args)
            assert "123-45-6789" not in str(entry.args)

            assert entry.pii_redacted is True

    def test_log_level_minimal(self, temp_workspace):
        """Test minimal log level only logs violations."""
        policy = SecurityPolicy.create_default("test-agent", "moderate")
        policy.log_level = LogLevel.MINIMAL

        logger = AuditLogger(policy, temp_workspace)

        # Tool calls should not be logged
        assert not logger._should_log_event("tool_call")

        # Violations should be logged
        assert logger._should_log_event("policy_violation")

    def test_log_level_standard(self, logger):
        """Test standard log level logs violations and tool calls."""
        assert logger._should_log_event("tool_call")
        assert logger._should_log_event("policy_violation")
        assert logger._should_log_event("cost_limit")

    def test_read_logs(self, logger):
        """Test reading logs with filters."""
        # We'll need to create some log entries first
        # This would be an integration test

    def test_cleanup_old_logs(self, logger, temp_workspace):
        """Test cleaning up old log files."""
        # Create old log file
        old_date = datetime.now() - timedelta(days=365)
        old_file = logger.audit_dir / f"{old_date.year}-{old_date.month:02d}.jsonl"
        old_file.write_text("old log data\n")

        # Cleanup
        deleted = logger.cleanup_old_logs()

        assert deleted >= 1
        assert not old_file.exists()


class TestCostTracker:
    """Test cost tracking."""

    @pytest.fixture
    def temp_file(self):
        """Create temporary cost tracking file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()

    @pytest.fixture
    def limits(self):
        """Create cost limits."""
        return CostLimits(
            max_per_hour=5.0,
            max_per_day=50.0,
            max_per_month=500.0,
        )

    @pytest.fixture
    def tracker(self, limits, temp_file):
        """Create cost tracker."""
        return CostTracker(limits, temp_file)

    def test_initial_totals_zero(self, tracker):
        """Test initial cost totals are zero."""
        assert tracker.current_hour == 0.0
        assert tracker.current_day == 0.0
        assert tracker.current_month == 0.0

    def test_would_allow_within_limits(self, tracker):
        """Test cost within limits is allowed."""
        assert tracker.would_allow(1.0) is True
        assert tracker.would_allow(4.99) is True

    def test_would_allow_exceeds_hourly(self, tracker):
        """Test cost exceeding hourly limit is blocked."""
        # Record costs totaling 4.0 within the last hour
        tracker.record_cost("test_tool", 4.0)

        assert tracker.would_allow(1.01) is False  # Would exceed 5.0

    def test_would_allow_exceeds_daily(self, tracker):
        """Test cost exceeding daily limit is blocked."""
        # Record costs totaling 49.0 within the last day
        tracker.record_cost("test_tool", 49.0)

        assert tracker.would_allow(1.01) is False  # Would exceed 50.0

    def test_would_allow_exceeds_monthly(self, tracker):
        """Test cost exceeding monthly limit is blocked."""
        # Record costs totaling 499.0 within the last month
        tracker.record_cost("test_tool", 499.0)

        assert tracker.would_allow(1.01) is False  # Would exceed 500.0

    def test_record_cost(self, tracker):
        """Test recording cost."""
        tracker.record_cost("web_search", 0.001, tokens_used=100)

        assert len(tracker.records) == 1
        assert tracker.current_hour > 0
        assert tracker.records[0].tool == "web_search"
        assert tracker.records[0].cost == 0.001
        assert tracker.records[0].tokens_used == 100

    def test_get_remaining(self, tracker):
        """Test getting remaining budget."""
        now = datetime.now()

        # Add costs with different timestamps
        # 2.0 in last hour
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(minutes=30), tool="test_tool", cost=2.0)
        )
        # 18.0 in last day (but not in last hour)
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(hours=2), tool="test_tool", cost=18.0)
        )
        # 180.0 in this month (but not in last day)
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(days=2), tool="test_tool", cost=180.0)
        )

        remaining = tracker.get_remaining()

        assert remaining["hourly"] == 3.0  # 5.0 - 2.0
        assert remaining["daily"] == 30.0  # 50.0 - 20.0
        assert remaining["monthly"] == 300.0  # 500.0 - 200.0

    def test_get_current(self, tracker):
        """Test getting current spending."""
        now = datetime.now()

        # Add costs with different timestamps
        # 2.0 in last hour
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(minutes=30), tool="test_tool", cost=2.0)
        )
        # 18.0 in last day (but not in last hour)
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(hours=2), tool="test_tool", cost=18.0)
        )
        # 180.0 in this month (but not in last day)
        tracker.records.append(
            CostRecord(timestamp=now - timedelta(days=2), tool="test_tool", cost=180.0)
        )

        current = tracker.get_current()

        assert current["hourly"] == 2.0
        assert current["daily"] == 20.0
        assert current["monthly"] == 200.0

    def test_persistence(self, limits, temp_file):
        """Test cost data persists across restarts."""
        # Create tracker and record cost
        tracker1 = CostTracker(limits, temp_file)
        tracker1.record_cost("test_tool", 1.5)

        # Create new tracker (simulates restart)
        tracker2 = CostTracker(limits, temp_file)

        # Should have loaded previous data
        assert len(tracker2.records) > 0
        assert tracker2.current_hour > 0

    def test_cleanup_old_records(self, tracker):
        """Test cleanup of old cost records."""
        # Add old record
        old_timestamp = datetime.now() - timedelta(days=31)
        old_record = CostRecord(
            timestamp=old_timestamp,
            tool="old_tool",
            cost=1.0,
        )
        tracker.records.append(old_record)

        # Add recent record
        tracker.record_cost("new_tool", 0.5)

        # Cleanup
        tracker._cleanup_old_records()

        # Old record should be removed
        assert len(tracker.records) == 1
        assert tracker.records[0].tool == "new_tool"


class TestRateLimiter:
    """Test rate limiting."""

    @pytest.fixture
    def limits(self):
        """Create rate limits."""
        return RateLimits(max_api_calls_per_minute=10)

    @pytest.fixture
    def limiter(self, limits):
        """Create rate limiter."""
        return RateLimiter(limits)

    def test_initial_allows_calls(self, limiter):
        """Test initial state allows calls."""
        assert limiter.would_allow() is True

    def test_within_limit(self, limiter):
        """Test calls within limit are allowed."""
        for i in range(9):
            limiter.record_call(f"tool_{i}")

        assert limiter.would_allow() is True

    def test_at_limit(self, limiter):
        """Test at limit blocks calls."""
        for i in range(10):
            limiter.record_call(f"tool_{i}")

        assert limiter.would_allow() is False

    def test_get_current_rate(self, limiter):
        """Test getting current call rate."""
        for i in range(5):
            limiter.record_call(f"tool_{i}")

        rate = limiter.get_current_rate()

        assert rate == 5

    def test_cleanup_old_records(self, limiter):
        """Test cleanup of old rate records."""
        # Add old record
        from teotl.core.security.cost_tracker import RateRecord

        old_timestamp = datetime.now() - timedelta(hours=2)
        old_record = RateRecord(timestamp=old_timestamp, tool="old_tool")
        limiter.records.append(old_record)

        # Add recent record
        limiter.record_call("new_tool")

        # Cleanup
        limiter._cleanup_old_records()

        # Old record should be removed
        assert len(limiter.records) == 1


class TestCostRecord:
    """Test cost record serialization."""

    def test_to_dict(self):
        """Test converting to dict."""
        record = CostRecord(
            timestamp=datetime(2026, 3, 26, 14, 30, 0),
            tool="web_search",
            cost=0.001,
            tokens_used=100,
        )

        data = record.to_dict()

        assert data["timestamp"] == "2026-03-26T14:30:00"
        assert data["tool"] == "web_search"
        assert data["cost"] == 0.001
        assert data["tokens_used"] == 100

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "timestamp": "2026-03-26T14:30:00",
            "tool": "web_search",
            "cost": 0.001,
            "tokens_used": 100,
        }

        record = CostRecord.from_dict(data)

        assert record.timestamp == datetime(2026, 3, 26, 14, 30, 0)
        assert record.tool == "web_search"
        assert record.cost == 0.001
        assert record.tokens_used == 100
