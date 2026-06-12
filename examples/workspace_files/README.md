# Workspace Files Example

This example demonstrates how workspace files (PERSONALITY.md, USER.md, INSTRUCTIONS.md, SKILLS.md) are loaded at runtime.

## How It Works

When you run an agent daemon, it automatically loads workspace files from your agent's directory:

```
~/.teotl/agents/my-agent/
├── PERSONALITY.md    # Agent identity, voice, values
├── USER.md           # Your preferences and context
├── INSTRUCTIONS.md   # Operating procedures and rules
├── SKILLS.md         # Available capabilities
├── security.yaml     # Security policy
└── memory/           # Memory database
```

## Loading Priority

The agent loads instructions in this order:

1. **Workspace files exist?** → Use workspace files (config.yaml instructions are IGNORED)
2. **No workspace files?** → Fall back to `instructions` from config.yaml

This means you can customize your agent by editing markdown files without touching YAML!

## Verify It's Loading

### Method 1: Check the Logs

When you start the daemon, look for this log message:

```
INFO - Loaded 4 workspace files from ~/.teotl/agents/my-agent
```

Or if using the executor factory:

```
INFO - Using workspace files for agent instructions
```

If you see this, workspace files are being loaded successfully!

### Method 2: Add Debug Logging

Edit your config.yaml and run with verbose logging:

```bash
python -m forge.daemon.run --config config.yaml 2>&1 | grep -i "workspace\|instruction"
```

You should see:
```
DEBUG - Loaded workspace file: PERSONALITY.md
DEBUG - Loaded workspace file: USER.md
DEBUG - Loaded workspace file: INSTRUCTIONS.md
DEBUG - Loaded workspace file: SKILLS.md
INFO - Using workspace files for agent instructions
```

### Method 3: Test with Unique Content

Add a unique phrase to PERSONALITY.md:

```markdown
# Agent Personality

UNIQUE_TEST_PHRASE_12345

You are a friendly assistant...
```

Then create a task that tests for it:

```python
from forge.primitives.tasks import Task, Priority

task = Task(
    description="What is your personality? Please include any unique test phrases you see.",
    priority=Priority.HIGH
)
```

If the agent mentions `UNIQUE_TEST_PHRASE_12345`, the file was loaded!

## Example: Custom Personality

Create a workspace and customize the agent:

```bash
# Run onboarding wizard
teotl onboard

# Edit the personality file
nano ~/.teotl/agents/my-agent/PERSONALITY.md

# Add custom content:
```

```markdown
# Agent Personality

## Name
I am Jarvis, your personal AI assistant.

## Voice & Tone
- Professional but warm
- Proactive problem-solver
- Never says "I cannot" - always finds alternatives
- Uses British English spelling

## Values
1. Efficiency over verbosity
2. Show, don't tell (provide examples)
3. Respect user's time - be concise
```

```bash
# Start the daemon
python -m forge.daemon.run --config config.yaml

# The agent will now use this personality!
```

## Files Loaded in Order

1. **PERSONALITY.md** - First (sets the foundation)
2. **USER.md** - Second (adds user context)
3. **INSTRUCTIONS.md** - Third (adds procedures)
4. **SKILLS.md** - Fourth (adds capabilities)

They're combined with `\n\n---\n\n` separators into one system prompt.

## Common Issues

### Issue: Workspace files not loading

**Check:**
1. Files exist in the correct directory
2. Directory path matches config.yaml (single vs multi-agent)
3. Files have content (empty files are skipped)
4. No file permission issues

**Debug:**
```python
from pathlib import Path
from forge.daemon.executor import load_workspace_files

workspace_dir = Path("~/.teotl/agents/my-agent").expanduser()
content = load_workspace_files(workspace_dir)

if content:
    print(f"✅ Loaded {len(content)} characters from workspace files")
    print(content[:200])  # Preview first 200 chars
else:
    print("❌ No workspace files found")
```

### Issue: Config instructions being used instead

This happens when:
- Workspace directory doesn't exist
- No markdown files in workspace
- All markdown files are empty

**Solution:** Re-run `teotl onboard` to create workspace files.

## See Also

- [WORKSPACE_FILES.md](../../docs/WORKSPACE_FILES.md) - Complete documentation
- [Autonomous Agent Example](../autonomous_agent/) - Working daemon example
- [docs/SECURITY_GUIDE.md](../../docs/SECURITY_GUIDE.md) - Security policies
