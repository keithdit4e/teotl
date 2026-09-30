# Skills Ecosystem & Compatibility

Teotl uses the **Anthropic Agent Skills standard** (SKILL.md format), so skills written for other SKILL.md-compatible tools can generally be used with Teotl.

## Overview

The SKILL.md format is shared by Teotl and other agent tools (for example Claude Code).
A skill is a folder containing a `SKILL.md` file: YAML frontmatter plus Markdown instructions.

## SKILL.md Format (Anthropic Standard)

Teotl reads the standard SKILL.md format:

```markdown
---
name: skill-name
version: 1.0.0
description: "One-line description for discovery"
author: your-name
repository: https://github.com/you/skill
license: MIT
tags:
  - tag1
  - tag2
allowed-tools:
  - bash
  - filesystem
---

# Skill Name

Full documentation loaded on-demand...

## Usage

Examples and instructions...
```

### Frontmatter Fields

Teotl reads these fields (see `teotl/primitives/skills/loader.py`):

| Field | Default if omitted | Description |
|-------|--------------------|-------------|
| `name` | Folder name | Unique identifier used in `skills=[...]` |
| `description` | `""` | One-line description, always in context (used for discovery) |
| `version` | `0.1.0` | Semantic version |
| `auth` | `none` | Authentication type (informational) |
| `triggers` | `[]` | Keywords associated with the skill |

Other fields (`author`, `repository`, `license`, `tags`, `allowed-tools`, `dependencies`, ...)
are accepted for compatibility with other tools but are **ignored by Teotl** — in particular,
`allowed-tools` does not restrict anything in Teotl. Always include a `description`.

## Skill Discovery

Teotl discovers skills from multiple sources:

### 1. Local User Skills
```
~/.teotl/skills/
├── my-custom-skill/
│   └── SKILL.md
├── database-queries/
│   └── SKILL.md
└── slack-automation/
    └── SKILL.md
```

### 2. Package Built-in Skills
```
teotl/skills/
├── claude_code/SKILL.md
├── filesystem/SKILL.md
├── git/SKILL.md
├── github/SKILL.md
├── social-media/SKILL.md
├── spec_kit/SKILL.md
└── web/SKILL.md
```

### 3. Environment Path
```bash
export TEOTL_SKILLS_PATH="/opt/company-skills:/home/user/projects/skills"
# (legacy TEOTL_SKILLS_PATH is also read)
```

Discovery looks **one level deep**: each search directory must directly contain skill
folders, each with its own `SKILL.md` (`<search-dir>/<skill-name>/SKILL.md`). A repository
that nests several skills in subfolders should be added to `TEOTL_SKILLS_PATH` at the
level that directly contains the skill folders.

## Using Community Skills

### Method 1: Clone Skill Repository

```bash
# Example: installing a (hypothetical) community database skill
mkdir -p ~/.teotl/skills
cd ~/.teotl/skills
git clone <skill-repo-url> postgres    # folder must contain SKILL.md at its top level

# Teotl discovers it automatically. To check, start a chat with it and use /skills:
teotl chat --skills postgres
```

Then in your agent:
```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(),
    skills=["filesystem", "git", "postgres"],
)
```

### Method 2: Symlink Skills

```bash
# Link to skills from another project
ln -s /path/to/project/skills/custom-skill ~/.teotl/skills/custom-skill

# Or link entire skill collection
ln -s /opt/company/skills/* ~/.teotl/skills/
```

### Method 3: Environment Variable

```bash
# Add to ~/.bashrc or ~/.zshrc
export TEOTL_SKILLS_PATH="/opt/company-skills:$HOME/projects/ml-skills"

# Teotl searches all paths
```

## Skill Marketplace (Planned — not yet available)

A skill marketplace with search/install/update commands is planned but does not exist yet.
There is currently no `teotl skills` CLI command; install skills by copying or cloning
their folders into `~/.teotl/skills/` or a directory on `TEOTL_SKILLS_PATH`.

## Creating Compatible Skills

### Quick Start

````bash
# Create skill directory
mkdir -p ~/.teotl/skills/my-skill
cd ~/.teotl/skills/my-skill

# Create SKILL.md
cat > SKILL.md << 'EOF'
---
name: my-skill
version: 1.0.0
description: "What this skill does in one line"
author: Your Name
license: MIT
tags:
  - tag1
  - tag2
---

# My Skill

## Overview
What this skill does...

## Operations

### Operation 1
```bash
command example
```

**Usage:**
When to use this...

**Security:**
Safety considerations...
EOF

# Test it (type /skills inside the chat to see enabled skills)
teotl chat --skills my-skill
````

### Best Practices

**Do:**
- ✅ Write clear, concise descriptions (Claude uses this for discovery)
- ✅ Include security considerations
- ✅ Provide concrete examples
- ✅ Use semantic versioning
- ✅ Include author and license info
- ✅ Add `triggers` keywords for discovery

**Don't:**
- ❌ Assume prior knowledge
- ❌ Skip error handling guidance
- ❌ Forget edge cases
- ❌ Make descriptions too long (Claude truncates)
- ❌ Include sensitive data (API keys, credentials)

## Sharing Skills

### 1. Publish to GitHub

````bash
# Create repository
cd ~/.teotl/skills/my-skill
git init
git add SKILL.md
git commit -m "Initial skill"
git remote add origin https://github.com/you/my-skill
git push -u origin main

# Add README
cat > README.md << 'EOF'
# My Skill

Agent skill for [purpose].

## Installation

```bash
cd ~/.teotl/skills
git clone https://github.com/you/my-skill
```

## Usage

```python
agent = Agent(provider=provider, skills=["my-skill"])
```
EOF
````

### 2. Share with the Community

Publish your skill repository and let others clone it into their `~/.teotl/skills/` directory.
See the Agent Skills standard at https://agentskills.io for format guidance.

## Compatibility Testing

### Test with Multiple Platforms

Your skill should work across all SKILL.md-compatible platforms:

```bash
# Test with Teotl (type /skills inside the chat)
teotl chat --skills my-skill
```

Check the other tools' own documentation for how they discover skills.

### Validation Script

```bash
# Validate SKILL.md format
python -c "
import yaml

with open('SKILL.md') as f:
    content = f.read()

# Extract frontmatter
if content.startswith('---'):
    parts = content.split('---', 2)
    frontmatter = yaml.safe_load(parts[1])

    required = ['name', 'description']  # Teotl defaults the rest
    for field in required:
        assert field in frontmatter, f'Missing {field}'

    print('✅ Valid SKILL.md')
else:
    print('❌ Missing frontmatter')
"
```

## Migration from Other Formats

### From MCP Tools

If you have MCP tools, you can generate a SKILL.md skeleton from a tool definition and
then fill in the usage instructions by hand:

```python
# mcp_to_skill.py
import json
from pathlib import Path

FENCE = "`" * 3  # Markdown code fence

# Read MCP tool definition
with open("mcp-tool.json") as f:
    mcp = json.load(f)

skill_dir = Path.home() / ".teotl" / "skills" / mcp["name"]
skill_dir.mkdir(parents=True, exist_ok=True)

# Generate SKILL.md
skill_md = f"""---
name: {mcp['name']}
version: 1.0.0
description: "{mcp['description']}"
---

# {mcp['name'].title()}

## Usage

{FENCE}bash
# TODO: describe the equivalent CLI command(s) for this tool
{FENCE}
"""

(skill_dir / "SKILL.md").write_text(skill_md)
```

## Skill Collections

### Company/Team Collections

Share skills across your organization:

```bash
# Company skills repository (folder that directly contains skill folders)
git clone <company-skills-repo-url> ~/company-skills

# Make it available to all agents
export TEOTL_SKILLS_PATH="$HOME/company-skills"
```

## Troubleshooting

### Skill Not Found

```bash
# Check if skill exists
ls ~/.teotl/skills/my-skill/SKILL.md

# Check if discovered (type /skills inside the chat)
teotl chat --skills my-skill

# Check frontmatter is valid (see the validation script above)
```

### Duplicate Skills

Directories are scanned in this order, and if multiple skills have the same name, the
**last one found wins**:

1. User skills (`~/.teotl/skills/`)
2. Package skills (`teotl/skills/`)
3. Environment path (`$TEOTL_SKILLS_PATH`, then legacy `$TEOTL_SKILLS_PATH`)

To override a bundled skill, put your version in a directory on `TEOTL_SKILLS_PATH`
(a same-named skill in `~/.teotl/skills/` is overridden by the bundled one).

### Version Conflicts

Skills don't version-conflict - agents load by name only. To use multiple versions:

```bash
# Rename skill directories and give each a distinct `name:` in its SKILL.md frontmatter
mv postgres-skill postgres-skill-v1
mv postgres-skill-new postgres-skill-v2
```

```python
# Reference in agent
agent = Agent(provider=provider, skills=["postgres-skill-v2"])
```

## Security Considerations

### Untrusted Skills

Before using community skills:

1. **Review SKILL.md** - Check what commands it runs
2. **Check repository** - Verify author and stars/reviews
3. **Test with a strict policy** - Run with `policy="strict"` first
4. **Limit scope** - Enable only the skills you need via `skills=[...]`

### Guardrails

Skill instructions are carried out through the agent's tools (e.g. `bash`), and every tool
call passes through Teotl's guardrails. Use the strict preset for untrusted skills:

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider

agent = Agent(
    provider=AnthropicProvider(),
    skills=["untrusted-skill"],
    policy="strict",  # minimal | standard (default) | strict
)
```

See [GUARDRAILS.md](GUARDRAILS.md) for custom policies.

## Resources

- **Anthropic Agent Skills Docs:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills
- **Agent Skills Standard:** https://agentskills.io
- **Skills Guide (PDF):** https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- **Teotl Skills Guide:** [SKILLS_GUIDE.md](SKILLS_GUIDE.md)

## Next Steps

1. **Browse community skills** - Find what you need
2. **Clone to ~/.teotl/skills/** - Install locally
3. **Enable in agent** - Add to `skills=[]` parameter
4. **Test with simple task** - Verify it works
5. **Create your own** - Share with community

---

**Key Takeaway:** Teotl uses the standard SKILL.md format, so most community skills can be used by dropping their folder into `~/.teotl/skills/`. Review a skill's instructions before enabling it.
