# Autonomous Agent Example

This example demonstrates how to create an autonomous agent that executes tasks and missions using the HeartbeatDaemon.

## What is an Autonomous Agent?

An autonomous agent runs in the background, automatically executing:
- **Tasks**: Immediate one-time work (e.g., "Send email to Alice")
- **Missions**: Scheduled recurring work (e.g., "Check email every hour")

## Architecture

```
┌─────────────────────────────────────────────┐
│         HeartbeatDaemon                     │
│  - Priority-based scheduling                │
│  - Mission interruption control             │
│  - Graceful shutdown                        │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│         AgentExecutor                       │
│  - Bridges daemon → agent                   │
│  - Handles timeouts & errors                │
│  - Context injection                        │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│         Agent                               │
│  - LLM provider                             │
│  - Skills & guardrails                      │
│  - Memory                                   │
└─────────────────────────────────────────────┘
```

## Quick Start

Run the example:

```bash
python examples/autonomous_agent/main.py
```

This will:
1. Create an autonomous email agent
2. Add some tasks and missions
3. Start the daemon
4. Watch it execute autonomously
5. Clean up on shutdown

## Files

- `main.py` - Complete working example
- `README.md` - This file

## Key Concepts

### Tasks vs Missions

**Tasks** are immediate:
```python
task = Task(
    description="Send email to alice@example.com",
    priority=Priority.HIGH,
    context={"to": "alice@example.com"},
    expires_at=datetime.now() + timedelta(hours=24)
)
```

**Missions** are scheduled:
```python
mission = Mission(
    description="Check for new emails",
    interval=MissionInterval.HOURLY,
    next_execution_at=datetime.now()
)
```

### Priority System

Tasks have priorities that control interruption:
- `CRITICAL` (5) - Always interrupts, even non-interruptible missions
- `URGENT` (4) - Interrupts if mission allows
- `HIGH` (3) - Queued before next mission
- `NORMAL` (2) - Standard priority
- `LOW` (1) - Best effort

### Execution Order

The daemon processes work in this order:
1. Cleanup expired tasks
2. CRITICAL tasks (always interrupt)
3. URGENT tasks (interrupt if allowed)
4. Due missions
5. Other tasks (HIGH, NORMAL, LOW)

### Mission Interruption

Missions can control when they can be interrupted:

```python
mission = Mission(
    description="Important backup",
    interval=MissionInterval.DAILY,
    can_be_interrupted=False,  # Can't be interrupted
    interrupt_threshold=Priority.CRITICAL,  # Only CRITICAL can interrupt
)
```

## Testing Your Agent

See `tests/integration/test_autonomous_agent.py` for examples of:
- Testing task execution
- Testing mission execution
- Testing priority ordering
- Testing error handling
- Testing full daemon lifecycle

## Next Steps

- Add your own LLM provider API key
- Customize agent instructions
- Add skills (gmail, calendar, etc.)
- Create your own missions
- Deploy with Docker/K8s
