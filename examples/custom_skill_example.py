"""Example: Creating and Loading Custom Skills

This example shows how to:
1. Create a custom skill in the correct directory
2. Write a SKILL.md file in Anthropic-compatible format
3. Load and use the skill in your agent
4. Verify the skill is discovered

Custom skills go in: ~/.forge/skills/your-skill-name/SKILL.md
"""

import asyncio
from pathlib import Path

from teotl.core.agent import Agent
from teotl.core.provider import AnthropicProvider


def create_example_skill():
    """Create an example custom skill: database queries."""
    # User skills directory
    skills_dir = Path.home() / ".forge" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create custom skill directory
    db_skill_dir = skills_dir / "database"
    db_skill_dir.mkdir(exist_ok=True)

    # Create SKILL.md file
    skill_content = """---
name: database
version: 1.0.0
description: "Query and manage PostgreSQL databases safely"
author: Your Name
license: MIT
tags:
  - database
  - postgres
  - sql
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

Set your database connection via environment variable:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

## Query Data (Read-Only)

```bash
# Simple SELECT query
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 10;"

# Query with formatting
psql $DATABASE_URL -c "SELECT id, email, created_at FROM users WHERE active = true LIMIT 10;" --csv

# Count records
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
```

## List Tables

```bash
# List all tables in database
psql $DATABASE_URL -c "\\dt"

# List tables matching pattern
psql $DATABASE_URL -c "\\dt user*"
```

## Describe Table Schema

```bash
# Show table structure
psql $DATABASE_URL -c "\\d users"

# Show table with details
psql $DATABASE_URL -c "\\d+ users"
```

## Best Practices

1. **Always use LIMIT** - Prevent accidentally fetching millions of rows
2. **Use read-only transactions** - Add `BEGIN TRANSACTION READ ONLY; ... COMMIT;`
3. **Validate queries** - Check for dangerous operations (DROP, DELETE, TRUNCATE)
4. **Use prepared statements** - Prevent SQL injection when using user input
5. **Check row counts** - Before bulk operations, verify with COUNT(*)

## Security Considerations

**READ-ONLY by default:**
- Never expose database passwords in output
- Use environment variables for credentials
- Require confirmation for writes/deletes
- Use `SET TRANSACTION READ ONLY;` for safety

**Dangerous operations (require explicit confirmation):**
- `DROP TABLE` / `DROP DATABASE`
- `DELETE FROM` / `TRUNCATE`
- `UPDATE` without WHERE clause
- `ALTER TABLE`

## Error Handling

```bash
# Check if database is accessible
psql $DATABASE_URL -c "SELECT 1;" 2>&1

# Capture errors
psql $DATABASE_URL -c "SELECT * FROM nonexistent_table;" 2>&1 || echo "Query failed"
```

## Examples

### Find users by email pattern
```bash
psql $DATABASE_URL -c "SELECT id, email FROM users WHERE email LIKE '%@example.com' LIMIT 50;"
```

### Aggregate data
```bash
psql $DATABASE_URL -c "SELECT status, COUNT(*) FROM orders GROUP BY status;"
```

### Join tables
```bash
psql $DATABASE_URL -c "SELECT u.email, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.email LIMIT 20;"
```
"""

    skill_file = db_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    print(f"✅ Created custom skill at: {skill_file}")
    print("\nSkill structure:")
    print("~/.forge/skills/")
    print("└── database/")
    print("    └── SKILL.md")

    return skill_file


def verify_skill_discovered():
    """Verify the custom skill is discovered by Forge."""
    from teotl.primitives.skills.registry import SkillRegistry

    print("\n" + "=" * 60)
    print("Verifying Skill Discovery")
    print("=" * 60)

    # Discover all skills (no filter)
    registry = SkillRegistry(enabled=None)

    print(f"\n✅ Discovered {len(registry.skills)} total skills:")
    for name, meta in registry.skills.items():
        print(f"   - {name}: {meta.description}")

    # Check if our custom skill is there
    if "database" in registry.skills:
        print("\n✅ Custom 'database' skill found!")
        db_skill = registry.skills["database"]
        print(f"   Name: {db_skill.name}")
        print(f"   Version: {db_skill.version}")
        print(f"   Description: {db_skill.description}")
        print(f"   Path: {db_skill.path}")
    else:
        print("\n❌ Custom 'database' skill not found")
        print("   Make sure it's in: ~/.forge/skills/database/SKILL.md")


async def use_custom_skill():
    """Use the custom skill in an agent."""
    print("\n" + "=" * 60)
    print("Using Custom Skill in Agent")
    print("=" * 60)

    # Create agent with custom skill
    agent = Agent(
        provider=AnthropicProvider(),
        instructions="You are a helpful database assistant.",
        skills=["database", "filesystem"],  # Include custom skill
    )

    # Verify skill is loaded
    if agent.skills:
        print(f"\n✅ Agent has {len(agent.skills.skills)} skills loaded:")
        for name in agent.skills.skills:
            print(f"   - {name}")

        # Get skill descriptions (what's always in context)
        descriptions = agent.skills.get_descriptions()
        print("\n📝 Skill descriptions in context:")
        print(descriptions[:400] + "...")

        # Manually activate skill to see full instructions
        print("\n🔧 Activating 'database' skill to see full instructions...")
        instructions = await agent.activate_skill("database")
        print(f"\n✅ Loaded {len(instructions)} characters of instructions")
        print(f"First 300 chars:\n{instructions[:300]}...")

        # Check bash tool is available
        if "bash" in agent._tool_handlers:
            print("\n✅ Bash tool available for executing skill commands")

            # Example: Could now use the skill
            # response = await agent.run("Show me the first 5 users from the database")
            # The agent would use the database skill instructions to execute:
            # psql $DATABASE_URL -c "SELECT * FROM users LIMIT 5;"

    else:
        print("\n❌ Skills not initialized")


def show_skill_locations():
    """Show where Forge looks for skills."""
    print("\n" + "=" * 60)
    print("Skill Discovery Locations")
    print("=" * 60)

    print("\n📁 Forge searches for skills in this order:")
    print("\n1. User Skills (highest priority)")
    print("   ~/.forge/skills/")
    print("   └── your-custom-skill/")
    print("       └── SKILL.md")

    print("\n2. Environment Path (optional)")
    print("   export FORGE_SKILLS_PATH='/opt/company-skills:/path/to/more/skills'")

    print("\n3. Built-in Skills (lowest priority)")
    print("   forge-agent/skills/")
    print("   ├── filesystem/SKILL.md")
    print("   ├── git/SKILL.md")
    print("   └── web/SKILL.md")

    print("\n💡 Tips:")
    print("   - Skills in user directory override built-in skills with same name")
    print("   - Use FORGE_SKILLS_PATH for team/company shared skills")
    print("   - Clone community skills: git clone <repo> ~/.forge/skills/<name>")


def show_skill_template():
    """Show minimal SKILL.md template."""
    print("\n" + "=" * 60)
    print("Minimal SKILL.md Template")
    print("=" * 60)

    template = """---
name: my-skill
version: 1.0.0
description: "One-line description (shown in context always)"
author: Your Name
license: MIT
tags:
  - tag1
  - tag2
triggers:
  - keyword1
  - keyword2
---

# My Skill Name

Brief overview of what this skill does.

## Operation 1

```bash
command-to-run --with-args
```

**When to use:** Describe when this operation is appropriate

**Best practices:**
- Practice 1
- Practice 2

## Operation 2

```bash
another-command
```

**Security:** Safety considerations for this operation

## Error Handling

How to handle common errors...
"""

    print("\n" + template)
    print("\n💡 Save this as: ~/.forge/skills/my-skill/SKILL.md")


async def main():
    """Run the complete example."""
    print("=" * 60)
    print("Custom Skills: Complete Example")
    print("=" * 60)

    # Show where skills go
    show_skill_locations()

    # Show template
    show_skill_template()

    # Create example skill
    print("\n" + "=" * 60)
    print("Creating Example Custom Skill")
    print("=" * 60)
    create_example_skill()

    # Verify it's discovered
    verify_skill_discovered()

    # Use it in an agent
    await use_custom_skill()

    print("\n" + "=" * 60)
    print("Summary: How to Add Your Own Skills")
    print("=" * 60)
    print("\n✅ Step 1: Create directory structure")
    print("   mkdir -p ~/.forge/skills/my-skill")
    print("\n✅ Step 2: Create SKILL.md file")
    print("   # Add frontmatter (name, version, description)")
    print("   # Add markdown content with bash commands")
    print("\n✅ Step 3: Enable in agent")
    print("   agent = Agent(skills=['my-skill'])")
    print("\n✅ Step 4: Use it!")
    print("   response = await agent.run('Use my-skill to do X')")

    print("\n📚 More resources:")
    print("   - docs/SKILLS_GUIDE.md - Complete skills guide")
    print("   - docs/SKILLS_ECOSYSTEM.md - Community skills")
    print("   - skills/filesystem/SKILL.md - Example built-in skill")


if __name__ == "__main__":
    asyncio.run(main())
