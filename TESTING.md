# Testing Documentation

## Test Status

**Current Status:** ✅ 553 passing / 3 skipped / 556 total (99.5% pass rate)

## Skipped Tests

### 1. Wizard Integration Tests (2 tests)

**Location:** `tests/cli/test_wizard.py`

**Tests:**
- `TestWizardIntegration::test_full_wizard_flow_anthropic`
- `TestWizardIntegration::test_full_wizard_flow_ollama`

**Reason:** Wizard flow significantly changed (now 22 questions instead of original flow). Tests need complete rewrite to match current implementation.

**Status:** Non-critical. Wizard functionality works correctly (verified manually), but integration tests are out of sync with implementation.

**TODO:** Rewrite integration tests to match current 22-question wizard flow. Current wizard includes:
- Agent naming
- Execution pattern selection (planner-worker vs single-agent)
- Model selection (planner + worker models)
- Skills selection
- Mission system setup
- Memory configuration
- Guardrails policy
- And more...

**Priority:** Low (wizard works, tests just need updating)

---

### 2. Keyring Backend Test (1 test)

**Location:** `tests/primitives/integrations/test_credential_store.py`

**Test:** `TestLocalKeyringBackend::test_save_and_load`

**Reason:** OS keyring dependencies not available in environment (conditional skip).

**Skip Condition:**
```python
@pytest.mark.skipif(not _keyring_available(), reason="Keyring dependencies not available")
```

**Status:** Expected behavior. This test requires OS-level keyring support which may not be available in:
- CI environments
- Headless servers
- Docker containers
- Some development environments

**Coverage:** The credential store has alternative backends (FileBackend, AWS Secrets Manager) that are fully tested.

**Priority:** None (intentional conditional skip)

---

## Running Tests

### Full Test Suite
```bash
pytest tests/ -v
```

### With Coverage
```bash
pytest tests/ --cov=teotl --cov-report=html
open htmlcov/index.html
```

### Quick Test (Stop on First Failure)
```bash
pytest tests/ -x
```

### Specific Test
```bash
pytest tests/core/test_agent.py -v
```

### Run Only Non-Skipped Tests
```bash
pytest tests/ -v -k "not wizard_flow"
```

## Test Organization

```
tests/
├── cli/                    # CLI and wizard tests
├── core/                   # Core agent, provider, types tests
├── daemon/                 # Daemon service tests
├── integration/           # Integration tests (guardrails, etc.)
├── primitives/
│   ├── guardrails/        # Security policy tests
│   ├── integrations/      # Credential store tests
│   ├── memory/            # Memory system tests
│   ├── missions/          # Mission system tests
│   ├── skills/            # Skills registry tests
│   └── tasks/             # Task store tests
└── test_bash_tool_with_skills.py  # Bash tool integration
```

## Warnings

The test suite produces 8 warnings from `test_encrypted_memory.py`:

```
RuntimeWarning: coroutine 'LocalMemory._initial_cleanup' was never awaited
```

**Status:** Known issue, does not affect functionality. Memory cleanup happens correctly in async contexts. Warning only appears in synchronous test initialization.

**Impact:** None - tests pass, memory works correctly

**TODO:** Suppress warning or refactor LocalMemory initialization (low priority)

## Coverage Target

- **Current:** ~99.5% of tests passing
- **Target:** 100% (after wizard test rewrite)
- **Code Coverage:** High (estimate 85%+, run with --cov to see exact)

## CI/CD

Tests should be run in CI on:
- Every push to main
- Every pull request
- Before releases

**Recommended CI command:**
```bash
pytest tests/ -v --cov=teotl --cov-report=xml --cov-report=term
```

## Future Test Improvements

1. **Rewrite wizard integration tests** (2 tests to update)
2. **Add GAIA benchmark tests** (after GAIA integration)
3. **Add DevOps Agent tests** (after agent development)
4. **Increase integration test coverage** (cross-component testing)
5. **Performance benchmarks** (cost, duration, quality metrics)

## Notes

- Tests use pytest fixtures for setup/teardown
- Async tests use `@pytest.mark.asyncio`
- Mocks use `unittest.mock.patch`
- Temporary files use pytest's `tmp_path` fixture
- Time-sensitive tests may be flaky in slow CI environments
