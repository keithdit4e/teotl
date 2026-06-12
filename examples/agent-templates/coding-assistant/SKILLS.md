# Coding Assistant Skills

These are the capabilities available to help you write better code.

## Core Skills

### filesystem

**What it does:**
- Read source code files in any programming language
- Search for code patterns using glob patterns
- Analyze project directory structure
- Write new files or modify existing ones
- Create project scaffolding

**When to use:**
- Reading code for review
- Finding files by name or extension
- Analyzing codebase structure
- Writing refactored code
- Creating new modules

**Limitations:**
- Subject to security policy (see security.yaml)
- Cannot access system files
- Requires confirmation for destructive operations

**Example tasks:**
```
"Read UserService.java"
"Find all Python files in src/"
"Show me the project structure"
"Create a new test file for UserController"
```

### git

**What it does:**
- View commit history and diffs
- Analyze pull request changes
- Find when code was introduced
- Check file modification history
- Review branch comparisons

**When to use:**
- Reviewing PR changes
- Understanding code evolution
- Finding code authors
- Checking recent modifications
- Analyzing commit patterns

**Limitations:**
- Read-only access (cannot commit/push)
- Must be in a git repository
- Requires git to be installed

**Example tasks:**
```
"Review changes in PR #234"
"Show me recent commits to auth.py"
"Who last modified this function?"
"What changed in the last commit?"
```

### web

**What it does:**
- Search for programming documentation
- Look up API references
- Find usage examples on Stack Overflow
- Check library versions and compatibility
- Search for error messages and solutions

**When to use:**
- Need official documentation
- Looking for usage examples
- Understanding error messages
- Checking best practices
- Finding library alternatives

**Limitations:**
- General web search, not code-specific
- May return outdated information
- Requires internet connection

**Example tasks:**
```
"Look up FastAPI authentication documentation"
"Find examples of React useEffect hook"
"Search for 'pandas merge vs join' differences"
"Check latest version of TypeScript"
```

### bash

**What it does:**
- Run linters (pylint, eslint, flake8)
- Execute test suites (pytest, jest, cargo test)
- Build projects (npm run build, mvn compile)
- Run code analysis tools (mypy, tsc, cargo clippy)
- Execute scripts

**When to use:**
- Running tests
- Checking code style
- Building project
- Running type checkers
- Executing custom scripts

**Limitations:**
- Subject to security policy
- Dangerous commands blocked
- Requires confirmation for some operations

**Example tasks:**
```
"Run pytest on test_user.py"
"Execute eslint on src/ directory"
"Build the project with npm run build"
"Run mypy type checking"
```

## Optional Enhancement Skills

These skills can be added for additional functionality:

### database (optional)

**What it does:**
- Connect to databases (PostgreSQL, MySQL, SQLite)
- Execute queries for testing
- Analyze query performance
- Inspect database schema

**When to use:**
- Testing database queries
- Analyzing query performance
- Checking database state
- Debugging ORM issues

**How to enable:**
```bash
teotl chat --agent coding-assistant --skills filesystem,git,web,database
```

### docker (optional)

**What it does:**
- Build Docker images
- Run containers for testing
- Manage development environments
- Check container logs

**When to use:**
- Testing in containers
- Building Docker images
- Debugging containerized apps
- Managing dev environments

**How to enable:**
```bash
teotl chat --agent coding-assistant --skills filesystem,git,web,docker
```

## Skill Combinations

### Standard Development (Recommended)
```bash
teotl chat --agent coding-assistant --skills filesystem,git,web
```
**Best for:** Code review, refactoring, documentation, debugging

### Testing & Quality
```bash
teotl chat --agent coding-assistant --skills filesystem,git,bash
```
**Best for:** Running tests, linters, type checkers, builds

### Full Stack Development
```bash
teotl chat --agent coding-assistant --skills filesystem,git,web,bash,database
```
**Best for:** Complete development workflow with database access

### DevOps & Deployment
```bash
teotl chat --agent coding-assistant --skills filesystem,git,bash,docker
```
**Best for:** Container management, deployment, infrastructure

## Skill Usage Guidelines

### Code Review Workflow

1. **Use git skill** to see what changed
2. **Use filesystem skill** to read modified files
3. **Use web skill** if need to check documentation
4. Analyze code and provide feedback
5. **Use filesystem skill** to write fixes (if requested)

### Debugging Workflow

1. **Use filesystem skill** to read error-causing code
2. **Use git skill** to check recent changes
3. **Use bash skill** to run tests and reproduce
4. **Use web skill** to research error messages
5. Identify root cause and suggest fixes

### Refactoring Workflow

1. **Use filesystem skill** to analyze code structure
2. **Use bash skill** to run tests (ensure they pass)
3. Plan refactoring steps
4. **Use filesystem skill** to apply changes
5. **Use bash skill** to verify tests still pass

### Test Generation Workflow

1. **Use filesystem skill** to read code to test
2. **Use git skill** to check for existing tests
3. Generate comprehensive test cases
4. **Use filesystem skill** to write test file
5. **Use bash skill** to run tests and verify

## Language-Specific Tools

### Python

**Available commands:**
```bash
# Linting
pylint src/
flake8 src/
black --check src/

# Type checking
mypy src/

# Testing
pytest tests/
pytest --cov=src tests/

# Formatting
black src/
isort src/
```

### JavaScript/TypeScript

**Available commands:**
```bash
# Linting
eslint src/
eslint --fix src/

# Type checking
tsc --noEmit

# Testing
npm test
npm run test:coverage

# Formatting
prettier --check src/
prettier --write src/
```

### Java

**Available commands:**
```bash
# Compilation
mvn compile
gradle build

# Testing
mvn test
gradle test

# Code quality
mvn pmd:check
mvn checkstyle:check
```

### Rust

**Available commands:**
```bash
# Linting
cargo clippy

# Type checking
cargo check

# Testing
cargo test

# Formatting
cargo fmt --check
cargo fmt
```

## Security Considerations

### Filesystem Access

**CAN access:**
- Project source directories
- Test directories
- Configuration files
- Documentation files

**CANNOT access:**
- System directories (/etc, /usr, /bin)
- User credentials (~/.ssh, ~/.aws)
- Environment secrets
- Other projects outside current directory

### Command Execution

**ALLOWED commands:**
- Linters, formatters, type checkers
- Test runners
- Build tools
- Code analysis tools
- git commands (read-only)

**BLOCKED commands:**
- File deletion (rm, del)
- System modification (chmod, chown)
- Network tools (curl, wget) - use web skill
- Package installation (pip, npm) - requires confirmation
- Privilege escalation (sudo, su)

### Git Operations

**READ operations allowed:**
- View commits, diffs, history
- Check branch status
- Compare branches
- View file history

**WRITE operations require confirmation:**
- Creating commits
- Pushing to remote
- Creating branches
- Merging branches

## Troubleshooting

### "Permission denied"

**Cause:** Trying to access restricted files or directories

**Fix:**
- Ensure you're in project directory
- Check security.yaml for allowed paths
- Use relative paths within project

### "Command not found"

**Cause:** Tool not installed on system

**Fix:**
```bash
# Python
pip install pylint pytest mypy

# JavaScript
npm install -g eslint prettier

# Check if tool is available
which pylint
which eslint
```

### "Tests failing after refactoring"

**Cause:** Code change broke functionality

**Fix:**
1. Use git to see exactly what changed
2. Run tests individually to find failure
3. Review failed test expectations
4. Fix code or update test

### "Slow code analysis"

**Cause:** Large codebase or complex analysis

**Fix:**
- Target specific files/directories
- Use git to analyze only changed files
- Run analysis on subset first

## Best Practices

### 1. Start with Context

Before reviewing or refactoring:
```
1. Use git to see recent changes
2. Use filesystem to understand structure
3. Check existing tests
4. Read documentation
```

### 2. Test After Changes

Always verify changes work:
```
1. Use bash to run tests
2. Check test coverage
3. Run linters
4. Verify build succeeds
```

### 3. Use Right Tool for Job

**For file operations:** filesystem skill (NOT bash cat/grep)
**For git operations:** git skill (NOT bash git commands)
**For web search:** web skill (NOT bash curl)
**For running tools:** bash skill

### 4. Incremental Changes

Make small, testable changes:
```
1. Change one thing
2. Run tests
3. Commit if successful
4. Move to next change
```

## Performance Tips

### Optimize File Reading

```
# Good - specific file
Read("src/services/user_service.py")

# Bad - read everything
Read all Python files
```

### Optimize Git Operations

```
# Good - specific changes
"Show changes in last commit"
"Diff main...feature-branch"

# Bad - entire history
"Show all commits"
```

### Optimize Web Search

```
# Good - specific query
"FastAPI async route handling"
"React useEffect dependency array"

# Bad - vague query
"Python web frameworks"
"JavaScript hooks"
```

---

*These skills provide comprehensive code assistance capabilities. Additional skills can be enabled based on specific development needs.*
