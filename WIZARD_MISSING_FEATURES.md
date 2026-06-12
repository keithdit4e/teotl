# Wizard Missing Features Analysis

## Executive Summary

The onboarding wizard is **out of sync** with the features we've built into the base Agent class. While the wizard creates a good basic configuration, it doesn't expose several important new features to users during onboarding.

---

## What the Wizard Currently Configures ✅

1. **Provider Setup** - Anthropic/OpenAI/Ollama with model selection
2. **Agent Configuration** - Instructions, work types (Goals/Missions/Tasks)
3. **Security** - Policy presets, compliance (GDPR/SOC2/HIPAA), audit logging
4. **Daemon** - Poll interval, data directory
5. **Rate Limits** - API request limits, cost limits
6. **Tasks** - Initial task queue setup
7. **Missions** - Scheduled mission setup

---

## Critical Missing Features ❌

### 1. Memory System Configuration

**Status:** ❌ NOT CONFIGURED

**What's Missing:**
- No option to enable/disable memory during onboarding
- Wizard creates memory directories (lines 1041-1044) but never configures Agent to use them!
- No configuration for memory backend (LocalMemory vs cloud-based)
- No memory capacity settings

**Impact:**
- Users don't get memory features (agent forgets context across sessions)
- Memory directories are created but unused
- Janitor auto-enables when memory enabled, but memory is never enabled

**What Should Be Asked:**
```
Enable memory for your agent?
  • Remembers past conversations and decisions
  • Learns from experience
  • Maintains context across sessions
  • Enables automatic context management (janitor)

Storage:
  • Local (SQLite) - Free, private, on your machine
  • [Future] Cloud - Synced, accessible anywhere
```

### 2. Janitor / Context Management

**Status:** ❌ NOT CONFIGURED

**What's Missing:**
- No configuration for `enable_auto_compact` (defaults to auto-enable with memory)
- No configuration for `compact_every` (defaults to 15 turns)
- No configuration for `max_context_tokens` (auto-detected but not customizable)

**Impact:**
- Users get default compaction settings (may not be optimal for their use case)
- Can't tune context management for their model
- Can't disable janitor even if they want to

**What Should Be Asked:**
```
Context Management (optional - auto-configured)

Your agent will automatically manage context to prevent running out of tokens.

Advanced users can customize:
  • Compaction frequency: Every X turns (default: 15)
  • Context limit: Max tokens before compaction (default: auto-detected from model)
  • Decision logging: Enable decision log file (default: yes)

Use defaults? [Yes/No]
```

### 3. Harness Features

**Status:** ⚠️ PARTIALLY CONFIGURED

**What's Configured:**
- ✅ Audit logging (via security setup)

**What's Missing:**
- ❌ Cost tracking (`enable_cost_tracking`)
- ❌ Checkpoints (`enable_checkpoints`)
- ❌ Heartbeat monitoring (`enable_heartbeat`)
- ❌ State management (`enable_state`)

**Impact:**
- Users don't get production-ready safety features
- No automatic cost tracking
- No checkpoints for recovery
- No stuck detection
- No persistent state across restarts

**What Should Be Asked:**
```
Production Features (recommended for production use)

Enable production safety features?

Cost Tracking:
  • Real-time cost monitoring
  • Per-hour, per-day, per-month limits
  • Automatic shutdown on budget exceeded
  [✓] Enable cost tracking

Checkpoints:
  • Automatic progress snapshots
  • Recover from crashes
  • Resume long-running tasks
  [✓] Enable checkpoints

Heartbeat Monitoring:
  • Detect stuck agents
  • Alert on errors
  • Automatic recovery
  [✓] Enable heartbeat

State Management:
  • Persistent agent state
  • Remember phase and progress
  • Survive restarts
  [✓] Enable state management
```

### 4. Skills Configuration

**Status:** ⚠️ TEMPLATE ONLY

**What's Configured:**
- Creates SKILLS.md template
- No actual skill selection/configuration

**What's Missing:**
- No built-in skill selection (filesystem, web, email, etc.)
- No skill capability descriptions
- No skill-specific configuration

**Impact:**
- Users have to manually edit SKILLS.md
- Don't discover available skills
- Miss out on powerful capabilities

**What Should Be Asked:**
```
Which skills should your agent have? (select all that apply)

Built-in Skills:
  [✓] Filesystem - Read/write files, create directories
  [✓] Web - Fetch URLs, search, scrape
  [ ] Email - Read/send emails (requires SMTP config)
  [ ] GitHub - Create issues, PRs, manage repos
  [ ] Slack - Send messages, read channels
  [ ] Database - Query SQL databases
  [ ] Calendar - Schedule events, check availability

Custom Skills:
  [ ] Add custom skill directory
```

### 5. Extensions

**Status:** ❌ NOT MENTIONED

**What's Missing:**
- No mention of agent extensions
- No configuration for custom extensions
- No discovery of available extensions

**Impact:**
- Users don't know extensions exist
- Can't configure custom behavior
- Miss advanced features

### 6. Workspace Configuration

**Status:** ⚠️ PARTIALLY CONFIGURED

**What's Configured:**
- Creates workspace files (PERSONALITY.md, USER.md, INSTRUCTIONS.md, SKILLS.md)
- Creates GOALS.md if Goals work type selected

**What's Missing:**
- No workspace directory selection (for tools/context)
- No workspace permissions configuration
- No workspace file customization prompts

**Impact:**
- Agent doesn't know where user's code/files are
- Can't provide workspace-aware assistance
- Limited context about user's actual work

**What Should Be Asked:**
```
Workspace Setup

Where is your primary workspace? (your code/projects directory)
  Default: ~/workspace

This helps your agent:
  • Understand your project structure
  • Access relevant files
  • Provide context-aware assistance
```

---

## Configuration Gaps in Detail

### Memory Configuration Missing

**In wizard:** Creates memory dirs but never enables memory

**In Agent.__init__():**
```python
def __init__(
    self,
    memory: Any | None = None,  # ❌ Wizard never sets this
    ...
)
```

**What wizard creates:**
```python
# Lines 1041-1044
memory_dir = workspace_dir / "memory"
memory_dir.mkdir(exist_ok=True)
(memory_dir / "daily").mkdir(exist_ok=True)
(memory_dir / "sessions").mkdir(exist_ok=True)
```

**Gap:** Directories created, but `memory` parameter never configured!

### Janitor Configuration Missing

**In Agent.__init__():**
```python
def __init__(
    self,
    enable_auto_compact: bool | None = None,  # ❌ Wizard never sets this
    compact_every: int = 15,  # ❌ Wizard uses default
    max_context_tokens: int | None = None,  # ❌ Wizard uses auto-detect
    ...
)
```

**Gap:** All janitor parameters use defaults, no user control

### Harness Features Missing

**In Agent.__init__():**
```python
def __init__(
    self,
    cost_tracker: CostTracker | None = None,  # ❌ Not configured
    checkpoint_manager: CheckpointManager | None = None,  # ❌ Not configured
    heartbeat_monitor: HeartbeatMonitor | None = None,  # ❌ Not configured
    state_manager: StateManager | None = None,  # ❌ Not configured
    ...
)
```

**In daemon executor:**
```python
# Lines 295-296 in executor.py
if workspace_dir and any([enable_cost_tracking, enable_audit,
                          enable_checkpoints, enable_heartbeat, enable_state]):
    self._init_harness_components()
```

**Gap:** Wizard never sets these flags, so harness features never initialize

---

## Impact Analysis

### For Users

**Current Experience:**
1. Run wizard
2. Get basic config
3. **Don't know about memory/janitor/harness features**
4. **Miss out on major capabilities**
5. Have to manually edit config.yaml to enable advanced features

**Impact:**
- 🔴 **Poor feature discovery** - Users don't know what's available
- 🔴 **Suboptimal defaults** - Can't tune for their use case
- 🔴 **Manual configuration required** - Defeats purpose of wizard
- 🔴 **Inconsistent experience** - Some features exposed, others hidden

### For the Product

**Feature Adoption:**
- Memory system: **Low** (not exposed)
- Janitor/context management: **Low** (auto-enabled but not customizable)
- Cost tracking: **Zero** (not exposed)
- Checkpoints: **Zero** (not exposed)
- Heartbeat: **Zero** (not exposed)
- State management: **Zero** (not exposed)

**Result:** We built great features but users don't use them because they don't know they exist.

---

## Recommended Wizard Updates

### Phase 1: Essential (High Priority) 🔴

**1. Add Memory Configuration Step**
```python
def _setup_memory(self) -> None:
    """Configure memory system."""
    print_header("Memory & Context Management")

    print("\nMemory helps your agent:")
    print("  • Remember past conversations")
    print("  • Learn from experience")
    print("  • Maintain context across sessions")
    print("  • Enable automatic context management")

    if ask_yes_no("Enable memory?", default=True):
        # Memory backend
        backend = ask_choice(
            "Storage backend",
            ["local (SQLite - recommended)", "custom"],
            default="local (SQLite - recommended)"
        )

        self.config["agent"]["memory"] = {
            "enabled": True,
            "backend": backend.split()[0],
            "path": "memory.db"
        }

        # Janitor auto-enables with memory, ask about customization
        if ask_yes_no("\nCustomize context management?", default=False):
            self._setup_janitor()
        else:
            print_info("Using automatic context management (default: compact every 15 turns)")
```

**2. Add Harness Features Step**
```python
def _setup_harness_features(self) -> None:
    """Configure production safety features."""
    print_header("Production Safety Features")

    print("\nProduction features provide:")
    print("  • Cost tracking and budget limits")
    print("  • Automatic checkpoints for recovery")
    print("  • Stuck detection and alerting")
    print("  • Persistent state across restarts")

    if ask_yes_no("Enable production features?", default=True):
        features = ask_multiselect(
            "Which features to enable?",
            [
                ("Cost Tracking", "Real-time cost monitoring with budget limits"),
                ("Checkpoints", "Automatic progress snapshots"),
                ("Heartbeat Monitoring", "Detect stuck agents"),
                ("State Management", "Persistent agent state"),
            ],
            defaults=["Cost Tracking", "State Management"]
        )

        self.config["agent"]["harness"] = {
            "cost_tracking": "Cost Tracking" in features,
            "checkpoints": "Checkpoints" in features,
            "heartbeat": "Heartbeat Monitoring" in features,
            "state": "State Management" in features,
        }
```

### Phase 2: Enhanced (Medium Priority) 🟡

**3. Add Skills Selection Step**
```python
def _setup_skills(self) -> None:
    """Configure agent skills."""
    print_header("Skills Configuration")

    skills = ask_multiselect(
        "Which skills should your agent have?",
        [
            ("Filesystem", "Read/write files, create directories"),
            ("Web", "Fetch URLs, search, scrape"),
            ("Email", "Read/send emails"),
            ("GitHub", "Create issues, PRs, manage repos"),
            ("Slack", "Send messages, read channels"),
        ],
        defaults=["Filesystem", "Web"]
    )

    self.config["agent"]["skills"] = [s.lower() for s in skills]
```

**4. Add Workspace Directory Configuration**
```python
def _setup_workspace(self) -> None:
    """Configure workspace directory."""
    print_header("Workspace Configuration")

    print("\nYour workspace is where your agent can access files.")
    print("This helps your agent understand your projects and provide context-aware help.")

    workspace = ask_question(
        "\nWorkspace directory",
        default=str(Path.home() / "workspace")
    )

    self.config["agent"]["workspace_dir"] = workspace
```

### Phase 3: Advanced (Low Priority) 🟢

**5. Add Advanced Janitor Configuration** (optional, for power users)

**6. Add Extension Configuration** (when we have extensions to configure)

**7. Add Skill-Specific Configuration** (email SMTP, GitHub tokens, etc.)

---

## Updated Wizard Flow

**Proposed new flow:**

```
1. Welcome
2. Provider Setup (existing)
3. Agent Configuration (existing)
   ├─ Instructions
   ├─ Work types
   └─ **NEW: Memory & Context Management**
4. **NEW: Skills Selection**
5. **NEW: Workspace Configuration**
6. Security & Compliance (existing)
7. Daemon Configuration (existing)
8. **NEW: Production Features (Harness)**
9. Rate Limits (existing)
10. Tasks (existing)
11. Missions (existing)
12. Review & Save
13. Auto-start daemon
```

**Total added steps:** 3 (Memory, Skills, Workspace, Harness)
**Time impact:** +2-3 minutes

---

## Implementation Priority

### Immediate (Phase 1)

1. **Memory Configuration** - Critical, users need this
2. **Harness Features** - Important for production readiness

### Soon (Phase 2)

3. **Skills Selection** - Improves discovery and UX
4. **Workspace Configuration** - Needed for context-aware assistance

### Later (Phase 3)

5. **Advanced Configuration** - Power user features
6. **Extension Configuration** - When we have more extensions

---

## Backward Compatibility

**Config file changes:**
- All new fields are optional
- Existing configs still work
- Defaults match current behavior
- No breaking changes

**Migration path:**
- Old configs: Work as-is (no memory, default janitor, no harness)
- New configs: Get full feature set
- Users can re-run wizard to upgrade

---

## Summary

**Current State:**
- Wizard configures ~50% of available features
- Memory, janitor, harness features hidden
- Users miss out on major capabilities

**Recommended:**
- Add 3-4 new configuration steps
- Expose memory, skills, workspace, harness
- Maintain simplicity with good defaults
- Keep "skip" option for power users who want to manually configure

**Impact:**
- Better feature discovery
- Higher adoption of advanced features
- More complete onboarding experience
- Still simple for basic use cases (skip advanced sections)

**Next Steps:**
1. Implement Phase 1 (Memory + Harness)
2. Test with real users
3. Iterate based on feedback
4. Add Phase 2 features
