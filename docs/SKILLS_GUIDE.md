# Skills Guide

Skills provide progressive disclosure for agent capabilities - keeping context costs low while making powerful tools available on-demand.

## Overview

**Problem:** MCP loads all tool schemas at startup = 30,000+ tokens permanently in context

**Solution:** Skills load descriptions (~50 tokens each), full instructions only when needed

**Result:** 10 skills = ~500 tokens (not 30,000+)

## Built-in Skills

Teotl bundles these skills in `teotl/skills/`:

| Skill | Description |
|-------|-------------|
| `filesystem` | Read, write, search, and navigate files and directories |
| `git` | Version control with Git: status, commits, branches, diffs |
| `github` | Interact with GitHub repositories, issues, and pull requests |
| `web` | Fetch web pages, download files, make HTTP requests (via `curl`) |
| `claude_code` | Coding assistant via the Claude Code CLI |
| `spec_kit` | Formal specification creation for structured planning |
| `social-media` | Cross-post and manage content across LinkedIn, X, Medium, Substack |

A skill is a set of instructions, not code. The agent carries them out with its built-in
`bash` tool (registered automatically), so every command still passes through the agent's
guardrail policy. For example, with the default `standard` policy, `rm` and `git push`
require confirmation and piping `curl` output into a shell is blocked.
See [GUARDRAILS.md](GUARDRAILS.md).

**Example:**
```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(provider=AnthropicProvider(), skills=["filesystem"])
response = await agent.run("Find all Python files larger than 1MB")
```

## Using Skills

### In Python Code

```python
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

# Enable specific skills
agent = Agent(
    provider=AnthropicProvider(),
    instructions="You are a helpful assistant",
    skills=["filesystem", "git", "web"],
)

# Skills auto-activate when the agent needs them
response = await agent.run("List all TODO comments in Python files")
```

### Progressive Disclosure

**Step 1: Descriptions always in context**
```
Available capabilities:
- filesystem: Read, write, search files and directories
- git: Version control operations
- web: Web search and URL fetching
```
Cost: ~150 tokens (3 skills × 50 tokens)

**Step 2: Skill is activated when relevant**
When the model's response mentions a skill's name or one of its `triggers`, the agent
activates that skill and loads its full instructions for the next turn. You can also
activate a skill manually (see below).

**Step 3: Full instructions loaded on-demand**
```
# Filesystem Operations

## Search File Contents
grep -rn "TODO" *.py

[... rest of the skill's instructions ...]
```
Cost: depends on the size of the SKILL.md (typically a few thousand tokens)

**Step 4: Deactivate when done**
Active skills stay loaded until deactivated. Call `agent.deactivate_skill(name)` to remove
a skill's instructions and return to the descriptions-only baseline.

### Manual Activation

```python
# Manually activate a skill
instructions = await agent.activate_skill("filesystem")
print(instructions)  # Full SKILL.md content

# Deactivate when done
agent.deactivate_skill("filesystem")
```

### List Available Skills

```python
# Get all registered skills (dict of name -> description)
skills = agent.list_skills()
for name, description in skills.items():
    print(f"{name}: {description}")

# Currently active skills
print(agent.list_active_skills())
```

## Creating Custom Skills

### Directory Structure

```
~/.forge/skills/my-skill/
├── SKILL.md          # Required: Frontmatter + instructions
└── scripts/          # Optional: helper scripts your instructions reference
    ├── action.sh
    └── helper.py
```

See [CUSTOM_SKILLS_QUICKSTART.md](CUSTOM_SKILLS_QUICKSTART.md) for a step-by-step walkthrough.

### SKILL.md Format

````markdown
---
name: my-skill
version: 1.0.0
description: "One-line description (shown in context always)"
auth: none|token|oauth
triggers:
  - keyword1
  - keyword2
  - phrase
---

# Skill Name

Full documentation loaded on-demand.

## Operations

### Operation 1
```bash
command example
```

**Best practices:**
- Practice 1
- Practice 2

### Operation 2
...

## Security Considerations
...

## Error Handling
...
````

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No (defaults to folder name) | Unique identifier (lowercase, no spaces) |
| `version` | No (defaults to `0.1.0`) | Semantic version (1.0.0) |
| `description` | Recommended | One-line description (always in context) |
| `auth` | No (defaults to `none`) | Authentication type: `none`, `token`, `oauth` (informational) |
| `triggers` | No | Keywords that auto-activate this skill when they appear in the model's response |

### Example: Database Skill

````markdown
---
name: database
version: 1.0.0
description: "Query and manage PostgreSQL databases"
auth: token
triggers:
  - database
  - postgres
  - sql
  - query
  - table
---

# Database Operations

Safe database querying with read-only defaults.

## Connection

```bash
# Set connection via environment variable
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

## Query Data

```bash
# Read-only query
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 10;"
```

**Security:**
- Default to read-only transactions
- Never expose passwords in output
- Use prepared statements to prevent SQL injection
- Require confirmation for writes/deletes

## Best Practices

1. Always use `LIMIT` in queries
2. Check row counts before bulk operations
3. Use transactions for multiple operations
4. Backup before destructive operations
5. Validate user input to prevent injection
````

## Skills Discovery

Skills are discovered from these locations, scanned in this order (if two skills share a
name, the one found last wins):

1. **User skills** (custom)
   - Location: `~/.forge/skills/`
   - Your custom skills

2. **Package skills** (built-in)
   - Location: `teotl/skills/`
   - Includes: filesystem, git, github, web, claude_code, spec_kit, social-media

3. **Environment path**
   - Set `TEOTL_SKILLS_PATH=/path1:/path2` (legacy `FORGE_SKILLS_PATH` also works)
   - Additional skill directories

### Discovery Process

```python
from teotl.primitives.skills.registry import SkillRegistry

# Discover all skills
registry = SkillRegistry()
print(f"Found {registry.registered_count} skills")

# Discover only specific skills
registry = SkillRegistry(enabled=["filesystem", "git"])
print(f"Loaded {registry.registered_count} skills")
```

## CLI

```bash
# Start a chat with specific skills enabled
teotl chat --skills filesystem,git,web

# Inside the chat, list enabled skills
/skills
```

## Cost Analysis

### Skills (Progressive Disclosure)

| Stage | Tokens | When |
|-------|--------|------|
| Descriptions | ~500 | Always in context |
| Full instructions | ~2000 | Temporarily when activated |
| After deactivation | ~500 | Back to descriptions only |

**Example: 10 skills enabled**
- Baseline: 500 tokens (descriptions)
- Peak: 2500 tokens (1 skill active)
- Average: 500-1000 tokens

### MCP (Traditional Approach)

| Stage | Tokens | When |
|-------|--------|------|
| All tool schemas | 30,000+ | Always in context |
| During task | 30,000+ | No change |
| After task | 30,000+ | Still in context |

**Example: 10 MCP servers**
- Baseline: 30,000+ tokens
- Peak: 30,000+ tokens
- Average: 30,000+ tokens

**Result:** a much smaller baseline context cost — actual savings depend on your skills and MCP servers.

## Best Practices

### When to Create a Skill

Create a skill when:
- ✅ Multiple related operations (database: query, insert, update)
- ✅ Complex setup or authentication (OAuth, API keys)
- ✅ Reusable across multiple agents
- ✅ Requires detailed documentation
- ✅ Has safety considerations

Don't create a skill for:
- ❌ Single one-off operations
- ❌ Simple bash commands
- ❌ Already covered by existing skills

### Skill Documentation

**Do:**
- Write clear examples for every operation
- Include security considerations
- Provide error handling guidance
- Show best practices
- Keep descriptions under 100 characters

**Don't:**
- Assume prior knowledge
- Skip edge cases
- Omit safety warnings
- Write essays (be concise)

### Skill Security

**Always:**
- Validate all inputs
- Require confirmation for destructive operations
- Use sandboxing (filesystem/network restrictions)
- Log all operations to audit trail
- Never expose credentials in output

**Never:**
- Execute arbitrary code without validation
- Trust user input directly
- Bypass security policies
- Access sensitive directories without permission

## Troubleshooting

### Skill Not Found

```python
# Error: SkillNotFound: 'my-skill' not found

# Check if skill exists
from pathlib import Path
skill_path = Path.home() / ".forge" / "skills" / "my-skill" / "SKILL.md"
print(f"Exists: {skill_path.exists()}")

# List all discovered skills
from teotl.primitives.skills.registry import SkillRegistry
registry = SkillRegistry()
print(list(registry.skills.keys()))
```

### Skill Not Auto-Activating

Add trigger keywords to frontmatter:

```yaml
triggers:
  - keyword1
  - keyword2
  - "multi word phrase"
```

Or manually activate:

```python
await agent.activate_skill("my-skill")
```

### Skill Instructions Too Long

Target: ~500-2000 tokens per skill

**Reduce by:**
- Using tables instead of prose
- Removing redundant examples
- Linking to external docs
- Splitting into multiple skills

### Permission Errors

If a command is blocked or needs confirmation, it is the agent's guardrail policy at work,
not the skill. Use a custom policy that allows the paths/commands you need — see
[GUARDRAILS.md](GUARDRAILS.md) — or, for daemon/wizard agents, adjust the `security`
section of the agent's config (see [SECURITY_GUIDE.md](SECURITY_GUIDE.md)).

## Planned: Skills Marketplace (not yet available)

A marketplace for discovering, installing, and updating skills is planned. Until then,
install a skill by copying its folder into `~/.forge/skills/` or a directory on
`TEOTL_SKILLS_PATH`. See [SKILLS_ECOSYSTEM.md](SKILLS_ECOSYSTEM.md).

## See Also

- [CUSTOM_SKILLS_QUICKSTART.md](CUSTOM_SKILLS_QUICKSTART.md) - Build your first skill
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Security policies
- [examples/workspace_files/SKILLS.md](../examples/workspace_files/SKILLS.md) - Example SKILLS.md file
