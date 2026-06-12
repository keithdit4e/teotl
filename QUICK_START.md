# Teotl MVP - Quick Start Guide

**Welcome to Forge development!** This guide gets you started on the MVP journey.

---

## Architecture Note

Forge uses a **hybrid architecture**:
- **Python** for agent logic (this MVP phase)
- **Erlang/BEAM** for fault-tolerant runtime (post-MVP)

See `ARCHITECTURE_DECISIONS.md` for full rationale.

**MVP Focus:** Python-only framework. BEAM runtime added in Phase 2.

---

## Today's Mission: Start Sprint 1

**Goal:** Begin security fixes (C-1: Encrypted credentials)

**Time:** ~4 hours for setup + first task

---

## Step 1: Environment Check (15 min)

### Verify Installation
```bash
cd /Users/keithfoster/Documents/GitHub/teotl

# Check Python version
python3 --version  # Should be 3.11+

# Check dependencies
python3 -c "import forge; print('✓ Forge installed')"

# Run tests
pytest
# Should see: 66 passed
```

### Install Security Dependencies
```bash
pip install keyring cryptography
```

---

## Step 2: Review Project Status (15 min)

### Read Key Documents
1. **MVP_ROADMAP.md** - Overall plan
2. **PROJECT_TRACKER.md** - Sprint details and tasks
3. **ARCHITECTURE_DECISIONS.md** - Technical decisions (Python + future Erlang)
4. **SECURITY_AUDIT.md** - What needs fixing
5. **SECURITY_QUICKSTART.md** - Implementation guides

### Current State
- ✅ Core framework scaffolded (3,520 LOC Python)
- ✅ All tests passing (66/66)
- ✅ Basic features working
- ⚠️ Security issues need fixing (3 critical)
- 📋 BEAM runtime planned for post-MVP

---

## Step 3: Start First Task - C-1 Encrypted Credentials (3 hours)

### Task Breakdown

#### Part 1: Create Secure Store (1 hour)
```bash
# Create the implementation file
touch forge/primitives/integrations/secure_store.py
```

Copy implementation from `docs/SECURITY_QUICKSTART.md` (SecureCredentialStore class).

Key points:
- Uses OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Fernet encryption for credential data
- Fallback to file-based with strict permissions
- **Note:** When we add BEAM runtime, credentials will be managed by Erlang supervisor for additional isolation

#### Part 2: Write Tests (45 min)

```bash
# Create test file
touch tests/primitives/integrations/test_secure_store.py
```

Add comprehensive tests (see SECURITY_QUICKSTART.md for examples).

#### Part 3: Update Integration Registry (30 min)

Edit `forge/primitives/integrations/registry.py` to use SecureCredentialStore.

**Future consideration:** When BEAM runtime is added, each agent will have isolated credential storage managed by its supervisor.

#### Part 4: Run Tests (15 min)
```bash
# Run new tests
pytest tests/primitives/integrations/test_secure_store.py -v

# Run all tests
pytest

# Check coverage
pytest --cov=forge/primitives/integrations
```

---

## Step 4: Commit Your Work (15 min)

```bash
# Create feature branch
git checkout -b feature/encrypted-credentials

# Stage files
git add forge/primitives/integrations/secure_store.py
git add tests/primitives/integrations/test_secure_store.py
git add forge/primitives/integrations/registry.py

# Commit
git commit -m "feat(security): implement encrypted credential storage

- Add SecureCredentialStore using OS keyring + Fernet encryption
- Update IntegrationRegistry to use secure storage
- Add comprehensive tests for credential encryption
- Resolves C-1 from security audit
- Note: BEAM runtime integration planned for Phase 2

Fixes #1"

# Push
git push -u origin feature/encrypted-credentials
```

---

## Step 5: Update Project Tracker (5 min)

Edit `PROJECT_TRACKER.md` and mark #1 as complete.

---

## This Week's Goals

### Sprint 1 Tasks (March 18-24)

**Critical Security:**
- [ ] C-1: Encrypted credentials (Day 1) ← YOU ARE HERE
- [ ] C-2: Memory encryption (Day 2-3)
- [ ] C-3: Rate limiting (Day 4)

**High-Priority:**
- [ ] H-2: File permissions (Day 5)
- [ ] H-4: Prompt injection (Day 5)

**Deliverables:**
- [ ] All critical issues resolved
- [ ] Tests passing at 80%+
- [ ] Can run agents securely

---

## Daily Routine

### Morning Checklist
1. ☕ Coffee
2. 📖 Review PROJECT_TRACKER.md
3. 🎯 Plan today's tasks
4. 💻 Start coding

### Afternoon Checklist
1. ✅ Run tests
2. 📝 Commit work
3. 📊 Update tracker
4. 🗓️ Plan tomorrow

---

## Useful Commands

### Development
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=forge --cov-report=html
open htmlcov/index.html

# Watch mode (auto-run on file changes)
pip install pytest-watch
ptw
```

### Code Quality
```bash
# Lint
ruff check forge/

# Format
ruff format forge/

# Type check
mypy forge/
```

---

## Phase 2 Preview: BEAM Runtime

After MVP (Python-only), we'll add optional Erlang/Elixir runtime for production:

### Benefits
- **Fault Tolerance:** Agents crash independently, auto-restart
- **Process Isolation:** Each agent in separate BEAM process
- **Hot Code Reloading:** Update agents without downtime
- **Distribution:** Agents across multiple machines

### Architecture
```
┌─────────────────────────────────┐
│   BEAM Supervisor Tree          │
│   ┌─────────┐  ┌─────────┐    │
│   │ Agent 1 │  │ Agent 2 │    │
│   │(Python) │  │(Python) │    │
│   └─────────┘  └─────────┘    │
└─────────────────────────────────┘
```

### For MVP
- Focus on Python framework
- Design with BEAM in mind (stateless agents)
- Keep agent logic portable

---

## Resources

### Documentation
- `README.md` - Project overview
- `MVP_ROADMAP.md` - Full roadmap
- `ARCHITECTURE_DECISIONS.md` - Tech decisions
- `PROJECT_TRACKER.md` - Sprint tracking
- `docs/SECURITY_*.md` - Security guides

### External
- **Anthropic:** https://docs.anthropic.com
- **Python:** https://docs.python.org/3/
- **Erlang/OTP:** https://www.erlang.org/doc/ (for Phase 2)
- **Elixir:** https://elixir-lang.org/ (for Phase 2)

---

## Troubleshooting

### Tests Failing
```bash
pytest --cache-clear
pip install -e ".[dev,all]" --force-reinstall
```

### Import Errors
```bash
pip install -e .
```

### Keyring Issues
Check logs - system will fall back to file-based encryption if keyring unavailable.

---

## Success Metrics

### Today
- [ ] C-1 implementation complete
- [ ] Tests passing
- [ ] Code committed
- [ ] Tracker updated

### This Week
- [ ] All critical security (C-1, C-2, C-3) resolved
- [ ] Test coverage ≥80%
- [ ] Sprint 1 complete
- [ ] Ready for Sprint 2 (guardrails)

---

## Next Steps

1. **Today:** Complete C-1 (encrypted credentials)
2. **Tomorrow:** Start C-2 (memory encryption)
3. **This Week:** Finish Sprint 1 (security foundation)
4. **Next Week:** Sprint 2 (guardrails system)

---

## Let's Build! 🚀

**First command:**
```bash
cd /Users/keithfoster/Documents/GitHub/teotl
touch forge/primitives/integrations/secure_store.py
# Open in editor and implement SecureCredentialStore
```

Remember: We're building a **framework**, not just an app. Every decision should enable other developers to build their own agents.

Python for development velocity. Erlang for production resilience. Best of both worlds.

Good luck! 💪
