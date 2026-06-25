"""Tests for multi-agent configuration parsing."""

import tempfile
from pathlib import Path

import pytest
import yaml

from teotl.config import (
    AgentConfig,
    AuditConfig,
    CheckpointConfig,
    CostTrackingConfig,
    HarnessConfig,
    HeartbeatConfig,
    JanitorConfig,
    MemoryConfig,
    ModelParametersConfig,
    MultiAgentConfig,
    PlannerWorkerConfig,
    ProviderConfig,
    SecurityConfig,
    StateConfig,
    load_multi_agent_config,
)


class TestMemoryConfig:
    """Tests for MemoryConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MemoryConfig()
        assert config.enabled is False
        assert config.backend == "local"
        assert config.path is None
        assert config.auto_cleanup is True
        assert config.max_memories == 10000

    def test_encrypted_backend(self):
        """Test encrypted backend configuration."""
        config = MemoryConfig(
            enabled=True,
            backend="encrypted",
            encryption_key_env="MY_KEY",
        )
        assert config.backend == "encrypted"
        assert config.encryption_key_env == "MY_KEY"


class TestJanitorConfig:
    """Tests for JanitorConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = JanitorConfig()
        assert config.enabled is True
        assert config.compact_every == 15
        assert config.max_context_tokens is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = JanitorConfig(
            enabled=True,
            compact_every=10,
            max_context_tokens=50000,
        )
        assert config.compact_every == 10
        assert config.max_context_tokens == 50000


class TestHarnessConfig:
    """Tests for HarnessConfig."""

    def test_boolean_shortcuts(self):
        """Test that boolean values are converted to full config objects."""
        config = HarnessConfig(
            cost_tracking=True,
            heartbeat=True,
            checkpoints=True,
            state=True,
            audit=True,
        )
        assert isinstance(config.cost_tracking, CostTrackingConfig)
        assert config.cost_tracking.enabled is True
        assert isinstance(config.heartbeat, HeartbeatConfig)
        assert config.heartbeat.enabled is True

    def test_full_config_objects(self):
        """Test passing full config objects."""
        cost_config = CostTrackingConfig(
            enabled=True,
            max_per_hour=10.0,
            max_per_day=100.0,
        )
        config = HarnessConfig(cost_tracking=cost_config)
        assert config.cost_tracking.max_per_hour == 10.0
        assert config.cost_tracking.max_per_day == 100.0


class TestCostTrackingConfig:
    """Tests for CostTrackingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CostTrackingConfig()
        assert config.enabled is False
        assert config.max_per_hour == 5.0
        assert config.max_per_day == 50.0
        assert config.max_per_month == 500.0
        assert config.currency == "USD"


class TestHeartbeatConfig:
    """Tests for HeartbeatConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HeartbeatConfig()
        assert config.enabled is False
        assert config.check_interval_turns == 5
        assert config.max_turns_without_progress == 10
        assert config.max_consecutive_errors == 5
        assert config.notify_on_critical is True
        assert config.notify_on_warning is False


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_basic_config(self):
        """Test basic provider configuration."""
        config = ProviderConfig(
            type="anthropic",
            model="claude-sonnet-4",
        )
        assert config.type == "anthropic"
        assert config.model == "claude-sonnet-4"
        assert config.api_key_env is None

    def test_with_parameters(self):
        """Test provider with model parameters."""
        config = ProviderConfig(
            type="openai",
            model="gpt-4",
            parameters=ModelParametersConfig(
                temperature=0.7,
                max_tokens=4096,
            ),
        )
        assert config.parameters.temperature == 0.7
        assert config.parameters.max_tokens == 4096


class TestSecurityConfig:
    """Tests for SecurityConfig."""

    def test_preset(self):
        """Test security preset configuration."""
        config = SecurityConfig(preset="strict")
        assert config.preset == "strict"

    def test_inline_overrides(self):
        """Test inline security overrides."""
        config = SecurityConfig(
            preset="moderate",
            log_level="detailed",
            cost_limits={"max_per_hour": 10.0},
            allowed_domains=["*.github.com"],
        )
        assert config.log_level == "detailed"
        assert config.cost_limits["max_per_hour"] == 10.0


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_minimal_config(self):
        """Test minimal agent configuration."""
        config = AgentConfig(agent_id="test-agent")
        assert config.agent_id == "test-agent"
        assert config.instructions == ""
        assert config.skills == []
        assert config.auto_approve is True

    def test_full_config(self):
        """Test full agent configuration."""
        config = AgentConfig(
            agent_id="full-agent",
            instructions="Be helpful",
            workspace="~/workspace",
            skills=["filesystem", "git"],
            auto_approve=False,
            max_turns=100,
            memory=True,  # Boolean shortcut
            janitor=True,
            harness=HarnessConfig(cost_tracking=True),
            security=SecurityConfig(preset="strict"),
        )
        assert config.agent_id == "full-agent"
        assert config.instructions == "Be helpful"
        assert config.skills == ["filesystem", "git"]
        # Boolean shortcuts converted to config objects
        assert isinstance(config.memory, MemoryConfig)
        assert config.memory.enabled is True
        assert isinstance(config.janitor, JanitorConfig)
        assert config.janitor.enabled is True

    def test_planner_worker_config(self):
        """Test planner-worker architecture configuration."""
        config = AgentConfig(
            agent_id="pw-agent",
            planner_worker=PlannerWorkerConfig(
                enabled=True,
                planner={"provider": "claude-sonnet-4"},
                worker={"provider": "claude-haiku-4", "skills": ["filesystem"]},
            ),
        )
        assert config.planner_worker.enabled is True


class TestMultiAgentConfig:
    """Tests for MultiAgentConfig."""

    def test_single_agent(self):
        """Test single agent configuration."""
        config = MultiAgentConfig(
            agents={
                "main": AgentConfig(
                    agent_id="main",
                    instructions="Be helpful",
                )
            },
            provider=ProviderConfig(type="anthropic", model="claude-sonnet-4"),
        )
        assert config.is_multi_agent is False
        assert config.agent_ids == ["main"]

    def test_multiple_agents(self):
        """Test multiple agent configuration."""
        config = MultiAgentConfig(
            agents={
                "dev": AgentConfig(agent_id="dev", instructions="Developer"),
                "reviewer": AgentConfig(agent_id="reviewer", instructions="Reviewer"),
            },
            provider=ProviderConfig(type="anthropic", model="claude-sonnet-4"),
        )
        assert config.is_multi_agent is True
        assert len(config.agent_ids) == 2
        assert "dev" in config.agent_ids
        assert "reviewer" in config.agent_ids


class TestLoadMultiAgentConfig:
    """Tests for load_multi_agent_config function."""

    def test_load_single_agent_format(self):
        """Test loading single-agent format YAML."""
        yaml_content = """
provider:
  type: anthropic
  model: claude-sonnet-4

agent:
  agent_id: test-agent
  instructions: "Be helpful"
  skills:
    - filesystem
    - git
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        assert config.agent_ids == ["test-agent"]
        agent = config.get_agent("test-agent")
        assert agent.instructions == "Be helpful"
        assert agent.skills == ["filesystem", "git"]

    def test_load_multi_agent_format(self):
        """Test loading multi-agent format YAML."""
        yaml_content = """
provider:
  type: anthropic
  model: claude-haiku-4

agents:
  dev:
    agent_id: dev
    instructions: "Developer"
    skills: [filesystem, git]
  review:
    agent_id: review
    instructions: "Reviewer"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        assert config.is_multi_agent is True
        assert len(config.agent_ids) == 2

    def test_load_with_memory_and_harness(self):
        """Test loading config with memory and harness settings."""
        yaml_content = """
provider:
  type: anthropic
  model: claude-sonnet-4

agent:
  agent_id: full-agent
  instructions: "Production agent"

  memory:
    enabled: true
    backend: local
    max_memories: 5000

  janitor:
    enabled: true
    compact_every: 10

  harness:
    cost_tracking:
      enabled: true
      max_per_hour: 10.0
    heartbeat:
      enabled: true
    checkpoints: true
    state: true
    audit: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        agent = config.get_agent("full-agent")
        assert agent.memory.enabled is True
        assert agent.memory.max_memories == 5000
        assert agent.janitor.compact_every == 10
        assert agent.harness.cost_tracking.enabled is True
        assert agent.harness.cost_tracking.max_per_hour == 10.0
        assert agent.harness.heartbeat.enabled is True
        assert agent.harness.checkpoints.enabled is True

    def test_load_with_security(self):
        """Test loading config with security settings."""
        yaml_content = """
provider:
  type: anthropic
  model: claude-sonnet-4

agent:
  agent_id: secure-agent
  instructions: "Secure agent"

  security:
    preset: strict
    log_level: detailed
    allowed_domains:
      - "*.anthropic.com"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        agent = config.get_agent("secure-agent")
        assert agent.security.preset == "strict"
        assert agent.security.log_level == "detailed"
        assert "*.anthropic.com" in agent.security.allowed_domains

    def test_load_with_provider_parameters(self):
        """Test loading config with model parameters."""
        yaml_content = """
provider:
  type: openai
  model: gpt-4
  api_key_env: OPENAI_API_KEY
  parameters:
    temperature: 0.3
    max_tokens: 8192
    top_p: 0.9

agent:
  agent_id: test-agent
  instructions: "Test"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        assert config.provider.parameters.temperature == 0.3
        assert config.provider.parameters.max_tokens == 8192
        assert config.provider.parameters.top_p == 0.9

    def test_load_missing_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_multi_agent_config("/nonexistent/path.yaml")

    def test_load_invalid_config(self):
        """Test error when config is invalid."""
        yaml_content = """
# Missing required 'provider' key
agent:
  agent_id: test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            with pytest.raises(ValueError):
                load_multi_agent_config(f.name)

    def test_load_empty_file(self):
        """Test error when config file is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            with pytest.raises(ValueError, match="Empty config file"):
                load_multi_agent_config(f.name)

    def test_load_with_daemon_and_tasks(self):
        """Test loading config with daemon, tasks, and missions."""
        yaml_content = """
provider:
  type: anthropic
  model: claude-haiku-4

agent:
  agent_id: daemon-agent
  instructions: "Daemon agent"

daemon:
  poll_interval: 60
  data_dir: ~/.teotl/daemon-agent

rate_limits:
  max_requests_per_minute: 20
  max_cost_per_minute: 1.0

tasks:
  - description: "Run tests"
    priority: HIGH
    context:
      test_command: "pytest"

missions:
  - description: "Daily review"
    interval: DAILY
    can_be_interrupted: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_multi_agent_config(f.name)

        assert config.daemon.poll_interval == 60
        assert config.rate_limits.max_requests_per_minute == 20
        assert len(config.tasks) == 1
        assert config.tasks[0].priority == "HIGH"
        assert len(config.missions) == 1
        assert config.missions[0].interval == "DAILY"
