# Email Bot Agent Template

An intelligent email assistant that helps you achieve inbox zero, prioritize messages, draft responses, and manage your calendar - all while respecting your communication style and preferences.

## What This Agent Does

- **📧 Inbox Monitoring** - Scans inbox at scheduled times for urgent emails
- **🎯 Smart Prioritization** - Categorizes emails: Urgent, Important, FYI, Low
- **✍️ Response Drafting** - Writes email replies matching your voice and style
- **📅 Calendar Integration** - Checks availability and suggests meeting times
- **🤖 Auto-Archive** - Automatically archives low-priority emails based on rules
- **📊 Email Analytics** - Tracks response times, volume, and follow-ups
- **🔔 Smart Notifications** - Alerts you only for truly urgent matters

## Quick Start

### 1. Set Up Your Email Bot

```bash
# Create your email bot workspace
mkdir -p ~/.teotl/agents/email-bot

# Copy template files
cp -r examples/agent-templates/email-bot/* ~/.teotl/agents/email-bot/
```

### 2. Customize Your Profile

Edit `~/.teotl/agents/email-bot/USER.md` to include:

- Your name, email, and working hours
- Priority contacts (boss, key clients)
- Email handling preferences
- Meeting schedule and blocks
- Current projects and context

**Important:** This is how the bot learns your preferences!

### 3. Configure Authentication

Set up Gmail and Calendar API access:

```bash
# Install required packages
pip install google-auth google-auth-oauthlib google-api-python-client

# Follow Gmail API quickstart to get credentials
# Save to: ~/.teotl/agents/email-bot/credentials.json
```

See [Gmail API Quickstart](https://developers.google.com/gmail/api/quickstart/python) for detailed setup.

### 4. Start Your Email Bot

#### Interactive Mode (Recommended)

```bash
# Start interactive chat with your email bot
teotl chat --agent email-bot --skills gmail,calendar,web

# The bot will greet you and load your preferences
# Try: "Check my inbox for urgent emails"
```

#### Daemon Mode (Background)

```bash
# Run email bot in background
python3 -m forge.daemon start --agent email-bot

# Check status
python3 -m forge.daemon status --agent email-bot

# View in web dashboard
python3 -m forge.web
# Open: http://localhost:8080
```

## Example Interactions

### Morning Email Scan

```
You: "Do my morning email scan"

Bot: "Good morning! Scanning your inbox...

📧 **5 Urgent Emails:**
1. Sarah (Project Alpha) - "Need approval by 10am" [DEADLINE]
2. Boss - "Quick sync today?" [MEETING REQUEST]
...

📧 **12 Important Emails:**
1. John - "Code review for PR #234"
2. Client - "Questions about Q2 roadmap"
...

Would you like me to summarize the urgent emails first?"
```

### Draft a Response

```
You: "Draft a response to Sarah's email about Project Alpha"

Bot: "I've read the thread. Sarah is asking for approval on the new feature design.

**Draft Response:**

Hi Sarah,

Thanks for sending this over. The design looks great - I especially like the simplified user flow.

Approved to move forward. Let me know if you need anything else.

Best regards,
[Your Name]

Should I save this draft for you to review in Gmail?"
```

### Meeting Request

```
You: "Someone wants to meet next week, when am I free?"

Bot: "I've checked your calendar. You're available:

📅 **Tuesday, March 30**
- 10:00 AM - 11:00 AM
- 2:00 PM - 3:00 PM

📅 **Wednesday, March 31**
- 9:00 AM - 10:00 AM
- 3:00 PM - 4:00 PM

📅 **Thursday, April 1**
- 11:00 AM - 12:00 PM

Which would you prefer, and should I draft a response?"
```

## Customization Guide

### Adjusting Personality

Edit `PERSONALITY.md` to change:

- **Communication style** - Formal vs casual tone
- **Proactiveness** - How much initiative to take
- **Summarization level** - Brief vs detailed
- **Priorities** - What matters most to you

### Modifying Instructions

Edit `INSTRUCTIONS.md` to customize:

- **Email check schedule** - Times to scan inbox
- **Priority rules** - What counts as urgent/important
- **Auto-archive rules** - What to automatically archive
- **Response templates** - Pre-written response formats
- **Meeting preferences** - Scheduling constraints

### Security Policy

Edit `security.yaml` to adjust:

- **Allowed directories** - Where files can be saved
- **Allowed domains** - What websites can be accessed
- **Confirmation requirements** - What needs approval
- **Rate limits** - API call frequency limits

### Adding Skills

Add more capabilities by enabling additional skills:

```bash
# Add filesystem (attachment management)
teotl chat --agent email-bot --skills gmail,calendar,web,filesystem

# Add database (email analytics)
teotl chat --agent email-bot --skills gmail,calendar,web,database

# Add git (for development coordination)
teotl chat --agent email-bot --skills gmail,calendar,web,git
```

## Automation with Missions

Set up recurring email tasks:

```python
from forge.primitives.mission import Mission, MissionInterval
from forge.primitives.mission.store import MissionStore

# Create daily morning email scan
mission = Mission(
    description="Morning email scan and summary",
    interval=MissionInterval.DAILY,
    instructions="Check inbox, categorize emails, notify about urgent items",
    tools=["gmail", "calendar"],
)

# Store mission
store = MissionStore.get_default_store()
await store.save(mission)
```

Then the email bot will automatically scan your inbox every morning!

## Use Cases

### Daily Email Management

**Schedule:** Morning, Midday, Afternoon scans

**What it does:**
- Categorizes all new emails
- Flags urgent items for immediate attention
- Archives low-priority emails
- Drafts responses for important emails
- Summarizes email activity

### Meeting Coordination

**Trigger:** Meeting request received

**What it does:**
- Checks calendar for conflicts
- Suggests 2-3 available time slots
- Respects your meeting preferences
- Drafts reply with availability
- Creates calendar event after approval

### Project Email Tracking

**Context:** Current projects from USER.md

**What it does:**
- Groups emails by project
- Tracks action items per project
- Notifies about project deadlines
- Maintains project context across threads
- Suggests responses using project knowledge

### Client Communication

**Context:** Priority contacts from USER.md

**What it does:**
- Prioritizes client emails as urgent
- Drafts professional, solution-oriented responses
- Ensures timely responses (<2 hours)
- Maintains formal tone
- Tracks client conversation history

## Best Practices

### 1. Keep USER.md Updated

Your email bot is only as good as the context you provide:

- **Update priority contacts** when they change
- **Add new projects** so bot understands context
- **Document preferences** as you discover them
- **Review monthly** to keep information current

### 2. Review Drafts Before Sending

The bot drafts responses but YOU send them:

- Always review for accuracy
- Check tone matches situation
- Verify all facts and dates
- Edit to add personal touches

### 3. Provide Feedback

Help your bot learn:

```
You: "That draft was too formal, I know Sarah well"
Bot: "Got it, I'll use a more casual tone with Sarah next time."
```

The bot learns from your edits and feedback.

### 4. Set Realistic Expectations

The email bot helps with:
- ✅ Categorization and prioritization
- ✅ Drafting routine responses
- ✅ Scheduling and calendar checks
- ✅ Reducing email overwhelm

The bot needs you for:
- ❌ Final decision on sending emails
- ❌ Complex negotiations
- ❌ Sensitive conversations
- ❌ Strategic communication

### 5. Monitor the Dashboard

Use the web dashboard to track:

```bash
python3 -m forge.web --agents email-bot
```

- Response time trends
- Email volume patterns
- Categories distribution
- Follow-up completion rate

## Troubleshooting

### "Gmail skill not available"

**Cause:** Gmail API not set up or credentials missing

**Fix:**
1. Follow [Gmail API Quickstart](https://developers.google.com/gmail/api/quickstart/python)
2. Save `credentials.json` to `~/.teotl/agents/email-bot/credentials.json`
3. Run OAuth flow: `python3 gmail_auth.py`

### "Calendar skill not available"

**Cause:** Calendar API not enabled

**Fix:**
1. Enable Calendar API in Google Cloud Console
2. Add calendar scope to OAuth consent screen
3. Re-run OAuth flow with calendar permissions

### Bot is too aggressive/not aggressive enough

**Cause:** Priority rules don't match your needs

**Fix:** Edit `INSTRUCTIONS.md` and adjust:
- Auto-archive rules
- Priority categorization rules
- Notification thresholds

### Bot uses wrong tone in drafts

**Cause:** Personality doesn't match your style

**Fix:**
1. Edit `PERSONALITY.md` communication style
2. Provide feedback: "That was too formal"
3. Review past emails to help bot learn your voice

### Missing context in responses

**Cause:** USER.md doesn't have enough project/contact info

**Fix:**
1. Update `USER.md` with current projects
2. Add context about ongoing conversations
3. Specify relationships with key contacts

## Security & Privacy

### What Data is Accessed

**Email Bot CAN:**
- ✅ Read emails (with your permission)
- ✅ Check calendar availability
- ✅ Search the web for context
- ✅ Save drafts locally

**Email Bot CANNOT:**
- ❌ Send emails (requires your approval)
- ❌ Delete emails (requires your approval)
- ❌ Modify calendar (requires your approval)
- ❌ Access emails without permission

### Privacy Protections

From `security.yaml`:

- **Email content never logged** - Only metadata stored
- **PII redacted** - Email addresses, phones removed from logs
- **Encrypted storage** - Local data is encrypted
- **90-day retention** - Old data automatically deleted
- **Audit log** - All actions tracked for review

### OAuth Security

Gmail/Calendar access uses OAuth2:

- **Scopes:** `gmail.readonly` and `calendar.readonly`
- **Tokens stored locally** - Never sent to external servers
- **Revocable anytime** - Via Google account settings
- **Refresh tokens** - Auto-refresh without re-auth

## Advanced Configuration

### Custom Response Templates

Add your own templates to `INSTRUCTIONS.md`:

```markdown
### For Customer Inquiries

"Thanks for reaching out about [product/service].

[Answer their specific question]

Is there anything else I can help clarify?

Best regards,"
```

### Integration with Other Tools

Connect email bot to other services:

```python
# Slack notifications for urgent emails
from forge.integrations.slack import SlackNotifier

notifier = SlackNotifier(webhook_url="...")
await notifier.send(f"Urgent email from {sender}: {subject}")
```

### Custom Email Filters

Add advanced filtering in `INSTRUCTIONS.md`:

```markdown
### Custom Filters

**Auto-archive if:**
- Subject contains "newsletter" AND sender not in priority list
- From domain ends with ".marketing"
- Age > 7 days AND unread

**Auto-flag if:**
- Subject matches regex: "(budget|invoice|payment)"
- Body contains: "[Your Name]" (direct mention)
```

## Getting Help

- **Documentation:** See `INSTRUCTIONS.md` for operating procedures
- **Skills:** See `SKILLS.md` for capabilities
- **Security:** See `security.yaml` for policy details
- **Issues:** Report problems at [teotl/issues](https://github.com/yourusername/teotl/issues)

## Template Files

```
email-bot/
├── README.md           # This file - usage guide
├── PERSONALITY.md      # Bot's personality and communication style
├── USER.md             # Your profile and preferences
├── INSTRUCTIONS.md     # Operating procedures and rules
├── SKILLS.md           # Available capabilities
└── security.yaml       # Security policy
```

## Contributing Improvements

Found a better way to handle emails? Improve this template:

1. Fork the repository
2. Edit template files
3. Test with your email workflow
4. Submit pull request

Share your improvements with the community!

---

**Start managing your email intelligently:**

```bash
teotl chat --agent email-bot --skills gmail,calendar,web
```

*Achieve inbox zero without the stress.*
