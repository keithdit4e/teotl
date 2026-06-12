---
name: github
version: 1.0.0
description: "Interact with GitHub repositories, issues, and pull requests"
auth: token
triggers:
  - github
  - gh
  - issue
  - pull request
  - pr
  - repository
  - commit
---

# GitHub Operations

GitHub CLI (`gh`) integration for repository management, issues, and pull requests.

## Prerequisites

GitHub CLI must be installed and authenticated:
```bash
# Check if gh is installed
which gh || echo "Install with: brew install gh"

# Authenticate (one-time setup)
gh auth status || gh auth login
```

## Repository Operations

### View Repository Information
```bash
# Get repository details
gh repo view OWNER/REPO

# List repository files
gh repo view OWNER/REPO --json nameWithOwner,description,url,defaultBranchRef
```

### Clone Repository
```bash
# Clone a repository
gh repo clone OWNER/REPO

# Clone to specific directory
gh repo clone OWNER/REPO /path/to/directory
```

## Issue Operations

### List Issues
```bash
# List all open issues
gh issue list --repo OWNER/REPO

# List issues with specific labels
gh issue list --repo OWNER/REPO --label "bug"

# List all issues (including closed)
gh issue list --repo OWNER/REPO --state all --limit 100
```

### View Issue Details
```bash
# View specific issue
gh issue view ISSUE_NUMBER --repo OWNER/REPO

# View issue with comments
gh issue view ISSUE_NUMBER --repo OWNER/REPO --comments

# Get issue as JSON
gh issue view ISSUE_NUMBER --repo OWNER/REPO --json number,title,body,state,labels,url
```

### Create Issue
```bash
# Create interactive issue
gh issue create --repo OWNER/REPO

# Create issue with details
gh issue create --repo OWNER/REPO \
  --title "Issue title" \
  --body "Issue description"

# Create issue with label
gh issue create --repo OWNER/REPO \
  --title "Bug report" \
  --body "Description" \
  --label "bug"
```

### Comment on Issue
```bash
# Add comment to issue
gh issue comment ISSUE_NUMBER --repo OWNER/REPO \
  --body "Comment text"
```

### Close Issue
```bash
# Close an issue
gh issue close ISSUE_NUMBER --repo OWNER/REPO

# Close with comment
gh issue close ISSUE_NUMBER --repo OWNER/REPO \
  --comment "Fixed in PR #123"
```

## Pull Request Operations

### List Pull Requests
```bash
# List open PRs
gh pr list --repo OWNER/REPO

# List all PRs
gh pr list --repo OWNER/REPO --state all

# List PRs by author
gh pr list --repo OWNER/REPO --author "@me"
```

### View Pull Request
```bash
# View PR details
gh pr view PR_NUMBER --repo OWNER/REPO

# View PR with diff
gh pr view PR_NUMBER --repo OWNER/REPO --diff

# Get PR as JSON
gh pr view PR_NUMBER --repo OWNER/REPO --json number,title,body,state,url
```

### Create Pull Request
```bash
# Create PR from current branch (interactive)
gh pr create --repo OWNER/REPO

# Create PR with details
gh pr create --repo OWNER/REPO \
  --title "Fix: Description" \
  --body "Detailed description of changes" \
  --base main \
  --head fix/issue-123

# Create PR referencing an issue
gh pr create --repo OWNER/REPO \
  --title "Fix: Issue #123" \
  --body "Fixes #123

## Changes
- Fixed the bug
- Added tests" \
  --base main
```

**Best practices for PRs:**
- Use semantic commit prefixes: `fix:`, `feat:`, `refactor:`, `docs:`
- Reference issue numbers in title and body: `#123`
- Include clear description of changes
- Link to the issue being fixed: `Fixes #123` or `Closes #123`

### Merge Pull Request
```bash
# Merge PR (default: merge commit)
gh pr merge PR_NUMBER --repo OWNER/REPO

# Squash and merge
gh pr merge PR_NUMBER --repo OWNER/REPO --squash

# Rebase and merge
gh pr merge PR_NUMBER --repo OWNER/REPO --rebase

# Auto-merge when checks pass
gh pr merge PR_NUMBER --repo OWNER/REPO --auto
```

### Comment on Pull Request
```bash
# Add comment to PR
gh pr comment PR_NUMBER --repo OWNER/REPO \
  --body "Comment text"
```

## File Operations

### View File Contents
```bash
# View file from repository
gh api repos/OWNER/REPO/contents/path/to/file \
  --jq '.content' | base64 -d

# View file from specific branch/commit
gh api repos/OWNER/REPO/contents/path/to/file?ref=BRANCH \
  --jq '.content' | base64 -d
```

### Search Code
```bash
# Search code in repository
gh search code --repo OWNER/REPO "search query"

# Search in specific file type
gh search code --repo OWNER/REPO "search query" --extension py
```

## Workflow Integration

### Check PR Status
```bash
# Check if PR checks are passing
gh pr checks PR_NUMBER --repo OWNER/REPO

# Watch PR checks
gh pr checks PR_NUMBER --repo OWNER/REPO --watch
```

### Typical DevOps Workflow

**1. Fetch issue details:**
```bash
gh issue view ISSUE_NUMBER --repo OWNER/REPO --json number,title,body,labels
```

**2. Clone repository and create branch:**
```bash
gh repo clone OWNER/REPO
cd REPO
git checkout -b fix/issue-ISSUE_NUMBER
```

**3. Make changes, commit:**
```bash
# ... make code changes ...
git add .
git commit -m "fix: description (#ISSUE_NUMBER)"
git push origin fix/issue-ISSUE_NUMBER
```

**4. Create pull request:**
```bash
gh pr create --repo OWNER/REPO \
  --title "Fix: Issue #ISSUE_NUMBER" \
  --body "Fixes #ISSUE_NUMBER

## Changes
- Fixed the bug
- Added regression tests

## Testing
- All tests passing
- Added test case for this issue"
```

**5. Add comment to issue:**
```bash
gh issue comment ISSUE_NUMBER --repo OWNER/REPO \
  --body "Fix submitted in PR #$(gh pr list --head fix/issue-ISSUE_NUMBER --json number --jq '.[0].number')"
```

## Authentication

The gh CLI uses the `GITHUB_TOKEN` environment variable or stored credentials from `gh auth login`.

**For automation:**
```bash
# Use token from environment
export GITHUB_TOKEN="ghp_your_token_here"

# Verify authentication
gh auth status
```

**Required token scopes for automation:**
- `repo` - Full repository access
- `read:org` - Read organization data (if working with org repos)

## Error Handling

**Check if command succeeded:**
```bash
if gh issue view 123 --repo OWNER/REPO &>/dev/null; then
  echo "Issue exists"
else
  echo "Issue not found or error occurred"
fi
```

**Capture error messages:**
```bash
if ! output=$(gh pr create --repo OWNER/REPO 2>&1); then
  echo "Error creating PR: $output"
  exit 1
fi
```

## Rate Limiting

GitHub API has rate limits. Check your current limit:
```bash
gh api rate_limit
```

If you hit rate limits:
- Authenticated requests: 5,000 requests per hour
- Unauthenticated: 60 requests per hour
- Consider implementing backoff and retry logic

## Security Best Practices

1. **Never log tokens:** Avoid echoing commands that contain tokens
2. **Use environment variables:** Store `GITHUB_TOKEN` in env, not in code
3. **Minimal permissions:** Use tokens with only required scopes
4. **Rotate tokens:** Regenerate tokens periodically
5. **Validate input:** Always validate repository names and issue numbers before using them

## Common Patterns

### Get PR URL after creation
```bash
pr_url=$(gh pr create --repo OWNER/REPO --title "Title" --body "Body" 2>&1 | grep -o 'https://github.com/[^ ]*')
echo "Created PR: $pr_url"
```

### Check if issue is open
```bash
state=$(gh issue view ISSUE_NUMBER --repo OWNER/REPO --json state --jq '.state')
if [ "$state" = "OPEN" ]; then
  echo "Issue is open"
fi
```

### List files changed in PR
```bash
gh pr diff PR_NUMBER --repo OWNER/REPO --name-only
```
