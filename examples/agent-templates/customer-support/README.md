# Customer Support Agent Template

An intelligent customer support assistant that handles inquiries, troubleshoots issues, provides product guidance, and maintains a friendly, helpful tone - scaling your support without compromising quality.

## What This Agent Does

- **💬 Answer Questions** - Provide accurate product/service information
- **🔧 Troubleshooting** - Guide customers through problem resolution
- **📚 Knowledge Base** - Search documentation and help articles
- **🎫 Ticket Management** - Track and organize support requests
- **📊 Issue Tracking** - Monitor common problems and trends
- **⏱️ Quick Responses** - Provide immediate first-level support
- **🤝 Escalation** - Know when to involve human support

## Quick Start

### 1. Set Up Your Support Agent

```bash
# Create workspace
mkdir -p ~/.teotl/agents/customer-support

# Copy template files
cp -r examples/agent-templates/customer-support/* ~/.teotl/agents/customer-support/
```

### 2. Customize for Your Product

Edit `~/.teotl/agents/customer-support/USER.md`:

- Your product/service details
- Common issues and solutions
- Support policies and procedures
- Escalation criteria
- Knowledge base locations

### 3. Start Your Support Agent

```bash
# Interactive mode
teotl chat --agent customer-support --skills filesystem,web

# The agent loads your product knowledge and support procedures
```

## Example Interactions

### Product Question

```
Customer: "How do I export my data?"

Agent: "I can help you export your data! Here's how:

**Export Your Data:**

1. Go to Settings → Account
2. Click "Export Data"
3. Select format: CSV or JSON
4. Click "Download"

Your export will be ready within 5 minutes. You'll receive an email with the download link.

**What Gets Exported:**
✅ All your projects
✅ User settings and preferences
✅ Collaboration data
✅ Activity history (last 90 days)

**Not Included:**
❌ Deleted items
❌ Shared team workspaces (export those separately)

Need help with anything else?"
```

### Troubleshooting

```
Customer: "I can't log in, it says my password is wrong but I'm sure it's correct"

Agent: "I understand how frustrating login issues can be. Let's troubleshoot this together:

**Quick Checks:**
1. ✅ Check if Caps Lock is on
2. ✅ Try copying/pasting the password
3. ✅ Clear browser cache and cookies
4. ✅ Try an incognito/private window

**Still not working?** Let's reset your password:

**Password Reset:**
1. Click "Forgot Password" on the login page
2. Enter your email: [their email if known]
3. Check your inbox (and spam folder)
4. Click the reset link (valid for 1 hour)
5. Create a new password

**Important:** Make sure you're using the correct email address. We have these accounts associated with you:
- user@example.com (active)
- old-user@example.com (inactive since 2022)

Did one of these steps work?"
```

### Escalation

```
Customer: "This is ridiculous! I've been trying to access my account for 3 days and nothing works!"

Agent: "I sincerely apologize for the frustration you've experienced over the past 3 days. That's completely unacceptable, and I want to get this resolved for you immediately.

I'm escalating this to our senior support team right now. Here's what's happening:

**Immediate Actions:**
✅ Created priority ticket #12345
✅ Escalated to senior support engineer
✅ Flagged for same-day resolution

**You'll receive:**
- Call from Sarah (Senior Support) within 2 hours
- Email with direct contact information
- Daily updates until resolved

**In the meantime:**
I've noted all the troubleshooting you've already tried. When Sarah calls, she'll have that context and won't make you repeat everything.

Is there a specific phone number or time that works best for Sarah to reach you?"
```

## Use Cases

### First-Line Support

Handle common inquiries automatically:

```bash
teotl chat --agent customer-support

> Customer: "How do I change my billing email?"
> Agent provides step-by-step instructions

> Customer: "What's included in the Pro plan?"
> Agent explains features and pricing
```

### Knowledge Base Search

Find relevant help articles:

```bash
teotl chat --agent customer-support

> Customer: "API rate limits"
> Agent searches knowledge base, provides relevant articles
> Summarizes key points with links for more info
```

### Issue Tracking

Monitor and categorize support issues:

```bash
teotl chat --agent customer-support

> Automatically categorizes: "login issue"
> Tracks frequency of this issue type
> Suggests creating help article if common
```

##Customization Guide

### Product Knowledge

Edit `USER.md` to add your product details:

```markdown
## Product Information

**Name:** [Your Product]
**Website:** [URL]
**Documentation:** [URL]

**Key Features:**
- Feature 1: [Description]
- Feature 2: [Description]

**Pricing Tiers:**
- Free: [Features, limits]
- Pro: $X/month - [Features]
- Enterprise: Custom - [Features]

**Common Use Cases:**
- Use case 1: [Description]
- Use case 2: [Description]
```

### Support Policies

Define your support approach:

```markdown
## Support Policies

**Response Time SLA:**
- Critical: 1 hour
- High: 4 hours
- Normal: 24 hours

**Escalation Criteria:**
- Customer is angry/frustrated
- Issue persists after 3 attempts
- Involves billing/refunds
- Security concern
- Bug requiring engineering

**Refund Policy:**
- Within 30 days: Full refund
- After 30 days: Prorated
- Annual plans: [Policy]
```

### Common Issues Database

Build a knowledge base:

```markdown
## Common Issues & Solutions

### Login Problems
**Symptoms:** Can't log in, password rejected
**Solutions:**
1. Password reset
2. Check email address
3. Clear cookies
4. Try different browser

### Billing Questions
**Symptoms:** Unexpected charge, need invoice
**Solutions:**
1. Check Billing page
2. Download invoices
3. Update payment method
4. Contact billing@ for disputes
```

## Best Practices

### 1. Acknowledge and Empathize

```
❌ "Reset your password"
✅ "I understand login issues are frustrating. Let's get you back in..."

❌ "You're doing it wrong"
✅ "That's a common confusion. Here's the correct process..."
```

### 2. Be Clear and Specific

```
❌ "Check the settings"
✅ "Go to Settings → Account → Privacy"

❌ "It should work soon"
✅ "Your export will be ready in 5 minutes"
```

### 3. Provide Next Steps

```
"I've done X. You should see Y. If not, try Z or contact us at [email]."
```

### 4. Know When to Escalate

Escalate when:
- Customer is frustrated/angry
- Issue requires code changes
- Involves money/billing
- Security/privacy concern
- You don't know the answer

## Template Files

```
customer-support/
├── README.md           # This file
├── PERSONALITY.md      # Agent personality
├── USER.md             # Product and policy knowledge
├── INSTRUCTIONS.md     # Support procedures
├── SKILLS.md           # Available capabilities
└── security.yaml       # Security policy
```

## Automation with Missions

Auto-respond to common questions:

```python
from forge.primitives.mission import Mission, MissionInterval

# Monitor support inbox
mission = Mission(
    description="Check support inbox for new tickets",
    interval=MissionInterval.HOURLY,
    instructions="""
    1. Check for new support emails
    2. Categorize by issue type
    3. Auto-respond to common questions
    4. Flag urgent issues for escalation
    """,
    tools=["filesystem", "web"],
)
```

---

**Start providing better support:**

```bash
teotl chat --agent customer-support --skills filesystem,web
```

*Scale your support without losing the personal touch.*
