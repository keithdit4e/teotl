# Agent Skills & Capabilities

This document describes the skills and tools available to me for completing tasks.

## Core Skills

### Filesystem Operations
Read, write, and manage files within allowed directories.

**Available Operations:**
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Create or overwrite file
- `append_file(path, content)` - Append to existing file
- `delete_file(path)` - Delete file (requires confirmation)
- `list_directory(path)` - List files in directory
- `create_directory(path)` - Create directory
- `move_file(src, dst)` - Move or rename file
- `copy_file(src, dst)` - Copy file

**Constraints:**
- Limited to workspace directory and explicitly allowed paths
- Cannot access sensitive directories (/etc, ~/.ssh, etc.)
- File size limit: 100 MB per file
- Binary files are read as base64

**Best Practices:**
- Always read files before editing
- Use relative paths when possible
- Request confirmation before deleting
- Check file exists before operating

---

### Git Operations
Version control and collaboration workflows.

**Available Operations:**
- `git_status()` - Check repository status
- `git_diff(file)` - Show changes
- `git_add(files)` - Stage files
- `git_commit(message)` - Create commit
- `git_push()` - Push to remote (requires confirmation)
- `git_pull()` - Pull from remote
- `git_branch(name)` - Create/switch branches
- `git_log(n)` - View commit history

**Constraints:**
- Must have git repository initialized
- Push operations require confirmation
- Force push is blocked
- No rewriting published history

**Best Practices:**
- Write clear commit messages
- Follow conventional commits format
- Review changes before committing
- Keep commits focused and atomic

---

### Bash Commands
Execute shell commands for system operations.

**Available Commands:**
Examples of commonly allowed commands:
- `ls`, `cat`, `grep`, `find`, `wc`
- `python`, `pip`, `pytest`
- `npm`, `node`, `yarn`
- `docker ps`, `docker logs` (if docker skill enabled)
- `curl`, `wget` (limited to allowed domains)

**Blocked Commands:**
Dangerous operations requiring confirmation:
- `rm -rf` - Recursive deletion
- `sudo` - Elevated privileges
- `chmod`, `chown` - Permission changes
- `dd`, `fdisk` - Disk operations
- `kill`, `killall` - Process termination

**Constraints:**
- Commands analyzed for safety before execution
- Destructive operations require confirmation
- No root/sudo access
- Resource limits enforced (CPU, memory, time)
- Output captured (stdout, stderr)

**Best Practices:**
- Use specific commands over wildcards
- Validate inputs to prevent injection
- Capture errors and handle gracefully
- Prefer built-in tools over bash when available

---

### Web Search & Fetch
Access information from the internet.

**Available Operations:**
- `web_search(query)` - Search web and return results
- `fetch_url(url)` - Fetch webpage content
- `http_request(url, method, data)` - Make HTTP API calls

**Constraints:**
- Limited to allowed domains (see security policy)
- HTTPS required for external connections
- Private network access blocked
- Rate limits apply (varies by provider)
- Response size limited to 1 MB

**Best Practices:**
- Validate URLs before fetching
- Handle HTTP errors gracefully
- Respect robots.txt
- Cache results when appropriate
- Don't leak sensitive data in requests

---

## Integration Skills

### Email (Gmail)
*Requires: Gmail skill enabled, OAuth credentials*

**Available Operations:**
- `gmail_list(query, limit)` - Search emails
- `gmail_read(message_id)` - Read email content
- `gmail_send(to, subject, body)` - Send email
- `gmail_reply(message_id, body)` - Reply to thread
- `gmail_archive(message_id)` - Archive email

**Constraints:**
- Requires user authentication
- Rate limits: 100 requests/minute
- No access to deleted items
- Cannot modify calendar (use Calendar skill)

---

### Calendar (Google Calendar)
*Requires: Calendar skill enabled, OAuth credentials*

**Available Operations:**
- `calendar_list_events(start, end)` - List events
- `calendar_create_event(title, start, end, attendees)` - Create event
- `calendar_update_event(event_id, changes)` - Update event
- `calendar_delete_event(event_id)` - Delete event (requires confirmation)

**Constraints:**
- Requires user authentication
- Rate limits: 50 requests/minute
- Only accesses user's primary calendar
- Cannot create recurring events (yet)

---

### Slack
*Requires: Slack skill enabled, bot token*

**Available Operations:**
- `slack_send_message(channel, text)` - Send message
- `slack_list_channels()` - List channels
- `slack_get_history(channel, limit)` - Read recent messages
- `slack_upload_file(channel, file_path)` - Upload file

**Constraints:**
- Requires workspace bot installation
- Rate limits: 20 requests/minute
- Only accesses public channels by default
- Cannot read DMs without explicit permission

---

### GitHub
*Requires: GitHub skill enabled, personal access token*

**Available Operations:**
- `github_list_repos()` - List repositories
- `github_create_issue(repo, title, body)` - Create issue
- `github_create_pr(repo, title, body, branch)` - Create pull request
- `github_list_issues(repo, state)` - List issues
- `github_comment(repo, issue_num, body)` - Add comment

**Constraints:**
- Requires authentication token
- Rate limits: 5000 requests/hour (authenticated)
- Only accesses repos user has access to
- Cannot force push or delete repos

---

## Memory & Context

### Memory System
Store and recall information across sessions.

**Available Operations:**
- `remember(content, tags)` - Store memory
- `recall(query, limit)` - Search memories
- `forget(memory_id)` - Delete memory
- `list_memories(limit)` - List recent memories

**What to Remember:**
- User preferences and decisions
- Important project context
- Solutions to problems
- Patterns in user's workflow
- Failures and lessons learned

**What NOT to Remember:**
- Sensitive data (credentials, secrets)
- Temporary or transient info
- Redundant information
- Data user explicitly asks to forget

---

## Skill Loading

Skills are loaded on-demand to minimize context usage:

1. **Always loaded:** Skill descriptions (~50 tokens each)
2. **On-demand:** Full instructions and tools when needed
3. **After task:** Skills are unloaded to free context

This means:
- 10 skills = ~500 tokens (not 30,000+)
- Fast loading when needed
- Memory-efficient execution

---

## Adding New Skills

To add a new skill, create a directory structure:

```
~/.teotl/skills/my-skill/
├── SKILL.md          # Short description (always loaded)
└── scripts/          # Executable scripts
    ├── action1.sh
    ├── action2.py
    └── README.md     # Detailed instructions (loaded on-demand)
```

**SKILL.md format:**
```markdown
# My Skill

Short description of what this skill does (1-2 sentences).

**Use cases:** When to use this skill
**Requirements:** Dependencies or setup needed
**Tools:** List of available commands
```

---

*This file documents available capabilities. It's loaded at runtime to inform me what tools I can use to complete tasks.*
