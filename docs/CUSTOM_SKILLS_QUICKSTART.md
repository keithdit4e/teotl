# Custom Skills Quick Start

Quick guide to creating and loading your own skills in Teotl.

## Directory Structure

```
~/.teotl/skills/           ← Your custom skills go here
├── my-skill/
│   └── SKILL.md           ← Skill definition (required)
├── database/
│   └── SKILL.md
└── slack-bot/
    └── SKILL.md
```

## Step-by-Step: Create Your First Skill

### 1. Create the directory

```bash
mkdir -p ~/.teotl/skills/my-skill
cd ~/.teotl/skills/my-skill
```

### 2. Create SKILL.md file

```bash
cat > SKILL.md << 'EOF'
---
name: my-skill
version: 1.0.0
description: "What your skill does in one line"
author: Your Name
license: MIT
tags:
  - category
triggers:
  - keyword
---

# My Skill Name

Brief description of what this skill does.

## Operation 1: Do Something

```bash
# Bash command to execute
echo "Hello from my skill"
```

**Usage:** When to use this operation

**Best practices:**
- Tip 1
- Tip 2

## Operation 2: Do Another Thing

```bash
# Another command
ls -la
```

**Security:** Any safety considerations
EOF
```

### 3. Verify it's discovered

```bash
# From your teotl directory
python3 -c "
from teotl.primitives.skills.registry import SkillRegistry
registry = SkillRegistry()
print('Discovered skills:', list(registry.skills.keys()))
"
```

### 4. Use it in your agent

```python
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(),
    skills=["my-skill"],  # Your custom skill!
)

# Agent can now use your skill
response = await agent.run("Use my-skill to do something")
```

## SKILL.md Format

### Required Frontmatter

```yaml
---
name: skill-name           # Required: lowercase, kebab-case
version: 1.0.0            # Required: semantic version
description: "..."        # Required: one-line description (always in context)
---
```

### Optional Frontmatter

```yaml
---
name: skill-name
version: 1.0.0
description: "..."
author: Your Name         # Recommended
repository: https://...   # Recommended (for sharing)
license: MIT              # Recommended
tags:                     # Optional: for discovery
  - database
  - postgres
triggers:                 # Optional: auto-activate keywords
  - database
  - sql
  - query
---
```

### Content Structure

```markdown
# Skill Name

## Overview
Brief description...

## Operation 1
\`\`\`bash
command here
\`\`\`

**Usage:** When to use this
**Best practices:**
- Practice 1
- Practice 2

## Operation 2
More operations...

## Security Considerations
Safety notes...

## Error Handling
How to handle errors...
```

## Real Example: Database Skill

```markdown
---
name: database
version: 1.0.0
description: "Query and manage PostgreSQL databases safely"
author: Your Name
license: MIT
tags:
  - database
  - postgres
triggers:
  - database
  - sql
  - query
---

# Database Operations

## Query Data

\`\`\`bash
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 10;"
\`\`\`

**Best practices:**
- Always use LIMIT
- Use read-only transactions
- Never expose passwords

## List Tables

\`\`\`bash
psql $DATABASE_URL -c "\\dt"
\`\`\`

## Security

- Default to read-only
- Require confirmation for writes
- Use environment variables for credentials
```

## Skill Discovery Locations

Teotl searches in this order (first match wins):

1. **User skills** (highest priority)
   - `~/.teotl/skills/`
   - Your custom skills

2. **Environment path** (optional)
   - Set `TEOTL_SKILLS_PATH=/path1:/path2`
   - Company/team shared skills

3. **Built-in skills** (lowest priority)
   - `teotl/skills/`
   - filesystem, git, web

## Using Community Skills

### From GitHub

```bash
# Clone Anthropic verified skills
git clone https://github.com/anthropics/agent-skills ~/.teotl/skills/anthropic

# Clone any community skill
git clone https://github.com/user/awesome-skill ~/.teotl/skills/awesome-skill

# Teotl auto-discovers all SKILL.md files
```

### From TEOTL_SKILLS_PATH

```bash
# Add to ~/.bashrc or ~/.zshrc
export TEOTL_SKILLS_PATH="/opt/company-skills:~/projects/team-skills"

# All SKILL.md files in these directories are discovered
```

## Debugging

### Check what skills are discovered

```python
from teotl.primitives.skills.registry import SkillRegistry

registry = SkillRegistry(enabled=None)  # Discover all
print(f"Found {len(registry.skills)} skills:")
for name, meta in registry.skills.items():
    print(f"  {name}: {meta.description}")
    print(f"    Path: {meta.path}")
```

### Verify skill is valid

```bash
# Check SKILL.md exists
ls -la ~/.teotl/skills/my-skill/SKILL.md

# Check frontmatter is valid YAML
python3 -c "
import yaml
with open('~/.teotl/skills/my-skill/SKILL.md'.replace('~', '$HOME')) as f:
    content = f.read()
    if content.startswith('---'):
        parts = content.split('---', 2)
        frontmatter = yaml.safe_load(parts[1])
        print('Valid frontmatter:', frontmatter)
"
```

### Test skill loading

```python
from teotl.primitives.skills.loader import SkillLoader
from pathlib import Path

skill_file = Path.home() / ".teotl" / "skills" / "my-skill" / "SKILL.md"

# Parse frontmatter only
meta = SkillLoader.parse_frontmatter(skill_file)
print(f"Name: {meta.name}")
print(f"Version: {meta.version}")
print(f"Description: {meta.description}")

# Parse full skill
full = SkillLoader.parse_full(skill_file)
print(f"Instructions length: {len(full.instructions)} chars")
```

## Best Practices

### Do

✅ **Write clear descriptions** (LLM uses this to decide when to activate)
✅ **Include examples** for every operation
✅ **Document security considerations**
✅ **Show error handling**
✅ **Keep descriptions under 100 chars** (always in context)
✅ **Use semantic versioning**
✅ **Add author and license info** (for sharing)

### Don't

❌ **Assume prior knowledge** - explain everything
❌ **Skip edge cases** - document error scenarios
❌ **Omit safety warnings** - security is critical
❌ **Write essays** - be concise and scannable
❌ **Include sensitive data** - no API keys or credentials

## Security Guidelines

### Command Safety

```markdown
## Safe Operation

\`\`\`bash
# Read-only, safe command
cat /path/to/file
\`\`\`

## Dangerous Operation (Requires Confirmation)

\`\`\`bash
# Destructive - user must approve
rm -rf /path/to/directory
\`\`\`

**Security:** This operation is destructive. Always:
- Backup first
- Verify path is correct
- Use with caution
```

### Credential Handling

```markdown
## Setup

Set credentials via environment variable (never hardcode):

\`\`\`bash
export API_KEY="your-key-here"
export DATABASE_URL="postgresql://..."
\`\`\`

## Usage

\`\`\`bash
# Good: Uses environment variable
curl -H "Authorization: Bearer $API_KEY" https://api.example.com

# Bad: Hardcoded credential (never do this)
# curl -H "Authorization: Bearer sk-abc123..." https://...
\`\`\`

**Security:** Never expose credentials in:
- Skill documentation
- Command output
- Error messages
- Logs
```

## Testing Your Skill

```python
import asyncio
from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider

async def test_my_skill():
    agent = Agent(
        provider=AnthropicProvider(),
        skills=["my-skill"],
    )

    # Check skill is loaded
    assert "my-skill" in agent.skills.skills
    print("✅ Skill loaded")

    # Check bash tool is available
    assert "bash" in agent._tool_handlers
    print("✅ Bash tool available")

    # Test manual activation
    instructions = await agent.activate_skill("my-skill")
    print(f"✅ Activated: {len(instructions)} chars")

    # Test execution (optional - requires real commands)
    bash_handler = agent._tool_handlers["bash"]
    result = await bash_handler(command="echo 'Testing my skill'")
    print(f"✅ Executed: {result}")

asyncio.run(test_my_skill())
```

## Examples

See working examples:
- **[examples/custom_skill_example.py](../examples/custom_skill_example.py)** - Complete walkthrough
- **[skills/filesystem/SKILL.md](../skills/filesystem/SKILL.md)** - Built-in skill example
- **[skills/git/SKILL.md](../skills/git/SKILL.md)** - Another built-in example

## Resources

- **[SKILLS_GUIDE.md](SKILLS_GUIDE.md)** - Complete skills documentation
- **[SKILLS_ECOSYSTEM.md](SKILLS_ECOSYSTEM.md)** - Anthropic compatibility & community skills
- **Anthropic Agent Skills Standard:** https://agentskills.io

## Quick Reference

```bash
# Create skill directory
mkdir -p ~/.teotl/skills/my-skill

# Create SKILL.md (use template above)
vim ~/.teotl/skills/my-skill/SKILL.md

# Verify discovery
python3 -c "from teotl.primitives.skills.registry import SkillRegistry; print(list(SkillRegistry().skills.keys()))"

# Use in agent
# agent = Agent(skills=["my-skill"])
```

---

**That's it!** Your custom skill is ready to use. The agent can now execute its commands through the secure bash tool.
