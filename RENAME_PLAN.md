# Project Rename Plan: teotl → teotl

**Goal:** Rename the project from "teotl" to "teotl" (the animating divine force) to avoid conflicts with existing teotl package on PyPI.

**Scope:** 276 files contain "forge" references that need review and potential update.

---

## 1. Rename Strategy

### Phase 1: Core Package Rename
- Rename `forge/` directory to `teotl/`
- Update all imports from `forge.*` to `teotl.*`
- Update package name in `pyproject.toml`

### Phase 2: Configuration & Scripts
- Update CLI entry points
- Update configuration files
- Update example scripts

### Phase 3: Documentation
- Update all documentation
- Update README and guides
- Update comparison infrastructure docs

### Phase 4: Git & Repository
- Update repository references
- Update URLs and links
- Consider repository rename

---

## 2. Detailed Changes by Category

### 2.1 Core Package Structure

**Directory Rename:**
```bash
forge/ → teotl/
```

**Subdirectories (automatic with parent):**
- `forge/cli/` → `teotl/cli/`
- `forge/core/` → `teotl/core/`
- `forge/daemon/` → `teotl/daemon/`
- `forge/primitives/` → `teotl/primitives/`
- `forge/web/` → `teotl/web/`
- `forge/ui/` → `teotl/ui/`
- `forge/config/` → `teotl/config/`
- `forge/templates/` → `teotl/templates/`
- `forge/extensions/` → `teotl/extensions/`
- `forge/cloud/` → `teotl/cloud/`

---

### 2.2 Python Package Configuration

**File: `pyproject.toml`**

Changes needed:
```toml
# BEFORE
[project]
name = "teotl"
# Package imports
[tool.setuptools.packages.find]
where = ["."]
include = ["forge*"]

# AFTER
[project]
name = "teotl"
# Package imports
[tool.setuptools.packages.find]
where = ["."]
include = ["teotl*"]
```

**CLI Entry Points:**
```toml
# BEFORE
[project.scripts]
teotl = "forge.cli:main"
forge-web = "forge.web.__main__:main"
forge-daemon = "forge.daemon.__main__:main"

# AFTER
[project.scripts]
teotl = "teotl.cli:main"
teotl-web = "teotl.web.__main__:main"
teotl-daemon = "teotl.daemon.__main__:main"
```

---

### 2.3 Import Statements (All Python Files)

**Pattern to find:**
```python
from forge.* import
import forge.*
```

**Replace with:**
```python
from teotl.* import
import teotl.*
```

**Files affected:** ~150+ Python files

**Example locations:**
- `forge/__init__.py` (internal imports)
- `forge/cli/*.py` (imports from forge.core, etc.)
- `forge/core/*.py` (imports from forge.primitives, etc.)
- `tests/**/*.py` (all test imports)
- `examples/**/*.py` (example imports)

---

### 2.4 CLI Command Names

**Files to update:**

1. **`forge/cli/__init__.py`** → `teotl/cli/__init__.py`
   - CLI command definitions
   - Help text references

2. **`forge/cli/__main__.py`** → `teotl/cli/__main__.py`
   - Entry point

3. **`forge/cli/wizard.py`** → `teotl/cli/wizard.py`
   - Wizard prompts mentioning "Forge"
   - Generated file paths (e.g., `~/.teotl/` → `~/.teotl/`)

4. **`forge_onboard.py`** → `teotl_onboard.py`
   - Onboarding script rename

---

### 2.5 Configuration Files

**Workspace Directory:**
```
# BEFORE
~/.teotl/
~/.teotl/my-agent/

# AFTER
~/.teotl/
~/.teotl/my-agent/
```

**Configuration Files:**
- `config.yaml` - References to forge in comments
- `examples/**/*.yaml` - Example configs
- `policies/*.json` - Policy files (check comments)

---

### 2.6 Documentation Files

**Major Documentation (76+ files):**

1. **Root Documentation:**
   - `README.md` - Main project description
   - `QUICK_START.md` - Quick start guide
   - `CONTRIBUTING.md` - Contribution guide
   - `LICENSE` - No change needed (already generic)

2. **docs/ Directory (~50 files):**
   - `docs/GETTING_STARTED.md`
   - `docs/FORGE_ONE_PAGER.md` → `docs/TEOTL_ONE_PAGER.md`
   - `docs/FORGE_VS_OPENCLAW.md` → `docs/TEOTL_VS_OPENCLAW.md`
   - `docs/QUICK_START_DEMO.md`
   - `docs/ARCHITECTURE.md`
   - All other guide files

3. **Implementation Summaries:**
   - `IMPLEMENTATION_SUMMARY.md`
   - `PHASE1_COMPLETE.md`
   - `CLAUDE_CODE_SKILL_COMPLETE.md`
   - `ERROR_HANDLING_COMPLETE.md`
   - etc. (20+ summary files)

---

### 2.7 Comparison Infrastructure

**Location:** `comparison/`

**Files to update:**

1. **Agent Configurations:**
   - `comparison/agents/forge_config.yaml` → `comparison/agents/teotl_config.yaml`
   - References to "forge" agent in config

2. **Scripts:**
   - `comparison/setup_gcp.sh` - VM names, bucket names
   - `comparison/setup_gcp_vpc.sh` - VM names, network names
   - `comparison/cleanup_gcp.sh` - VM names
   - `comparison/cleanup_gcp_vpc.sh` - VM names

3. **Python Scripts:**
   - `comparison/measure_agent.py` - Agent name references
   - `comparison/analyze_results.py` - Agent name references

4. **Documentation:**
   - `comparison/README.md`
   - `comparison/QUICKSTART.md`
   - `comparison/NETWORKING_OPTIONS.md`
   - `AGENT_COMPARISON_PLAN.md`
   - `AGENT_COMPARISON_IMPLEMENTATION.md`

**VM Names:**
```bash
# BEFORE
teotl-vm

# AFTER
teotl-agent-vm
```

**Bucket Names:**
```bash
# BEFORE
${PROJECT_ID}-agent-comparison-results

# AFTER (no change, generic name)
${PROJECT_ID}-agent-comparison-results
```

---

### 2.8 Example Files

**Location:** `examples/`

**Files to update (~15 files):**
- `examples/harness_demo.py`
- `examples/planner_worker_demo.py`
- `examples/autonomous_agent/main.py`
- `examples/claude_code_agent.py`
- All example configs (`.yaml`)
- All agent templates in `examples/agent-templates/`

---

### 2.9 Test Files

**Location:** `tests/`

**Files to update (~40+ files):**
- All test files with imports from `forge`
- Test configuration files
- Mock/fixture files

---

### 2.10 Skills and Templates

**Skill Files:**
```
skills/*/SKILL.md - Check for "Forge" mentions in descriptions
```

**Template Files:**
- `forge/templates/INSTRUCTIONS_AUTONOMOUS.md`
- `forge/templates/SKILLS.md`

---

### 2.11 Git Repository

**Repository Name:**
```
# Current
teotl

# Proposed
teotl

# Alternative (if teotl taken)
teotl-agent
```

**URLs in Documentation:**
```
# BEFORE
https://github.com/your-org/teotl

# AFTER
https://github.com/your-org/teotl
```

---

## 3. Execution Order

### Step 1: Preparation ✅ (This Plan)
- ✅ Create comprehensive rename plan
- ✅ Identify all affected files
- ✅ Define replacement patterns

### Step 2: Core Package Rename
1. Rename `forge/` directory to `teotl/`
2. Update `pyproject.toml` (package name, entry points)
3. Update `forge/__init__.py` → `teotl/__init__.py`
4. Update all Python imports (automated find/replace)

### Step 3: CLI & Configuration
1. Rename `forge_onboard.py` → `teotl_onboard.py`
2. Update wizard default paths (`~/.teotl/` → `~/.teotl/`)
3. Update CLI command names in help text
4. Update configuration file references

### Step 4: Documentation Updates
1. Update `README.md` (main description)
2. Update all `docs/*.md` files
3. Update implementation summaries
4. Update comparison documentation
5. Rename specific files (`FORGE_ONE_PAGER.md`, etc.)

### Step 5: Examples & Tests
1. Update all `examples/*.py`
2. Update all `tests/**/*.py`
3. Update example configurations

### Step 6: Comparison Infrastructure
1. Update agent configs (`forge_config.yaml` → `teotl_config.yaml`)
2. Update GCP scripts (VM names, etc.)
3. Update measurement/analysis scripts
4. Update comparison documentation

### Step 7: Verification
1. Run tests: `pytest tests/`
2. Test CLI: `teotl --help`
3. Test wizard: `python teotl_onboard.py`
4. Check imports: `python -c "import teotl"`
5. Verify examples work

### Step 8: Git Commit
1. Commit all changes with clear message
2. Update remote repository name (if needed)
3. Update GitHub settings

---

## 4. Automated Replacement Patterns

### 4.1 Directory Rename
```bash
git mv forge teotl
```

### 4.2 Python Imports (regex)
```bash
# Pattern 1: from forge
from forge\.([a-zA-Z0-9_.]+) import
→ from teotl.\1 import

# Pattern 2: import forge
import forge\.([a-zA-Z0-9_.]+)
→ import teotl.\1

# Pattern 3: import forge
^import forge$
→ import teotl
```

### 4.3 File Content (case-sensitive)
```bash
# Package references
"teotl" → "teotl"
'teotl' → 'teotl'

# Module references
forge. → teotl.

# CLI references
teotl --help → teotl --help
teotl run → teotl run

# Directory paths
~/.teotl/ → ~/.teotl/
.forge/ → .teotl/
```

### 4.4 File Content (case-insensitive in docs)
```bash
# In documentation only
Forge Agent → Teotl
Forge Framework → Teotl
the Forge → Teotl
```

---

## 5. Files to Rename

### Exact File Renames:
```
forge/ → teotl/  (directory)
forge_onboard.py → teotl_onboard.py
comparison/agents/forge_config.yaml → comparison/agents/teotl_config.yaml
docs/FORGE_ONE_PAGER.md → docs/TEOTL_ONE_PAGER.md
docs/FORGE_VS_OPENCLAW.md → docs/TEOTL_VS_OPENCLAW.md
```

---

## 6. Files to Check Manually

### Keep "forge" in these contexts:
1. **Historical references** - Implementation logs, past decisions
2. **Comparison contexts** - When comparing to other frameworks named "Forge"
3. **Git history** - Old commit messages (don't rewrite history)

### Exceptions:
- `LICENSE` - Already generic, no project name
- `.gitignore` - Generic patterns
- Git history - Don't change

---

## 7. Testing Checklist

After rename, verify:

- [ ] Package imports: `python -c "import teotl"`
- [ ] CLI works: `teotl --help`
- [ ] Wizard works: `python teotl_onboard.py`
- [ ] Tests pass: `pytest tests/`
- [ ] Examples work: `python examples/harness_demo.py`
- [ ] Web dashboard: `teotl-web`
- [ ] Daemon: `teotl-daemon`
- [ ] Documentation builds (if using doc generator)
- [ ] Install works: `pip install -e .`

---

## 8. Potential Issues & Solutions

### Issue 1: Circular Imports
**Risk:** Renaming might expose circular import issues
**Solution:** Run tests frequently, fix imports incrementally

### Issue 2: Path References
**Risk:** Hard-coded paths like `~/.teotl/`
**Solution:** Search for all path references, update systematically

### Issue 3: Git History
**Risk:** Contributors might reference old name in PRs
**Solution:** Add note to README about rename

### Issue 4: External References
**Risk:** Blog posts, tutorials might reference old name
**Solution:** Add redirect note in README

---

## 9. Communication Plan

### Update README.md with:
```markdown
## Project Renamed

**Note:** This project was previously known as "teotl" but has been renamed to "teotl" to avoid conflicts with an existing package on PyPI.

- Old name: teotl
- New name: teotl
- Renamed: [Date]

If you have existing installations, please:
1. Uninstall old: `pip uninstall teotl`
2. Install new: `pip install teotl`
3. Update configs: Change `~/.teotl/` to `~/.teotl/`
```

---

## 10. Risk Assessment

### Low Risk:
✅ Python package rename (standard operation)
✅ Documentation updates (no functionality change)
✅ Example updates (isolated from core)

### Medium Risk:
⚠️ Import statement updates (many files, prone to typos)
⚠️ CLI command changes (user-facing impact)
⚠️ Configuration path changes (breaks existing configs)

### High Risk:
🔴 Git repository rename (breaks existing clones/forks)
🔴 PyPI package name (existing installations break)

### Mitigation:
- Test thoroughly after each phase
- Keep both CLI names initially (`forge` → `teotl`)
- Add deprecation warnings
- Maintain compatibility layer temporarily

---

## 11. Estimated Time

| Phase | Time | Notes |
|-------|------|-------|
| Core Package Rename | 15 min | Directory + imports |
| Configuration Updates | 10 min | Entry points, paths |
| Documentation Updates | 30 min | 76+ files |
| Examples & Tests | 20 min | Update imports |
| Comparison Infrastructure | 15 min | Scripts + docs |
| Verification & Testing | 20 min | Run all tests |
| **Total** | **~110 min** | **~2 hours** |

---

## 12. Rollback Plan

If issues arise:

1. **Git revert:**
   ```bash
   git reset --hard HEAD~1
   ```

2. **Manual rollback:**
   ```bash
   git mv teotl forge
   # Revert pyproject.toml
   # Revert imports
   ```

3. **Keep backup branch:**
   ```bash
   git checkout -b backup-before-rename
   git checkout main
   # ... perform rename ...
   ```

---

## Decision Points

Before execution, confirm:

1. ✅ **Package name:** "teotl" (single word, simple)
2. ✅ **CLI name:** `teotl` (not `teotl-agent`)
3. ⚠️ **Compatibility:** Break old installations or maintain compatibility?
4. ⚠️ **Repository name:** Rename GitHub repo or keep old URL?
5. ⚠️ **Workspace dir:** Change `~/.teotl/` or keep for compatibility?

---

## Recommendation

**Approach:** Clean break (no backward compatibility)

**Rationale:**
- Project is pre-1.0 (beta/development)
- No public PyPI release yet
- Better to rename now than later
- Simpler codebase without compatibility shims

**Timeline:** Execute rename immediately, single commit

---

## Status

- [x] Plan created
- [ ] Plan reviewed and approved
- [ ] Execution started
- [ ] Core package renamed
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Verification complete
- [ ] Committed to Git

---

**Ready to execute?** Review this plan, then proceed with systematic rename.
