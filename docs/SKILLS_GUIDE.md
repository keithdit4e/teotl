# Skills Guide

Skills provide progressive disclosure for agent capabilities - keeping context costs low while making powerful tools available on-demand.

## Overview

**Problem:** MCP loads all tool schemas at startup = 30,000+ tokens permanently in context

**Solution:** Skills load descriptions (~50 tokens each), full instructions only when needed

**Result:** 10 skills = ~500 tokens (not 30,000+)

## Built-in Skills

Teotl includes three production-ready skills:

### 1. Filesystem Skill
Read, write, search, and navigate files and directories.

**Capabilities:**
- Read/write files with safety checks
- Search file contents (grep)
- Find files by name/size/date
- Create/delete directories
- File metadata and permissions
- Archive operations (tar, zip)

**Security:**
- Filesystem sandboxing enforced
- Blocked patterns (`/etc`, `~/.ssh`, etc.)
- Confirmation required for deletions
- Backup recommendations before overwrites

**Example:**
```python
agent = Agent(skills=["filesystem"])
response = await agent.run("Find all Python files larger than 1MB")
```

### 2. Git Skill
Version control operations with safety guardrails.

**Capabilities:**
- Status, diff, log
- Add, commit, push
- Branch management
- Stash operations
- Merge and rebase

**Security:**
- Push requires confirmation
- Force push blocked
- No rewriting published history
- Validates clean working tree

**Example:**
```python
agent = Agent(skills=["git"])
response = await agent.run("Create a commit with all changes")
```

### 3. Web Skill
Web search and content fetching.

**Capabilities:**
- Search web (via search provider API)
- Fetch webpage content
- Parse HTML/markdown
- Follow redirects
- Cache results

**Security:**
- Domain allowlist enforced
- HTTPS required
- Response size limited
- Rate limits applied

**Example:**
```python
agent = Agent(skills=["web"])
response = await agent.run("Search for Python async best practices")
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

**Step 2: Agent determines relevance**
User asks: "List all TODO comments in Python files"
Agent thinks: "I need filesystem skill for searching"

**Step 3: Full instructions loaded on-demand**
```
# Filesystem Operations

## Search File Contents
grep -rn "TODO" *.py

[... 398 lines of detailed instructions ...]
```
Cost: ~2000 tokens (temporary)

**Step 4: Task completed, skill deactivated**
Instructions removed from context → back to ~150 tokens

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
# Get all registered skills
skills = agent.list_skills()
for name, description in skills.items():
    print(f"{name}: {description}")
```

## Creating Custom Skills

### Directory Structure

```
~/.teotl/skills/my-skill/
├── SKILL.md          # Required: Frontmatter + instructions
└── scripts/          # Optional: Executable tools
    ├── action.sh
    ├── helper.py
    └── README.md
```

### SKILL.md Format

```markdown
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
\`\`\`bash
command example
\`\`\`

**Best practices:**
- Practice 1
- Practice 2

### Operation 2
...

## Security Considerations
...

## Error Handling
...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier (lowercase, no spaces) |
| `version` | Yes | Semantic version (1.0.0) |
| `description` | Yes | One-line description (always in context) |
| `auth` | No | Authentication type: `none`, `token`, `oauth` |
| `triggers` | No | Keywords that should auto-activate this skill |

### Example: Database Skill

```markdown
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

\`\`\`bash
# Set connection via environment variable
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
\`\`\`

## Query Data

\`\`\`bash
# Read-only query
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 10;"
\`\`\`

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
```

## Skills Discovery

Skills are discovered from multiple locations:

1. **Package skills** (built-in)
   - Location: `teotl/skills/`
   - Includes: filesystem, git, web

2. **User skills** (custom)
   - Location: `~/.teotl/skills/`
   - Your custom skills

3. **Environment path**
   - Set `TEOTL_SKILLS_PATH=/path1:/path2`
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

## CLI Commands

```bash
# List all available skills
teotl skills list

# Output:
#   filesystem — Read, write, search files and directories
#   git — Version control operations
#   web — Web search and URL fetching
```

## Cost Analysis

### Skills (Progressive Disclosure)

| Stage | Tokens | When |
|-------|--------|------|
| Descriptions | ~500 | Always in context |
| Full instructions | ~2000 | Temporarily when activated |
| After task | ~500 | Deactivated, back to descriptions |

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

**Savings:** ~97% reduction in context usage

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
skill_path = Path.home() / ".teotl" / "skills" / "my-skill" / "SKILL.md"
print(f"Exists: {skill_path.exists()}")

# List all discovered skills
from teotl.primitives.skills.registry import SkillRegistry
registry = SkillRegistry()
print(registry.skills.keys())
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

```bash
# Error: Permission denied accessing /etc/config

# Check security policy
cat ~/.teotl/agents/my-agent/security.yaml

# Add path to allowed_paths:
sandbox:
  allowed_paths:
    - "~/.teotl/agents/my-agent/**"
    - "/path/to/allow/**"
```

## Future: Skills Marketplace

Coming soon:
- `teotl skills install <name>` - Install from marketplace
- `teotl skills search <query>` - Discover skills
- `teotl skills update` - Update installed skills
- Skill ratings and reviews
- Skill dependencies and versioning

## See Also

- [WORKSPACE_FILES.md](WORKSPACE_FILES.md) - Customizing agent behavior
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - Security policies
- [examples/workspace_files/SKILLS.md](../examples/workspace_files/SKILLS.md) - Example SKILLS.md file
