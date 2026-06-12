# User Profile - Coding Assistant

## About Me

**Name:** [Your Name]
**Role:** [Software Engineer / Full Stack Developer / etc.]
**Experience:** [Junior / Mid-level / Senior]
**Team Size:** [Solo / 3-5 / 10+]

**Primary Focus:**
- Backend development
- API design
- Database optimization
- [Add your specialties]

## Programming Languages & Frameworks

### Primary Languages
**Python** (Expert)
- Frameworks: FastAPI, Django, Flask
- Testing: pytest, unittest
- Tools: Black, mypy, pylint

**JavaScript/TypeScript** (Proficient)
- Frontend: React, Vue.js
- Backend: Node.js, Express
- Testing: Jest, Vitest

**[Add your languages]**
- Frameworks:
- Testing:
- Tools:

### Secondary Languages
**SQL** - PostgreSQL, MySQL
**Bash** - Shell scripting
**[Other languages]**

## Code Style Preferences

### Formatting

**Python:**
- Formatter: Black (88 character line length)
- Import sorting: isort
- Type checking: mypy (strict mode)
- Linting: pylint, flake8

**JavaScript/TypeScript:**
- Formatter: Prettier
- Linting: ESLint (Airbnb config)
- Type checking: TypeScript strict mode

**General:**
- Indentation: 4 spaces (Python), 2 spaces (JS/TS)
- Line length: 88 (Python), 100 (JS/TS)
- Trailing commas: Always
- Semicolons: Required (JS)

### Naming Conventions

**Python:**
```python
# Classes
class UserService:

# Functions/Methods
def calculate_total():

# Constants
MAX_RETRY_COUNT = 3

# Private
def _internal_helper():
```

**JavaScript/TypeScript:**
```javascript
// Classes
class UserService

// Functions
function calculateTotal()

// Constants
const MAX_RETRY_COUNT = 3

// Private (TypeScript)
private _internalHelper()
```

**Database:**
- Tables: snake_case (plural) → `user_accounts`
- Columns: snake_case → `created_at`
- Indexes: `idx_table_column`

### Documentation Standards

**Functions/Methods:**
```python
def process_payment(amount: Decimal, user_id: int) -> PaymentResult:
    """Process payment for user.

    Args:
        amount: Payment amount in USD (must be positive)
        user_id: ID of user making payment

    Returns:
        PaymentResult with transaction ID and status

    Raises:
        ValueError: If amount is invalid
        PaymentError: If payment processing fails
    """
```

**Classes:**
```python
class UserService:
    """Service for managing user accounts.

    Handles user creation, updates, authentication, and
    account lifecycle operations.

    Attributes:
        db: Database connection
        cache: Redis cache instance
    """
```

**Inline Comments:**
- Explain "why", not "what"
- Complex logic only
- TODO/FIXME/NOTE when appropriate

## Testing Preferences

### Testing Framework
**Python:** pytest
**JavaScript:** Jest

### Test Structure

**File naming:**
- Python: `test_module_name.py`
- JavaScript: `module-name.test.ts`

**Test naming:**
```python
def test_create_user_with_valid_data_succeeds():
    """Should create user when data is valid."""
    # Arrange, Act, Assert pattern
```

### Coverage Goals
- **Target:** 80% line coverage minimum
- **Critical code:** 100% branch coverage
- **Always test:**
  - Public API methods
  - Business logic
  - Error conditions
  - Edge cases (null, empty, boundary values)

### Test Types

**Unit Tests:**
- Fast (<10ms per test)
- Isolated (mocked dependencies)
- One assertion per test (when possible)

**Integration Tests:**
- Test database queries
- Test API endpoints
- Test external service integration

**Skip These:**
- Don't test framework code
- Don't test simple getters/setters
- Don't test generated code

## Current Projects

### Project 1: E-commerce API

**Tech Stack:**
- Language: Python 3.11
- Framework: FastAPI
- Database: PostgreSQL 15
- Cache: Redis
- ORM: SQLAlchemy 2.0

**Code Organization:**
```
src/
├── api/          # API endpoints
├── services/     # Business logic
├── models/       # Database models
├── schemas/      # Pydantic schemas
└── core/         # Config, dependencies
```

**Key Conventions:**
- Dependency injection for services
- Pydantic for validation
- Async/await throughout
- Repository pattern for data access

**Current Focus:**
- Adding payment processing
- Implementing order workflow
- Optimizing database queries

### Project 2: Admin Dashboard

**Tech Stack:**
- Language: TypeScript 5.2
- Framework: React 18, Vite
- State: Redux Toolkit
- UI: Material-UI (MUI)

**Code Organization:**
```
src/
├── components/   # React components
├── features/     # Redux slices
├── services/     # API clients
├── hooks/        # Custom React hooks
└── utils/        # Helpers
```

**Key Conventions:**
- Functional components only
- Custom hooks for logic
- Redux for global state
- React Query for server state

## Development Environment

### Editor
**Primary:** VS Code
**Plugins:**
- Pylance (Python)
- ESLint
- Prettier
- GitLens
- Error Lens

### Version Control
**Git workflow:**
- Branch naming: `feature/description`, `bugfix/description`
- Commit format: `type(scope): message`
  - Example: `feat(api): add user authentication`
- PR requirements: Tests pass, coverage >80%, review approved

### Tools
```bash
# Python
poetry          # Dependency management
black           # Code formatting
mypy            # Type checking
pytest          # Testing

# JavaScript
npm/yarn        # Package management
prettier        # Code formatting
eslint          # Linting
jest            # Testing

# Database
postgresql      # Primary database
redis           # Caching
```

## Code Review Preferences

### What I Want Reviewed

**Always flag:**
- Security vulnerabilities
- Potential bugs and logic errors
- Performance issues
- Poor error handling
- Missing tests

**Suggest improvements:**
- Code duplication
- Complex functions (>50 lines)
- Unclear naming
- Missing documentation
- Architectural issues

**Low priority:**
- Style issues (handled by formatters)
- Alternative approaches (unless significantly better)
- Micro-optimizations

### Review Style I Prefer

**Format:**
```
**Issue Type** (Location)
Description of the issue
Impact: Why this matters

Suggestion:
[Code example or explanation]

Alternative:
[Other approach if applicable]
```

**Tone:**
- Constructive, not critical
- Explain the "why"
- Provide examples
- Offer alternatives

## Debugging Approach

### My Process

1. **Reproduce** - Verify the bug consistently occurs
2. **Isolate** - Narrow down to smallest failing code
3. **Understand** - Read code carefully, trace execution
4. **Hypothesize** - Form theory about root cause
5. **Test** - Verify hypothesis with print/debugger
6. **Fix** - Apply minimal change to fix root cause
7. **Verify** - Ensure fix works and doesn't break other things
8. **Test** - Add test case to prevent regression

### When I Need Help

**Provide:**
- Stack trace (full output)
- Steps to reproduce
- Expected vs actual behavior
- Relevant code snippets
- What I've already tried

**Help me:**
- Understand root cause
- Find where error originates
- Identify edge cases
- Suggest fix approaches

## Architecture Preferences

### Design Patterns I Use

**Backend:**
- **Repository Pattern** - Data access abstraction
- **Dependency Injection** - Loose coupling
- **Service Layer** - Business logic separation
- **DTO/Schema** - Data validation and transformation

**Frontend:**
- **Container/Presenter** - Logic vs UI separation
- **Custom Hooks** - Reusable logic
- **Context** - Global state (sparingly)
- **Composition** - Build complex UIs from simple components

### Principles I Follow

**SOLID:**
- Single Responsibility
- Open/Closed
- Liskov Substitution
- Interface Segregation
- Dependency Inversion

**Others:**
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Separation of Concerns

### When to Use Patterns

**Use when:**
- Pattern solves actual problem
- Benefits outweigh complexity
- Team understands pattern

**Avoid when:**
- Adds unnecessary complexity
- Simple solution works fine
- Pattern doesn't fit problem

## Learning Style

### How I Learn Best

**For new concepts:**
- Show me working examples
- Explain with analogies
- Provide official documentation links

**For debugging:**
- Walk through the logic step-by-step
- Show me where error occurs
- Explain root cause clearly

**For refactoring:**
- Show before/after comparison
- Explain why new version is better
- Quantify improvements (complexity, testability)

### Documentation I Reference

**Python:**
- Official Python docs
- FastAPI documentation
- SQLAlchemy docs
- pytest documentation

**JavaScript:**
- MDN Web Docs
- React documentation
- TypeScript handbook

**General:**
- Stack Overflow
- GitHub repositories
- Technical blogs

## Communication Preferences

### What I Appreciate

**In reviews:**
- Start with positive feedback
- Be specific about issues
- Provide code examples
- Explain reasoning

**In debugging:**
- Show me the root cause first
- Then explain the fix
- Suggest prevention strategies

**In refactoring:**
- Acknowledge current code works
- Explain the improvement
- Show concrete benefits

### What Frustrates Me

**Avoid:**
- Vague feedback ("this is wrong")
- Rewriting everything without explanation
- Suggesting patterns I don't need
- Ignoring project conventions
- Assuming I know advanced concepts

## Continuous Improvement

### My Goals

**Short-term:**
- Improve error handling in current project
- Increase test coverage to 85%
- Learn advanced SQL optimization

**Long-term:**
- Master system design patterns
- Improve code review skills
- Learn cloud architecture (AWS/GCP)

### Track for Me

**Code metrics:**
- Functions >50 lines (goal: reduce)
- Duplicated code (goal: eliminate)
- Test coverage (goal: >80%)
- Cyclomatic complexity (goal: <10)

**Patterns:**
- Common bugs I make
- Frequently duplicated code
- Areas needing more tests

---

*This profile helps me provide personalized coding assistance that matches your style, projects, and goals.*
