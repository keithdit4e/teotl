# Skills Ecosystem & Compatibility

Teotl uses the **Anthropic Agent Skills standard** (SKILL.md format), making it compatible with thousands of community-created skills.

## Overview

As of March 2026, the Anthropic skills ecosystem includes:
- **Official Anthropic skills** - Verified, production-ready
- **Third-party verified skills** - Reviewed and approved
- **Community skills** - Thousands of user-contributed skills

**All use the same SKILL.md format** that works across:
- Teotl (this framework)
- Claude Code
- Cursor
- Gemini CLI
- Codex CLI
- Antigravity IDE

## SKILL.md Format (Anthropic Standard)

Teotl is **fully compatible** with Anthropic's SKILL.md format:

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

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique identifier (lowercase, kebab-case) |
| `version` | ✅ | Semantic version (1.0.0) |
| `description` | ✅ | One-line description (used for discovery) |
| `author` | Recommended | Creator name or organization |
| `repository` | Recommended | Source code URL |
| `license` | Recommended | License (MIT, Apache-2.0, etc.) |
| `tags` | Optional | Discovery keywords |
| `allowed-tools` | Optional | Restrict which tools can be used |
| `dependencies` | Optional | Other skills this depends on |
| `auth` | Optional | Authentication type (none, token, oauth) |

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
├── filesystem/SKILL.md
├── git/SKILL.md
└── web/SKILL.md
```

### 3. Environment Path
```bash
export TEOTL_SKILLS_PATH="/opt/company-skills:/home/user/projects/skills"
```

### 4. Git Repositories (Recommended for Community Skills)
```bash
# Clone Anthropic verified skills
git clone https://github.com/anthropics/agent-skills ~/.teotl/skills/anthropic

# Clone community skills
git clone https://github.com/user/awesome-skills ~/.teotl/skills/awesome

# Teotl auto-discovers all SKILL.md files in subdirectories
```

## Using Community Skills

### Method 1: Clone Skill Repository

```bash
# Example: Using a community database skill
cd ~/.teotl/skills
git clone https://github.com/community/postgres-skill

# Teotl automatically discovers it
teotl skills list
# Output:
#   postgres — Execute PostgreSQL queries safely
```

Then in your agent:
```python
agent = Agent(
    provider=AnthropicProvider(),
    skills=["filesystem", "git", "postgres"],  # ✅ Works!
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
export TEOTL_SKILLS_PATH="/opt/company-skills:~/projects/ml-skills"

# Teotl searches all paths
```

## Skill Marketplace (Future)

**Coming soon:**
```bash
# Discover skills
teotl skills search postgres
# Output:
#   postgres-admin (official) - Database administration
#   postgres-query (community) ⭐ 1.2k - Safe query execution
#   postgres-migrate (verified) - Schema migrations

# Install from marketplace
teotl skills install postgres-query

# Update installed skills
teotl skills update

# Show skill info
teotl skills info postgres-query
# Output:
#   Name: postgres-query
#   Author: @dbexpert
#   Version: 2.1.0
#   Downloads: 15k
#   Rating: 4.8/5
#   Repository: https://github.com/dbexpert/postgres-skill
```

## Creating Compatible Skills

### Quick Start

```bash
# Create skill directory
mkdir ~/.teotl/skills/my-skill
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
\`\`\`bash
command example
\`\`\`

**Usage:**
When to use this...

**Security:**
Safety considerations...
EOF

# Test it
teotl skills list | grep my-skill
```

### Best Practices

**Do:**
- ✅ Write clear, concise descriptions (Claude uses this for discovery)
- ✅ Include security considerations
- ✅ Provide concrete examples
- ✅ List dependencies explicitly
- ✅ Use semantic versioning
- ✅ Include author and license info
- ✅ Tag appropriately for discovery

**Don't:**
- ❌ Assume prior knowledge
- ❌ Skip error handling guidance
- ❌ Forget edge cases
- ❌ Make descriptions too long (Claude truncates)
- ❌ Include sensitive data (API keys, credentials)

## Sharing Skills

### 1. Publish to GitHub

```bash
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
agent = Agent(skills=["my-skill"])
```
EOF
```

### 2. Submit to Anthropic Verified Skills

Follow guidelines at: https://agentskills.io/contribute

**Requirements:**
- Comprehensive documentation
- Security review passed
- Examples and tests included
- Actively maintained
- Open source license

### 3. List in Community Registry

Submit PR to: https://github.com/anthropics/agent-skills

**Benefits:**
- Discoverable via `teotl skills search`
- Installation via `teotl skills install`
- Automatic updates
- Usage analytics

## Compatibility Testing

### Test with Multiple Platforms

Your skill should work across all SKILL.md-compatible platforms:

```bash
# Test with Teotl
teotl skills list | grep my-skill

# Test with Claude Code (if installed)
claude skills list | grep my-skill

# Test with Cursor (if installed)
cursor --list-skills | grep my-skill
```

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

    required = ['name', 'version', 'description']
    for field in required:
        assert field in frontmatter, f'Missing {field}'

    print('✅ Valid SKILL.md')
else:
    print('❌ Missing frontmatter')
"
```

## Migration from Other Formats

### From MCP Tools

If you have MCP tools, convert to SKILL.md:

```python
# mcp_to_skill.py
import json

# Read MCP tool definition
with open('mcp-tool.json') as f:
    mcp = json.load(f)

# Generate SKILL.md
skill_md = f"""---
name: {mcp['name']}
version: 1.0.0
description: "{mcp['description']}"
---

# {mcp['name'].title()}

## Usage

\`\`\`bash
# Convert MCP tool parameters to bash command
{generate_bash_example(mcp)}
\`\`\`
"""

with open('SKILL.md', 'w') as f:
    f.write(skill_md)
```

### From LangChain Tools

LangChain tools can be wrapped:

```python
from langchain.tools import Tool

# Existing LangChain tool
langchain_tool = Tool(
    name="calculator",
    description="Perform calculations",
    func=lambda x: eval(x)
)

# Create SKILL.md wrapper
with open('~/.teotl/skills/calculator/SKILL.md', 'w') as f:
    f.write(f"""---
name: {langchain_tool.name}
version: 1.0.0
description: "{langchain_tool.description}"
---

# {langchain_tool.name.title()}

Uses Python for calculations.

## Usage

\`\`\`bash
python -c "print({langchain_tool.name}('expression'))"
\`\`\`
""")
```

## Skill Collections

### Official Anthropic Skills

```bash
# Clone official collection
git clone https://github.com/anthropics/agent-skills ~/.teotl/skills/anthropic

# Available skills:
# - web-search
# - database-query
# - file-operations
# - git-workflow
# - api-client
# - data-analysis
# [and many more]
```

### Awesome Agent Skills

Community-curated collection:

```bash
# Clone awesome-agent-skills
git clone https://github.com/awesome-skills/agent-skills ~/.teotl/skills/awesome

# Browse at: https://github.com/awesome-skills/agent-skills
```

### Company/Team Collections

Share skills across your organization:

```bash
# Company skills repository
git clone https://github.com/company/internal-skills ~/.teotl/skills/company

# Set as default for all agents
export TEOTL_SKILLS_PATH="~/.teotl/skills/company:~/.teotl/skills/anthropic"
```

## Troubleshooting

### Skill Not Found

```bash
# Check if skill exists
ls ~/.teotl/skills/my-skill/SKILL.md

# Check if discovered
teotl skills list | grep my-skill

# Check frontmatter is valid
python -m yaml ~/.teotl/skills/my-skill/SKILL.md
```

### Duplicate Skills

If multiple skills have the same name, the first one found wins:

1. User skills (`~/.teotl/skills/`)
2. Environment path (`$TEOTL_SKILLS_PATH`)
3. Package skills (`teotl/skills/`)

Override by placing your version in `~/.teotl/skills/`.

### Version Conflicts

Skills don't version-conflict - agents load by name only. To use multiple versions:

```bash
# Rename skill directories
mv postgres-skill postgres-skill-v1
mv postgres-skill-new postgres-skill-v2

# Reference in agent
agent = Agent(skills=["postgres-skill-v2"])
```

## Security Considerations

### Untrusted Skills

Before using community skills:

1. **Review SKILL.md** - Check what commands it runs
2. **Check repository** - Verify author and stars/reviews
3. **Test in sandbox** - Run with strict security policy first
4. **Limit scope** - Use `allowed-tools` to restrict capabilities

### Sandboxing

All skill commands run through Teotl's sandbox:

```python
from teotl.core.security import SecurityPolicy

# Strict policy for untrusted skills
policy = SecurityPolicy.create_default("agent", "strict")
policy.sandbox.allowed_paths = ["~/.teotl/agents/agent/**"]
policy.sandbox.allowed_domains = []  # Block network

agent = Agent(
    skills=["untrusted-skill"],
    policy=policy  # Sandboxed execution
)
```

## Resources

- **Anthropic Agent Skills Docs:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills
- **Agent Skills Standard:** https://agentskills.io
- **Skills Guide (PDF):** https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- **Awesome Agent Skills:** https://github.com/awesome-skills/agent-skills (community)
- **Teotl Skills Guide:** [SKILLS_GUIDE.md](SKILLS_GUIDE.md)

## Next Steps

1. **Browse community skills** - Find what you need
2. **Clone to ~/.teotl/skills/** - Install locally
3. **Enable in agent** - Add to `skills=[]` parameter
4. **Test with simple task** - Verify it works
5. **Create your own** - Share with community

---

**Key Takeaway:** Teotl is fully compatible with the Anthropic Agent Skills ecosystem. You can use any SKILL.md-compatible skill from the community without modification!
