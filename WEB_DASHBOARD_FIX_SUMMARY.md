# Web Dashboard Agent Discovery Fix

## Problem Identified

**This was a CODE BUG**, not a user initialization issue.

When running the web dashboard after creating agents via the onboarding wizard:
```bash
python3 -m forge.web
```

The dashboard showed:
```
❌ Error: No agents found!
```

Even though agents existed in `~/.teotl/agents/` with all workspace files.

### Root Cause

The onboarding wizard created agent workspace files but did NOT initialize the database files that the web dashboard requires to discover agents.

**Onboarding wizard created:**
- ✅ Workspace directory (`~/.teotl/agents/agent-name/`)
- ✅ Memory directories
- ✅ PERSONALITY.md
- ✅ INSTRUCTIONS.md
- ✅ USER.md
- ✅ SKILLS.md
- ✅ security.yaml
- ❌ **tasks.db** (missing)
- ❌ **missions.db** (missing)

**Web dashboard requires:**
```python
# forge/web/__main__.py line 32
if agent_dir.is_dir() and (agent_dir / "tasks.db").exists():
    agents[agent_dir.name] = agent_dir
```

Without `tasks.db`, the agent is **not discoverable** by the web dashboard.

## Fix Applied

Modified `forge/cli/wizard.py` to initialize database files during agent creation:

### Changes:

1. **Added `_create_database_files()` method** (lines 1204-1220):
   ```python
   def _create_database_files(self, workspace_dir: Path) -> None:
       """Initialize task and mission database files.

       These are required for the web dashboard to discover agents.
       """
       from forge.primitives.tasks import TaskStore
       from forge.primitives.missions import MissionStore

       # Create tasks.db
       task_store = TaskStore(workspace_dir / "tasks.db")
       task_store.close()

       # Create missions.db
       mission_store = MissionStore(workspace_dir / "missions.db")
       mission_store.close()
   ```

2. **Integrated into workspace creation** (line 1007-1010):
   ```python
   # Initialize database files for web dashboard
   progress.update(main_task, description=f"[cyan]Initializing databases for '{agent_id}'...")
   self._create_database_files(workspace_dir)
   progress.advance(main_task)
   ```

3. **Updated progress tracking** (line 953):
   ```python
   total_tasks = len(workspaces) * 8  # Was 7, now 8 steps per workspace
   ```

## Impact

**Before Fix:**
- Agents created by wizard not discoverable by web dashboard
- Users had to manually run daemon mode or manually create database files
- Poor user experience - wizard seemed to work but dashboard didn't

**After Fix:**
- ✅ Agents created by wizard immediately discoverable by web dashboard
- ✅ Database files automatically initialized during onboarding
- ✅ Smooth end-to-end experience from wizard → dashboard

## Testing After Fix

### Step 1: Create Agent with Wizard
```bash
teotl onboard
```

Follow the wizard prompts to create an agent (e.g., "my-agent").

### Step 2: Start Web Dashboard
```bash
python3 -m forge.web
```

**Expected Output:**
```
🔍 Auto-discovering agents...
✅ Found 1 agent(s): my-agent

🚀 Starting Forge Dashboard
📊 Monitoring 1 agent(s): my-agent
🌐 Dashboard: http://localhost:8080
```

### Step 3: Verify in Browser
Open http://localhost:8080 and you should see:
- Agent listed in dashboard
- Task count: 0 pending, 0 completed, 0 failed (fresh agent)
- Mission count: 0 total

## Workaround for Existing Agents

If you have agents created before this fix, you can initialize their databases manually:

```bash
cd /path/to/teotl
python3 << 'EOF'
import asyncio
from pathlib import Path
from forge.primitives.tasks import TaskStore
from forge.primitives.missions import MissionStore

async def init_agent_databases():
    agents_dir = Path.home() / ".forge" / "agents"
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir():
            print(f"Initializing databases for {agent_dir.name}...")
            task_store = TaskStore(agent_dir / "tasks.db")
            task_store.close()
            mission_store = MissionStore(agent_dir / "missions.db")
            mission_store.close()
            print(f"  ✅ Done")

asyncio.run(init_agent_databases())
EOF
```

Or simply re-run the onboarding wizard (it will update existing agents).

## Why This Is a Code Issue

1. **Broken workflow**: Wizard creates agents that dashboard can't find
2. **Poor error messaging**: Dashboard doesn't explain *why* agents aren't found
3. **Inconsistent initialization**: Some workflows create databases (daemon mode), others don't (wizard)
4. **Missing documentation**: No mention that databases need to exist for discovery

The fix ensures **consistent agent initialization** across all creation methods.

## Related Fixes

1. **Skills Parsing Fix** (commit 383f047)
   - Fixed comma-separated skills CLI argument

2. **Tool Use API Format Fix** (commit 83149d8)
   - Fixed Anthropic API message format for tool results

3. **Web Dashboard Discovery Fix** (commit 86070eb) ← **This fix**
   - Initialize database files during agent creation

## Files Changed

- `forge/cli/wizard.py`:
  - Added `_create_database_files()` method
  - Integrated database initialization into workspace creation
  - Updated progress tracking count

## Commit Details

```
commit 86070eb
Author: keithdit4e <keith.foster@dit4e.com>
Date: Sun Mar 29 11:30:00 2026 -0400

fix: initialize database files during agent onboarding
```
