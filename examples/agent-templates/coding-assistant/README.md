# Coding Assistant Agent Template

An intelligent pair programming companion that helps with code reviews, debugging, refactoring, testing, and documentation - adapting to your coding style and project conventions.

## What This Agent Does

- **💻 Code Review** - Analyzes pull requests for bugs, style, and best practices
- **🐛 Debugging Help** - Traces errors, suggests fixes, explains root causes
- **♻️ Refactoring** - Improves code structure, reduces duplication, applies patterns
- **🧪 Test Generation** - Writes unit tests, integration tests, edge cases
- **📚 Documentation** - Generates docstrings, comments, API docs
- **🔍 Code Search** - Finds functions, classes, usage examples across codebase
- **🏗️ Architecture Guidance** - Suggests design patterns and best practices

## Quick Start

### 1. Set Up Your Coding Assistant

```bash
# Create workspace
mkdir -p ~/.teotl/agents/coding-assistant

# Copy template files
cp -r examples/agent-templates/coding-assistant/* ~/.teotl/agents/coding-assistant/
```

### 2. Customize Your Profile

Edit `~/.teotl/agents/coding-assistant/USER.md`:

- Your programming languages and frameworks
- Code style preferences (formatting, naming conventions)
- Current projects and tech stack
- Testing preferences
- Documentation standards

### 3. Start Your Assistant

```bash
# Interactive mode
teotl chat --agent coding-assistant --skills filesystem,git,web

# The assistant loads your preferences and project context
```

## Example Interactions

### Code Review

```
You: "Review this function for potential bugs"

Bot: "Analyzing the calculate_total function...

**Issues Found:**

1. **Potential Division by Zero** (Line 45)
   - If `quantity` is 0, will raise ZeroDivisionError
   - Suggest: Add validation at function start

2. **Type Safety** (Line 42)
   - No type hints - unclear if price should be float or Decimal
   - Suggest: Add type annotations

3. **Edge Case** (Line 48)
   - Negative prices not handled
   - Suggest: Add validation or document assumption

**Style Issues:**
- Variable name `x` is not descriptive (Line 47)
- Missing docstring

**Suggested Fix:**
```python
def calculate_total(price: Decimal, quantity: int) -> Decimal:
    \"\"\"Calculate total price for given quantity.

    Args:
        price: Unit price (must be positive)
        quantity: Number of items (must be positive)

    Returns:
        Total price

    Raises:
        ValueError: If price or quantity is invalid
    \"\"\"
    if quantity <= 0:
        raise ValueError(\"Quantity must be positive\")
    if price < 0:
        raise ValueError(\"Price cannot be negative\")

    discount_rate = 0.1 if quantity > 100 else 0.0
    return price * quantity * (1 - discount_rate)
```

Would you like me to apply these changes?"
```

### Debugging

```
You: "I'm getting a 'list index out of range' error"

Bot: "Let me analyze the stack trace and code...

**Root Cause:**
The error occurs at line 123 in `process_items()`:
```python
item = items[index]  # ← Error here
```

**Problem:**
You're iterating with a fixed range(10) but the list might have fewer items.

**Fix Options:**

1. **Use enumerate** (Recommended):
```python
for index, item in enumerate(items):
    process(item)
```

2. **Check length**:
```python
for index in range(min(len(items), 10)):
    item = items[index]
```

3. **Add bounds check**:
```python
if index < len(items):
    item = items[index]
```

**Prevention:**
Consider adding a type hint and docstring to document expected list size.

Should I apply option 1 (enumerate)?"
```

### Refactoring

```
You: "This function is too long and hard to understand"

Bot: "Analyzing the 150-line handle_request function...

**Issues:**
- Multiple responsibilities (parsing, validation, processing, response)
- High cyclomatic complexity (15 branches)
- Code duplication in error handling

**Refactoring Plan:**

1. **Extract Methods**:
   - `parse_request()` - Lines 10-35
   - `validate_request()` - Lines 36-60
   - `process_request()` - Lines 61-120
   - `build_response()` - Lines 121-145

2. **Extract Error Handler**:
   - Common error pattern appears 5 times
   - Create `handle_error()` helper

3. **Apply Strategy Pattern**:
   - Different processing logic for request types
   - Create RequestProcessor interface

**After Refactoring:**
```python
def handle_request(request: Request) -> Response:
    \"\"\"Process incoming request and return response.\"\"\"
    try:
        data = parse_request(request)
        validate_request(data)
        result = process_request(data)
        return build_response(result)
    except RequestError as e:
        return handle_error(e)
```

This reduces complexity from 15 to 4 and makes each piece testable.

Should I create the extracted functions?"
```

### Test Generation

```
You: "Generate tests for the UserService class"

Bot: "Analyzing UserService methods...

**Test Suite Generated:**

```python
import pytest
from unittest.mock import Mock, patch
from myapp.services import UserService

class TestUserService:
    @pytest.fixture
    def service(self):
        \"\"\"Create UserService instance for testing.\"\"\"
        return UserService(db=Mock())

    def test_create_user_success(self, service):
        \"\"\"Should create user with valid data.\"\"\"
        user_data = {
            "email": "test@example.com",
            "name": "Test User"
        }

        result = service.create_user(user_data)

        assert result.email == "test@example.com"
        assert result.name == "Test User"
        service.db.save.assert_called_once()

    def test_create_user_duplicate_email(self, service):
        \"\"\"Should raise error for duplicate email.\"\"\"
        service.db.find_by_email.return_value = Mock()

        with pytest.raises(DuplicateEmailError):
            service.create_user({"email": "exists@example.com"})

    def test_create_user_invalid_email(self, service):
        \"\"\"Should raise error for invalid email format.\"\"\"
        with pytest.raises(ValidationError):
            service.create_user({"email": "invalid-email"})

    @pytest.mark.parametrize("email", [
        "",
        "no-at-sign",
        "@no-local",
        "no-domain@",
    ])
    def test_create_user_invalid_emails(self, service, email):
        \"\"\"Should reject various invalid email formats.\"\"\"
        with pytest.raises(ValidationError):
            service.create_user({"email": email})
```

**Coverage:** 8 tests covering:
- ✅ Happy path
- ✅ Duplicate detection
- ✅ Validation errors
- ✅ Edge cases

Should I also generate integration tests?"
```

## Use Cases

### Daily Code Review

Use for pull request reviews:

```bash
# Review changes in PR
cd /path/to/repo
teotl chat --agent coding-assistant

> "Review the changes in PR #234"
```

### Debugging Session

Get help with errors:

```bash
teotl chat --agent coding-assistant

> "I'm getting this error: [paste stack trace]"
> "Show me where this function is called"
> "Why would this variable be None here?"
```

### Refactoring Project

Improve code quality:

```bash
teotl chat --agent coding-assistant

> "Find functions longer than 50 lines in src/"
> "Show me duplicated code in the services module"
> "Suggest refactoring for high complexity functions"
```

### Test Coverage

Increase test coverage:

```bash
teotl chat --agent coding-assistant

> "What files in src/ don't have tests?"
> "Generate tests for UserController"
> "Find edge cases I haven't tested"
```

## Customization Guide

### Code Style Preferences

Edit `USER.md` to specify your preferences:

```markdown
## Code Style

**Formatting:**
- Line length: 88 characters (Black)
- Indentation: 4 spaces
- Quotes: Double quotes for strings

**Naming Conventions:**
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE
- Private methods: _leading_underscore

**Testing:**
- Framework: pytest
- Coverage target: >80%
- Test file naming: test_*.py
```

### Project Context

Add your project details to `USER.md`:

```markdown
## Current Projects

**Project: E-commerce API**
- Language: Python 3.11
- Framework: FastAPI
- Database: PostgreSQL
- Testing: pytest, httpx
- CI/CD: GitHub Actions
```

### Adding Skills

Enable additional capabilities:

```bash
# Basic (filesystem + git)
teotl chat --agent coding-assistant --skills filesystem,git

# With database access
teotl chat --agent coding-assistant --skills filesystem,git,database

# With web search (for docs lookup)
teotl chat --agent coding-assistant --skills filesystem,git,web
```

## Best Practices

### 1. Provide Context

Help the assistant understand your code:

```
❌ "Fix this"
✅ "This function should sort users by name, but it's returning unsorted results"

❌ "Review my code"
✅ "Review UserService.create_user() for security issues and edge cases"
```

### 2. Iterate on Suggestions

Refine the assistant's output:

```
You: "Generate tests for calculate_total"
Bot: [generates 3 basic tests]

You: "Add tests for edge cases: negative numbers, zero, very large numbers"
Bot: [adds 4 more edge case tests]
```

### 3. Ask for Explanations

Learn from the suggestions:

```
You: "Why did you suggest using a context manager here?"
Bot: "A context manager ensures the file is properly closed even if an exception
      occurs. It's more reliable than manual try/finally blocks..."
```

### 4. Verify Changes

Always review generated code:

- Run tests before and after
- Check for unintended side effects
- Verify style matches your conventions
- Test edge cases manually

## Automation with Missions

Set up recurring code quality tasks:

```python
from forge.primitives.mission import Mission, MissionInterval

# Daily code quality check
mission = Mission(
    description="Daily code quality scan",
    interval=MissionInterval.DAILY,
    instructions="""
    1. Run linter on changed files
    2. Check test coverage
    3. Find TODO/FIXME comments
    4. Report any issues
    """,
    tools=["filesystem", "git", "bash"],
)
```

## Skills Reference

### filesystem
- Read source files
- Search for code patterns
- Analyze directory structure
- Find files by type

### git
- Review commits and diffs
- Analyze PR changes
- Check git history
- Find code authors

### web
- Look up documentation
- Search Stack Overflow
- Find library examples
- Check API references

### bash
- Run linters (pylint, eslint)
- Execute tests
- Run build scripts
- Check dependencies

See `SKILLS.md` for detailed capabilities.

## Troubleshooting

### "Cannot access repository"

**Fix:** Ensure you're in a git repository:
```bash
cd /path/to/your/project
teotl chat --agent coding-assistant
```

### "File not found"

**Fix:** Provide full paths or ensure working directory is correct

### "Suggestions don't match my style"

**Fix:** Update `USER.md` with your specific style preferences

### "Assistant changes too much code"

**Fix:** Be more specific in requests:
```
❌ "Improve this file"
✅ "Add type hints to calculate_total function only"
```

## Security & Privacy

### Code Access

**Assistant CAN:**
- ✅ Read source code files
- ✅ Analyze code structure
- ✅ Search for patterns
- ✅ Suggest changes

**Assistant CANNOT:**
- ❌ Modify files without approval
- ❌ Commit changes without approval
- ❌ Push to remote without approval
- ❌ Delete files without approval

### Privacy

From `security.yaml`:

- Code never sent to external services (except approved APIs)
- Credentials and secrets ignored
- Git history stays local
- All changes require confirmation

## Integration Examples

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
teotl chat --agent coding-assistant --skills git,filesystem << EOF
Review staged changes for:
1. Syntax errors
2. Common bugs
3. Style violations
4. Missing tests
EOF
```

### CI/CD Pipeline

```yaml
# .github/workflows/code-review.yml
name: AI Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: AI Review
        run: |
          forge chat --agent coding-assistant << EOF
          Review PR changes and comment on potential issues
          EOF
```

## Template Files

```
coding-assistant/
├── README.md           # This file
├── PERSONALITY.md      # Assistant personality
├── USER.md             # Your profile and preferences
├── INSTRUCTIONS.md     # Operating procedures
├── SKILLS.md           # Available capabilities
└── security.yaml       # Security policy
```

## Getting Help

- **Commands:** `/help` in chat mode
- **Skills:** `/skills` to list available capabilities
- **Docs:** See other template files for details

---

**Start pair programming with AI:**

```bash
teotl chat --agent coding-assistant --skills filesystem,git,web
```

*Write better code, faster.*