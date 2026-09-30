---
name: git
version: 2.0.0
description: "Version control with Git: status, commits, branches, diffs"
auth: none
triggers:
  - git
  - commit
  - branch
  - merge
  - diff
  - repository
  - version control
  - repo
---

# Git Version Control

Comprehensive Git operations for version control and collaboration.

## Essential Status & Info

### Repository Status
```bash
# Show working tree status
git status

# Concise status
git status -s

# Show branch info and divergence
git status -sb
```

### Viewing History
```bash
# Recent commits (one line per commit)
git log --oneline -20

# Detailed commits with diffs
git log -p -5

# Graphical branch history
git log --oneline --graph --all -20

# Show commits by author
git log --author="AuthorName" --oneline -10

# Show commits in date range
git log --since="2 weeks ago" --until="yesterday" --oneline
```

### Branch Information
```bash
# List local branches
git branch

# List all branches (including remote)
git branch -a

# List branches with last commit
git branch -v

# Show remote repositories
git remote -v

# Show remote branch tracking
git branch -vv
```

## Making Changes

### Staging Files
```bash
# Stage specific file
git add /path/to/file

# Stage all changes
git add -A

# Stage all in current directory
git add .

# Stage interactively (choose hunks)
git add -p /path/to/file

# Unstage file
git reset HEAD /path/to/file
```

### Committing
```bash
# Commit with message
git commit -m "commit message"

# Commit with detailed message (opens editor)
git commit

# Commit all tracked changes
git commit -am "commit message"

# Amend last commit (change message or add files)
git add forgotten_file
git commit --amend --no-edit
```

**Commit Message Best Practices:**
- Use imperative mood: "Add feature" not "Added feature"
- First line: brief summary (<50 chars)
- Blank line, then detailed description if needed
- Reference issues: "Fix #123" or "Closes #456"

### Viewing Changes
```bash
# Show unstaged changes
git diff

# Show staged changes
git diff --staged

# Show changes between branches
git diff branch1..branch2

# Show changes for specific file
git diff /path/to/file

# Show changes since last commit
git diff HEAD~1

# Word-level diff
git diff --word-diff
```

## Branching & Merging

### Branch Management
```bash
# Create new branch
git checkout -b feature-name

# Switch to existing branch
git checkout branch-name

# Create branch without switching
git branch feature-name

# Delete local branch (safe)
git branch -d branch-name

# Delete local branch (force)
git branch -D branch-name

# Rename current branch
git branch -m new-name
```

### Merging
```bash
# Merge branch into current branch
git merge branch-name

# Merge with commit message
git merge branch-name -m "Merge branch-name"

# Abort merge in progress
git merge --abort

# Merge with fast-forward only
git merge --ff-only branch-name
```

### Handling Merge Conflicts
```bash
# 1. See which files have conflicts
git status

# 2. View conflict markers in files
cat conflicted-file.txt

# 3. Resolve conflicts manually (edit files)
# Remove conflict markers (<<<<, ====, >>>>)

# 4. Mark as resolved
git add conflicted-file.txt

# 5. Complete merge
git commit
```

## Working with Remotes

### Fetching & Pulling
```bash
# Fetch from remote (doesn't merge)
git fetch origin

# Fetch all remotes
git fetch --all

# Pull (fetch + merge)
git pull

# Pull with rebase
git pull --rebase

# Pull specific branch
git pull origin branch-name
```

### Pushing
```bash
# Push to remote branch
git push

# Push and set upstream
git push -u origin branch-name

# Push all branches
git push --all

# Push tags
git push --tags

# Force push (DANGEROUS - use with caution)
git push --force-with-lease
```

**CRITICAL**: Never force push to shared branches (main/master) unless absolutely necessary and coordinated with team.

### Remote Management
```bash
# Add remote
git remote add origin https://github.com/user/repo.git

# Change remote URL
git remote set-url origin https://github.com/user/new-repo.git

# Remove remote
git remote remove origin

# Show remote details
git remote show origin
```

## Advanced Operations

### Stashing
```bash
# Save uncommitted changes
git stash

# Stash with message
git stash save "work in progress"

# List stashes
git stash list

# Apply most recent stash
git stash apply

# Apply and remove stash
git stash pop

# Apply specific stash
git stash apply stash@{2}

# Drop stash
git stash drop stash@{0}

# Clear all stashes
git stash clear
```

### Rebase
```bash
# Rebase current branch onto another
git rebase main

# Interactive rebase (last 3 commits)
git rebase -i HEAD~3

# Continue after resolving conflicts
git rebase --continue

# Abort rebase
git rebase --abort

# Skip current commit
git rebase --skip
```

### Cherry-Pick
```bash
# Apply specific commit to current branch
git cherry-pick abc123

# Cherry-pick without committing
git cherry-pick --no-commit abc123

# Cherry-pick multiple commits
git cherry-pick abc123 def456
```

### Reset & Revert
```bash
# Undo last commit (keep changes staged)
git reset --soft HEAD~1

# Undo last commit (keep changes unstaged)
git reset HEAD~1

# Undo last commit (DISCARD changes - DANGEROUS)
git reset --hard HEAD~1

# Revert commit (creates new commit)
git revert abc123

# Discard all local changes (DANGEROUS)
git reset --hard HEAD
```

## Inspection & History

### Viewing Commits
```bash
# Show specific commit
git show abc123

# Show commit with stats
git show --stat abc123

# Show files in commit
git show --name-only abc123
```

### Blame & Attribution
```bash
# Show who changed each line
git blame /path/to/file

# Blame specific lines (10-20)
git blame -L 10,20 /path/to/file

# Blame with commit details
git blame -c /path/to/file
```

### Searching
```bash
# Search for text in commits
git log --all --grep="search term"

# Search for code changes
git log -S"function_name" --oneline

# Search in current files
git grep "search term"

# Search with line numbers
git grep -n "search term"
```

### Comparing Branches
```bash
# Show commits in branch1 not in branch2
git log branch1 ^branch2 --oneline

# Show files that differ between branches
git diff --name-only branch1..branch2

# Show commit count between branches
git rev-list --count branch1..branch2
```

## Working with Tags

### Creating Tags
```bash
# Lightweight tag
git tag v1.0.0

# Annotated tag (recommended)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Tag specific commit
git tag v1.0.0 abc123
```

### Managing Tags
```bash
# List tags
git tag

# List tags matching pattern
git tag -l "v1.*"

# Show tag details
git show v1.0.0

# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin :refs/tags/v1.0.0

# Push specific tag
git push origin v1.0.0
```

## Configuration

### User Settings
```bash
# Set user name
git config user.name "Your Name"

# Set email
git config user.email "your@email.com"

# Set globally
git config --global user.name "Your Name"

# View configuration
git config --list

# View specific setting
git config user.name
```

### Aliases
```bash
# Create alias
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit

# Usage: git st instead of git status
```

## Common Workflows

### Feature Branch Workflow
```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes and commit
git add .
git commit -m "Implement new feature"

# 3. Push to remote
git push -u origin feature/new-feature

# 4. Update from main
git checkout main
git pull
git checkout feature/new-feature
git merge main

# 5. Push updates
git push
```

### Hotfix Workflow
```bash
# 1. Create hotfix from main
git checkout main
git checkout -b hotfix/critical-bug

# 2. Fix and commit
git add .
git commit -m "Fix critical bug"

# 3. Merge back to main
git checkout main
git merge hotfix/critical-bug

# 4. Also merge to develop if exists
git checkout develop
git merge hotfix/critical-bug

# 5. Delete hotfix branch
git branch -d hotfix/critical-bug
```

### Updating Fork
```bash
# 1. Add upstream remote (once)
git remote add upstream https://github.com/original/repo.git

# 2. Fetch upstream changes
git fetch upstream

# 3. Merge into your main
git checkout main
git merge upstream/main

# 4. Push to your fork
git push origin main
```

## Cleanup & Maintenance

### Cleaning Repository
```bash
# Remove untracked files (dry run)
git clean -n

# Remove untracked files
git clean -f

# Remove untracked files and directories
git clean -fd

# Remove ignored files too
git clean -fdx
```

### Pruning
```bash
# Remove deleted remote branches from local tracking
git remote prune origin

# Remove local branches that no longer exist on remote
git fetch --prune

# Delete all local branches already merged
git branch --merged | grep -v "\*" | xargs -n 1 git branch -d
```

### Repository Optimization
```bash
# Garbage collection
git gc

# Aggressive garbage collection
git gc --aggressive

# Check repository integrity
git fsck

# Show repository size
git count-objects -vH
```

## Troubleshooting

### Undoing Mistakes
```bash
# Undo last commit (keep changes)
git reset HEAD~1

# Discard changes in working directory
git checkout -- /path/to/file

# Recover deleted branch (within 30 days)
git reflog
git checkout -b recovered-branch abc123

# Recover lost commits
git reflog
git cherry-pick abc123
```

### Resolving Issues
```bash
# Detached HEAD - create branch
git checkout -b temp-branch

# Stuck in merge - abort
git merge --abort

# Stuck in rebase - abort
git rebase --abort

# Remove file from Git but keep locally
git rm --cached /path/to/file
```

## Security & Best Practices

### Protected Operations
Require user confirmation:
- `git push --force` or `git push -f`
- `git reset --hard`
- `git clean -fd`
- `git push origin :branch-name` (delete remote branch)
- Force push to main/master branches

### Safe Practices
1. **Always run `git status`** before major operations
2. **Pull before push** to avoid conflicts
3. **Use descriptive commit messages**
4. **Commit atomic changes** (one logical change per commit)
5. **Review changes** with `git diff` before committing
6. **Test before pushing** to shared branches
7. **Never commit sensitive data** (passwords, keys, tokens)
8. **Use `.gitignore`** for generated/sensitive files

### Dangerous Commands
```bash
# EXTREME CAUTION:
git reset --hard HEAD          # Discards all local changes
git clean -fdx                 # Deletes all untracked files
git push --force               # Rewrites remote history
git filter-branch              # Rewrites entire history
git reset --hard origin/main   # Discards all local commits
```

## Git Hooks

### Common Hooks
```bash
# Pre-commit hook location
.git/hooks/pre-commit

# Pre-push hook location
.git/hooks/pre-push
```

### Example Pre-commit Hook
```bash
#!/bin/sh
# Prevent commits to main branch
branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "main" ]; then
  echo "Direct commits to main are not allowed"
  exit 1
fi
```

## .gitignore Patterns

### Common Patterns
```bash
# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
*.o
*.pyc

# Environment files
.env
.env.local

# IDE files
.vscode/
.idea/
*.swp

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/
```

## Quick Reference

| Operation | Command | Safety Level |
|-----------|---------|--------------|
| View status | `git status` | Safe |
| View history | `git log --oneline -20` | Safe |
| Stage changes | `git add .` | Safe |
| Commit | `git commit -m "message"` | Safe |
| Pull | `git pull` | Medium - may cause conflicts |
| Push | `git push` | Medium - confirm for shared branches |
| Reset (soft) | `git reset HEAD~1` | Medium - keeps changes |
| Reset (hard) | `git reset --hard` | **DANGEROUS - discards all changes** |
| Force push | `git push --force` | **CRITICAL - rewrites history** |
| Clean | `git clean -fd` | **DANGEROUS - deletes untracked files** |

## Performance Tips

1. **Use shallow clones** for large repos: `git clone --depth 1`
2. **Fetch only needed branches**: `git fetch origin branch-name`
3. **Use sparse checkout** for monorepos
4. **Run `git gc`** periodically to optimize
5. **Use `.gitignore`** to exclude large files

---

**Remember**: Always verify branch and changes with `git status` before destructive operations. When in doubt, create a backup branch first.
