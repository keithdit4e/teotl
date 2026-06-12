# Contributing to Teotl

Thank you for your interest in contributing to Teotl! We welcome contributions from the community to help make autonomous agents more accessible, reliable, and cost-efficient.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Community](#community)

---

## Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the community
- Show empathy towards other contributors

We're building a welcoming community. Harassment, trolling, or discriminatory behavior will not be tolerated.

---

## Getting Started

### Prerequisites

- **Python 3.11 or higher**
- **Git**
- **API keys** for Anthropic Claude or OpenAI (for testing)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/teotl
cd teotl

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests to verify installation
pytest tests/ -v
```

---

## Development Setup

### Editable Installation

Install Teotl in editable mode so your changes are immediately reflected:

```bash
pip install -e ".[dev]"
```

This installs:
- Core dependencies (anthropic, openai, rich, click, etc.)
- Development tools (pytest, ruff, mypy, etc.)
- Testing utilities

### Environment Variables

Set up your API keys for testing:

```bash
# Anthropic Claude (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI (optional)
export OPENAI_API_KEY="sk-..."
```

### Directory Structure

```
teotl/
├── teotl/               # Main package
│   ├── core/           # Core agent, provider, types
│   ├── primitives/     # Skills, memory, missions, guardrails
│   ├── cli/            # CLI commands
│   ├── ui/             # User interface components
│   └── daemon/         # Daemon services
├── tests/              # Test suite (553 tests)
├── docs/               # Documentation
├── examples/           # Example agents and demos
└── pyproject.toml      # Package configuration
```

---

## How to Contribute

### Types of Contributions

We welcome:

1. **Bug fixes** - Fix issues, improve error handling
2. **New features** - Skills, integrations, improvements
3. **Documentation** - Tutorials, guides, API docs
4. **Examples** - Demo agents, use cases
5. **Tests** - Increase coverage, edge cases
6. **Performance** - Optimize cost, speed, quality

### Areas That Need Help

Check our [GitHub Issues](https://github.com/yourusername/teotl/issues) for:
- Issues labeled `good first issue` (great for newcomers)
- Issues labeled `help wanted` (community contributions welcome)
- TODO.md for documented future enhancements

---

## Development Workflow

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions/fixes
- `refactor/` - Code refactoring

### 2. Make Changes

- Write clean, well-documented code
- Follow existing patterns and conventions
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run full test suite
pytest tests/ -v

# Run specific tests
pytest tests/core/test_agent.py -v

# Check coverage
pytest tests/ --cov=teotl --cov-report=html
open htmlcov/index.html

# Quick test (stop on first failure)
pytest tests/ -x
```

### 4. Format and Lint

```bash
# Format code with ruff
ruff format .

# Check for lint issues
ruff check .

# Type checking (optional)
mypy teotl/
```

### 5. Commit Changes

Use semantic commit messages:

```bash
git add .
git commit -m "feat: add new GitHub skill for issue management"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

---

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length:** 100 characters (not 80)
- **Formatter:** ruff (automatically formats code)
- **Import order:** Standard library, third-party, local (ruff handles this)
- **Type hints:** Use type hints for public APIs
- **Docstrings:** Google-style docstrings for public functions

### Formatting with Ruff

```bash
# Format all code
ruff format .

# Check specific file
ruff format teotl/core/agent.py

# Check for issues without fixing
ruff check .
```

### Example Code Style

```python
"""Module docstring explaining purpose."""

from __future__ import annotations

from typing import TYPE_CHECKING

from teotl.core.types import Message

if TYPE_CHECKING:
    from teotl.core.provider import Provider


class Agent:
    """An autonomous AI agent.
    
    Args:
        provider: The LLM provider to use
        instructions: System instructions for the agent
        policy: Guardrail policy level (minimal/standard/strict)
    
    Example:
        ```python
        agent = Agent(
            provider=AnthropicProvider(),
            instructions="You are a helpful assistant.",
            policy="standard"
        )
        response = await agent.run("Hello!")
        ```
    """
    
    def __init__(
        self,
        provider: Provider,
        instructions: str,
        policy: str = "standard",
    ) -> None:
        self.provider = provider
        self.instructions = instructions
        self.policy = policy
```

---

## Testing

### Test Requirements

- **All new features must include tests**
- **Bug fixes should include regression tests**
- **Maintain >99% test pass rate** (currently 553/556 = 99.5%)
- **Aim for high code coverage** (>85%)

### Running Tests

```bash
# Full test suite
pytest tests/ -v

# Specific test file
pytest tests/core/test_agent.py -v

# Specific test function
pytest tests/core/test_agent.py::test_agent_initialization -v

# With coverage
pytest tests/ --cov=teotl --cov-report=html

# Skip slow tests
pytest tests/ -m "not slow"

# Run only unit tests (not integration)
pytest tests/ -k "not integration"
```

### Writing Tests

```python
import pytest
from teotl.core.agent import Agent


@pytest.mark.asyncio
async def test_agent_basic_response():
    """Test agent can generate basic responses."""
    agent = Agent(
        provider=MockProvider(),
        instructions="You are a test assistant.",
    )
    
    response = await agent.run("Hello!")
    
    assert response.text
    assert len(response.text) > 0


def test_agent_initialization_without_provider():
    """Test agent initialization fails without provider."""
    with pytest.raises(TypeError):
        Agent(instructions="Test")
```

### Test Organization

- **Unit tests:** Test individual components in isolation
- **Integration tests:** Test component interactions
- **End-to-end tests:** Test complete workflows

Place tests in `tests/` matching the source structure:
- `teotl/core/agent.py` → `tests/core/test_agent.py`
- `teotl/primitives/skills/filesystem.py` → `tests/primitives/skills/test_filesystem.py`

---

## Pull Request Process

### Before Submitting

1. **Tests pass:** `pytest tests/ -v` shows all tests passing
2. **Code formatted:** `ruff format .` has been run
3. **No lint errors:** `ruff check .` shows no issues
4. **Documentation updated:** If API changed, update docs
5. **CHANGELOG entry:** Add entry to CHANGELOG.md (if applicable)

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] All tests pass locally
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

### Review Process

1. **Automated checks:** CI runs tests, linting, coverage
2. **Maintainer review:** Code review by maintainers
3. **Feedback addressed:** Make requested changes
4. **Approval:** PR approved by maintainer
5. **Merge:** Merged to main branch

### After Merge

- Your contribution will be included in the next release
- You'll be added to CONTRIBUTORS.md
- Thank you! 🎉

---

## Reporting Issues

### Bug Reports

Use the bug report template and include:

1. **Description:** Clear description of the bug
2. **Steps to reproduce:** Minimal code to reproduce issue
3. **Expected behavior:** What should happen
4. **Actual behavior:** What actually happens
5. **Environment:**
   - Python version
   - Teotl version
   - OS (macOS/Linux/Windows)
6. **Error messages:** Full stack traces
7. **Additional context:** Screenshots, logs, etc.

### Feature Requests

Use the feature request template and include:

1. **Problem:** What problem does this solve?
2. **Solution:** Proposed solution
3. **Alternatives:** Alternative solutions considered
4. **Use case:** Example use case
5. **Willingness to contribute:** Will you implement this?

### Security Issues

**Do not open public issues for security vulnerabilities.**

Email security concerns to: security@teotl.dev (or your security contact)

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

---

## Community

### Get Help

- **GitHub Discussions:** [Ask questions, share ideas](https://github.com/yourusername/teotl/discussions)
- **GitHub Issues:** [Report bugs, request features](https://github.com/yourusername/teotl/issues)
- **Twitter:** [@yourusername](https://twitter.com/yourusername)

### Stay Updated

- **Watch repository** for updates
- **Star the project** to show support
- **Follow releases** for new versions

---

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README (for significant contributions)

Thank you for contributing to Teotl! Together we're making autonomous agents more accessible and reliable. 🚀

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
