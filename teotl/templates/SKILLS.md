# Agent Skills

Documentation of available skills and how to use them effectively.

---

## File Operations

**Skills:** `read_file`, `write_file`, `list_directory`, `delete_file`

### Use Cases

- Reading configuration files
- Checking logs and error messages
- Managing workspace organization
- Creating reports and summaries
- Organizing research notes

### Usage Guidelines

- Always confirm before writing to important files
- Use `read_file` before editing to understand context
- Create backups before major modifications
- Don't delete files without explicit permission
- Respect file permissions and workspace boundaries

### Examples

```markdown
**Good:** Read log file, identify errors, summarize findings
**Good:** Create daily summary in memory/daily/
**Bad:** Delete files without asking
**Bad:** Modify system files outside workspace
```

---

## Web Search & Fetching

**Skills:** `web_search`, `fetch_url`, `extract_content`

### Use Cases

- Finding current information
- Research tasks
- Monitoring news sources
- Fact-checking claims
- Gathering data for reports

### Usage Guidelines

- Always cite sources with URLs
- Cross-reference multiple sources for important facts
- Flag when information is speculative vs. confirmed
- Respect rate limits (max 10 searches per mission)
- Cache results to avoid redundant requests
- Check publication dates for time-sensitive info

### Examples

```markdown
**Good:** Search for "latest AI research papers 2026", cite top 3 sources
**Good:** Fetch article, extract key points, summarize
**Bad:** Make 50 search queries in rapid succession
**Bad:** Share information without citing source
```

---

## Communication

**Skills:** `send_notification`, `create_message`, `format_output`

### Use Cases

- Alerting user to urgent items
- Sending mission results
- Formatting reports and summaries
- Providing status updates

### Usage Guidelines

- Use notifications sparingly (URGENT+ only)
- Include context with every notification
- Format for readability (markdown, bullets)
- Highlight action items clearly
- Don't spam with routine updates

### Examples

```markdown
**Good:** Notify about CRITICAL email from VIP sender
**Good:** Send daily digest as formatted markdown
**Bad:** Notify for every email received
**Bad:** Send walls of unformatted text
```

---

## Data Processing

**Skills:** `parse_json`, `parse_yaml`, `extract_data`, `transform_data`

### Use Cases

- Processing API responses
- Extracting structured data from documents
- Converting between formats
- Analyzing logs and metrics

### Usage Guidelines

- Validate data structure before processing
- Handle errors gracefully
- Preserve data integrity
- Document transformations applied
- Cache processed results when appropriate

### Examples

```markdown
**Good:** Parse API response, extract key metrics, store as structured data
**Good:** Convert CSV to JSON with validation
**Bad:** Process malformed data without validation
**Bad:** Lose data during transformation
```

---

## Task Management

**Skills:** `create_task`, `update_task`, `complete_task`, `list_tasks`

### Use Cases

- Breaking down complex work
- Tracking progress
- Managing priorities
- Scheduling follow-ups

### Usage Guidelines

- Create specific, actionable tasks
- Set appropriate priorities
- Include context and deadlines
- Update status regularly
- Archive completed tasks

### Examples

```markdown
**Good:** Create task "Review PR #123" with URGENT priority, context link
**Good:** Break large project into 5 specific sub-tasks
**Bad:** Create vague task "Fix everything"
**Bad:** Set everything as CRITICAL priority
```

---

## Scheduling & Time

**Skills:** `check_calendar`, `find_availability`, `create_reminder`, `check_time`

### Use Cases

- Checking daily schedule
- Finding meeting times
- Setting reminders
- Detecting conflicts
- Time zone conversions

### Usage Guidelines

- Respect user's focus time blocks
- Never create events without confirmation
- Flag scheduling conflicts immediately
- Consider time zones when scheduling
- Provide sufficient lead time for reminders

### Examples

```markdown
**Good:** Check calendar, find 30-min slot respecting focus time
**Good:** Set reminder 15 min before meeting
**Bad:** Schedule meeting during documented focus time
**Bad:** Create reminder without asking
```

---

## Memory & Learning

**Skills:** `store_memory`, `recall_memory`, `search_memory`, `update_context`

### Use Cases

- Remembering user preferences
- Learning from past interactions
- Building knowledge base
- Tracking patterns and trends

### Usage Guidelines

- Store important context for future reference
- Update memories when learning new preferences
- Search memory before asking repeated questions
- Organize memories logically
- Prune outdated information

### Examples

```markdown
**Good:** Store "User prefers bullet points over paragraphs"
**Good:** Recall past email patterns to improve filtering
**Bad:** Forget user corrections
**Bad:** Store sensitive information insecurely
```

---

## Skill Development

As you learn which skills work best for different tasks, update this file with:

- New usage patterns discovered
- Common mistakes to avoid
- Skill combinations that work well
- Tips for better results

This living document helps you improve over time and maintain consistency.
