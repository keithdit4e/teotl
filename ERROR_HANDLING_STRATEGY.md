# Error Handling Strategy

## Overview

Comprehensive error handling for Forge agent framework, covering wizard configuration, skill validation, runtime execution, and graceful degradation.

---

## Error Categories

### 1. Configuration Errors (Wizard)
**When:** During wizard setup
**Impact:** Prevents agent creation
**Strategy:** Validate early, provide clear fix instructions

### 2. Skill Errors
**When:** Skills referenced but not available
**Impact:** Agent can't perform required tasks
**Strategy:** Check at wizard time and runtime

### 3. API/Provider Errors
**When:** API keys invalid, rate limits, network issues
**Impact:** Agent can't execute
**Strategy:** Validate keys, retry with backoff, fallback

### 4. CLI Tool Errors
**When:** claude-code, spec-kit not installed
**Impact:** Skills can't function
**Strategy:** Check before use, provide install instructions

### 5. File System Errors
**When:** Missing files, permission issues
**Impact:** Can't read/write required files
**Strategy:** Validate paths, check permissions, create if needed

### 6. Runtime Execution Errors
**When:** Agent running, tasks failing
**Impact:** Incomplete work
**Strategy:** Retry, checkpoint, report clearly

---

## Error Handling by Component

### Wizard (`forge/cli/wizard.py`)

#### Configuration Validation
```python
def _validate_config(self) -> list[str]:
    """Validate configuration before saving.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    if "execution_pattern" not in self.config:
        errors.append("Missing execution_pattern")

    # Pattern-specific validation
    pattern = self.config.get("execution_pattern")

    if pattern in ["daemon", "hybrid"]:
        if "provider" not in self.config:
            errors.append("Daemon pattern requires provider configuration")
        if "agent" not in self.config:
            errors.append("Daemon pattern requires agent configuration")

    if pattern in ["planner_worker", "hybrid"]:
        if "planner_worker" not in self.config:
            errors.append("Planner-Worker pattern requires planner_worker configuration")

        pw = self.config.get("planner_worker", {})

        if "planner" not in pw or "provider" not in pw.get("planner", {}):
            errors.append("Planner-Worker requires planner.provider")

        if "worker" not in pw or "provider" not in pw.get("worker", {}):
            errors.append("Planner-Worker requires worker.provider")

        if "worker" not in pw or "skills" not in pw.get("worker", {}):
            errors.append("Planner-Worker requires worker.skills")

    return errors
```

#### API Key Validation
```python
def _validate_api_key(self, key: str, provider_type: str) -> tuple[bool, str]:
    """Validate API key format.

    Args:
        key: API key to validate
        provider_type: Provider type (anthropic, openai, etc.)

    Returns:
        (is_valid, error_message)
    """
    if not key or key.strip() == "":
        return False, "API key cannot be empty"

    if provider_type == "anthropic":
        if not key.startswith("sk-ant-"):
            return False, "Anthropic API keys should start with 'sk-ant-'"
        if len(key) < 20:
            return False, "Anthropic API key too short (minimum 20 characters)"

    elif provider_type == "openai":
        if not key.startswith("sk-"):
            return False, "OpenAI API keys should start with 'sk-'"
        if len(key) < 20:
            return False, "OpenAI API key too short (minimum 20 characters)"

    return True, ""
```

#### Skill Availability Check
```python
def _validate_skills(self, skills: list[str]) -> tuple[list[str], list[str]]:
    """Validate that requested skills exist.

    Args:
        skills: List of skill names

    Returns:
        (available_skills, missing_skills)
    """
    available = []
    missing = []

    for skill in skills:
        skill_path = Path(f"skills/{skill}/SKILL.md")
        if skill_path.exists():
            available.append(skill)
        else:
            missing.append(skill)

    return available, missing
```

### Runner Script (`run_planner_worker.py`)

#### CLI Tool Availability Check
```python
def check_cli_tools() -> dict[str, bool]:
    """Check if required CLI tools are installed.

    Returns:
        Dict mapping tool name to availability
    """
    import shutil

    tools = {}

    # Check claude-code if skill is enabled
    if "claude_code" in worker_skills:
        tools["claude-code"] = shutil.which("claude-code") is not None

    # Check spec-kit if enabled
    if use_spec_kit:
        tools["spec-kit"] = shutil.which("spec-kit") is not None

    return tools


def print_cli_tool_warnings(tools: dict[str, bool]):
    """Print warnings for missing CLI tools.

    Args:
        tools: Dict from check_cli_tools()
    """
    missing = [name for name, available in tools.items() if not available]

    if missing:
        print("⚠️  WARNING: Missing CLI tools:")
        print()

        for tool in missing:
            if tool == "claude-code":
                print(f"  • {tool} - Required for claude_code skill")
                print(f"    Install: https://github.com/anthropics/claude-code")
            elif tool == "spec-kit":
                print(f"  • {tool} - Required for spec-kit planning")
                print(f"    Install: npm install -g spec-kit")

        print()
        print("Agent will continue but these skills will not function.")
        print()
```

#### Constitution File Check
```python
def check_constitution_files() -> tuple[list[str], list[str]]:
    """Check if constitution files exist (when spec-kit enabled).

    Returns:
        (existing_files, missing_files)
    """
    if not use_spec_kit:
        return [], []

    required_files = [
        "CONSTITUTION.md",
        "ARCHITECTURE.md",
        "STANDARDS.md",
        "SECURITY.md",
    ]

    existing = []
    missing = []

    for filename in required_files:
        file_path = workspace_dir / filename
        if file_path.exists():
            existing.append(filename)
        else:
            missing.append(filename)

    return existing, missing


def print_constitution_warnings(missing: list[str]):
    """Print warnings for missing constitution files.

    Args:
        missing: List of missing filenames
    """
    if missing:
        print("⚠️  WARNING: Missing constitution files:")
        print()
        for filename in missing:
            print(f"  • {filename}")
        print()
        print("Planner will continue but constitution-driven planning may be limited.")
        print("Create these files or re-run wizard to generate templates.")
        print()
```

#### API Key Validation
```python
def validate_api_keys() -> dict[str, str]:
    """Validate API keys from environment.

    Returns:
        Dict mapping provider to error message (empty string if valid)
    """
    errors = {}

    # Check planner API key
    planner_key_env = planner_config.get("api_key_env", "ANTHROPIC_API_KEY")
    planner_key = os.getenv(planner_key_env)

    if not planner_key:
        errors["planner"] = f"Missing environment variable: {planner_key_env}"
    elif len(planner_key) < 20:
        errors["planner"] = f"Invalid {planner_key_env}: too short"

    # Check worker API key
    worker_key_env = worker_config.get("api_key_env", "ANTHROPIC_API_KEY")
    worker_key = os.getenv(worker_key_env)

    if not worker_key:
        errors["worker"] = f"Missing environment variable: {worker_key_env}"
    elif len(worker_key) < 20:
        errors["worker"] = f"Invalid {worker_key_env}: too short"

    return errors


def print_api_key_errors(errors: dict[str, str]):
    """Print API key errors and exit.

    Args:
        errors: Dict from validate_api_keys()
    """
    if errors:
        print("❌ API Key Validation Failed:")
        print()
        for component, error in errors.items():
            print(f"  • {component}: {error}")
        print()
        print("Set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print()
        sys.exit(1)
```

#### Execution Error Handling
```python
async def execute_with_retry(
    harness,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> dict:
    """Execute task with retry logic.

    Args:
        harness: PlannerWorkerHarness instance
        max_retries: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier

    Returns:
        Result dict with status and details
    """
    import time

    for attempt in range(max_retries):
        try:
            result = await harness.execute_next_step()
            return {"success": True, "result": result}

        except RateLimitError as e:
            wait_time = backoff_factor ** attempt
            print(f"⚠️  Rate limit hit. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue

        except NetworkError as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                print(f"⚠️  Network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return {"success": False, "error": f"Network error after {max_retries} attempts: {e}"}

        except APIError as e:
            # API errors usually not transient, don't retry
            return {"success": False, "error": f"API error: {e}"}

        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {e}"}

    return {"success": False, "error": f"Failed after {max_retries} attempts"}
```

### Skill Files

#### Claude Code Error Handling
```bash
# In claude_code skill - check CLI available
if ! command -v claude-code &> /dev/null; then
    echo "❌ ERROR: claude-code CLI not installed"
    echo ""
    echo "Install Claude Code:"
    echo "  1. Visit https://github.com/anthropics/claude-code"
    echo "  2. Follow installation instructions"
    echo "  3. Verify: claude-code --version"
    echo ""
    echo "Without claude-code, this skill cannot function."
    exit 1
fi

# Handle execution failures
claude-code "$TASK_DESCRIPTION"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Claude Code task failed with exit code: $EXIT_CODE"
    echo ""
    echo "Possible issues:"
    echo "  • API key invalid or missing"
    echo "  • Task description unclear"
    echo "  • File permissions"
    echo "  • Network connectivity"
    echo ""
    echo "Check logs above for specific error."
    exit 1
fi
```

#### spec-kit Error Handling
```bash
# In spec_kit skill - check CLI available
if ! command -v spec-kit &> /dev/null; then
    echo "⚠️  WARNING: spec-kit CLI not installed"
    echo ""
    echo "Install spec-kit:"
    echo "  npm install -g spec-kit"
    echo ""
    echo "Continuing without spec-kit (using manual specifications)..."
    # Fallback: Create spec manually
    USE_MANUAL_SPEC=true
fi

# Check constitution files exist
if [ ! -f "CONSTITUTION.md" ]; then
    echo "⚠️  WARNING: CONSTITUTION.md not found"
    echo "Creating basic constitution template..."

    cat > CONSTITUTION.md << 'EOF'
# Project Constitution
## Core Values
- Quality: All code must be tested
- Security: All endpoints require authentication
EOF
fi
```

---

## Graceful Degradation Strategies

### 1. Missing CLI Tools
```yaml
Strategy: Continue with reduced functionality

Example (claude-code missing):
  • Worker can still use filesystem and git skills
  • Warn user that coding tasks will be manual
  • Provide installation instructions
  • Continue execution with available skills
```

### 2. Missing Constitution Files
```yaml
Strategy: Generate minimal constitution, continue

Example:
  • Create basic CONSTITUTION.md with defaults
  • Warn user that planning may be generic
  • Continue with spec-kit using minimal constitution
  • Suggest customization for better results
```

### 3. API Key Issues
```yaml
Strategy: Fail fast with clear instructions

Example:
  • Validate keys before starting work
  • Show exactly which env var to set
  • Provide example command
  • Exit immediately (cannot continue without keys)
```

### 4. Skill Not Available
```yaml
Strategy: Remove skill, warn, continue

Example:
  • Detect missing skill at wizard time
  • Offer to continue without that skill
  • Adjust worker instructions accordingly
  • Continue with available skills only
```

### 5. Network/API Failures
```yaml
Strategy: Retry with exponential backoff

Example:
  • Retry up to 3 times
  • Wait 1s, 2s, 4s between retries
  • Show progress to user
  • If all retries fail, report clear error
```

---

## Error Messages

### Good Error Messages

✅ **Specific and Actionable:**
```
❌ API Key Validation Failed:
  • planner: Missing environment variable: ANTHROPIC_API_KEY

Set your API key:
  export ANTHROPIC_API_KEY='your-key-here'
```

✅ **Context and Solution:**
```
⚠️  WARNING: claude-code CLI not installed

Required for claude_code skill.

Install:
  https://github.com/anthropics/claude-code

Without claude-code, coding tasks will not function.
Continue anyway? (yes/no):
```

### Bad Error Messages

❌ **Vague:**
```
Error: Invalid configuration
```

❌ **No Action:**
```
API key missing
```

❌ **Too Technical:**
```
ConfigurationException: NoneType object has no attribute 'get' at line 1234
```

---

## Testing Strategy

### Unit Tests
- Configuration validation
- API key format validation
- Skill availability checks
- CLI tool detection

### Integration Tests
- End-to-end with missing tools
- API key errors
- Network failures (mocked)
- File permission errors

### Error Scenarios to Test
1. Missing API key
2. Invalid API key format
3. Missing skill files
4. Missing CLI tools (claude-code, spec-kit)
5. Missing constitution files
6. Network timeout
7. Rate limit exceeded
8. File permission denied
9. Invalid configuration
10. Malformed YAML

---

## Implementation Priority

### High Priority (Implement First)
1. ✅ API key validation (wizard + runner)
2. ✅ Configuration validation (wizard)
3. ✅ CLI tool checks (runner)
4. ✅ Skill availability (wizard)

### Medium Priority
5. ✅ Constitution file validation
6. ✅ Error handling in runner script
7. ✅ Graceful degradation strategies
8. ✅ Retry logic for network errors

### Low Priority
9. ⏸️ Advanced error recovery
10. ⏸️ Error telemetry/logging
11. ⏸️ User-friendly error portal

---

## Next Steps

1. Add validation methods to wizard
2. Update runner script template with error handling
3. Add CLI tool checks to skills
4. Create error handling tests
5. Document error scenarios in user guide
