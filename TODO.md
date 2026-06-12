# TODO Items

This document tracks future enhancements and known incomplete features.

## Critical (Must Fix Before Production Use)

None currently. All critical functionality is complete and tested.

## High Priority (Should Fix Soon)

### 1. MCP Bridge Implementation
**Location:** `teotl/primitives/integrations/mcp_bridge.py`

**Current State:** Placeholder implementation with TODO comments

**Issue:**
```python
# TODO: Implement actual MCP client connection
```

**Impact:** MCP (Model Context Protocol) integration is incomplete. Currently returns empty results.

**Action Needed:** Implement full MCP client using official MCP SDK when available

**Workaround:** For now, users can use custom skills to integrate with external tools. MCP is optional.

**Priority:** Medium (nice-to-have, not required for core functionality)

---

## Medium Priority (Future Enhancements)

### 2. Full Sandbox Implementation
**Location:** `teotl/core/tools/bash.py:301`

**Current State:** Policy-only enforcement (no filesystem sandboxing)

**Issue:**
```python
# TODO: Create SandboxManager from policy.sandbox config
# For now, sandbox is None (policy-only enforcement)
```

**Impact:** Bash commands are filtered by policy but don't run in isolated sandbox

**Current Behavior:**
- ✅ Dangerous commands blocked by guardrails
- ✅ Policy enforcement working
- ❌ No chroot/container isolation

**Action Needed:** Implement SandboxManager to create isolated execution environments

**Priority:** Medium (guardrails provide good protection, full sandboxing is additional layer)

---

### 3. Agent Daemon Management
**Location:** `teotl/cli/orchestrator.py`

**Current State:** Orchestrator doesn't fully manage daemon lifecycle

**Issues:**
```python
# TODO: Actually start the agents as daemons
# TODO: Send stop signal to agent process
```

**Impact:** Agent orchestration incomplete

**Current Behavior:**
- Agents can run individually
- Orchestrator exists but doesn't manage multi-agent systems

**Action Needed:** Implement proper daemon lifecycle management (start, stop, restart, status)

**Priority:** Medium (single-agent use cases work fine)

---

### 4. Agent Capabilities Registration
**Location:** `teotl/daemon/agent_daemon.py`

**Issues:**
```python
# TODO: Get capabilities and endpoint from agent config
capabilities=[],  # TODO: Get from agent
endpoint="http://localhost:8000/a2a",  # TODO: Get from config
```

**Impact:** Agent-to-agent communication incomplete

**Current Behavior:**
- Single agents work perfectly
- Multi-agent coordination not fully implemented

**Action Needed:**
- Parse capabilities from agent config
- Dynamic endpoint configuration
- Full A2A protocol support

**Priority:** Low (single-agent use is primary use case)

---

### 5. Checkpoint Git History Rewriting
**Location:** `teotl/primitives/harness/checkpoint.py`

**Issue:**
```python
# TODO: Implement git history rewriting if needed
```

**Impact:** Checkpoints save state but don't clean up git history

**Current Behavior:**
- Checkpoints work correctly
- Git history may contain checkpoint commits

**Action Needed:** Optional git history cleanup after checkpoint restore

**Priority:** Low (current checkpointing works fine)

---

## Low Priority (Nice to Have)

### 6. Wizard Integration Test Rewrite
**Documented in:** `TESTING.md`

**Issue:** 2 wizard tests skipped due to flow changes

**Action Needed:** Rewrite tests to match current 22-question wizard flow

**Priority:** Low (wizard works, just tests out of sync)

---

### 7. Memory Cleanup Warning
**Documented in:** `TESTING.md`

**Issue:** RuntimeWarning for async cleanup in sync context

**Action Needed:** Refactor LocalMemory initialization or suppress warning

**Priority:** Low (cosmetic, no functional impact)

---

## Not Planned (Out of Scope)

None currently.

---

## Contributing

Want to tackle one of these TODOs? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

For each TODO:
1. Create an issue on GitHub
2. Reference this document
3. Discuss approach before implementing
4. Write tests for your changes
5. Submit PR with updates to this file

---

## Review Schedule

This document should be reviewed:
- After each major release
- When new TODOs are added to code
- Quarterly (reassess priorities)

**Last Updated:** 2025-05-13
**Next Review:** 2025-08-13
