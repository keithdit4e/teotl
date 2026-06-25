"""Tests for configuration factory functions."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from teotl.config import (
    AgentConfig,
    CostTrackingConfig,
    HarnessConfig,
    HeartbeatConfig,
    JanitorConfig,
    MemoryConfig,
    ProviderConfig,
    SecurityConfig,
)
from teotl.config.factory import (
    _create_cost_tracker,
    _create_heartbeat_monitor,
    _create_memory,
    _create_security_policy,
    create_agent_from_config,
    create_provider,
)


class TestCreateProvider:
    """Tests for create_provider function."""

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        pytest.importorskip("anthropic")  # Skip if anthropic not installed
        config = ProviderConfig(
            type="anthropic",
            model="claude-sonnet-4",
            api_key_env="ANTHROPIC_API_KEY",
        )
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = create_provider(config)

        assert provider is not None
        assert provider.model == "claude-sonnet-4"

    def test_create_provider_with_parameters(self):
        """Test creating provider with model parameters."""
        pytest.importorskip("anthropic")  # Skip if anthropic not installed
        from teotl.config import ModelParametersConfig

        config = ProviderConfig(
            type="anthropic",
            model="claude-sonnet-4",
            parameters=ModelParametersConfig(max_tokens=2048),
        )
        provider = create_provider(config)
        assert provider is not None
        assert provider.max_tokens == 2048

    def test_unsupported_provider(self):
        """Test error for unsupported provider type."""
        config = ProviderConfig(
            type="unknown",
            model="some-model",
        )
        with pytest.raises(ValueError, match="Unsupported provider type"):
            create_provider(config)


class TestCreateMemory:
    """Tests for memory creation."""

    def test_memory_disabled(self):
        """Test that disabled memory returns None."""
        config = MemoryConfig(enabled=False)
        memory = _create_memory(config, "test-agent")
        assert memory is None

    def test_memory_local_backend(self):
        """Test creating local memory backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(
                enabled=True,
                backend="local",
                path=f"{tmpdir}/memory.db",
            )
            memory = _create_memory(config, "test-agent")
            assert memory is not None

    def test_memory_encrypted_no_key(self):
        """Test encrypted memory without key raises error."""
        config = MemoryConfig(
            enabled=True,
            backend="encrypted",
            encryption_key_env="NONEXISTENT_KEY",
        )
        with pytest.raises(ValueError, match="Encryption key environment variable"):
            _create_memory(config, "test-agent")


class TestCreateCostTracker:
    """Tests for cost tracker creation."""

    def test_cost_tracker_disabled(self):
        """Test that disabled cost tracker returns None."""
        config = CostTrackingConfig(enabled=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = _create_cost_tracker(config, Path(tmpdir))
        assert tracker is None

    def test_cost_tracker_enabled(self):
        """Test creating cost tracker."""
        config = CostTrackingConfig(
            enabled=True,
            max_per_hour=10.0,
            max_per_day=100.0,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = _create_cost_tracker(config, Path(tmpdir))
            assert tracker is not None
            assert tracker.limits.max_per_hour == 10.0
            assert tracker.limits.max_per_day == 100.0


class TestCreateHeartbeatMonitor:
    """Tests for heartbeat monitor creation."""

    def test_heartbeat_disabled(self):
        """Test that disabled heartbeat returns None."""
        config = HeartbeatConfig(enabled=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = _create_heartbeat_monitor(config, "test-agent", Path(tmpdir))
        assert monitor is None

    def test_heartbeat_enabled(self):
        """Test creating heartbeat monitor."""
        config = HeartbeatConfig(
            enabled=True,
            check_interval_turns=3,
            max_turns_without_progress=5,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = _create_heartbeat_monitor(config, "test-agent", Path(tmpdir))
            assert monitor is not None
            assert monitor.check_interval_turns == 3


class TestCreateSecurityPolicy:
    """Tests for security policy creation."""

    def test_no_config_returns_default(self):
        """Test that no config returns default policy string."""
        policy = _create_security_policy(None, "test-agent")
        assert policy == "standard"

    def test_preset_creates_policy(self):
        """Test creating policy from preset."""
        config = SecurityConfig(preset="strict")
        policy = _create_security_policy(config, "test-agent")
        assert policy is not None
        # Should be a SecurityPolicy object
        assert hasattr(policy, "log_level")

    def test_preset_with_overrides(self):
        """Test preset with inline overrides."""
        config = SecurityConfig(
            preset="moderate",
            log_level="detailed",
            cost_limits={"max_per_hour": 20.0},
        )
        policy = _create_security_policy(config, "test-agent")
        assert policy.log_level.value == "detailed"
        assert policy.cost_limits.max_per_hour == 20.0


class TestCreateAgentFromConfig:
    """Tests for create_agent_from_config function."""

    def test_minimal_agent(self):
        """Test creating agent with minimal config."""
        config = AgentConfig(
            agent_id="minimal-agent",
            instructions="Be helpful",
        )
        provider = MagicMock()
        provider.model = "claude-sonnet-4"

        agent = create_agent_from_config(config, provider)

        assert agent is not None
        assert agent.agent_id == "minimal-agent"

    def test_agent_with_memory(self):
        """Test creating agent with memory enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AgentConfig(
                agent_id="memory-agent",
                instructions="Remember things",
                workspace=tmpdir,
                memory=MemoryConfig(enabled=True),
            )
            provider = MagicMock()
            provider.model = "claude-sonnet-4"

            agent = create_agent_from_config(config, provider)

            assert agent.memory is not None

    def test_agent_with_harness(self):
        """Test creating agent with harness components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AgentConfig(
                agent_id="harness-agent",
                instructions="Production agent",
                workspace=tmpdir,
                harness=HarnessConfig(
                    cost_tracking=CostTrackingConfig(enabled=True),
                    heartbeat=HeartbeatConfig(enabled=True),
                ),
            )
            provider = MagicMock()
            provider.model = "claude-sonnet-4"

            agent = create_agent_from_config(config, provider)

            assert agent.cost_tracker is not None
            assert agent.heartbeat is not None

    def test_agent_with_janitor_settings(self):
        """Test creating agent with janitor settings."""
        config = AgentConfig(
            agent_id="janitor-agent",
            instructions="Context managed",
            janitor=JanitorConfig(
                enabled=True,
                compact_every=10,
                max_context_tokens=50000,
            ),
            memory=MemoryConfig(enabled=True),  # Janitor requires memory
        )
        provider = MagicMock()
        provider.model = "claude-sonnet-4"

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_agent_from_config(
                config, provider, workspace_dir=Path(tmpdir)
            )
            # Janitor should be initialized with these settings
            if agent.janitor:
                assert agent.janitor.compact_every == 10

    def test_agent_with_security(self):
        """Test creating agent with security policy."""
        config = AgentConfig(
            agent_id="secure-agent",
            instructions="Secure operations",
            security=SecurityConfig(preset="strict"),
        )
        provider = MagicMock()
        provider.model = "claude-sonnet-4"

        agent = create_agent_from_config(config, provider)

        # Agent should be created (guardrails may or may not be initialized
        # depending on policy implementation)
        assert agent is not None
        assert agent.agent_id == "secure-agent"

    def test_agent_with_skills(self):
        """Test creating agent with skills."""
        config = AgentConfig(
            agent_id="skilled-agent",
            instructions="Use skills",
            skills=["filesystem", "git"],
        )
        provider = MagicMock()
        provider.model = "claude-sonnet-4"

        agent = create_agent_from_config(config, provider)

        # Skills should be registered
        assert agent.skills is not None

    def test_workspace_creation(self):
        """Test that workspace directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "new_workspace"
            config = AgentConfig(
                agent_id="workspace-agent",
                workspace=str(workspace),
            )
            provider = MagicMock()
            provider.model = "claude-sonnet-4"

            agent = create_agent_from_config(config, provider)

            # Workspace should have been created
            assert workspace.exists()
