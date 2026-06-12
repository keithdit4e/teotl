---
name: spec_kit
version: 1.0.0
description: "Formal specification creation for structured planning with constitution-driven requirements"
auth: none
triggers:
  - create spec
  - specification
  - formal spec
  - requirements
  - acceptance criteria
  - planning
  - constitution
  - verify spec
---

# spec-kit - Constitution-Driven Specification Tool

Use spec-kit CLI to create formal, structured specifications that enforce project values and standards from your constitution. Perfect for planner agents to create detailed, verifiable execution plans.

## When to Use spec-kit

**Use spec-kit during planning phase for:**
- Feature specifications with clear acceptance criteria
- Constitution-driven requirement generation
- Structured task extraction from specifications
- Verification checklists tied to project standards
- Dependency analysis between tasks
- Progress tracking against formal criteria

**Don't use for:**
- Simple one-line tasks
- Ad-hoc exploratory work
- Non-planning activities

## Core Workflow

### Planning Flow with spec-kit

```
1. Read Constitution → 2. Create Spec → 3. Extract Tasks → 4. Verify Completion
```

### 1. Read Project Constitution

Before creating any spec, read the project constitution:

```bash
# Constitution files define project values and standards
cat CONSTITUTION.md       # Values, principles, non-negotiables
cat ARCHITECTURE.md       # Architectural patterns, decisions
cat STANDARDS.md          # Coding standards, conventions
cat SECURITY.md          # Security requirements, policies
```

**Why read constitution first:**
- Ensures specs align with project values
- Enforces standards automatically
- Includes required criteria (e.g., test coverage)
- Maintains architectural consistency

### 2. Create Formal Specification

```bash
# Create spec with constitution context
spec-kit create <feature-name> \
  --type feature \
  --constitution CONSTITUTION.md \
  --architecture ARCHITECTURE.md \
  --standards STANDARDS.md \
  --output specs/<feature-name>.md

# Alternative: Provide context inline
spec-kit create email-verification \
  --type feature \
  --context "$(cat CONSTITUTION.md ARCHITECTURE.md STANDARDS.md)" \
  --output specs/email-verification.md
```

**What spec-kit generates:**

```markdown
# Specification: Email Verification

## Problem Statement
Users need to verify their email addresses during signup.

## Constitution Requirements
(Auto-extracted from CONSTITUTION.md)
- Security: All auth changes require security review
- Testing: 80% code coverage minimum
- Privacy: Never log email addresses

## Functional Requirements
- REQ-1: Generate unique verification tokens
- REQ-2: Send verification emails
- REQ-3: Verify tokens via endpoint
- REQ-4: Handle token expiration

## Non-Functional Requirements
- NFR-1: Tokens expire after 1 hour
- NFR-2: Rate limit: 3 emails per hour per user
- NFR-3: Email delivery within 30 seconds

## Acceptance Criteria
- AC-1: UUID4 tokens generated securely
- AC-2: Tokens stored with 1-hour TTL
- AC-3: Email contains personalized verification link
- AC-4: /verify endpoint validates tokens
- AC-5: Expired tokens return clear error
- AC-6: Rate limiting prevents abuse
- AC-7: 80% test coverage achieved
- AC-8: Security review completed

## Technical Approach
- Token generation: crypto.randomUUID()
- Storage: PostgreSQL with TTL
- Email: SendGrid API
- Endpoint: POST /api/auth/verify

## Dependencies
- Email service (SendGrid)
- Database (PostgreSQL)
- Auth system (JWT)

## Security Considerations
- Tokens are single-use
- HTTPS only for verification links
- Rate limiting on email sending
- Token entropy: 128 bits

## Testing Requirements
- Unit tests: Token generation, validation
- Integration tests: Email sending, endpoint
- Security tests: Rate limiting, token security
- Target coverage: 80%

## Tasks
(Structured task list)
1. Implement token generation
2. Create database schema
3. Build email templates
4. Implement /verify endpoint
5. Add rate limiting
6. Write tests
7. Security review
```

### 3. Extract Structured Tasks

```bash
# Extract tasks from spec into JSON format
spec-kit extract-tasks specs/email-verification.md \
  --format json \
  --output specs/email-verification.tasks.json

# Or get tasks as markdown checklist
spec-kit extract-tasks specs/email-verification.md \
  --format markdown \
  --output TASKS.md
```

**Task JSON output:**
```json
{
  "spec": "email-verification",
  "constitution_enforced": true,
  "tasks": [
    {
      "id": "ev-1",
      "title": "Implement token generation",
      "description": "Generate UUID4 verification tokens with secure randomness",
      "acceptance_criteria": [
        "Uses crypto.randomUUID()",
        "128-bit entropy minimum",
        "Tokens are unique across system"
      ],
      "dependencies": [],
      "complexity": "medium",
      "estimated_time": "2 hours",
      "required_by_constitution": ["Security review required"]
    },
    {
      "id": "ev-2",
      "title": "Create database schema",
      "description": "Add verification_tokens table with TTL",
      "acceptance_criteria": [
        "Table has: id, user_id, token, expires_at",
        "Index on token for fast lookup",
        "Auto-cleanup of expired tokens"
      ],
      "dependencies": ["ev-1"],
      "complexity": "low",
      "estimated_time": "1 hour"
    },
    {
      "id": "ev-3",
      "title": "Build email templates",
      "description": "Create HTML and text email templates",
      "acceptance_criteria": [
        "HTML and plain text versions",
        "Personalized with user name",
        "Includes verification link",
        "Mobile-responsive design"
      ],
      "dependencies": ["ev-1"],
      "complexity": "medium",
      "estimated_time": "3 hours"
    },
    {
      "id": "ev-4",
      "title": "Implement /verify endpoint",
      "description": "Create API endpoint to validate tokens",
      "acceptance_criteria": [
        "POST /api/auth/verify",
        "Validates token exists and not expired",
        "Marks user as verified",
        "Returns JWT on success"
      ],
      "dependencies": ["ev-1", "ev-2"],
      "complexity": "high",
      "estimated_time": "4 hours"
    },
    {
      "id": "ev-5",
      "title": "Add rate limiting",
      "description": "Prevent email sending abuse",
      "acceptance_criteria": [
        "Max 3 emails per hour per user",
        "Clear error message on limit",
        "Redis-based tracking"
      ],
      "dependencies": ["ev-3"],
      "complexity": "medium",
      "estimated_time": "2 hours",
      "required_by_constitution": ["Security review required"]
    },
    {
      "id": "ev-6",
      "title": "Write tests",
      "description": "Comprehensive test suite",
      "acceptance_criteria": [
        "Unit tests for token generation",
        "Integration tests for email flow",
        "Security tests for rate limiting",
        "80% code coverage minimum"
      ],
      "dependencies": ["ev-1", "ev-2", "ev-3", "ev-4", "ev-5"],
      "complexity": "high",
      "estimated_time": "5 hours",
      "required_by_constitution": ["80% coverage required"]
    },
    {
      "id": "ev-7",
      "title": "Security review",
      "description": "Review implementation for security issues",
      "acceptance_criteria": [
        "Token entropy verified",
        "Rate limiting tested",
        "No PII logging confirmed",
        "HTTPS enforcement verified"
      ],
      "dependencies": ["ev-6"],
      "complexity": "medium",
      "estimated_time": "2 hours",
      "required_by_constitution": ["Security review required"]
    }
  ],
  "total_tasks": 7,
  "estimated_total_time": "19 hours",
  "constitution_requirements": [
    "80% test coverage",
    "Security review",
    "No PII logging"
  ]
}
```

### 4. Analyze Dependencies

```bash
# Visualize task dependencies
spec-kit analyze-dependencies specs/email-verification.tasks.json

# Output shows execution order
spec-kit analyze-dependencies specs/email-verification.tasks.json \
  --output execution-order
```

**Dependency analysis output:**
```
Execution Order Analysis:

Wave 1 (No dependencies - can run in parallel):
  ✓ ev-1: Implement token generation

Wave 2 (Depends on Wave 1):
  ✓ ev-2: Create database schema
  ✓ ev-3: Build email templates

Wave 3 (Depends on Wave 2):
  ✓ ev-4: Implement /verify endpoint
  ✓ ev-5: Add rate limiting

Wave 4 (Depends on Wave 3):
  ✓ ev-6: Write tests

Wave 5 (Depends on Wave 4):
  ✓ ev-7: Security review

Critical Path: ev-1 → ev-2 → ev-4 → ev-6 → ev-7 (14 hours)
Parallelizable: ev-2 and ev-3 (saves 3 hours)
Minimum execution time: 16 hours (with parallelization)
```

### 5. Verify Against Spec

After worker completes tasks, verify implementation meets spec:

```bash
# Comprehensive verification
spec-kit verify specs/email-verification.md \
  --implementation src/ \
  --tests tests/ \
  --check-coverage \
  --check-security

# Output verification report
spec-kit verify specs/email-verification.md \
  --implementation src/ \
  --tests tests/ \
  --output verification-report.md
```

**Verification report:**
```markdown
# Verification Report: Email Verification

## Requirements Status

### Functional Requirements
- ✅ REQ-1: Generate unique verification tokens (PASS)
- ✅ REQ-2: Send verification emails (PASS)
- ✅ REQ-3: Verify tokens via endpoint (PASS)
- ✅ REQ-4: Handle token expiration (PASS)

### Non-Functional Requirements
- ✅ NFR-1: Tokens expire after 1 hour (PASS)
- ✅ NFR-2: Rate limit: 3/hour (PASS)
- ⚠️  NFR-3: Email delivery <30s (WARNING: 45s average)

### Acceptance Criteria
- ✅ AC-1: UUID4 tokens (PASS)
- ✅ AC-2: 1-hour TTL (PASS)
- ✅ AC-3: Personalized email (PASS)
- ✅ AC-4: /verify endpoint (PASS)
- ✅ AC-5: Expired token error (PASS)
- ✅ AC-6: Rate limiting (PASS)
- ✅ AC-7: 80% coverage (PASS - 87%)
- ✅ AC-8: Security review (PASS)

## Test Results
- Total tests: 47
- Passing: 47
- Failing: 0
- Coverage: 87% (exceeds 80% requirement)

## Constitution Compliance
- ✅ Security review: Completed
- ✅ Test coverage: 87% (meets 80%)
- ✅ No PII logging: Verified

## Security Scan
- ✅ Token entropy: 128 bits
- ✅ Rate limiting: Working
- ✅ HTTPS enforcement: Yes
- ⚠️  Email delivery time: Exceeds target

## Overall Status
✅ PASS (1 warning)

Recommendation: Address email delivery performance
```

## Constitution-Driven Planning

### Reading Constitution Files

```bash
# Check if constitution files exist
if [ -f "CONSTITUTION.md" ]; then
    echo "Reading project constitution..."
    constitution=$(cat CONSTITUTION.md)
fi

if [ -f "ARCHITECTURE.md" ]; then
    echo "Reading architecture guide..."
    architecture=$(cat ARCHITECTURE.md)
fi

if [ -f "STANDARDS.md" ]; then
    echo "Reading coding standards..."
    standards=$(cat STANDARDS.md)
fi
```

### Constitution File Structure

**CONSTITUTION.md:**
```markdown
# Project Constitution

## Core Values
- Security First: All auth changes require security review
- User Privacy: Never log PII
- Test Quality: 80% coverage minimum
- Fast Delivery: <1s response time for APIs

## Non-Negotiables
- HTTPS everywhere
- Rate limiting on all public APIs
- Input validation on all endpoints
- Automated testing before deploy

## Development Standards
- TypeScript strict mode
- ESLint + Prettier
- Conventional commits
- PR reviews required
```

**ARCHITECTURE.md:**
```markdown
# Architecture Guide

## Patterns
- Microservices for bounded contexts
- JWT for authentication
- PostgreSQL for persistence
- Redis for caching
- Event-driven for async operations

## Technology Stack
- Backend: Node.js + TypeScript
- Database: PostgreSQL 14+
- Cache: Redis 6+
- Queue: Bull (Redis-backed)
- Email: SendGrid

## API Design
- RESTful endpoints
- JSON payloads
- Versioned APIs (/api/v1/)
- OpenAPI documentation
```

**STANDARDS.md:**
```markdown
# Coding Standards

## TypeScript
- Strict mode enabled
- No any types
- Explicit return types
- Interfaces over types

## Testing
- Jest framework
- 80% coverage minimum
- Unit + integration tests
- E2E for critical flows

## Naming
- camelCase for variables
- PascalCase for classes
- SCREAMING_SNAKE for constants
- Descriptive names (no abbreviations)

## Git
- Conventional commits
- Feature branches
- PR reviews (2 approvals)
- Squash merges to main
```

### Enforcing Constitution in Specs

```bash
# spec-kit auto-enforces constitution requirements
spec-kit create feature-name \
  --constitution CONSTITUTION.md \
  --enforce-values \
  --enforce-standards

# Results in spec that includes:
# - Security review task (from "Security First" value)
# - 80% coverage requirement (from "Test Quality" value)
# - Rate limiting check (from "Non-Negotiables")
# - TypeScript strict mode (from "Development Standards")
```

## Integration with Planner-Worker

### Planner Uses spec-kit

```
Planner receives goal: "Implement email verification"
  ↓
1. Read constitution files
   - CONSTITUTION.md
   - ARCHITECTURE.md
   - STANDARDS.md
  ↓
2. Create spec with spec-kit
   spec-kit create email-verification \
     --constitution CONSTITUTION.md \
     --architecture ARCHITECTURE.md
  ↓
3. Extract structured tasks
   spec-kit extract-tasks specs/email-verification.md \
     --format json
  ↓
4. Analyze dependencies
   spec-kit analyze-dependencies \
     specs/email-verification.tasks.json
  ↓
5. Generate PLAN.md with:
   - Constitution-enforced requirements
   - Structured tasks with acceptance criteria
   - Execution order based on dependencies
   - Verification checklist
  ↓
6. Worker executes tasks in order
  ↓
7. Planner verifies completion
   spec-kit verify specs/email-verification.md \
     --implementation src/ \
     --tests tests/
```

### Example Planner Output (PLAN.md)

```markdown
# Plan: Email Verification

## Constitution Context
- Security review required (from CONSTITUTION.md)
- 80% test coverage required (from CONSTITUTION.md)
- PostgreSQL for persistence (from ARCHITECTURE.md)
- TypeScript strict mode (from STANDARDS.md)

## Specification
See: specs/email-verification.md

## Execution Plan

### Wave 1: Foundation
**Task ev-1: Implement token generation**
- Generate UUID4 verification tokens
- Acceptance Criteria:
  ✓ Uses crypto.randomUUID()
  ✓ 128-bit entropy
  ✓ Tokens unique across system
- Estimated: 2 hours
- Constitution: Security review required

### Wave 2: Data & UI (Parallel)
**Task ev-2: Create database schema**
- Add verification_tokens table
- Acceptance Criteria:
  ✓ Table has: id, user_id, token, expires_at
  ✓ Index on token
  ✓ Auto-cleanup expired tokens
- Dependencies: ev-1
- Estimated: 1 hour

**Task ev-3: Build email templates**
- HTML and text email templates
- Acceptance Criteria:
  ✓ HTML and text versions
  ✓ Personalized with name
  ✓ Verification link included
  ✓ Mobile-responsive
- Dependencies: ev-1
- Estimated: 3 hours

### Wave 3: Business Logic
**Task ev-4: Implement /verify endpoint**
- API endpoint for token validation
- Acceptance Criteria:
  ✓ POST /api/auth/verify
  ✓ Validates token
  ✓ Marks user verified
  ✓ Returns JWT
- Dependencies: ev-1, ev-2
- Estimated: 4 hours

**Task ev-5: Add rate limiting**
- Prevent abuse
- Acceptance Criteria:
  ✓ Max 3 emails/hour/user
  ✓ Clear error message
  ✓ Redis-based tracking
- Dependencies: ev-3
- Estimated: 2 hours
- Constitution: Security review required

### Wave 4: Quality Assurance
**Task ev-6: Write tests**
- Comprehensive test suite
- Acceptance Criteria:
  ✓ Unit tests for tokens
  ✓ Integration tests for email
  ✓ Security tests for rate limit
  ✓ 80% coverage minimum
- Dependencies: ev-1, ev-2, ev-3, ev-4, ev-5
- Estimated: 5 hours
- Constitution: 80% coverage required

### Wave 5: Security Review
**Task ev-7: Security review**
- Review for security issues
- Acceptance Criteria:
  ✓ Token entropy verified
  ✓ Rate limiting tested
  ✓ No PII logging
  ✓ HTTPS enforcement
- Dependencies: ev-6
- Estimated: 2 hours
- Constitution: Security review required

## Summary
- Total tasks: 7
- Estimated time: 19 hours (16 with parallelization)
- Constitution requirements: 3
- Critical path: ev-1 → ev-2 → ev-4 → ev-6 → ev-7

## Verification
After completion, verify with:
```bash
spec-kit verify specs/email-verification.md \
  --implementation src/ \
  --tests tests/ \
  --check-coverage \
  --check-security
```
```

## Advanced Features

### Multi-Feature Specs (Epics)

```bash
# Create epic spec with multiple sub-features
spec-kit create auth-system \
  --type epic \
  --features "JWT tokens,Email verification,Password reset,2FA" \
  --constitution CONSTITUTION.md \
  --output specs/auth-system.md

# Extract all tasks from epic
spec-kit extract-tasks specs/auth-system.md \
  --include-sub-features \
  --format json
```

### Spec Templates

```bash
# List available templates
spec-kit templates list

# Create spec from template
spec-kit create api-endpoint \
  --template rest-api \
  --constitution CONSTITUTION.md

# Create custom template
spec-kit template create my-template \
  --based-on feature \
  --add-section "Migration Strategy"
```

### Progress Tracking

```bash
# Check progress against spec
spec-kit status specs/email-verification.md \
  --implementation src/ \
  --tests tests/

# Output shows completion percentage
Specification Progress: Email Verification

Requirements: 4/4 complete (100%)
Acceptance Criteria: 7/8 complete (87%)
Tasks: 6/7 complete (85%)

Remaining:
  ⏳ ev-7: Security review

Overall: 87% complete
```

### Diff and Updates

```bash
# Show what changed in implementation vs spec
spec-kit diff specs/email-verification.md \
  --implementation src/

# Update spec based on implementation changes
spec-kit update specs/email-verification.md \
  --from-implementation src/ \
  --interactive
```

## Common Workflows

### Workflow 1: New Feature Planning

```bash
# 1. Read constitution
cat CONSTITUTION.md ARCHITECTURE.md STANDARDS.md

# 2. Create spec
spec-kit create new-feature \
  --constitution CONSTITUTION.md \
  --architecture ARCHITECTURE.md \
  --output specs/new-feature.md

# 3. Review and refine spec
cat specs/new-feature.md
# Edit if needed

# 4. Extract tasks
spec-kit extract-tasks specs/new-feature.md \
  --format json \
  --output specs/new-feature.tasks.json

# 5. Analyze dependencies
spec-kit analyze-dependencies specs/new-feature.tasks.json

# 6. Ready for worker execution
```

### Workflow 2: Verification After Implementation

```bash
# 1. Worker completes tasks

# 2. Run verification
spec-kit verify specs/feature.md \
  --implementation src/ \
  --tests tests/ \
  --check-coverage \
  --output verification-report.md

# 3. Review report
cat verification-report.md

# 4. If issues found, create fix tasks
spec-kit create-fix-tasks verification-report.md \
  --output FIXES.md
```

### Workflow 3: Constitution Update

```bash
# 1. Update constitution
# (e.g., change test coverage from 80% to 90%)

# 2. Check which specs need updates
spec-kit check-constitution-compliance specs/ \
  --constitution CONSTITUTION.md

# 3. Update affected specs
spec-kit update-from-constitution specs/feature.md \
  --constitution CONSTITUTION.md \
  --interactive
```

## Error Handling

### spec-kit Not Installed

```bash
# Check if spec-kit is available
if ! command -v spec-kit &> /dev/null; then
    echo "ERROR: spec-kit CLI not installed"
    echo "Install from: https://github.com/spec-kit/spec-kit"
    echo "Or: npm install -g spec-kit"
    exit 1
fi
```

### Constitution Files Missing

```bash
# Check for constitution files
if [ ! -f "CONSTITUTION.md" ]; then
    echo "WARNING: No CONSTITUTION.md found"
    echo "Creating spec without constitution context"
    echo "Recommendation: Create CONSTITUTION.md for better planning"
fi
```

### Verification Failures

```bash
# Handle verification failures
spec-kit verify specs/feature.md \
  --implementation src/ \
  --tests tests/

if [ $? -ne 0 ]; then
    echo "❌ Verification failed"
    echo "Review verification-report.md for details"
    echo "Create fix tasks with: spec-kit create-fix-tasks verification-report.md"
fi
```

## Best Practices

### 1. Always Read Constitution First
```bash
# Bad: Create spec without context
spec-kit create feature

# Good: Create spec with constitution
spec-kit create feature \
  --constitution CONSTITUTION.md \
  --architecture ARCHITECTURE.md
```

### 2. Use Structured Tasks
```bash
# Bad: Free-form task list in PLAN.md
echo "- Do the thing" >> PLAN.md

# Good: Extract structured tasks from spec
spec-kit extract-tasks specs/feature.md \
  --format json
```

### 3. Verify Against Spec
```bash
# Bad: Assume implementation matches spec
echo "Done!"

# Good: Verify objectively
spec-kit verify specs/feature.md \
  --implementation src/ \
  --tests tests/
```

### 4. Track Dependencies
```bash
# Bad: Execute tasks in random order
# Good: Analyze dependencies first
spec-kit analyze-dependencies specs/feature.tasks.json \
  --output execution-order
```

### 5. Update Constitution Regularly
```bash
# Review and update constitution quarterly
# Check spec compliance after updates
spec-kit check-constitution-compliance specs/ \
  --constitution CONSTITUTION.md
```

## Quick Reference

| Operation | Command | Use Case |
|-----------|---------|----------|
| Create spec | `spec-kit create <name> --constitution CONSTITUTION.md` | Initial planning |
| Extract tasks | `spec-kit extract-tasks <spec> --format json` | Get structured tasks |
| Analyze deps | `spec-kit analyze-dependencies <tasks.json>` | Execution order |
| Verify | `spec-kit verify <spec> --implementation src/` | Check completion |
| Status | `spec-kit status <spec> --implementation src/` | Track progress |
| Diff | `spec-kit diff <spec> --implementation src/` | Find changes |

---

**Remember**: spec-kit enforces your constitution automatically. Define your values once, and every spec will include them as requirements. This ensures consistency and quality across all features.
