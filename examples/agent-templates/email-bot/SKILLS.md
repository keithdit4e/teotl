# Email Bot Skills

These are the capabilities available to help you manage email effectively.

## Core Skills

### gmail

**What it does:**
- Read emails from Gmail inbox
- Search for specific emails
- Access email metadata (sender, subject, date)
- Read email threads and conversations
- Access labels and categories

**When to use:**
- Morning/midday/afternoon email scans
- Searching for specific emails by sender or subject
- Reading email threads for context
- Checking for urgent messages

**Limitations:**
- Read-only access (cannot send emails)
- Requires Gmail API authentication
- Subject to Gmail API rate limits

**Example tasks:**
```
"Check inbox for urgent emails"
"Find all emails from sarah@company.com today"
"Read the email thread about Project Alpha"
"List unread emails from the last 2 hours"
```

### calendar

**What it does:**
- Check calendar availability
- View scheduled meetings
- Detect meeting conflicts
- See free/busy times

**When to use:**
- Processing meeting requests
- Suggesting available time slots
- Identifying schedule conflicts
- Planning response times

**Limitations:**
- Read-only access (cannot create events)
- Requires calendar API authentication

**Example tasks:**
```
"Check if I'm free Tuesday at 2pm"
"What meetings do I have tomorrow?"
"Find 3 available 1-hour slots this week"
"Check for conflicts with the proposed meeting time"
```

### web

**What it does:**
- Search the web for information
- Look up company/contact information
- Research topics mentioned in emails
- Verify links and references

**When to use:**
- Need context about a sender or company
- Verify information before responding
- Research topics for better responses
- Check if links are safe

**Limitations:**
- General web search, not email-specific
- May return outdated information
- Requires internet connection

**Example tasks:**
```
"Look up Acme Corp to understand their business"
"Search for background on this conference mentioned in the email"
"Verify this sender's company website"
"Find information about the product mentioned"
```

## Optional Enhancement Skills

These skills can be added for additional functionality:

### filesystem (optional)

**What it does:**
- Save email attachments
- Create folders for email organization
- Store email templates locally

**When to use:**
- User wants to save attachments from emails
- Creating local backup of important emails
- Managing email templates

**How to enable:**
```bash
teotl chat --agent email-bot --skills gmail,calendar,web,filesystem
```

### database (optional)

**What it does:**
- Track email metrics over time
- Store email categorizations
- Build historical analytics

**When to use:**
- User wants email analytics
- Tracking response time trends
- Building custom reports

**How to enable:**
```bash
teotl chat --agent email-bot --skills gmail,calendar,web,database
```

## Skill Combinations

### Standard Email Management
```bash
teotl chat --agent email-bot --skills gmail,calendar,web
```
**Best for:** Daily email processing, response drafting, meeting coordination

### Email + File Management
```bash
teotl chat --agent email-bot --skills gmail,calendar,web,filesystem
```
**Best for:** Handling attachments, saving important emails, template management

### Email + Analytics
```bash
teotl chat --agent email-bot --skills gmail,calendar,web,database
```
**Best for:** Power users who want metrics, trends, and historical analysis

## Skill Usage Guidelines

### When Reading Emails

1. **Use gmail skill** to access inbox
2. **Categorize** based on INSTRUCTIONS.md priority system
3. **Use calendar skill** if email mentions meetings
4. **Use web skill** if context/research needed

### When Drafting Responses

1. **Use gmail skill** to read email thread for context
2. **Use web skill** if need to verify information
3. **Use calendar skill** if suggesting meeting times
4. **Draft response** following user's communication style

### When Processing Meeting Requests

1. **Use gmail skill** to read meeting request details
2. **Use calendar skill** to check availability
3. **Draft response** with available time slots
4. **Avoid** scheduling during blocked times (USER.md)

## Authentication Requirements

### Gmail Skill
Requires Gmail API OAuth2 authentication:
- Scopes: `gmail.readonly`
- Setup: Follow Gmail API quickstart guide
- Credentials: Store in `~/.teotl/agents/email-bot/credentials.json`

### Calendar Skill
Requires Google Calendar API authentication:
- Scopes: `calendar.readonly`
- Setup: Can use same OAuth2 flow as Gmail
- Credentials: Same credentials file as Gmail

### Web Skill
No authentication required (public web search)

## Troubleshooting

### "Gmail skill not available"
**Solution:**
1. Install required packages: `pip install google-auth google-auth-oauthlib google-api-python-client`
2. Set up Gmail API credentials
3. Run OAuth2 flow to authorize access

### "Calendar skill not available"
**Solution:**
1. Ensure Calendar API is enabled in Google Cloud Console
2. Use same credentials as Gmail
3. Re-run OAuth2 flow with calendar scope

### "Rate limit exceeded"
**Solution:**
1. Gmail API has rate limits (usually 25,000 calls/day)
2. Reduce email checking frequency
3. Request quota increase from Google Cloud Console

## Privacy and Security

### Data Access

**Gmail skill can access:**
- ✅ Email content (for reading and categorization)
- ✅ Email metadata (sender, date, subject)
- ✅ Labels and categories
- ❌ Cannot send emails
- ❌ Cannot delete emails
- ❌ Cannot modify labels

**Calendar skill can access:**
- ✅ Event times and descriptions
- ✅ Attendee lists
- ✅ Free/busy status
- ❌ Cannot create events
- ❌ Cannot modify events
- ❌ Cannot delete events

**Web skill can access:**
- ✅ Public web pages
- ❌ No access to email or calendar

### Security Policy

All skill access is governed by `security.yaml`:
- Filesystem access limited to safe directories
- Network access restricted to approved domains
- All sensitive operations require user confirmation

See `security.yaml` in this template for specific policies.

---

*These skills provide the capabilities needed for effective email management. Additional skills can be enabled based on specific needs.*
