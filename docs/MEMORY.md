# Memory System

**Persistent, context-aware memory for AI agents.**

Teotl's memory system provides intelligent long-term storage that helps agents maintain context across sessions, remember user preferences, and build on past interactions.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Memory Retention & TTL](#memory-retention--ttl)
5. [Memory Recall](#memory-recall)
6. [Auto-Extraction](#auto-extraction)
7. [Manual Memory API](#manual-memory-api)
8. [CLI Commands](#cli-commands)
9. [Security & Privacy](#security--privacy)
10. [Best Practices](#best-practices)

---

## Overview

### What is the Memory System?

The memory system stores facts, preferences, and context that persist across agent sessions:

- **User preferences**: "I prefer Python over JavaScript"
- **User identity**: "My name is Alice, I work at Anthropic"
- **Project context**: "Working on a CLI tool for developers"
- **Decisions made**: "Decided to use SQLite for local storage"

### Key Features

✅ **Persistent** - Memories survive agent restarts
✅ **Optional Encryption** - `EncryptedMemory` encrypts content at rest
✅ **Searchable** - Full-text search with BM25 ranking
✅ **Auto-Expiring** - Importance-based TTL prevents bloat
✅ **Context-Aware** - Relevant memories injected automatically
✅ **Budget-Aware** - Token limits prevent prompt bloat

---

## Quick Start

### Basic Usage

```python
from teotl import Agent
from teotl.core.provider import AnthropicProvider
from teotl.primitives.memory.local import LocalMemory

# Create memory store
memory = LocalMemory()  # Defaults to ~/.forge/memory.db

# Create agent with memory
agent = Agent(
    provider=AnthropicProvider(),
    memory=memory
)

# Agent automatically recalls relevant memories and injects them into context
response = await agent.run("What programming language do I prefer?")
print(response.text)
```

### Storing Memories Manually

```python
# Store a preference
await agent.remember(
    "User prefers dark mode in all applications",
    importance=8,
    tags=["preferences", "ui"]
)

# Store user identity
await agent.remember(
    "User's name is Alice Chen",
    importance=10,  # Critical - never expires
    tags=["identity", "name"]
)

# Store temporary context
await agent.remember(
    "Currently debugging build issue in CI/CD",
    importance=3,  # Low - expires in 7 days
    ttl_days=7
)
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Loop                            │
│                                                          │
│  User Message → Memory Recall → LLM + Memories → Response
│                      ↓                    ↓              │
│                  Inject into          Extract new        │
│                  system prompt        memories           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │      Local Memory            │
            │  (SQLite + FTS5)             │
            └─────────────────────────────┘
```

### Storage

**Default location:** `~/.forge/memory.db`

**Database schema:**
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,           -- The memory content
    source TEXT DEFAULT 'manual',    -- 'manual', 'explicit', 'session'
    tags TEXT DEFAULT '[]',          -- JSON array of tags
    importance INTEGER DEFAULT 5,    -- 1-10 importance rating
    session_id TEXT,                 -- Associated session ID
    created TEXT NOT NULL,           -- ISO timestamp
    last_accessed TEXT,              -- Last recall timestamp
    access_count INTEGER DEFAULT 0,  -- How many times recalled
    expires_at TEXT                  -- ISO timestamp (NULL = never)
);
```

**Full-text search:**
```sql
CREATE VIRTUAL TABLE memories_fts USING fts5(
    content,
    tags
);
```

---

## Memory Retention & TTL

### Importance-Based Auto-TTL

Memories automatically expire based on their importance rating:

| Importance | Retention | Description |
|------------|-----------|-------------|
| **10** | Forever | Critical user identity |
| **9** | Forever | Core preferences |
| **7-8** | 1 year | Important context |
| **5-6** | 90 days | Medium-term context |
| **1-4** | 7 days | Temporary notes |

### Explicit TTL Override

```python
# Force expiration regardless of importance
await agent.remember(
    "Meeting rescheduled to tomorrow",
    importance=8,  # Normally 1 year
    ttl_days=1     # Override: expires in 1 day
)
```

### Inactive Memory Cleanup

Memories are also cleaned up based on access patterns:

| Importance | Inactive Threshold | Action |
|------------|-------------------|---------|
| **9-10** | Never | Always kept |
| **7-8** | 6 months | Delete if not accessed |
| **5-6** | 30 days | Delete if not accessed |
| **1-4** | 7 days | Delete if not accessed |

### Manual Cleanup

```bash
# See what would be deleted
teotl memory cleanup --dry-run

# Clean up expired and inactive memories
teotl memory cleanup

# View retention statistics
teotl memory stats
```

---

## Memory Recall

### How Recall Works

When the user sends a message, the agent automatically:

1. **Searches** memories using full-text search (FTS5)
2. **Ranks** results using:
   - **Relevance** (BM25 score from FTS5)
   - **Importance** (user-defined 1-10)
   - **Recency** (newer memories rank slightly higher)
3. **Injects** top results into system prompt (budget-aware)

### Ranking Algorithm

```sql
-- SQLite query (simplified)
ORDER BY
    bm25(memories_fts) *            -- Relevance to query
    (importance / 5.0) *            -- Importance weighting
    (1.0 + 1.0 / (1.0 + days_old))  -- Recency boost
```

If the query isn't valid FTS5 syntax, recall falls back to a `LIKE` search ordered by
importance and recency.


### Token Budget

The agent recalls up to 10 memories per message and limits the injected memory context to
~500 tokens:

```python
# Default budget
memory_context = memory.format_for_context(
    memories,
    token_budget=500  # ~500 tokens max
)
```

**Why?** Prevents prompt bloat. A typical system prompt is 1000-2000 tokens; memories shouldn't dominate.

### Manual Recall

```python
# Search memories explicitly
memories = await agent.recall("Python programming")

for m in memories:
    print(f"{m.content} (importance: {m.metadata.importance})")
```

---

## Auto-Extraction

### Pattern-Based Extraction

The agent automatically extracts memories from conversations when users say:

| Pattern | Example | Importance |
|---------|---------|------------|
| **"Remember that..."** | "Remember that I work remotely" | 8 |
| **"My name is..."** | "My name is Alice" | 8 |
| **"I prefer..."** | "I prefer dark mode" | 8 |
| **"Note that..."** | "Note that I'm in Pacific timezone" | 8 |
| **"Keep in mind..."** | "Keep in mind I'm a beginner" | 8 |

### How It Works

After each agent turn, the system:
1. Scans user message for memory patterns
2. Extracts the factual content
3. Stores with `source="explicit"` and `importance=8`

**Example:**
```
User: "My name is Bob. I prefer Python."

# Two memories stored automatically:
# 1. "My name is Bob" (importance=8)
# 2. "I prefer Python" (importance=8)
```

Matching is simple pattern-based, so phrasing matters (e.g. "My name is Bob and I prefer
Python" only stores the preference).

### Future: LLM-Based Extraction

**Not yet implemented** (planned for post-MVP):

Use a cheap/fast model (like Haiku) to analyze completed sessions and extract implicit facts
such as "User is working on a CLI project" or "User is debugging a performance issue".

---

## Manual Memory API

### Agent Methods

#### remember()
```python
async def remember(
    content: str,
    *,
    importance: int = 5,
    tags: list[str] | None = None,
    ttl_days: int | None = None,
) -> str: ...
```

**Parameters:**
- `content`: The information to remember
- `importance`: 1-10 rating (default: 5)
- `tags`: Optional categorization tags
- `ttl_days`: Override default TTL

**Returns:** Memory ID

**Example:**
```python
await agent.remember(
    "User's favorite color is blue",
    importance=7,
    tags=["preferences", "color"]
)
```

---

#### recall()
```python
async def recall(query: str, *, limit: int = 10) -> list[Memory]: ...
```

**Parameters:**
- `query`: Search query (full-text search)
- `limit`: Maximum results to return

**Returns:** List of Memory objects

**Example:**
```python
memories = await agent.recall("Python programming")
for m in memories:
    print(m.content)
```

---

#### forget()
```python
async def forget(memory_id: str) -> bool: ...
```

**Parameters:**
- `memory_id`: ID of memory to delete

**Returns:** True if deleted, False if not found

**Example:**
```python
if await agent.forget("abc123"):
    print("Memory deleted")
```

---

#### list_memories()
```python
async def list_memories(*, limit: int = 100, offset: int = 0) -> list[Memory]: ...
```

**Parameters:**
- `limit`: Maximum memories to return
- `offset`: Pagination offset

**Returns:** List of Memory objects (most recent first)

**Example:**
```python
# Get first page
page1 = await agent.list_memories(limit=50, offset=0)

# Get second page
page2 = await agent.list_memories(limit=50, offset=50)
```

---

## CLI Commands

### List Memories

```bash
# List all memories
teotl memory list

# With pagination
teotl memory list --limit 50 --offset 100

# Custom database path
teotl memory list --path ~/my-agent/memory.db
```

**Output (illustrative):**
```
┌────────┬──────────────────────────────┬────────────┬────────────┬───────────┐
│ ID     │ Content                      │ Importance │ Created    │ Expires   │
├────────┼──────────────────────────────┼────────────┼────────────┼───────────┤
│ abc123 │ User prefers Python          │ 8          │ 2026-03-15 │ 2027-03-15│
│ def456 │ My name is Alice             │ 10         │ 2026-03-14 │ Never     │
│ ghi789 │ Working on CLI project       │ 6          │ 2026-03-13 │ 2026-06-11│
└────────┴──────────────────────────────┴────────────┴────────────┴───────────┘
```

---

### Search Memories

```bash
teotl memory search "Python programming"
```

**Output (illustrative):**
```
Found 3 memories:

┌─────────────────────────────────────────────────────────┐
│ 1. abc123                                                │
├─────────────────────────────────────────────────────────┤
│ User prefers Python over JavaScript for web development │
│                                                          │
│ Importance: 8 | Source: explicit | Created: 2026-03-15  │
└─────────────────────────────────────────────────────────┘
```

---

### Delete Memory

```bash
teotl memory delete abc123
```

**Output (illustrative):**
```
✓ Deleted memory abc123
```

All `teotl memory` subcommands accept `--path` to point at a specific database.

---

### Cleanup

```bash
# Dry run (see what would be deleted)
teotl memory cleanup --dry-run

# Actually clean up
teotl memory cleanup
```

**Output (illustrative):**
```
✓ Cleaned up 12 memories
  - Expired: 5
  - Over storage limit: 7
```

---

### Statistics

```bash
teotl memory stats
```

**Output (illustrative):**
```
┌──────────────────────────────┬────────┐
│ Metric                        │  Value │
├──────────────────────────────┼────────┤
│ Total Memories                │    234 │
│ Expired (pending cleanup)     │      5 │
│ Never Accessed                │     12 │
│ Avg Access Count              │   3.45 │
└──────────────────────────────┴────────┘

By Importance:
┌────────────┬───────┐
│ Importance │ Count │
├────────────┼───────┤
│     10     │    15 │
│      9     │    23 │
│      8     │    67 │
│      7     │    45 │
│      6     │    32 │
│      5     │    28 │
└────────────┴───────┘
```

---

### Export/Import

```bash
# Export to JSON
teotl memory export memories.json

# Import from JSON
teotl memory import-memories memories.json
```

---

## Security & Privacy

### Encryption

**EncryptedMemory** (optional, requires `cryptography`): Encrypts content at rest while keeping metadata searchable.

```python
from teotl.primitives.memory.encrypted import EncryptedMemory

# Use encrypted storage
memory = EncryptedMemory()  # Encryption key from credential store

agent = Agent(provider=provider, memory=memory)
```

**What's encrypted:**
- Memory content (the actual text)

**What's NOT encrypted:**
- Metadata (importance, tags, timestamps)
- Sanitized content for FTS search (PII removed)

### PII Detection

EncryptedMemory automatically removes PII from search index:

**Detected patterns:**
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers
- API keys and tokens

**Example:**
```python
# Store: "My email is alice@example.com"
# Encrypted: Full content encrypted
# FTS index: "My email is [EMAIL]" (PII redacted)
```

### File Permissions

Teotl does not change the database file's permissions; it is created with your default
umask. Restrict it yourself if needed (e.g. `chmod 600 ~/.forge/memory.db`).

---

## Best Practices

### 1. Use Appropriate Importance Ratings

| Rating | When to Use |
|--------|-------------|
| **10** | User's name, core identity |
| **9** | Critical preferences (always use X) |
| **8** | Strong preferences (I prefer Y) |
| **7** | Project context, technical decisions |
| **6** | Temporary project context |
| **5** | General facts, mild preferences |
| **1-4** | Transient context, debug notes |

### 2. Tag Memories for Organization

```python
# Good: Clear, specific tags
await agent.remember(
    "User prefers PostgreSQL",
    tags=["databases", "preferences", "postgres"]
)

# Bad: Vague or redundant tags
await agent.remember(
    "User prefers PostgreSQL",
    tags=["stuff", "things", "database preference for user"]
)
```

### 3. Avoid Storing Secrets

**Don't store:**
- API keys
- Passwords
- Private keys
- Access tokens

**Instead:** Use the credential store:
```python
from teotl.primitives.integrations.credential_store import CredentialStore

store = CredentialStore.create()
store.save_credential("github", {"token": "ghp_..."})
```

### 4. Clean Up Regularly

```bash
# Weekly cleanup recommended
teotl memory cleanup

# Monitor storage
teotl memory stats
```

### 5. Use TTL for Temporary Context

```python
# Don't let temporary context linger
await agent.remember(
    "Currently refactoring auth module",
    importance=5,
    ttl_days=14  # Only relevant for 2 weeks
)
```

### 6. Review Memory Periodically

```bash
# Review what's stored
teotl memory list

# Search for potentially outdated info
teotl memory search "project"

# Delete obsolete memories
teotl memory delete <id>
```

---

## Troubleshooting

### Memory Not Being Recalled

**Symptom:** Agent doesn't seem to remember things.

**Checks:**
1. Verify memory was stored:
   ```bash
   teotl memory list
   teotl memory search "what you told it"
   ```

2. Check importance (low-importance memories expire quickly)

3. Check if memory expired:
   ```bash
   teotl memory stats  # Look at "Expired (pending cleanup)"
   ```

4. Try explicit recall:
   ```python
   memories = await agent.recall("your query")
   print(f"Found {len(memories)} memories")
   ```

---

### Database Locked Errors

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Multiple processes accessing same database.

**Solution:**
- Only one agent instance per database
- Or use separate database files:
  ```python
  memory = LocalMemory("./agent1_memory.db")
  ```

---

### Too Many Memories

**Symptom:** Agent responses slow, high token usage.

**Solution:**
1. Clean up old memories:
   ```bash
   teotl memory cleanup
   ```

2. Lower the storage limit: `LocalMemory(max_memories=1000)`

3. Delete memories you no longer need (`teotl memory delete <id>`)

---

### Memories Not Persisting

**Symptom:** Memories disappear after restart.

**Cause:** Database file deleted, or a different `path` used between runs.

**Solution:**
```python
# Explicitly specify persistent path
memory = LocalMemory(path="./persistent_memory.db")

# Verify location
print(f"Memory DB: {memory.path}")
```

---

## API Reference

See [Manual Memory API](#manual-memory-api) for detailed API documentation.

---

## Future Enhancements

**Planned for post-MVP:**

- **Vector similarity search** (semantic search)
- **LLM-based extraction** (extract implicit facts)
- **Multi-agent memory sharing** (shared context)
- **Cloud sync** (sync across devices)
- **Memory summaries** (compress old memories)

---

## Related Documentation

- [Guardrails System](GUARDRAILS.md) - Safety controls
- [Skills Guide](SKILLS_GUIDE.md) - Agent capabilities

---

**Last Updated:** September 2026
