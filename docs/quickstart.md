# Quick Start Guide

Build your first Teotl agent in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Teotl installed from source (see [Installation](installation.md))
- API key configured: `export ANTHROPIC_API_KEY="sk-ant-..."`

## Your First Agent (30 Seconds)

Create a simple agent that can chat with you:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

async def main():
    # Create provider
    provider = AnthropicProvider(model="claude-sonnet-4-20250514")
    
    # Create agent
    agent = Agent(
        provider=provider,
        instructions="You are a helpful AI assistant.",
    )
    
    # Run agent
    response = await agent.run("Hello! What can you help me with?")
    print(response.text)

# Run
asyncio.run(main())
```

**Output:**
```
Hello! I'm an AI assistant powered by Teotl. I can help you with:
- Writing and editing code
- Analyzing repositories
- Automating tasks
- And much more!
```

## Planner-Worker Architecture (40% Cost Savings)

Create an agent with strategic planning and fast execution:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

async def main():
    # Create planner (strategic)
    planner = AnthropicProvider(model="claude-sonnet-4-20250514")
    
    # Create worker (fast execution)
    worker = AnthropicProvider(model="claude-haiku-4-20250514")
    
    # Create planner-worker agent
    agent = Agent.create_planner_worker(
        planner=planner,
        worker=worker,
    )
    
    # Run complex task
    response = await agent.run(
        "Analyze the files in the current directory and suggest improvements"
    )
    print(response.text)

asyncio.run(main())
```

**Why this saves 40%:**
- **Planner:** Uses expensive model (Sonnet) for strategic decisions (infrequent)
- **Worker:** Uses cheap model (Haiku) for execution (frequent)
- **Result:** Same quality, lower cost

## Adding Skills (Tool Use)

Give your agent capabilities like file access and shell commands:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.skills.registry import SkillRegistry

async def main():
    provider = AnthropicProvider(model="claude-sonnet-4-20250514")
    
    # Load skills
    registry = SkillRegistry()
    registry.register_builtin("filesystem")  # File read/write
    registry.register_builtin("bash")        # Shell commands
    
    # Create agent with skills
    agent = Agent(
        provider=provider,
        instructions="You are a coding assistant with file and shell access.",
        skills=registry,
    )
    
    # Agent can now read files, write code, run commands
    response = await agent.run(
        "Read the README.md file and summarize it"
    )
    print(response.text)

asyncio.run(main())
```

**Available Built-in Skills:**
- `filesystem` - Read/write files
- `git` - Repository operations
- `bash` - Shell commands
- `python_repl` - Dynamic code execution

## Adding Security (Guardrails)

Protect your system with built-in security policies:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.skills.registry import SkillRegistry

async def main():
    provider = AnthropicProvider(model="claude-sonnet-4-20250514")
    registry = SkillRegistry()
    registry.register_builtin("filesystem")
    registry.register_builtin("bash")
    
    # Create agent with guardrails
    agent = Agent(
        provider=provider,
        instructions="You are a helpful assistant.",
        skills=registry,
        policy="standard",  # or "strict" for high-security
    )
    
    # Dangerous commands are blocked automatically
    response = await agent.run("Delete all files in the system")
    # Agent will refuse or ask for confirmation
    
    print(response.text)

asyncio.run(main())
```

**Policy Levels:**
- `permissive` - Minimal restrictions, trust agent
- `standard` - Balanced security (recommended)
- `strict` - Maximum security, confirmation required

## Adding Memory (Context Persistence)

Give your agent long-term memory across conversations:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.memory.local import LocalMemory

async def main():
    provider = AnthropicProvider(model="claude-sonnet-4-20250514")
    
    # Create memory
    memory = LocalMemory()
    
    # Create agent with memory
    agent = Agent(
        provider=provider,
        instructions="You are a helpful assistant with long-term memory.",
        memory=memory,
    )
    
    # First conversation
    response1 = await agent.run("My name is Alice and I love Python programming.")
    print(response1.text)
    
    # Later conversation (agent remembers)
    response2 = await agent.run("What's my name and what do I like?")
    print(response2.text)
    # Output: "Your name is Alice and you love Python programming."
    
    # Clean up
    memory.close()

asyncio.run(main())
```

## Autonomous Missions

Create long-running autonomous workflows:

```python
import asyncio
from teotl.primitives.missions import Mission
from teotl.core.provider import AnthropicProvider

async def main():
    # Define mission (YAML or dict)
    mission_config = {
        "name": "code_review_agent",
        "objective": "Review pull requests and provide feedback",
        "execution_pattern": "planner_worker",
        "planner_worker": {
            "planner": {"provider": "claude-sonnet-4"},
            "worker": {
                "provider": "claude-haiku-4",
                "skills": ["filesystem", "git"]
            }
        }
    }
    
    # Create and run mission
    mission = Mission.from_dict(mission_config)
    result = await mission.run(context={
        "repository": "owner/repo",
        "pr_number": 42
    })
    
    print(f"Mission completed: {result.status}")
    print(result.summary)

asyncio.run(main())
```

**Mission Features:**
- Long-running autonomous execution
- Automatic error recovery
- Context-aware decision making
- Cost tracking and optimization

## Interactive CLI Mode

Use Teotl from the command line:

```bash
# Start interactive chat
teotl

# Chat with specific provider
teotl --provider anthropic --model claude-sonnet-4

# Chat with guardrails
teotl --policy strict

# Chat with skills
teotl chat --skills filesystem,git,bash
```

**Interactive commands:**
```
/help         Show available commands
/skills       List loaded skills
/memory       Show memory status
/policy       Show security policy
/quit         Exit
```

## Using the Onboarding Wizard

Interactive setup for your first agent:

```bash
teotl onboard
```

The wizard guides you through:
1. API key configuration
2. Agent naming and preferences
3. Execution pattern (planner-worker vs single-agent)
4. Model selection
5. Skills selection
6. Memory configuration
7. Security policy setup

**Output:**
```
~/.teotl/agents/my-agent/
├── config.yaml        # Agent configuration
├── missions/          # Mission definitions
└── skills/            # Custom skills (optional)
```

## Example: DevOps Automation Agent

A complete example that autonomously fixes GitHub issues:

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.skills.registry import SkillRegistry

async def main():
    # Setup
    planner = AnthropicProvider(model="claude-sonnet-4-20250514")
    worker = AnthropicProvider(model="claude-haiku-4-20250514")
    
    registry = SkillRegistry()
    registry.register_builtin("filesystem")
    registry.register_builtin("git")
    registry.register_builtin("bash")
    
    # Create DevOps agent
    agent = Agent.create_planner_worker(
        planner=planner,
        worker=worker,
        instructions="""
        You are a DevOps automation agent.
        Your job is to investigate GitHub issues and create fixes.
        
        Steps:
        1. Reproduce the bug
        2. Investigate root cause
        3. Create a fix
        4. Test the fix
        5. Create pull request
        """,
        skills=registry,
        policy="standard",
    )
    
    # Run autonomous investigation
    response = await agent.run(
        "Investigate issue #42 in this repository and create a fix"
    )
    
    print(response.text)

asyncio.run(main())
```

See [examples/devops_agent/](../examples/devops_agent/) for the full implementation.

## What's Next?

### Learn Core Concepts
- [Concepts Guide](concepts.md) - Understand missions, skills, guardrails, memory
- [Architecture](../ARCHITECTURE.md) - Deep dive into planner-worker pattern

### Explore Examples
- [DevOps Agent](../examples/devops_agent/) - Autonomous bug fixing
- [Comparison Framework](../examples/comparison/) - Benchmark agents

### Advanced Topics
- [Custom Skills](../docs/CUSTOM_SKILLS_QUICKSTART.md) - Build your own skills
- [Security Guide](../docs/SECURITY_GUIDE.md) - Production security
- [API Reference](api_reference.md) - Complete API documentation

## Common Patterns

### Pattern 1: Simple Task Automation

```python
agent = Agent(provider=provider, instructions="...")
result = await agent.run("Analyze codebase and suggest improvements")
```

### Pattern 2: Multi-Step Workflow

```python
mission = Mission.from_file("missions/workflow.yaml")
result = await mission.run(context={"param": "value"})
```

### Pattern 3: Cost Optimization

```python
agent = Agent.create_planner_worker(
    planner=expensive_model,  # Strategic decisions
    worker=cheap_model,       # Fast execution
)
```

### Pattern 4: Interactive Agent

```python
agent = Agent(provider=provider)

while True:
    user_input = input("You: ")
    response = await agent.run(user_input)
    print(f"Agent: {response.text}")
```

## Troubleshooting

### Issue: "API key not found"

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or run: teotl onboard
```

### Issue: "No module named 'teotl'"

**Solution:**
```bash
pip install --upgrade teotl
```

### Issue: Agent doesn't use skills

**Solution:**
```python
# Make sure skills are registered
registry = SkillRegistry()
registry.register_builtin("filesystem")  # Register explicitly

# And passed to agent
agent = Agent(provider=provider, skills=registry)
```

### Issue: Guardrails blocking everything

**Solution:**
```python
# Use more permissive policy
agent = Agent(provider=provider, policy="permissive")

# Or disable guardrails for testing
agent = Agent(provider=provider, policy=None)
```

## Tips and Best Practices

### 1. Use Planner-Worker for Cost Savings

```python
# ✅ Good: 40% cost savings
agent = Agent.create_planner_worker(planner=sonnet, worker=haiku)

# ❌ Expensive: Uses expensive model for everything
agent = Agent(provider=sonnet)
```

### 2. Enable Guardrails in Production

```python
# ✅ Good: Production-safe
agent = Agent(provider=provider, policy="standard")

# ❌ Risky: No protection
agent = Agent(provider=provider, policy=None)
```

### 3. Use Memory for Context

```python
# ✅ Good: Agent remembers across conversations
agent = Agent(provider=provider, memory=LocalMemory())

# ❌ Limited: No context retention
agent = Agent(provider=provider)
```

### 4. Scope Skills Appropriately

```python
# ✅ Good: Only necessary skills
registry.register_builtin("filesystem")

# ❌ Risky: Too many capabilities
registry.register_all_builtins()
```

## Getting Help

- **Documentation:** [docs/](../docs/)
- **GitHub Issues:** [Report bugs](https://github.com/yourusername/teotl/issues)
- **Discussions:** [Ask questions](https://github.com/yourusername/teotl/discussions)

---

**Next:** [Concepts Guide](concepts.md) - Understand core concepts
