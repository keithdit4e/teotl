# Demo Setup: Real Provider Configuration

**Purpose:** Configure autonomous agent to use real LLM provider (Anthropic, OpenAI, etc.) instead of mock

**Time Required:** 10-15 minutes

---

## Prerequisites

### 1. LLM Provider Account
Choose one:
- **Anthropic** (Recommended for demo - best reasoning)
  - Sign up: https://console.anthropic.com/
  - Get API key: https://console.anthropic.com/settings/keys
  - Cost: ~$0.50-$2.00 for full demo

- **OpenAI**
  - Sign up: https://platform.openai.com/
  - Get API key: https://platform.openai.com/api-keys
  - Cost: ~$0.30-$1.50 for full demo

- **Ollama** (Free, local)
  - Install: https://ollama.ai/
  - Pull model: `ollama pull llama3.1`
  - Cost: $0 (runs locally)

### 2. Environment Variables
Set your API key:

```bash
# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Ollama (no key needed)
# Just make sure ollama is running: ollama serve
```

---

## Configuration Changes

### Option 1: Anthropic (Recommended)

**Modify:** `examples/autonomous_agent/main.py`

**Find this section:**
```python
# NOTE: Replace with your actual provider
# For this example, we'll use a mock provider
from unittest.mock import AsyncMock, Mock

mock_provider = Mock()
mock_provider.complete = AsyncMock(
    return_value=Mock(
        message=Mock(content="Task completed successfully", tool_calls=[])
    )
)
```

**Replace with:**
```python
# Real Anthropic provider
import os
from anthropic import Anthropic

# Check for API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
    print("   Run: export ANTHROPIC_API_KEY='your-key-here'")
    exit(1)

# Create provider
from forge.core.provider import AnthropicProvider

real_provider = AnthropicProvider(
    api_key=api_key,
    model="claude-sonnet-4-20250514",  # Latest model
)
```

**Update executor creation:**
```python
executor = create_simple_executor(
    provider=real_provider,  # Changed from mock_provider
    instructions="""You are an email assistant that helps manage emails.

    You can:
    - Check for new emails
    - Send emails
    - Organize emails into folders
    - Flag important messages

    For this demo, simulate actions by describing what you would do.
    Example: "I would send an email to alice@example.com with subject 'Welcome'..."
    """,
    skills=[],  # No skills for demo - just descriptions
    auto_approve=True,
)
```

---

### Option 2: OpenAI

**Replace provider section with:**
```python
# Real OpenAI provider
import os
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    exit(1)

from forge.core.provider import OpenAIProvider

real_provider = OpenAIProvider(
    api_key=api_key,
    model="gpt-4o",  # or "gpt-4o-mini" for cheaper
)
```

---

### Option 3: Ollama (Free, Local)

**Replace provider section with:**
```python
# Ollama local provider
import os
from ollama import Client

# Check Ollama is running
try:
    client = Client()
    models = client.list()
    print(f"✅ Ollama connected. Available models: {[m['name'] for m in models['models']]}")
except Exception as e:
    print("❌ Error: Ollama not running")
    print("   Start it with: ollama serve")
    exit(1)

from forge.core.provider import OllamaProvider

real_provider = OllamaProvider(
    model="llama3.1:latest",  # or "mistral", "codellama", etc.
)
```

---

## Additional Configuration for Real Providers

### 1. Adjust Poll Interval (Optional)

For real providers, you might want slower polling to save costs:

```python
daemon = HeartbeatDaemon(
    agent_id="email-agent",
    agent_executor=executor,
    poll_interval=30,  # Changed from 5 to 30 seconds
)
```

### 2. Reduce Task Expiration (Optional)

For demo, make tasks expire faster to show cleanup:

```python
Task(
    description="Send welcome email to new user",
    priority=Priority.HIGH,
    context={"to": "newuser@example.com"},
    expires_at=datetime.now() + timedelta(minutes=5),  # 5 min instead of 1 hour
)
```

### 3. Add Rate Limiting (Recommended)

Wrap provider with rate limiter:

```python
from forge.core.rate_limited_provider import RateLimitedProvider

# Wrap your provider
limited_provider = RateLimitedProvider(
    provider=real_provider,
    max_requests_per_minute=10,
    max_cost_per_minute=0.50,  # $0.50/min max
)

# Use limited_provider in executor
executor = create_simple_executor(
    provider=limited_provider,  # Rate limited
    instructions=...,
)
```

### 4. Enable Logging (Recommended)

See what the agent is doing:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler("demo.log"),  # File
    ]
)
```

---

## Configuration File Approach (Better for Multiple Demos)

### Create: `demos/internal/config.yaml`

```yaml
# Demo Configuration
provider:
  type: anthropic  # or openai, ollama
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY  # Environment variable name

agent:
  agent_id: email-agent-demo
  instructions: |
    You are an email assistant that helps manage emails.
    For this demo, simulate actions by describing what you would do.
  auto_approve: true

daemon:
  poll_interval: 30  # seconds
  data_dir: ~/.teotl/demo/email-agent

rate_limits:
  max_requests_per_minute: 10
  max_cost_per_minute: 0.50

tasks:
  - description: Send welcome email to new user
    priority: HIGH
    context:
      to: newuser@example.com
      template: welcome
    expires_minutes: 60

  - description: Reply to customer support ticket #1234
    priority: URGENT
    context:
      ticket_id: "1234"
      category: billing
    expires_minutes: 120

  - description: Archive old emails from last year
    priority: LOW
    context:
      before_date: "2024-01-01"
    expires_days: 7

missions:
  - description: Check for new emails and flag important ones
    interval: HOURLY
    can_be_interrupted: true
    interrupt_threshold: URGENT

  - description: Clean up spam folder
    interval: DAILY
    can_be_interrupted: true
    interrupt_threshold: URGENT
```

### Create: `demos/internal/demo_with_config.py`

```python
"""
Autonomous Agent Demo with Real Provider
Uses configuration file for easy setup.
"""

import asyncio
import os
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from forge.daemon.executor import create_simple_executor
from forge.daemon.heartbeat import HeartbeatDaemon
from forge.primitives.missions import Mission, MissionInterval
from forge.primitives.tasks import Priority, Task

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_provider(config):
    """Create provider based on config."""
    provider_type = config["provider"]["type"]
    model = config["provider"]["model"]
    api_key_env = config["provider"].get("api_key_env")

    # Get API key from environment
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"Environment variable {api_key_env} not set")

    # Create provider based on type
    if provider_type == "anthropic":
        from forge.core.provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model=model)

    elif provider_type == "openai":
        from forge.core.provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_type == "ollama":
        from forge.core.provider import OllamaProvider
        return OllamaProvider(model=model)

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


async def main():
    """Run demo with real provider."""

    # Load configuration
    config = load_config()
    logger.info("📄 Configuration loaded")

    # Create provider
    provider = create_provider(config)
    logger.info(f"✅ Provider created: {config['provider']['type']}")

    # Add rate limiting if configured
    if "rate_limits" in config:
        from forge.core.rate_limited_provider import RateLimitedProvider
        provider = RateLimitedProvider(
            provider=provider,
            max_requests_per_minute=config["rate_limits"]["max_requests_per_minute"],
            max_cost_per_minute=config["rate_limits"]["max_cost_per_minute"],
        )
        logger.info("🛡️  Rate limiting enabled")

    # Create executor
    executor = create_simple_executor(
        provider=provider,
        instructions=config["agent"]["instructions"],
        auto_approve=config["agent"]["auto_approve"],
    )

    # Create data directory
    data_dir = Path(config["daemon"]["data_dir"]).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create daemon
    daemon = HeartbeatDaemon(
        agent_id=config["agent"]["agent_id"],
        agent_executor=executor,
        data_dir=data_dir,
        poll_interval=config["daemon"]["poll_interval"],
    )

    logger.info(f"🤖 Created daemon: {config['agent']['agent_id']}")

    # Add missions from config
    for mission_config in config["missions"]:
        mission = Mission(
            description=mission_config["description"],
            interval=MissionInterval[mission_config["interval"]],
            next_execution_at=datetime.now() + timedelta(seconds=10),
            can_be_interrupted=mission_config["can_be_interrupted"],
            interrupt_threshold=Priority[mission_config["interrupt_threshold"]],
        )
        await daemon.mission_store.create(mission)
        logger.info(f"📅 Added mission: {mission.description}")

    # Add tasks from config
    for task_config in config["tasks"]:
        # Calculate expiration
        expires_at = datetime.now()
        if "expires_minutes" in task_config:
            expires_at += timedelta(minutes=task_config["expires_minutes"])
        elif "expires_days" in task_config:
            expires_at += timedelta(days=task_config["expires_days"])

        task = Task(
            description=task_config["description"],
            priority=Priority[task_config["priority"]],
            context=task_config.get("context", {}),
            expires_at=expires_at,
        )
        await daemon.task_store.create(task)
        logger.info(f"✅ Added {task.priority.name} task: {task.description}")

    # Start daemon
    logger.info("\n🚀 Starting autonomous agent daemon...")
    logger.info("Press Ctrl+C to stop\n")

    daemon_task = asyncio.create_task(daemon.start())

    try:
        # Monitor for 2 minutes or until Ctrl+C
        for i in range(24):  # 24 x 5 seconds = 2 minutes
            await asyncio.sleep(5)

            pending_tasks = await daemon.task_store.get_pending()
            logger.info(
                f"📊 Status: {len(pending_tasks)} pending tasks, "
                f"Current: {daemon.current_mission.description[:30] + '...' if daemon.current_mission else 'None'}"
            )

            if not pending_tasks and not daemon.current_mission:
                due_missions = await daemon.mission_store.list_due()
                if not due_missions:
                    logger.info("✨ All work completed!")
                    break

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupt received, shutting down gracefully...")

    finally:
        # Stop daemon
        await daemon.stop()
        await daemon_task
        logger.info("👋 Daemon stopped")

        # Show final stats
        all_tasks = await daemon.task_store.get_all()
        completed = sum(1 for t in all_tasks if t.state.value == "completed")
        failed = sum(1 for t in all_tasks if t.state.value == "failed")

        all_missions = await daemon.mission_store.list_all()
        total_executions = sum(m.execution_count for m in all_missions)

        logger.info(f"\n📈 Final Statistics:")
        logger.info(f"   Tasks completed: {completed}")
        logger.info(f"   Tasks failed: {failed}")
        logger.info(f"   Mission executions: {total_executions}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Demo Execution Steps

### 1. Set Environment Variable
```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# OR OpenAI
export OPENAI_API_KEY="sk-..."

# OR start Ollama
ollama serve  # In separate terminal
```

### 2. Verify Setup
```bash
# Check environment variable
echo $ANTHROPIC_API_KEY  # Should show your key

# Install dependencies if needed
pip install anthropic  # or openai, or ollama
```

### 3. Run Demo

**Option A - Modified example:**
```bash
python examples/autonomous_agent/main.py
```

**Option B - Config-based (recommended):**
```bash
cd demos/internal
python demo_with_config.py
```

### 4. Monitor Output

You should see real LLM responses instead of mock responses:
```
INFO - Executing: Reply to customer support ticket #1234...
INFO - [Agent] I'll help you respond to ticket #1234 regarding billing...
INFO - [Agent] Let me check the ticket details in context: {'ticket_id': '1234', 'category': 'billing'}
INFO - [Agent] I would send this reply: "Thank you for contacting support about..."
INFO - Execution completed successfully
```

### 5. Check Costs

**Anthropic:**
- Console: https://console.anthropic.com/settings/usage
- Expected: $0.50-$2.00 for full demo

**OpenAI:**
- Console: https://platform.openai.com/usage
- Expected: $0.30-$1.50 for full demo

**Ollama:**
- Free! Runs locally

---

## Troubleshooting

### "API key not set"
```bash
# Make sure you exported the variable
export ANTHROPIC_API_KEY="your-key"

# Verify it's set
echo $ANTHROPIC_API_KEY
```

### "Rate limit exceeded"
```python
# Add rate limiter in config
rate_limits:
  max_requests_per_minute: 5  # Reduce from 10
  max_cost_per_minute: 0.25   # Reduce from 0.50
```

### "Connection error"
```bash
# Check internet connection
ping api.anthropic.com

# For Ollama, make sure it's running
ollama list  # Should show models
```

### "Agent not responding as expected"
```python
# Adjust instructions to be more explicit
instructions: |
  You are an email assistant.

  IMPORTANT: This is a demo. You cannot actually send emails.
  Instead, describe what you would do.

  Example good response:
  "I would send an email to alice@example.com with subject 'Welcome'
  and body: 'Thank you for joining...'"
```

---

## Cost Estimates

### Full Demo Run (~2 minutes):

| Provider | Model | Cost per Request | Total Cost |
|----------|-------|------------------|------------|
| Anthropic | Claude Sonnet 4 | $0.15-0.40 | $0.60-1.60 |
| Anthropic | Claude Haiku | $0.05-0.10 | $0.20-0.40 |
| OpenAI | GPT-4o | $0.10-0.30 | $0.40-1.20 |
| OpenAI | GPT-4o-mini | $0.03-0.08 | $0.12-0.32 |
| Ollama | Llama 3.1 | $0.00 | $0.00 |

**Recommendation for Demo:** Use Anthropic Claude Sonnet 4 for best quality, or Haiku for cost savings.

---

## Configuration Quick Reference

```python
# Minimal config for real provider

# 1. Import real provider
from forge.core.provider import AnthropicProvider

# 2. Create with API key
provider = AnthropicProvider(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-4-20250514"
)

# 3. Use in executor
executor = create_simple_executor(
    provider=provider,  # Real provider
    instructions="...",
    auto_approve=True
)

# Done! Everything else stays the same
```

---

## Next Steps

After demo works with real provider:
1. Save successful config.yaml for reuse
2. Document any provider-specific quirks
3. Consider adding provider comparison (Anthropic vs OpenAI)
4. Test with different models to optimize cost/quality