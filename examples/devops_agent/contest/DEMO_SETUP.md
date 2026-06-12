# Demo Video Setup Guide

**Goal:** Prepare keithdit4e/devops-agent-test for recording demo video

---

## Test Repository Setup

### 1. Create Simple Calculator Project

**File Structure:**
```
devops-agent-test/
├── calculator.py          # Main calculator code with bugs
├── test_calculator.py     # Test suite
├── README.md             # Simple project description
└── .github/
    └── workflows/
        └── tests.yml     # CI workflow (optional)
```

---

## Demo Bugs to Create

These bugs should be **simple, visual, and easy to fix** for demo purposes:

### Bug 1: Wrong Operator in subtract()
**File:** `calculator.py`
**Issue Title:** "subtract() returns wrong result"
**Bug:** Uses `+` instead of `-`
```python
def subtract(a, b):
    return a + b  # BUG: Should be a - b
```
**Expected Fix:** Change to `return a - b`

### Bug 2: Indentation Error in add()
**File:** `calculator.py`
**Issue Title:** "add() has indentation error"
**Bug:** Extra indentation
```python
def add(a, b):
        return a + b  # BUG: Extra indentation
```
**Expected Fix:** Remove extra indentation

### Bug 3: Zero Division Not Handled
**File:** `calculator.py`
**Issue Title:** "divide() crashes on zero division"
**Bug:** No error handling
```python
def divide(a, b):
    return a / b  # BUG: No check for b == 0
```
**Expected Fix:** Add zero check and raise ValueError

### Bug 4: Missing multiply_all() Function
**File:** `calculator.py`
**Issue Title:** "Add multiply_all() function"
**Bug:** Function referenced in README but doesn't exist
**Expected Fix:** Add new function

### Bug 5: Type Error in power()
**File:** `calculator.py`
**Issue Title:** "power() doesn't handle negative exponents"
**Bug:** Returns wrong result for negative exponents
```python
def power(base, exponent):
    return base ** int(abs(exponent))  # BUG: abs() breaks negatives
```
**Expected Fix:** Remove abs()

---

## Step-by-Step Setup Process

### Step 1: Check if Repository Exists
```bash
gh repo view keithdit4e/devops-agent-test 2>/dev/null
```

**If exists:** Clean it up or use as-is
**If not exists:** Create new repository

### Step 2: Create Repository (if needed)
```bash
gh repo create keithdit4e/devops-agent-test --public --description "Test repository for Autonomous DevOps Agent demo"
```

### Step 3: Clone and Set Up Locally
```bash
cd ~/Documents/GitHub
git clone https://github.com/keithdit4e/devops-agent-test.git
cd devops-agent-test
```

### Step 4: Create Calculator Files

**calculator.py:**
```python
"""Simple calculator with intentional bugs for demo."""

def add(a, b):
        return a + b  # BUG: Extra indentation

def subtract(a, b):
    return a + b  # BUG: Wrong operator

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b  # BUG: No zero check

def power(base, exponent):
    return base ** int(abs(exponent))  # BUG: abs() breaks negatives

# Missing: multiply_all() - referenced in README but doesn't exist
```

**test_calculator.py:**
```python
"""Tests for calculator - some will fail due to bugs."""
import pytest
from calculator import add, subtract, multiply, divide, power

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2  # Will FAIL - bug in subtract
    assert subtract(10, 5) == 5  # Will FAIL

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(-2, 3) == -6

def test_divide():
    assert divide(6, 2) == 3
    # Missing: test_divide_by_zero - should test for ValueError

def test_power():
    assert power(2, 3) == 8
    assert power(2, -2) == 0.25  # Will FAIL - bug with negative exponents
```

**README.md:**
```markdown
# Calculator Test Project

Simple Python calculator for testing autonomous bug fixing.

## Features

- Addition
- Subtraction
- Multiplication
- Division
- Power function
- multiply_all() for multiple numbers

## Usage

\`\`\`python
from calculator import add, subtract, multiply_all

result = add(5, 3)
numbers = multiply_all([2, 3, 4])  # BUG: Function doesn't exist
\`\`\`

## Testing

\`\`\`bash
pytest test_calculator.py
\`\`\`
```

### Step 5: Commit and Push
```bash
git add .
git commit -m "Initial calculator with bugs for demo"
git push origin main
```

### Step 6: Create GitHub Issues

Create 5 issues manually on GitHub:

**Issue #1: "subtract() returns wrong result"**
```
The subtract function returns incorrect results.

Expected: subtract(5, 3) = 2
Actual: subtract(5, 3) = 8

The function appears to be adding instead of subtracting.
```

**Issue #2: "add() has indentation error"**
```
IndentationError in calculator.py line 4:
  File "calculator.py", line 4
    return a + b
    ^
IndentationError: unexpected indent

Please fix the indentation in the add() function.
```

**Issue #3: "divide() crashes on zero division"**
```
ZeroDivisionError when calling divide(x, 0)

Steps to reproduce:
1. Call divide(10, 0)
2. Program crashes with ZeroDivisionError

Expected: Should raise ValueError with helpful message
Actual: Unhandled ZeroDivisionError
```

**Issue #4: "Add multiply_all() function"**
```
README.md references multiply_all() function but it doesn't exist in calculator.py

Error:
ImportError: cannot import name 'multiply_all' from 'calculator'

Please implement multiply_all(numbers) that multiplies a list of numbers.
```

**Issue #5: "power() doesn't handle negative exponents"**
```
power() function returns incorrect results for negative exponents.

Expected: power(2, -2) = 0.25
Actual: power(2, -2) = 4

The function appears to use abs() on the exponent, making all results positive.
```

---

## Pre-Recording Checklist

### Repository Ready:
- [ ] Repository created: keithdit4e/devops-agent-test
- [ ] calculator.py with 5 bugs committed
- [ ] test_calculator.py committed
- [ ] README.md committed
- [ ] 5 GitHub issues created
- [ ] All issues labeled as "bug"

### Agent Ready:
- [ ] API keys exported (ANTHROPIC_API_KEY, GITHUB_TOKEN)
- [ ] Test autonomous_mode.py locally first
- [ ] Verify agent can access repository
- [ ] Verify MCP bridge working

### Recording Environment:
- [ ] Terminal theme: High contrast (light text, dark background)
- [ ] Font size: Large (18-20pt for readability)
- [ ] Terminal window: Full screen or large size
- [ ] Browser: GitHub logged in, ready to show PRs
- [ ] Screen recording software ready (QuickTime, OBS, etc.)
- [ ] Audio test (microphone working, no background noise)

### Test Run (Dry Run):
- [ ] Run agent on 1-2 issues first
- [ ] Verify PRs are created correctly
- [ ] Check timing (how long for 5 issues?)
- [ ] Verify output is demo-worthy

---

## Recording Tips

### Terminal Recording:
- **Resolution:** 1920x1080 minimum
- **Font:** Monospace, 18-20pt
- **Colors:** High contrast theme
- **Clear history:** `clear` before starting
- **Slow down:** Add pauses for voiceover
- **Speed up:** Can 2x speed up boring parts in editing

### GitHub Recording:
- **Full screen:** Hide bookmarks bar
- **Clean tabs:** Close unnecessary tabs
- **Zoom:** 125% for readability
- **Focus:** Show PR diffs, commit messages, descriptions

### Voiceover:
- **Quiet room:** No background noise
- **Clear speech:** Speak slowly and clearly
- **Enthusiasm:** Sound excited but professional
- **Pauses:** Leave pauses for visual transitions

---

## Next Steps

1. **Create repository** (Step 1-3)
2. **Add buggy code** (Step 4-5)
3. **Create issues** (Step 6)
4. **Test locally** (Pre-recording checklist)
5. **Record footage** (Terminal + GitHub)
6. **Edit video** (Add voiceover, music, text)

---

**Estimated Time:**
- Setup: 30 minutes
- Test run: 15 minutes
- Recording: 30 minutes
- **Total: 1-1.5 hours**
