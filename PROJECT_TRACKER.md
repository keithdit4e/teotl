# Forge MVP Project Tracker

**Start Date:** March 18, 2026
**Target Completion:** May 13, 2026 (8 weeks)
**Status:** 🚀 In Progress

---

## Sprint Overview

| Sprint | Dates | Focus | Status |
|--------|-------|-------|--------|
| Sprint 1 | Mar 18-24 | Security Foundation | ✅ Complete |
| Sprint 2 | Mar 19 | Guardrails | ✅ Complete |
| Sprint 3 | Mar 19 | Skills System | 🟡 71% Complete |
| Sprint 4 | Mar 19-20 | Memory Integration | ✅ Complete |
| Sprint 5 | Mar 20 - Apr 3 | Autonomy Foundation | 🔵 In Progress |
| Sprint 6 | Apr 15-21 | Integrations | ⚪ Planned |
| Sprint 6 | Apr 15-21 | Integrations | ⚪ Planned |
| Sprint 7 | Apr 22-28 | Extensions | ⚪ Planned |
| Sprint 8 | Apr 29-May 5 | CLI & Dev UX | ⚪ Planned |
| Sprint 9 | May 6-13 | Reference Impl | ⚪ Planned |

---

## Current Sprint: Sprint 1 - Security Foundation

**Goal:** Fix all critical security issues and solidify core framework

**Dates:** March 18-24, 2026

### Tasks

#### Critical Security (P0 - MUST COMPLETE)

- [x] **C-1: Encrypted Credential Storage** `security` `critical` ✅ **COMPLETED** (Mar 18, 2026)
  - Location: `forge/primitives/integrations/`
  - Files created:
    - [x] `credential_store.py` - Pluggable backend abstraction (600+ LOC)
    - [x] `tests/test_credential_store.py` - Comprehensive tests (28 tests)
    - [x] `tests/test_registry.py` - Integration tests (15 tests)
  - Files updated:
    - [x] `registry.py` - Now uses CredentialStore
  - Implementation:
    - ✅ LocalKeyringBackend (OS keyring)
    - ✅ FileBackend (encrypted files with Fernet)
    - ✅ EnvironmentBackend (env vars for CI/CD)
    - ✅ AWSSecretsBackend (cloud deployments)
    - ✅ Auto-detection logic (environment > cloud > keyring > file)
    - ✅ All credentials encrypted at rest
    - ✅ File permissions restricted to 600
  - Tests: All 108 tests passing
  - Commit: a9c2635
  - Owner: Keith
  - Completed: Mar 18

- [x] **C-2: Memory Encryption** `security` `critical` ✅ **COMPLETED** (Mar 18, 2026)
  - Location: `forge/primitives/memory/`
  - Files created:
    - [x] `encrypted.py` - Hybrid encryption implementation (400+ LOC)
    - [x] `tests/test_encrypted_memory.py` - Comprehensive tests (17 tests)
  - Implementation:
    - ✅ Content encrypted at rest (Fernet)
    - ✅ Sanitized content for FTS search (PII removed)
    - ✅ Metadata remains searchable
    - ✅ PII patterns: emails, API keys, tokens, credit cards, phones, SSNs
    - ✅ Encryption key from credential store
    - ✅ Migration tool for existing memories
    - ✅ Backward compatible with LocalMemory
  - Tests: All 125 tests passing
  - Commit: c1433dc
  - Owner: Keith
  - Completed: Mar 18

- [x] **C-3: Rate Limiting** `security` `critical` ✅ **COMPLETED** (Mar 18, 2026)
  - Location: `forge/primitives/guardrails/`
  - Files created:
    - [x] `rate_limiter.py` - Rate limiter implementation (350+ LOC)
    - [x] `tests/test_rate_limiter.py` - Comprehensive tests (22 tests)
    - [x] `rate_limited_provider.py` - Provider wrapper (150+ LOC)
    - [x] `tests/test_rate_limited_provider.py` - Provider tests (14 tests)
  - Implementation:
    - ✅ Token bucket-based rate limiting
    - ✅ Multiple time windows (RPM, hourly, daily)
    - ✅ Cost tracking for Anthropic and OpenAI models
    - ✅ Token limits per request (200K default)
    - ✅ Multi-user isolation (MultiUserRateLimiter)
    - ✅ Wrapper pattern for easy integration
    - ✅ Failed requests count toward limits
    - ✅ Automatic cleanup of old entries
  - Tests: All 162 tests passing (36 new tests)
  - Coverage: 59% (up from 47%)
  - Commit: cd9daa6
  - Owner: Keith
  - Completed: Mar 18

#### High-Priority Security (P1 - SHOULD COMPLETE)

- [x] **H-2: Session File Permissions** `security` `high` ✅ **COMPLETED** (Mar 18, 2026)
  - Location: `forge/core/session.py`
  - Implementation:
    - ✅ Set file permissions to 0o600 (owner read/write only)
    - ✅ Prevents other users from reading session data
    - ✅ Applied on first write to new files
  - Tests: 11 session tests passing (1 new test)
  - Commit: 6be6f82
  - Owner: Keith
  - Completed: Mar 18

- [x] **H-4: Prompt Injection Defenses** `security` `high` ✅ **COMPLETED** (Mar 18, 2026)
  - Location: `forge/primitives/guardrails/prompt_injection.py`, `forge/core/agent.py`
  - Files created:
    - [x] `prompt_injection.py` - Detection and defense module (200+ LOC)
    - [x] `tests/test_prompt_injection.py` - Comprehensive tests (26 tests)
  - Implementation:
    - ✅ Pattern-based attack detection (system prompt extraction, role confusion, override, etc.)
    - ✅ Input sanitization (role markers, code blocks)
    - ✅ Delimiter wrapping (XML/Markdown/text styles)
    - ✅ Instruction hierarchy (explicit security notice)
    - ✅ Instruction validation (pre-flight checks)
    - ✅ Integrated into Agent class (`enable_injection_defense` parameter)
    - ✅ Event emission for detected injections
  - Tests: All 189 tests passing (26 new tests)
  - Coverage: 60% (up from 59%)
  - Commit: 414a165
  - Owner: Keith
  - Completed: Mar 18

#### Framework Essentials (P1)

- [ ] **Test Suite Validation** `testing`
  - Run full test suite
  - Verify 80%+ coverage maintained
  - Fix any broken tests from security changes
  - Estimate: 2 hours
  - Owner: Keith
  - Due: Mar 24

- [ ] **Documentation** `docs`
  - [ ] Architecture overview
  - [ ] Security model documentation
  - [ ] Getting started guide
  - Estimate: 4 hours
  - Owner: Keith
  - Due: Mar 24

### Sprint 1 Success Criteria

- ✅ All C-* issues resolved (C-1, C-2, C-3 complete)
- ✅ All H-* high-priority security issues resolved (H-2, H-4 complete)
- ⚠️ Tests passing at 80%+ coverage (60% current - in progress)
- ⚪ Security audit checklist updated (can defer to Sprint 2)
- ✅ Can run basic agent with secure credentials

**Sprint 1 Status: 🟢 CORE SECURITY COMPLETE**
- All critical (P0) and high-priority (P1) security issues resolved
- Remaining: Test coverage improvement (ongoing) and documentation

---

## Sprint 2: Guardrails System ✅ COMPLETE

**Goal:** Complete guardrails integration with comprehensive testing and documentation

**Dates:** March 19, 2026 (completed same day)

### Tasks

- [x] **Wire guardrails fully into agent loop** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `tests/integration/test_guardrails_integration.py`
  - Implementation:
    - ✅ Integration tests proving guardrails work in agent loop
    - ✅ Safe actions allowed without confirmation
    - ✅ Destructive actions blocked
    - ✅ Medium-risk actions require confirmation
    - ✅ User approval/denial flows working
    - ✅ Trust building system functional
  - Tests: 7 integration tests passing
  - Commit: 18ac834

- [x] **Test all risk levels and blocking flows** ✅ **COMPLETED** (Mar 19, 2026)
  - All risk levels validated: SAFE, MEDIUM, HIGH, CRITICAL
  - Blocking flows tested (destructive commands)
  - Approval flows tested (write operations)
  - Trust building tested (auto-approve after N confirmations)

- [x] **Create policy loading utilities** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/primitives/guardrails/policy.py`
  - Implementation:
    - ✅ Added YAML support to Policy.from_file()
    - ✅ Supports both JSON and YAML formats
    - ✅ Auto-detection based on file extension
  - Commit: 18ac834

- [x] **Write custom policy examples** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `examples/policies/`
  - Files created:
    - ✅ `development.json` - Permissive policy for dev environments
    - ✅ `production.json` - Strict policy for production deployments
    - ✅ `ci-cd.json` - Non-interactive policy for CI/CD pipelines
    - ✅ `custom-example.yaml` - Fully documented template with all options
  - Commit: 18ac834

- [x] **Create policy testing utilities** ✅ **COMPLETED** (Mar 19, 2026)
  - Integration test suite validates policy enforcement
  - All policy examples validated

- [x] **Documentation for policy creation** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `docs/GUARDRAILS.md`
  - Coverage:
    - ✅ Overview and architecture (500+ lines total)
    - ✅ How it works (step-by-step flow)
    - ✅ Quick start guide
    - ✅ Complete policy configuration reference
    - ✅ Built-in policies documentation
    - ✅ Custom policy creation guide with examples
    - ✅ Risk levels explained
    - ✅ Trust building system details
    - ✅ Security guarantees and limitations
    - ✅ Best practices (7 recommendations)
    - ✅ Complete API reference
    - ✅ Troubleshooting guide
    - ✅ Usage examples
  - Commit: bd14c93

### Sprint 2 Success Criteria

- ✅ Guardrails fully integrated and tested in agent loop
- ✅ All risk levels validated
- ✅ Policy loading from JSON and YAML working
- ✅ 4 example policies created (development, production, ci-cd, custom)
- ✅ Comprehensive documentation complete

**Sprint 2 Status: ✅ 100% COMPLETE**

---

## Sprint 3: Skills System 🔵 IN PROGRESS

**Goal:** Complete skills system with auto-activation and production-ready built-in skills

**Dates:** March 19, 2026 (in progress)

### Tasks

- [x] **Wire skills into agent loop** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ Auto-activation when LLM mentions skill name or trigger keywords
    - ✅ Skill instructions automatically injected into system prompt
    - ✅ Progressive disclosure model (descriptions always in context, full instructions on-demand)
    - ✅ Detection after each LLM response
    - ✅ Loads full instructions for next turn (500-2000 tokens)
  - Tests: 11 integration tests passing
  - Commit: 2d12ba2

- [x] **Implement skill activation/deactivation** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ Manual activation: `agent.activate_skill(name)`
    - ✅ Manual deactivation: `agent.deactivate_skill(name)`
    - ✅ List skills: `agent.list_skills()`
    - ✅ List active: `agent.list_active_skills()`
    - ✅ Auto-activation in agent loop
    - ✅ Idempotent activation (no duplicates)
  - Commit: 2d12ba2

- [x] **Build filesystem skill (complete)** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `skills/filesystem/SKILL.md`
  - Version: 2.0.0 (397 lines)
  - Implementation:
    - ✅ Core operations (read, write, search, find)
    - ✅ Directory management
    - ✅ File management (copy, move, delete)
    - ✅ Advanced operations (archives, comparison, text processing)
    - ✅ Security considerations (protected directories, safe practices)
    - ✅ Error handling patterns
    - ✅ Common workflows (safe edit, search with context, cleanup)
    - ✅ Performance tips
    - ✅ Quick reference table
  - Commit: f3eb5a6

- [x] **Build web skill (complete)** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `skills/web/SKILL.md`
  - Version: 2.0.0 (489 lines)
  - Implementation:
    - ✅ Core operations (fetch, download, status check)
    - ✅ Full REST API support (GET, POST, PUT, PATCH, DELETE)
    - ✅ Authentication patterns (Bearer, Basic, API Key)
    - ✅ Advanced features (cookies, timeouts, retries, headers)
    - ✅ Common workflows (API testing, pagination, web scraping)
    - ✅ Security considerations (SSRF protection, SSL verification)
    - ✅ Response format handling (JSON, XML, CSV, HTML)
    - ✅ GraphQL and webhook patterns
    - ✅ Quick reference table
  - Commit: f3eb5a6

- [x] **Build git skill (complete)** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `skills/git/SKILL.md`
  - Version: 2.0.0 (691 lines)
  - Implementation:
    - ✅ Essential operations (status, commit, branch, merge)
    - ✅ Advanced workflows (rebase, stash, cherry-pick, tags)
    - ✅ Remote operations with safety guidelines
    - ✅ Common workflows (feature branches, hotfix, fork updates)
    - ✅ Troubleshooting and recovery
    - ✅ Security best practices (protected operations, dangerous commands)
    - ✅ Repository maintenance and optimization
    - ✅ Git hooks and .gitignore patterns
    - ✅ Quick reference table
  - Commit: f3eb5a6

- [ ] **Create skill template generator** `cli` `tooling`
  - Planned: CLI tool to scaffold new skills
  - Command: `teotl new skill <name>`
  - Features:
    - Generate SKILL.md template
    - Interactive prompts for metadata
    - Example commands and patterns
  - Estimate: 3-4 hours
  - Owner: Keith

- [ ] **Write skill development guide** `docs`
  - Planned: Comprehensive documentation for skill developers
  - Topics:
    - Skill structure and frontmatter
    - Writing effective instructions
    - Security considerations
    - Testing skills
    - Best practices
  - Estimate: 2-3 hours
  - Owner: Keith

### Sprint 3 Success Criteria

- ✅ Skills auto-activate when mentioned in LLM responses
- ✅ Manual skill management API available
- ✅ All three built-in skills enhanced to production quality
- ✅ Integration tests validating skill system
- ⚪ Skill template generator CLI (deferred)
- ⚪ Skill development documentation (deferred)

**Sprint 3 Status: 🟡 71% COMPLETE (5/7 tasks)**
- Core skills system fully functional and tested
- Remaining: Tooling and documentation for skill developers

---

## Sprint 4: Memory Integration ✅ COMPLETE

**Goal:** Integrate memory system into agent loop with auto-extraction and context injection

**Dates:** March 19-20, 2026

### Tasks

- [x] **Wire memory.recall() into agent loop for context injection** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ Async memory recall before building system prompt
    - ✅ Relevant memories injected into system prompt based on user query
    - ✅ Full-text search with BM25 ranking via SQLite FTS5
    - ✅ Memory context section added to system prompt
    - ✅ Graceful fallback when memory system disabled
  - Tests: 12 integration tests passing
  - Commit: f4ab76b

- [x] **Implement auto-extraction of memories from conversations** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ Pattern-based extraction for explicit memory statements
    - ✅ Lightweight regex matching at turn end
    - ✅ Patterns: "Remember that...", "My name is...", "I prefer...", "Note that...", "Keep in mind..."
    - ✅ Auto-storage with importance=8 for explicit memories
    - ✅ Length validation and content sanitization
  - Tests: All extraction patterns validated
  - Commit: f4ab76b

- [x] **Build context injection with token budget awareness** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ Token budget control (500 tokens default)
    - ✅ Uses existing MemoryContext.format_for_context()
    - ✅ Prevents prompt bloat from excessive memories
    - ✅ Budget-aware truncation of memory list
  - Tests: Token budget validated in integration tests
  - Commit: f4ab76b

- [x] **Create manual memory management API** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/core/agent.py`
  - Implementation:
    - ✅ `agent.remember()` - Store memories manually
    - ✅ `agent.recall()` - Retrieve memories by query
    - ✅ `agent.forget()` - Delete specific memory by ID
    - ✅ `agent.list_memories()` - List all memories with pagination
    - ✅ Proper error handling (ValueError when memory not initialized)
  - Tests: All manual API methods tested
  - Commit: f4ab76b

- [x] **Create comprehensive integration tests** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `tests/integration/test_memory_integration.py`
  - Implementation:
    - ✅ 12 comprehensive integration tests (367 lines)
    - ✅ Tests memory recall in context
    - ✅ Tests explicit memory extraction
    - ✅ Tests multiple memory patterns
    - ✅ Tests manual memory API (remember, recall, forget, list)
    - ✅ Tests token budget compliance
    - ✅ Tests memory persistence across runs
    - ✅ Tests edge cases (no matches, uninitialized memory)
  - Tests: All 12 tests passing
  - Commit: f4ab76b

- [x] **Implement data retention policies (TTL, cleanup)** ✅ **COMPLETED** (Mar 19, 2026)
  - Location: `forge/primitives/memory/local.py`
  - Implementation:
    - ✅ Added TTL (time-to-live) for memories with expires_at field
    - ✅ Automatic cleanup of expired memories (cleanup_expired)
    - ✅ Importance-based retention (critical=never, important=1yr, medium=90d, low=7d)
    - ✅ Storage limit enforcement (cleanup_by_storage_limit)
    - ✅ Auto-cleanup on initialization
    - ✅ Retention statistics (get_retention_stats)
  - Tests: 11 comprehensive retention tests
  - Commit: e1f3c8a

- [x] **Create memory management CLI commands** ✅ **COMPLETED** (Mar 20, 2026)
  - Location: `forge/cli/memory.py`
  - Implementation:
    - ✅ `teotl memory list` - List all memories with pagination
    - ✅ `teotl memory search <query>` - Search memories
    - ✅ `teotl memory delete <id>` - Delete specific memory
    - ✅ `teotl memory cleanup` - Remove expired memories (with --dry-run)
    - ✅ `teotl memory stats` - Show retention statistics
    - ✅ `teotl memory export` - Export memories to JSON
    - ✅ `teotl memory import` - Import memories from JSON
    - ✅ Rich formatting (tables, panels) for output
  - Tests: All CLI commands tested manually
  - Commit: 5aa160f

- [x] **Write memory system documentation** ✅ **COMPLETED** (Mar 20, 2026)
  - Location: `docs/MEMORY.md`
  - Coverage:
    - ✅ Architecture overview (800+ lines total)
    - ✅ How memory recall works (FTS5, BM25 ranking)
    - ✅ Retention policies and TTL rules
    - ✅ Auto-extraction patterns
    - ✅ Manual memory API guide
    - ✅ CLI command reference with examples
    - ✅ Token budget configuration
    - ✅ PII detection and encryption
    - ✅ Security and privacy guidelines
    - ✅ Best practices
    - ✅ Troubleshooting guide
  - Commit: 5aa160f

### Sprint 4 Success Criteria

- ✅ Memory recall integrated into agent loop
- ✅ Auto-extraction working for explicit memory patterns
- ✅ Context injection with token budget control
- ✅ Manual memory API available (remember, recall, forget, list)
- ✅ Comprehensive integration tests (12 tests passing)
- ✅ Data retention policies (TTL, cleanup)
- ✅ Memory management CLI (8 commands)
- ✅ Memory documentation (comprehensive guide)

**Sprint 4 Status: ✅ 100% COMPLETE (8/8 tasks)**
- Complete memory system with retention, CLI, and documentation
- Note: Enhanced PII detection deferred to post-MVP security hardening

---

## Sprint 5: Autonomy Foundation 🔵 IN PROGRESS

**Goal:** Implement simplified autonomy system with persistent goals, heartbeat daemon, and basic permissions

**Dates:** March 20 - April 3, 2026 (2 weeks)

**Roadmap:** See [docs/AUTONOMY_ROADMAP.md](docs/AUTONOMY_ROADMAP.md) for complete autonomy plan

### Week 1: Goals & Daemon (Mar 20-26)

- [ ] **Design persistent goal storage schema** `autonomy` `planning`
  - Location: `forge/primitives/goals/`
  - Scope:
    - [ ] SQLite schema for goal storage
    - [ ] Goal states: ACTIVE, PAUSED, COMPLETED, FAILED, CANCELLED
    - [ ] Interval scheduling (hourly, daily, weekly)
    - [ ] Goal metadata (budget, permissions, history)
  - Estimate: 0.5 days
  - Owner: Keith

- [ ] **Implement Goal class and storage** `autonomy` `core`
  - Location: `forge/primitives/goals/persistent.py`
  - Scope:
    - [ ] Goal model with Pydantic
    - [ ] CRUD operations (create, read, update, delete)
    - [ ] Goal lifecycle management
    - [ ] SQLite persistence layer
    - [ ] Migration from in-memory to persistent
  - Estimate: 1.5 days
  - Owner: Keith

- [ ] **Build simple heartbeat daemon** `autonomy` `daemon`
  - Location: `forge/daemon/heartbeat.py`
  - Scope:
    - [ ] Daemon process management (start, stop, status)
    - [ ] Interval-based execution (cron-like scheduling)
    - [ ] Goal loading and execution
    - [ ] PID file management
    - [ ] Signal handling (SIGTERM, SIGINT)
    - [ ] Daemon logging
  - Estimate: 2 days
  - Owner: Keith

- [ ] **Integrate daemon with agent loop** `autonomy` `integration`
  - Location: `forge/core/agent.py`
  - Scope:
    - [ ] Daemon execution context
    - [ ] Goal execution wrapper
    - [ ] Error handling and recovery
    - [ ] Execution history tracking
  - Estimate: 1 day
  - Owner: Keith

### Week 2: Permissions & Budget (Mar 27 - Apr 2)

- [ ] **Design permission grant system** `autonomy` `security`
  - Location: `forge/primitives/permissions/`
  - Scope:
    - [ ] Grant levels: ONCE, SESSION, GOAL, ALWAYS, NEVER
    - [ ] Permission storage (SQLite)
    - [ ] Pattern matching (action types, file patterns)
    - [ ] Grant revocation
  - Estimate: 0.5 days
  - Owner: Keith

- [ ] **Implement PermissionGrant class** `autonomy` `security`
  - Location: `forge/primitives/permissions/grant.py`
  - Scope:
    - [ ] Grant model with Pydantic
    - [ ] CRUD operations
    - [ ] Pattern matching logic
    - [ ] Grant expiration (session, goal scopes)
    - [ ] SQLite persistence
  - Estimate: 1.5 days
  - Owner: Keith

- [ ] **Integrate permissions with guardrails** `autonomy` `integration`
  - Location: `forge/primitives/guardrails/engine.py`
  - Scope:
    - [ ] Check grants before policy evaluation
    - [ ] Auto-approve if ALWAYS grant exists
    - [ ] Auto-deny if NEVER grant exists
    - [ ] Store new grants from user approvals
    - [ ] Grant scope management
  - Estimate: 1 day
  - Owner: Keith

- [ ] **Implement simple budget enforcement** `autonomy` `security`
  - Location: `forge/primitives/goals/budget.py`
  - Scope:
    - [ ] Budget model (API calls, cost limits)
    - [ ] Budget tracking per goal
    - [ ] Execution halt on budget exceeded
    - [ ] Budget reporting
  - Estimate: 1 day
  - Owner: Keith

- [ ] **Add emergency controls** `autonomy` `security`
  - Location: `forge/daemon/heartbeat.py`, `forge/cli/daemon.py`
  - Scope:
    - [ ] Pause daemon (stop executing goals)
    - [ ] Resume daemon
    - [ ] Stop daemon (graceful shutdown)
    - [ ] Emergency stop (kill all execution)
    - [ ] CLI commands for all controls
  - Estimate: 1 day
  - Owner: Keith

### Testing & Documentation (Apr 3)

- [ ] **Create autonomy integration tests** `testing`
  - Location: `tests/integration/test_autonomy.py`
  - Scope:
    - [ ] Goal creation and execution
    - [ ] Daemon lifecycle tests
    - [ ] Permission grant tests
    - [ ] Budget enforcement tests
    - [ ] Emergency controls tests
  - Estimate: 1 day
  - Owner: Keith

- [ ] **Write autonomy user guide** `docs`
  - Location: `docs/AUTONOMY.md`
  - Scope:
    - [ ] Quick start guide
    - [ ] Goal creation and management
    - [ ] Daemon usage
    - [ ] Permission system
    - [ ] Budget configuration
    - [ ] Emergency controls
    - [ ] Security considerations
    - [ ] Troubleshooting
  - Estimate: 0.5 days
  - Owner: Keith

### Sprint 5 Success Criteria

- ⚪ Persistent goal storage working (SQLite)
- ⚪ Heartbeat daemon can execute goals on schedule
- ⚪ Permission grant system integrated with guardrails
- ⚪ Budget enforcement prevents runaway execution
- ⚪ Emergency controls (pause, stop) working
- ⚪ Comprehensive integration tests
- ⚪ User documentation complete

**Sprint 5 Status: 🔵 0% COMPLETE (0/13 tasks)**
- Starting implementation of autonomy foundation

---

## Sprint 6: Integration System

**Dates:** April 15-21, 2026

### Planned Tasks

- [ ] Build OAuth2 flow helpers
- [ ] Implement token refresh logic
- [ ] Create Gmail integration (complete)
  - [ ] OAuth2 authentication
  - [ ] List/read/search emails
  - [ ] Send email
- [ ] Create GitHub integration (basic)
- [ ] Write integration development guide

---

## Sprint 7: Extension System

**Dates:** April 22-28, 2026

### Planned Tasks

- [ ] Implement extension permissions model
- [ ] Add extension audit logging
- [ ] Create sandboxed agent interface
- [ ] Build extension generator CLI
- [ ] Create extension testing framework
- [ ] Write extension development guide

---

## Sprint 8: CLI & Developer UX

**Dates:** April 29-May 5, 2026

### Planned Tasks

- [ ] Implement `teotl init`
- [ ] Implement `teotl new agent`
- [ ] Implement `teotl new skill`
- [ ] Implement `teotl new extension`
- [ ] Implement `teotl auth <service>`
- [ ] Implement `teotl run`
- [ ] Build interactive REPL
- [ ] Add streaming responses
- [ ] Create developer documentation

---

## Sprint 9: Reference Implementation

**Dates:** May 6-13, 2026

### Planned Tasks

- [ ] Build personal assistant agent
- [ ] Integrate filesystem operations
- [ ] Integrate email management
- [ ] Add task tracking extension
- [ ] Wire up memory/context
- [ ] End-to-end testing
- [ ] User documentation
- [ ] Demo preparation

---

## Issue Tracking

### Open Issues

None! All critical (P0) and high-priority (P1) security issues are resolved.

### Completed Issues

| ID | Title | Completed | Sprint |
|----|-------|-----------|--------|
| - | Initial scaffold | Mar 5 | Pre-MVP |
| - | Core agent loop | Mar 5 | Pre-MVP |
| - | Event system | Mar 5 | Pre-MVP |
| - | Guardrails engine | Mar 5 | Pre-MVP |
| - | Memory system | Mar 5 | Pre-MVP |
| - | Skills system | Mar 5 | Pre-MVP |
| #1 | C-1: Encrypted credentials | Mar 18 | Sprint 1 |
| #2 | C-2: Memory encryption | Mar 18 | Sprint 1 |
| #3 | C-3: Rate limiting | Mar 18 | Sprint 1 |
| #4 | H-2: Session file permissions | Mar 18 | Sprint 1 |
| #5 | H-4: Prompt injection defenses | Mar 18 | Sprint 1 |
| #6 | Sprint 2: Guardrails integration | Mar 19 | Sprint 2 |
| #7 | Sprint 2: Policy examples | Mar 19 | Sprint 2 |
| #8 | Sprint 2: Guardrails documentation | Mar 19 | Sprint 2 |
| #9 | Sprint 3: Skills auto-activation | Mar 19 | Sprint 3 |
| #10 | Sprint 3: Skill management API | Mar 19 | Sprint 3 |
| #11 | Sprint 3: Enhanced filesystem skill | Mar 19 | Sprint 3 |
| #12 | Sprint 3: Enhanced web skill | Mar 19 | Sprint 3 |
| #13 | Sprint 3: Enhanced git skill | Mar 19 | Sprint 3 |
| #14 | Sprint 4: Memory recall integration | Mar 19 | Sprint 4 |
| #15 | Sprint 4: Auto-extraction of memories | Mar 19 | Sprint 4 |
| #16 | Sprint 4: Context injection with budget | Mar 19 | Sprint 4 |
| #17 | Sprint 4: Manual memory API | Mar 19 | Sprint 4 |
| #18 | Sprint 4: Memory integration tests | Mar 19 | Sprint 4 |
| #19 | Sprint 4: Memory retention policies | Mar 19 | Sprint 4 |
| #20 | Sprint 4: Memory CLI commands | Mar 20 | Sprint 4 |
| #21 | Sprint 4: Memory documentation | Mar 20 | Sprint 4 |

---

## Code Quality & Refactoring (Post-MVP Phase 1)

**Priority:** P1 (Post-Sprint 8, before production deployment)
**Epic:** Technical Debt & Code Health
**Timeline:** 2-3 weeks after MVP completion

**Current State:** Codebase is healthy and functional, but will benefit from strategic refactoring before production deployment.

### Goals

1. **Reduce complexity** - Simplify complex modules, improve readability
2. **Eliminate duplication** - Extract common patterns, DRY principle
3. **Improve maintainability** - Better abstractions, clearer boundaries
4. **Optimize performance** - Identify and fix bottlenecks
5. **Enhance testability** - Improve test coverage, reduce test duplication

### Phase 1: Assessment & Planning (Week 1)

- [ ] **Code Complexity Analysis** `quality` `assessment`
  - Run McCabe complexity analysis (target: complexity <10 per function)
  - Run Halstead complexity metrics
  - Identify hotspots with high cyclomatic complexity
  - Document top 10 most complex modules
  - Estimate: 1 day

- [ ] **Duplication Detection** `quality` `assessment`
  - Run `pylint --duplicate-code` across codebase
  - Identify repeated patterns in tests (MockProvider setup, etc.)
  - Find similar logic across guardrails/skills/integrations
  - Document duplication candidates for extraction
  - Estimate: 1 day

- [ ] **Dependency Audit** `security` `quality`
  - Review all external dependencies
  - Check for unused dependencies
  - Identify security vulnerabilities (safety, pip-audit)
  - Update outdated packages
  - Estimate: 0.5 days

- [ ] **Code Coverage Analysis** `testing` `quality`
  - Generate detailed coverage report with branch coverage
  - Identify untested code paths
  - Prioritize critical paths for testing
  - Create test coverage improvement plan
  - Estimate: 0.5 days

- [ ] **Performance Profiling** `performance` `assessment`
  - Profile agent loop with realistic workloads
  - Identify slow operations (memory encryption, session I/O)
  - Memory usage analysis
  - Create performance optimization backlog
  - Estimate: 1 day

- [ ] **Architecture Review** `architecture` `assessment`
  - Review module boundaries and dependencies
  - Identify circular dependencies
  - Document architectural smells
  - Propose refactoring strategies
  - Estimate: 1 day

### Phase 2: Strategic Refactoring (Week 2-3)

#### High-Priority Refactorings

- [ ] **Extract Common Test Utilities** `testing` `refactoring`
  - Location: `tests/`
  - Scope:
    - [ ] Create shared `MockProvider` base class
    - [ ] Extract common test fixtures to `conftest.py`
    - [ ] Shared UI mocks and helpers
    - [ ] Reduce test duplication by 30%+
  - Estimate: 2 days
  - Impact: Improves test maintainability

- [ ] **Simplify Agent Class** `core` `refactoring`
  - Location: `forge/core/agent.py`
  - Current size: ~400 LOC
  - Scope:
    - [ ] Extract tool management to `ToolRegistry` class
    - [ ] Move skill logic to dedicated `SkillManager`
    - [ ] Separate command handling into `CommandRouter`
    - [ ] Target: Reduce Agent to <200 LOC
  - Estimate: 3 days
  - Impact: Better separation of concerns, easier testing

- [ ] **Consolidate Validation Logic** `quality` `refactoring`
  - Location: `forge/primitives/`
  - Scope:
    - [ ] Extract common validation patterns
    - [ ] Create `validators.py` module
    - [ ] Shared path validation (used in guardrails, skills)
    - [ ] Shared credential validation (integrations, memory)
  - Estimate: 2 days
  - Impact: Reduces duplication, consistent validation

- [ ] **Optimize Memory Encryption** `performance` `refactoring`
  - Location: `forge/primitives/memory/encrypted.py`
  - Scope:
    - [ ] Batch encryption/decryption for bulk operations
    - [ ] Async encryption for large memories
    - [ ] LRU cache for frequently accessed memories
    - [ ] Compression before encryption
    - [ ] Target: 50% faster for large datasets
  - Estimate: 2 days
  - Impact: Better performance at scale

- [ ] **Improve Error Handling Consistency** `quality` `refactoring`
  - Location: All modules
  - Scope:
    - [ ] Standardize exception hierarchy
    - [ ] Create custom exceptions for each module
    - [ ] Consistent error messages and codes
    - [ ] Better error context in logs
  - Estimate: 2 days
  - Impact: Easier debugging, better UX

- [ ] **Skills Documentation Optimization** `skills` `refactoring`
  - Location: `skills/*/SKILL.md`
  - Current size: 1,577 LOC (verbose for LLM consumption)
  - Scope:
    - [ ] Create "condensed" versions for faster loading
    - [ ] Extract common security sections to shared include
    - [ ] Progressive detail levels (basic → advanced)
    - [ ] Target: 30% token reduction while maintaining quality
  - Estimate: 1 day
  - Impact: Faster skill activation, lower LLM costs

#### Medium-Priority Refactorings

- [ ] **Type Hints Improvement** `quality` `refactoring`
  - Add comprehensive type hints to all public APIs
  - Run `mypy --strict` and fix issues
  - Add return type annotations
  - Estimate: 2 days
  - Impact: Better IDE support, catch bugs earlier

- [ ] **Logging Enhancement** `observability` `refactoring`
  - Standardize log levels across modules
  - Add structured logging (JSON format option)
  - Performance metrics logging
  - Add log correlation IDs
  - Estimate: 1 day
  - Impact: Better debugging, production monitoring

- [ ] **Configuration Management** `architecture` `refactoring`
  - Create centralized configuration system
  - Environment-based config (dev, staging, prod)
  - Validation of configuration at startup
  - Estimate: 2 days
  - Impact: Easier deployment, fewer config errors

### Phase 3: Quality Gates & Automation (Week 3)

- [ ] **Pre-commit Hooks** `tooling` `quality`
  - Complexity limits (McCabe <10)
  - Max file size (400 LOC)
  - Code formatting (ruff, black)
  - Type checking (mypy)
  - Estimate: 1 day

- [ ] **CI/CD Quality Checks** `tooling` `quality`
  - Automated complexity analysis
  - Coverage reports (fail if <80%)
  - Security scanning (bandit)
  - Dependency vulnerability checks
  - Estimate: 1 day

- [ ] **Code Review Guidelines** `process` `docs`
  - Complexity thresholds
  - Performance considerations
  - Security checklist
  - Testing requirements
  - Estimate: 0.5 days

### Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test Coverage | 60% | 85% | 🟡 In Progress |
| Avg Cyclomatic Complexity | TBD | <8 | ⚪ Not Measured |
| Code Duplication | TBD | <5% | ⚪ Not Measured |
| Type Coverage | ~40% | >90% | 🟡 Partial |
| LOC per Module | ~150 avg | <300 max | 🟢 Good |
| Build Time | <1s | <2s | 🟢 Good |
| Test Suite Time | 0.34s | <5s | 🟢 Excellent |

### Technical Debt Register

Current known technical debt items:

| ID | Item | Priority | Effort | Assigned |
|----|------|----------|--------|----------|
| TD-1 | Trust building test infinite loop | P2 | 2h | Deferred |
| TD-2 | Agent class too large (400+ LOC) | P1 | 3d | Phase 2 |
| TD-3 | Test fixture duplication | P1 | 2d | Phase 2 |
| TD-4 | Skills docs verbose (1,577 LOC) | P2 | 1d | Phase 2 |
| TD-5 | Missing type hints in core modules | P2 | 2d | Phase 2 |
| TD-6 | Encryption performance bottleneck | P1 | 2d | Phase 2 |

### Notes

- **Refactoring is NOT feature work** - strictly improving existing code
- **All refactorings must maintain test coverage** - no coverage drops
- **Performance changes must be benchmarked** - before/after metrics
- **Breaking API changes require major version bump** - follow semver
- **Document all architectural decisions** - ADRs for major refactorings

---

## Future Enhancements (Post-MVP)

### Agent Sandboxing & Isolation

**Priority:** P0 (Post-MVP Phase 2 - CRITICAL for production)
**Epic:** Process Isolation & Sandboxing
**Documentation:** [docs/SANDBOXING_PLAN.md](docs/SANDBOXING_PLAN.md)

**Current State:** ⚠️ **Agents run with full user privileges - NOT sandboxed**

#### What's Missing:
- ❌ Process isolation (agent runs with full user privileges)
- ❌ Filesystem sandboxing (can read/write any user-accessible file)
- ❌ Network restrictions (can make any network connection)
- ❌ Resource limits (no CPU/memory/disk quotas)
- ❌ Capability dropping (runs with all user capabilities)
- ❌ Syscall filtering (no seccomp-bpf restrictions)

#### Phase 1: Basic Isolation (4-5 weeks)

- [ ] **Filesystem Sandbox** `security` `critical`
  - Path validation and blocklists
  - User approval for out-of-bounds access
  - Blocked directory patterns (/etc, /var, ~/.ssh, etc.)
  - Estimate: 2 weeks

- [ ] **Network Sandbox** `security` `critical`
  - Domain allowlist/blocklist
  - IP range filtering
  - Private network blocking (optional)
  - Connection monitoring
  - Estimate: 1.5 weeks

- [ ] **Resource Limits** `security` `high`
  - Memory limits (rlimit)
  - CPU time limits
  - File descriptor limits
  - File size limits
  - Monitoring and alerts
  - Estimate: 1 week

- [ ] **Integration & Testing** `testing`
  - Integrate all sandboxes into Agent class
  - Configuration system
  - Documentation
  - End-to-end tests
  - Estimate: 0.5 weeks

#### Phase 2: Process Isolation (3-4 weeks)

- [ ] **Subprocess Sandbox** `security` `critical`
  - Cross-platform subprocess isolation
  - Linux namespaces support
  - macOS sandbox-exec support
  - Windows job objects
  - IPC between host and sandbox
  - Estimate: 3 weeks

- [ ] **Container Support** `security` `high`
  - Docker/Podman integration
  - Dockerfile for sandbox image
  - Volume mounting
  - Network isolation
  - Estimate: 1 week

#### Phase 3: Advanced Security (2-3 weeks)

- [ ] **SELinux/AppArmor Policies** `security` `high`
  - Policy generation
  - Installation scripts
  - Testing on various distros
  - Estimate: 1 week

- [ ] **Seccomp-BPF** `security` `high`
  - Syscall filtering
  - Platform-specific filters
  - Performance testing
  - Estimate: 1 week

- [ ] **Audit & Monitoring** `observability` `medium`
  - Security event logging
  - Anomaly detection
  - Alerting system
  - Estimate: 1 week

**Total Estimate:** 9-12 weeks (Phase 1-3)
**Minimum Viable Sandbox:** Phase 1 (4-5 weeks)
**Suggested Sprint:** Post-MVP Phase 2 (Security Hardening)

**Rationale:** Agent sandboxing is critical for production deployments where untrusted or semi-trusted agents run on user systems. Current guardrails provide detection and approval, but not isolation.

---

### Encryption & Key Management Enhancements

**Priority:** P2 (Post-Sprint 8)
**Epic:** Advanced Security & Cryptography

#### Tasks to Add:

- [ ] **Encryption Algorithm Flexibility** `security` `enhancement`
  - Location: `forge/primitives/integrations/credential_store.py`, `forge/primitives/memory/encrypted.py`
  - Scope:
    - [ ] Add pluggable encryption backend abstraction
    - [ ] Implement AES-GCM as alternative to Fernet
    - [ ] Support Age encryption (modern standard)
    - [ ] Add ChaCha20-Poly1305 option
    - [ ] Migration tool for algorithm changes
  - Estimate: 3-4 days
  - Rationale: Future-proof against algorithm weaknesses, support compliance requirements

- [ ] **Key Rotation & Management** `security` `critical`
  - Location: `forge/primitives/integrations/credential_store.py`, `forge/primitives/memory/encrypted.py`
  - Scope:
    - [ ] Implement key rotation without data re-encryption (envelope encryption)
    - [ ] Add key versioning (track which key encrypted which data)
    - [ ] Automatic key expiration and renewal
    - [ ] Key backup and recovery mechanisms
    - [ ] Support for Hardware Security Modules (HSM)
    - [ ] Integration with cloud KMS (AWS KMS, GCP KMS, Azure Key Vault)
  - Estimate: 5-7 days
  - Rationale: Essential for production deployments, compliance (PCI-DSS, HIPAA)

- [ ] **Key Derivation & Multi-Tenancy** `security` `enhancement`
  - Location: `forge/primitives/integrations/credential_store.py`
  - Scope:
    - [ ] Per-agent key derivation (isolate agent credentials)
    - [ ] Per-user key derivation (multi-tenant support)
    - [ ] Hierarchical key management (master key → agent keys → data keys)
    - [ ] Key scoping and access controls
  - Estimate: 4-5 days
  - Rationale: Required for multi-agent, multi-user deployments

- [ ] **Encryption Auditing & Monitoring** `security` `observability`
  - Location: `forge/primitives/integrations/`, `forge/primitives/memory/`
  - Scope:
    - [ ] Log all encryption/decryption operations
    - [ ] Track key usage and access patterns
    - [ ] Alert on decryption failures
    - [ ] Metrics for encryption performance
    - [ ] Compliance audit trail
  - Estimate: 2-3 days
  - Rationale: Security monitoring, compliance, debugging

- [ ] **Encryption Performance Optimization** `performance` `enhancement`
  - Location: `forge/primitives/memory/encrypted.py`
  - Scope:
    - [ ] Batch encryption/decryption for bulk operations
    - [ ] Async encryption for large memories
    - [ ] Caching of decrypted content (with TTL)
    - [ ] Compression before encryption
  - Estimate: 2-3 days
  - Rationale: Performance at scale

- [ ] **Advanced Key Storage Options** `security` `enhancement`
  - Location: `forge/primitives/integrations/credential_store.py`
  - Scope:
    - [ ] TPM (Trusted Platform Module) support
    - [ ] Vault (HashiCorp) integration
    - [ ] 1Password/Bitwarden CLI integration
    - [ ] YubiKey/hardware token support
  - Estimate: 4-5 days
  - Rationale: Enterprise security requirements

**Total Estimate:** 20-27 days (4-5 weeks)
**Suggested Sprint:** Post-MVP Phase 2 (Security Hardening)

**Note:** These enhancements integrate well with the planned Erlang/BEAM runtime (Phase 2), where encryption keys can be isolated per-agent supervisor process.

---

## Blockers & Risks

### Current Blockers

None currently.

### Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Gmail OAuth complexity | High | Start early, use official SDK | ⚠️ Monitoring |
| Memory encryption breaks search | High | Use hybrid approach | ✅ Resolved (C-2) |
| Rate limiting too strict | Medium | Make configurable | ⚠️ Monitoring |
| Key rotation complexity | Medium | Defer to post-MVP, use envelope encryption | ⚠️ Acknowledged |
| Algorithm obsolescence | Low | Pluggable backends planned for Phase 2 | ⚠️ Monitoring |

---

## Metrics

### Code Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test Coverage | 60% | 80% | 🟡 Below Target |
| Lines of Code | 9,964 | ~10,000 | 🟢 On Track |
| Tests Passing | 231/231 | 100% | 🟢 Good |
| Security Issues | 0 | 0 critical/high | 🟢 All Resolved |

### Velocity (Story Points per Sprint)

| Sprint | Planned | Completed | Velocity |
|--------|---------|-----------|----------|
| Sprint 1 | TBD | TBD | - |

---

## Daily Standup Template

### Today (Date)

**What I did yesterday:**
-

**What I'm doing today:**
-

**Blockers:**
-

**Notes:**
-

---

## Weekly Review Template

### Week of [Date]

**Completed:**
-

**In Progress:**
-

**Blocked:**
-

**Next Week:**
-

**Learnings:**
-

---

## Sprint Retrospective Template

### Sprint [Number] Retrospective

**What went well:**
-

**What could be improved:**
-

**Action items:**
-

---

## Quick Commands

### Run Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=forge --cov-report=term-missing

# Specific module
pytest tests/primitives/guardrails/
```

### Code Quality
```bash
# Linting
ruff check forge/

# Type checking
mypy forge/

# Format
ruff format forge/
```

### Git Workflow
```bash
# Start new feature
git checkout -b feature/encrypted-credentials

# Commit with conventional commits
git commit -m "feat(security): implement encrypted credential storage"
git commit -m "fix(memory): resolve search query bug"
git commit -m "docs: add security architecture guide"

# Push
git push -u origin feature/encrypted-credentials
```

---

## Notes & Decisions

### Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| Mar 18 | Use OS keyring for credentials | More secure than file-based | Requires `keyring` dependency |
| Mar 18 | Hybrid memory encryption | Keeps search working | More complex implementation |
| Mar 18 | Focus on framework | Enable any agent type | Broader market potential |

### Technical Debt

| Item | Priority | Target Sprint |
|------|----------|---------------|
| MCP bridge implementation | P2 | Post-MVP |
| Cloud services stubs | P3 | Post-MVP |
| Multi-agent orchestration | P3 | Post-MVP |

---

## Contact & Communication

**Project Lead:** Keith Foster
**Repository:** https://github.com/teotl/teotl
**Issues:** GitHub Issues
**Discussions:** GitHub Discussions

---

## Sprint Planning Schedule

- **Sprint Planning:** Monday 9am
- **Daily Standup:** Every morning 9am (async/self-check-in)
- **Sprint Review:** Friday 4pm
- **Sprint Retrospective:** Friday 4:30pm

---

**Last Updated:** March 20, 2026
**Next Review:** April 3, 2026
