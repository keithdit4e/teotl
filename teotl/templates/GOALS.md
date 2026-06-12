# Autonomous Agent Goals

## Your Workspace

{workspace_path}

## Active Goals

{goals}

---

## About This File

This file defines what your agent works on autonomously.

**Keep goals:**
- High-level (what to achieve, not how)
- Specific enough to be actionable
- Focused on your workspace

**Examples:**
- Continuously improve code quality
- Add type hints to functions missing them
- Fix failing tests
- Add docstrings to public methods
- Improve test coverage

**Editing:**
You can edit this file anytime. The agent will pick up changes on the next execution cycle.

**How it works:**
The agent reads this file, decides the next action to take, executes it, and commits when tests pass. See INSTRUCTIONS.md for the execution specification.
