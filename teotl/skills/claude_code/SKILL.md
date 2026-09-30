---
name: claude_code
version: 1.0.0
description: "AI-powered coding assistant via Claude Code CLI for refactoring, features, bug fixes, and code reviews"
auth: none
triggers:
  - refactor
  - implement feature
  - fix bug
  - code review
  - write tests
  - update documentation
  - migrate code
  - coding task
  - software development
  - programming
---

# Claude Code - AI-Powered Coding Assistant

Use the Claude Code CLI to delegate complex coding tasks to a specialized AI coding assistant. Claude Code excels at refactoring, implementing features, fixing bugs, writing tests, and code reviews.

## When to Use Claude Code

**Use Claude Code for:**
- Complex refactoring (restructuring code, design patterns)
- Implementing new features with multiple files
- Fixing bugs requiring codebase understanding
- Writing comprehensive test suites
- Migrating code between frameworks/libraries
- Code reviews and quality improvements
- Documentation generation

**Don't use for:**
- Simple file operations (use filesystem skill)
- One-line code changes (do it directly)
- Git operations (use git skill)
- Non-coding tasks

## Core Operations

### Start Interactive Coding Session

```bash
# Start Claude Code in current directory
claude-code

# Start in specific directory
cd /path/to/project && claude-code
```

**Best practice**: Always start in the project root directory where relevant files are located.

### Execute Single Coding Task

```bash
# Refactor a specific component
claude-code "Refactor the authentication module to use JWT instead of sessions"

# Implement a feature
claude-code "Add email validation to the signup form with proper error messages"

# Fix a bug
claude-code "Fix the race condition in the payment processing flow"

# Write tests
claude-code "Write comprehensive unit tests for the UserService class"
```

**Task Description Guidelines:**
1. **Be specific**: Include file/module names if known
2. **State requirements**: Mention constraints, patterns, or standards
3. **Provide context**: Reference related code or documentation
4. **Set scope**: Define what should/shouldn't change

### Read-Only Code Review

```bash
# Review code quality
claude-code "Review the code in src/api/ and suggest improvements" --read-only

# Check security
claude-code "Audit the authentication code for security vulnerabilities" --read-only

# Analyze architecture
claude-code "Analyze the data layer architecture and suggest optimizations" --read-only
```

**Use `--read-only` when:**
- You want suggestions without changes
- Reviewing code before accepting changes
- Analyzing architecture/patterns
- Security audits

## Refactoring Tasks

### Extract Function/Class

```bash
# Extract reusable logic
claude-code "Extract the data validation logic in handlers.py into a separate validator class"

# Decompose large function
claude-code "Break down the process_order function into smaller, testable functions"

# Create abstraction
claude-code "Extract the database queries in UserController into a UserRepository class"
```

### Apply Design Patterns

```bash
# Implement pattern
claude-code "Refactor the notification system to use the Observer pattern"

# Add dependency injection
claude-code "Refactor services to use dependency injection instead of global instances"

# Implement strategy pattern
claude-code "Refactor payment processing to use Strategy pattern for different payment methods"
```

### Code Organization

```bash
# Reorganize modules
claude-code "Reorganize the utility functions into focused modules by functionality"

# Extract constants
claude-code "Extract all magic numbers and strings into a constants file"

# Improve naming
claude-code "Rename variables and functions in auth.py to follow Python naming conventions"
```

## Feature Implementation

### Add New Feature

```bash
# Complete feature with tests
claude-code "Implement user profile editing with validation, API endpoint, and tests"

# Multi-file feature
claude-code "Add dark mode support: update CSS, add toggle component, persist preference"

# Integration feature
claude-code "Implement Stripe payment integration with webhook handling and error recovery"
```

**Feature Specification Template:**
```bash
claude-code "Implement [FEATURE_NAME]:
- [Requirement 1]
- [Requirement 2]
- [Edge case to handle]
- Include tests
- Update documentation"
```

### Extend Existing Feature

```bash
# Add capabilities
claude-code "Add pagination to the user list API endpoint"

# Improve functionality
claude-code "Add file upload progress tracking to the upload component"

# Add validation
claude-code "Add input validation and error handling to the contact form"
```

## Bug Fixing

### Fix Specific Bug

```bash
# With error message
claude-code "Fix the TypeError: Cannot read property 'id' of undefined in checkout.js line 45"

# With description
claude-code "Fix the bug where users can't log in after password reset"

# With logs
claude-code "Fix the 500 error in /api/orders endpoint. Error log:
[ERROR] Division by zero in calculate_total
File: orders.py, Line: 156"
```

**Bug Report Best Practice:**
1. Include error message/stack trace
2. Mention reproduction steps if known
3. Note affected files/lines
4. Describe expected vs actual behavior

### Fix Race Conditions

```bash
# Concurrency issues
claude-code "Fix the race condition when multiple users update the same document"

# Async bugs
claude-code "Fix the promise chain in fetchUserData that causes intermittent failures"
```

### Fix Memory Leaks

```bash
# Memory issues
claude-code "Fix the memory leak in the WebSocket connection manager"

# Resource cleanup
claude-code "Fix improper cleanup of database connections in the API handlers"
```

## Testing

### Write Unit Tests

```bash
# Test specific module
claude-code "Write unit tests for the EmailValidator class with edge cases"

# Test coverage
claude-code "Add tests for all public methods in src/services/PaymentService.ts"

# Test-driven development
claude-code "Write tests for the UserRepository class before implementation"
```

### Write Integration Tests

```bash
# API testing
claude-code "Write integration tests for the /api/auth endpoints"

# Database testing
claude-code "Write tests for the database migration scripts"

# End-to-end tests
claude-code "Write E2E tests for the checkout flow from cart to confirmation"
```

### Test Refactoring

```bash
# Improve tests
claude-code "Refactor tests in test_api.py to reduce duplication and improve readability"

# Add test utilities
claude-code "Create test fixtures and helpers for database tests"
```

## Code Migration

### Framework Migration

```bash
# Migrate between frameworks
claude-code "Migrate the authentication routes from Express to Fastify"

# Update dependencies
claude-code "Migrate from Vue 2 to Vue 3 composition API"

# Language migration
claude-code "Convert the validation module from JavaScript to TypeScript"
```

### API Migration

```bash
# REST to GraphQL
claude-code "Convert the user management REST endpoints to GraphQL resolvers"

# API versioning
claude-code "Create v2 API endpoints with improved error handling and pagination"
```

## Documentation

### Generate Documentation

```bash
# Code documentation
claude-code "Add comprehensive docstrings to all functions in src/utils/"

# API documentation
claude-code "Generate OpenAPI/Swagger documentation for the REST API"

# README
claude-code "Create a detailed README for the authentication module"
```

### Update Documentation

```bash
# Sync docs with code
claude-code "Update the API documentation to match the current endpoint signatures"

# Add examples
claude-code "Add usage examples to the SDK documentation"
```

## Advanced Workflows

### Multi-Step Refactoring

```bash
# Complex refactoring with phases
claude-code "Refactor authentication system to microservices:
Phase 1: Extract auth logic into separate service
Phase 2: Implement JWT with refresh tokens
Phase 3: Add OAuth2 support
Phase 4: Update all client code
Phase 5: Write integration tests"
```

**Best Practice**: For multi-step tasks, Claude Code will create a plan and execute systematically.

### Code Review + Fix Cycle

```bash
# 1. Review first (read-only)
claude-code "Review src/api/handlers.py for security issues" --read-only

# 2. Review the suggestions

# 3. Apply fixes
claude-code "Fix the SQL injection vulnerability in the search handler"
```

### Implement Feature with Best Practices

```bash
claude-code "Implement password reset flow:
- Email verification
- Secure token generation
- Token expiration (1 hour)
- Rate limiting
- HTTPS only
- Include unit and integration tests
- Follow OWASP security guidelines
- Add logging for security events"
```

## Working with Claude Code Output

### Review Changes

After Claude Code completes:

```bash
# Check what changed
git status

# Review diff
git diff

# Check specific files
git diff src/auth/jwt.py
```

### Accept or Reject Changes

```bash
# Accept changes
git add .
git commit -m "Refactor: migrate auth to JWT"

# Reject changes (revert)
git checkout -- .

# Accept partial changes
git add -p  # Interactive staging
```

### Run Tests

```bash
# Always run tests after Claude Code changes
npm test
# or
pytest
# or
go test ./...
```

## Configuration and Preferences

### Project-Specific Instructions

Create `.claude/instructions.md` in your project:

```markdown
# Project Guidelines

## Code Style
- Use TypeScript strict mode
- Follow Airbnb style guide
- Max line length: 100 characters

## Testing Requirements
- 80% code coverage minimum
- Unit tests for all business logic
- Integration tests for API endpoints

## Security
- Never log sensitive data
- Validate all user input
- Use parameterized queries for DB

## Documentation
- JSDoc for all public functions
- OpenAPI specs for all endpoints
```

**Claude Code will automatically load and follow these instructions**.

### Skill-Specific Instructions

Create `.claude/skills/coding.md`:

```markdown
# Coding Agent Instructions

- Prefer composition over inheritance
- Use dependency injection
- Write self-documenting code
- Add comments only for complex logic
- Follow TDD when writing new features
```

## Common Workflows

### Feature Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/user-notifications

# 2. Implement with Claude Code
claude-code "Implement email and push notifications:
- NotificationService with email and push providers
- User notification preferences
- Template system for messages
- Queue system for async delivery
- Tests with 80% coverage"

# 3. Review changes
git diff

# 4. Run tests
npm test

# 5. Commit
git add .
git commit -m "feat: add notification system"

# 6. Push
git push -u origin feature/user-notifications
```

### Bug Fix Workflow

```bash
# 1. Create hotfix branch
git checkout -b hotfix/payment-validation

# 2. Fix with Claude Code
claude-code "Fix payment validation bug:
- Issue: Users can submit orders with $0 total
- File: src/api/orders.py, line 234
- Add validation for minimum order amount
- Add test to prevent regression"

# 3. Run tests
pytest tests/test_orders.py

# 4. Commit and deploy
git add .
git commit -m "fix: add minimum order amount validation"
```

### Code Review Workflow

```bash
# 1. Review PR changes (read-only)
git checkout pr/feature-branch
claude-code "Review all changes in this branch for:
- Code quality and style
- Security vulnerabilities
- Performance issues
- Missing tests
- Documentation gaps" --read-only

# 2. Review suggestions and provide feedback
```

### Refactoring Workflow

```bash
# 1. Create refactoring branch
git checkout -b refactor/auth-layer

# 2. Document current state
claude-code "Document the current authentication architecture" --read-only

# 3. Plan refactoring
claude-code "Create refactoring plan for auth:
- Identify components to extract
- Define new interfaces
- Plan migration strategy
- Estimate impact" --read-only

# 4. Execute refactoring
claude-code "Execute the refactoring plan:
[Copy plan from step 3]"

# 5. Verify tests pass
npm test

# 6. Commit incrementally
git add src/auth/
git commit -m "refactor: extract authentication service"
```

## Security Best Practices

### Code Security Review

```bash
# General security audit
claude-code "Security audit: Review all API endpoints for vulnerabilities" --read-only

# Specific security checks
claude-code "Check for SQL injection vulnerabilities in database queries" --read-only

claude-code "Review authentication code for session fixation and CSRF vulnerabilities" --read-only
```

### Secure Coding Practices

When asking Claude Code to implement features:

```bash
# ✅ Good - specific security requirements
claude-code "Implement file upload with:
- Max size 10MB
- Validate file type (images only)
- Scan for malware
- Sanitize filenames
- Store with random UUIDs
- Serve with content-type headers"

# ❌ Bad - no security considerations
claude-code "Add file upload to the form"
```

### Sensitive Data

**IMPORTANT**: Claude Code operates on your local files. Never:
- Commit secrets, API keys, or passwords
- Ask Claude Code to generate/store secrets in code
- Process files with sensitive customer data

Use environment variables:
```bash
# ✅ Good
claude-code "Update config to use environment variables for API keys"

# ❌ Bad
claude-code "Add my Stripe API key sk_live_xxx to config.py"
```

## Performance Optimization

### Profile-Guided Optimization

```bash
# 1. Profile first (if available)
python -m cProfile app.py > profile.txt

# 2. Ask Claude Code to optimize based on profile
claude-code "Optimize performance based on profile.txt:
- Focus on database_query function (40% of time)
- Reduce memory allocations in parse_request
- Cache expensive computations"
```

### Specific Optimizations

```bash
# Database optimization
claude-code "Optimize database queries in UserRepository:
- Add indexes for common queries
- Use select_related to reduce N+1 queries
- Batch bulk operations"

# Frontend optimization
claude-code "Optimize React component rendering:
- Add React.memo where appropriate
- Implement virtualization for long lists
- Lazy load heavy components"
```

## Integration with Planner-Worker Pattern

When Claude Code is used by a Worker agent in a Planner-Worker harness, it receives detailed execution plans:

### Worker Delegation Pattern

```python
# Worker agent detects coding task and uses Claude Code
# Example internal decision-making:

Step: "Refactor authentication to use JWT"
  ↓
Worker analyzes: This is a complex coding task
  ↓
Worker activates claude_code skill
  ↓
Worker executes: claude-code "Refactor authentication to use JWT..."
  ↓
Claude Code performs refactoring
  ↓
Worker verifies: Run tests, check git diff
  ↓
Worker reports success to Planner
```

### Handling Claude Code in Plans

If you're a Worker executing a plan with coding steps:

1. **Activate claude_code skill**: Skill system loads these instructions
2. **Delegate to Claude Code**: Use `claude-code` command with specific task
3. **Verify results**: Check git diff, run tests
4. **Report status**: Success/failure with details

## Troubleshooting

### Claude Code Not Available

```bash
# Check if Claude Code CLI is installed
which claude-code

# If not installed, inform user:
# "Claude Code CLI is not installed. Please install from:
#  https://github.com/anthropics/claude-code"
```

### Changes Not Applied

```bash
# Check if Claude Code completed successfully
echo $?  # Should be 0 for success

# If non-zero, check error message and retry with more specific instructions
```

### Tests Failing After Changes

```bash
# 1. Review what changed
git diff

# 2. Ask Claude Code to fix
claude-code "Fix the failing tests in test_auth.py:
[Paste test failure output]"

# 3. If still failing, revert and try different approach
git checkout -- .
claude-code "Implement [feature] with TDD approach:
- Write tests first
- Then implement functionality"
```

### Unexpected Behavior

```bash
# Review changes in detail
git diff --stat  # Summary
git diff src/    # Full diff for directory

# Revert specific files if needed
git checkout -- src/problematic_file.py

# Ask Claude Code to explain
claude-code "Explain the changes you made to src/auth/jwt.py" --read-only
```

## Cost Optimization

### Use Appropriate Model

Claude Code typically uses Haiku (cheap, fast) for execution and Sonnet (expensive, smart) for planning.

**Planner-Worker Pattern Savings**:
- Planner creates plan once: ~$0.10
- Worker executes plan 20 times: 20 × $0.005 = $0.10
- **Total: $0.20** vs $2.00 if Sonnet ran everything
- **90% cost savings**

### Scope Tasks Appropriately

```bash
# ✅ Good - specific scope
claude-code "Fix the TypeError in checkout.js line 45"

# ❌ Bad - too broad (expensive)
claude-code "Review and improve the entire application"
```

### Use Read-Only for Analysis

```bash
# ✅ Good - read-only analysis is cheaper
claude-code "Analyze the architecture and suggest improvements" --read-only

# Then apply specific improvements
claude-code "Implement the suggested repository pattern"
```

## Quick Reference

| Operation | Command | Use Case |
|-----------|---------|----------|
| Interactive session | `claude-code` | Complex multi-file changes |
| Single task | `claude-code "task"` | Specific coding task |
| Read-only review | `claude-code "review" --read-only` | Code review, analysis |
| Refactoring | `claude-code "refactor X to Y"` | Code restructuring |
| Feature | `claude-code "implement feature X"` | New functionality |
| Bug fix | `claude-code "fix bug in X"` | Fix specific issue |
| Tests | `claude-code "write tests for X"` | Test generation |
| Documentation | `claude-code "document X"` | Generate docs |

## Claude Code Commands & Features

Claude Code has powerful built-in commands and features that workers should leverage for optimal results.

### Context Management: `/clear`

**Use `/clear` to start fresh context when beginning a new feature or unrelated task.**

```bash
# Start Claude Code interactive session
claude-code

# After completing one feature, clear context before starting another
> /clear
```

**When to use `/clear`:**
- ✅ **Starting a new feature** - Prevents context pollution from previous feature
- ✅ **Switching domains** - Moving from authentication to payment processing
- ✅ **After major refactoring** - Start clean for next task
- ✅ **Context getting too large** - If responses slow down or become confused
- ✅ **Between unrelated tasks** - Email verification → Database migration

**When NOT to use `/clear`:**
- ❌ **Mid-feature** - Don't clear while implementing related changes
- ❌ **Debugging** - Keep context when iterating on bug fixes
- ❌ **Follow-up tasks** - If current task builds on previous work

**Example workflow:**
```bash
claude-code

# Feature 1: User authentication
> Implement JWT authentication
> Add token refresh endpoint
> Write authentication tests
✅ Feature complete

# Clear context before new feature
> /clear

# Feature 2: Email verification (unrelated)
> Implement email verification system
> Add verification endpoints
> Write verification tests
✅ Feature complete
```

### Plan Mode: Complex Task Planning

**Use plan mode for tasks that need breaking down into steps.**

Plan mode is automatically triggered by Claude Code for complex requests, or you can explicitly request it:

```bash
# Claude Code will enter plan mode automatically for complex tasks
claude-code "Migrate the authentication system from sessions to JWT tokens across the entire codebase"

# Within interactive session, describe complex task
> Refactor the entire data layer to use the repository pattern, update all services, and ensure all tests pass
```

**When Claude Code enters plan mode:**
1. Creates detailed step-by-step plan
2. Shows you the plan for review
3. Asks for approval before executing
4. Executes steps systematically
5. Tracks progress through each step

**When to expect/request plan mode:**
- ✅ **Multi-file refactoring** - Touching 5+ files
- ✅ **Architecture changes** - Implementing new patterns
- ✅ **Large features** - Multiple components needed
- ✅ **Complex migrations** - Framework upgrades, API changes
- ✅ **Cross-cutting concerns** - Adding logging, error handling everywhere

**Example plan mode workflow:**
```bash
claude-code "Migrate all API endpoints from REST to GraphQL"

# Claude Code responds:
I'll need to plan this complex migration. Here's my approach:

Plan: Migrate REST to GraphQL
1. Install and configure GraphQL server
2. Create GraphQL schema from REST endpoints
3. Implement resolvers for each endpoint
4. Update client code to use GraphQL
5. Add GraphQL tests
6. Update documentation

Proceed with execution? (yes/no): yes

# Claude Code executes each step systematically
✅ Step 1/6: Installed apollo-server-express...
✅ Step 2/6: Created schema.graphql with 15 types...
...
```

### Other Useful Commands

**Available in interactive Claude Code sessions:**

#### `/help`
```bash
> /help
# Shows all available commands and features
```

#### `/review`
```bash
> /review
# Reviews all changes made in current session
# Useful before committing
```

#### `/undo`
```bash
> /undo
# Undoes the last change
# Use if Claude Code made an incorrect modification
```

#### `/diff`
```bash
> /diff
# Shows diff of all changes in current session
# Useful for reviewing before /clear or exit
```

### Best Practice: Feature-Scoped Sessions

**Optimal workflow for workers using Claude Code:**

```bash
# Pattern: One Claude Code session per feature

# Feature: User Profile Editing
claude-code  # Start session

> Implement user profile edit functionality
> Add profile validation
> Write profile edit tests
> Update profile documentation

# Review all changes before committing
> /diff

# Exit and commit
> exit

git add .
git commit -m "feat: implement user profile editing"

# NEW FEATURE = NEW SESSION
claude-code  # Fresh session with /clear equivalent

> Implement password reset via email
...
```

### Advanced: Using .claude Directory

**Configure Claude Code behavior for your project:**

```bash
# Create project-specific instructions
mkdir -p .claude
cat > .claude/instructions.md << 'EOF'
# Project Guidelines for Claude Code

## Code Style
- Use TypeScript strict mode
- Follow Airbnb style guide
- Maximum line length: 100 characters

## Testing
- Write tests for all new features
- Maintain 80%+ coverage
- Use Jest for unit tests

## Architecture
- Use repository pattern for data access
- Services for business logic
- Controllers for HTTP handling

## Security
- Validate all user input
- Use parameterized queries
- Never log sensitive data
EOF

# Claude Code will automatically read and follow these instructions
claude-code "Implement user registration"
# ↑ Will follow your project guidelines automatically
```

### Command Quick Reference

| Command | When to Use | Example |
|---------|------------|---------|
| `/clear` | Start new feature | Before implementing unrelated feature |
| `/help` | Learn commands | When unsure what's available |
| `/review` | Before committing | Review all session changes |
| `/undo` | Incorrect change | Claude Code made a mistake |
| `/diff` | See changes | Check what's been modified |
| Plan mode | Complex tasks | Multi-file refactoring, migrations |
| `.claude/` | Project config | Set standards once, use always |

### Worker Best Practices with Commands

**When worker detects it needs Claude Code:**

```bash
#!/bin/bash
# Worker script for using Claude Code optimally

# 1. Check if starting new feature (different from previous task)
if [[ "$NEW_FEATURE" == "true" ]]; then
    # Start fresh session (implicitly clean context)
    claude-code "Implement $FEATURE_NAME"
else
    # Continue in same domain
    claude-code "Continue with $TASK_NAME"
fi

# 2. For complex multi-step tasks, describe fully (triggers plan mode)
if [[ "$TASK_COMPLEXITY" == "high" ]]; then
    claude-code "Complex task: $DETAILED_DESCRIPTION with requirements: $REQUIREMENTS"
    # Claude Code will create plan, show it, ask approval, then execute
fi

# 3. Review changes before proceeding
# (Worker can check exit code and git diff)
if [ $? -eq 0 ]; then
    git diff --stat
    # Proceed with next task
fi
```

**Context Management Strategy:**

```yaml
# In worker configuration
worker_claude_code_strategy:
  # Clear context between features
  clear_between_features: true

  # Use plan mode for complex tasks
  auto_plan_threshold: "high_complexity"

  # Review changes before committing
  auto_review: true

  # Follow project .claude/ guidelines
  respect_project_config: true
```

## Best Practices Summary

1. **Start in project root**: Ensures Claude Code has full codebase context
2. **Use `/clear` between features**: Fresh context for unrelated tasks
3. **Leverage plan mode**: Let Claude Code plan complex multi-step tasks
4. **Be specific in task descriptions**: Include files, requirements, constraints
5. **Configure `.claude/` directory**: Set project standards once
6. **Review changes before committing**: Use `/diff` or `/review`
7. **Run tests after changes**: Verify functionality preserved
8. **Use read-only for analysis**: Cheaper and safer for reviews
9. **Commit incrementally**: Break large changes into logical commits
10. **Handle errors gracefully**: Use `/undo` or retry with clarified instructions

## Error Handling

### Command Not Found

```bash
if ! command -v claude-code &> /dev/null; then
    echo "ERROR: claude-code CLI not installed"
    echo "Install from: https://github.com/anthropics/claude-code"
    exit 1
fi
```

### Task Failed

```bash
# Retry with more context
claude-code "Previous task failed. Here's the error:
[ERROR MESSAGE]

Please try again with this approach:
[ALTERNATIVE APPROACH]"
```

### Verify Before Continuing

```bash
# After Claude Code completes, always verify
if [ $? -eq 0 ]; then
    echo "✅ Task completed successfully"
    git status
    npm test  # or appropriate test command
else
    echo "❌ Task failed - see output above"
    exit 1
fi
```

---

**Remember**: Claude Code is a powerful coding assistant, but you should always review its changes before committing. Use it for complex tasks where AI assistance adds value, but handle simple operations directly for better efficiency.
