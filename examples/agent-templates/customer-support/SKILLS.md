# Customer Support Skills

Essential capabilities for providing excellent customer support.

## Core Skills

### filesystem

**What it does:**
- Read product documentation
- Access knowledge base articles
- Read solution databases
- Save support tickets/notes
- Track common issues

**When to use:**
- Looking up solutions to common issues
- Accessing support documentation
- Reading product guides
- Saving ticket information

**Limitations:**
- Subject to security policy
- Cannot access customer data outside allowed paths

**Example tasks:**
```
"Look up the solution for login issues in common-issues.md"
"Read the billing policy documentation"
"Save this support ticket to tickets/ticket-12345.md"
```

### web

**What it does:**
- Search online help center
- Access product documentation website
- Check service status pages
- Find community forum discussions
- Look up error codes

**When to use:**
- Need to find help articles
- Check if service is down
- Look up error messages
- Find community solutions

**Limitations:**
- Public web access only
- Cannot access customer accounts
- Cannot make changes to websites

**Example tasks:**
```
"Check the status page for any outages"
"Search the help center for 'export data'"
"Find the API documentation for rate limits"
```

## Skill Combinations

### Standard Support (Recommended)
```bash
teotl chat --agent customer-support --skills filesystem,web
```
**Best for:** Answering questions, troubleshooting, accessing documentation

### Documentation Only
```bash
teotl chat --agent customer-support --skills filesystem
```
**Best for:** Offline support using local knowledge base

## Support Workflows

### Answer Product Question
1. **Check filesystem** for common questions document
2. **Use web** if need to access online help center
3. Provide clear, step-by-step answer
4. Link to relevant documentation

### Troubleshoot Issue
1. **Check filesystem** for known issues and solutions
2. **Use web** to check status page for outages
3. **Use web** to search for error messages
4. Guide customer through troubleshooting steps
5. Escalate if unresolved

### Billing Question
1. **Check filesystem** for billing policies
2. **Check filesystem** for pricing documentation
3. Explain clearly with examples
4. Provide links to billing help articles
5. Escalate if requires manual intervention

### Bug Report
1. **Check filesystem** to see if known bug
2. **Use web** to check if already reported
3. Document bug details
4. **Save to filesystem** for tracking
5. Escalate to engineering

## Knowledge Base Organization

### Suggested Structure

```
~/Support/
├── common-issues/
│   ├── login.md
│   ├── billing.md
│   ├── technical.md
│   └── features.md
├── policies/
│   ├── refund-policy.md
│   ├── sla.md
│   └── escalation.md
├── docs/
│   ├── getting-started.md
│   ├── features.md
│   └── api.md
└── tickets/
    ├── ticket-12345.md
    └── ticket-12346.md
```

### Common Issues File Example

```markdown
# Login Issues

## Password Reset

**Symptoms:**
- User can't remember password
- Password not working

**Solution:**
1. Click "Forgot Password" on login page
2. Enter email address
3. Check email (and spam folder)
4. Click reset link (valid 1 hour)
5. Create new password

**Escalate if:** Reset email not received after 10 minutes

## Wrong Email Address

**Symptoms:**
- Password reset not working
- Account not found

**Solution:**
1. Ask customer for email address they used
2. Check against known variants (work vs personal)
3. Try password reset with each email
4. If found, update customer's records

**Escalate if:** No account found with any email variant
```

## Response Templates

### Account Access Issues
```markdown
"Let's get you back into your account:

**Password Reset:**
1. Go to [login URL]
2. Click 'Forgot Password'
3. Enter your email: [email]
4. Check your inbox (and spam) for reset link
5. Link expires in 1 hour

**Still having trouble?**
- Make sure you're using the correct email
- Try a different browser
- Clear your cookies

Let me know if this works!"
```

### Feature Explanation
```markdown
"Here's how [Feature] works:

**What it does:**
[Clear explanation]

**How to use it:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Example:**
[Concrete example]

**Learn more:** [Link to documentation]

Want me to walk you through it?"
```

### Escalation Message
```markdown
"I'm escalating this to our [team] for specialized help.

**What happens next:**
- [Person/Team] will contact you within [timeframe]
- Via [method]
- Ticket #: [number]

They'll have all the context from our conversation.

Is there anything else I can help with while we wait?"
```

## Best Practices

### Knowledge Base Management

**Keep it current:**
- Update solutions when product changes
- Add new common issues
- Remove outdated information
- Test all troubleshooting steps

**Organize clearly:**
- Use consistent structure
- Clear headings and sections
- Include search keywords
- Cross-reference related issues

**Document everything:**
- Common questions
- Troubleshooting steps
- Escalation criteria
- Resolution outcomes

### Ticket Management

**Save important interactions:**
```markdown
# Ticket #12345

**Customer:** customer@example.com
**Date:** 2026-03-27
**Issue:** Cannot export data
**Category:** Technical

**Resolution:**
- Provided step-by-step export instructions
- Verified customer had Pro plan (required for export)
- Sent documentation link
- Issue resolved in first contact

**Status:** Closed
**CSAT:** 5/5
```

**Track patterns:**
- Note frequently asked questions
- Identify product issues
- Suggest documentation improvements
- Report bugs to engineering

## Limitations

### Cannot Access
- ❌ Customer account data (passwords, payment info)
- ❌ Internal admin systems
- ❌ Customer databases
- ❌ Billing systems

### Cannot Perform
- ❌ Make refunds (escalate)
- ❌ Delete accounts (escalate)
- ❌ Change billing (escalate)
- ❌ Fix bugs (escalate)

### Can Do
- ✅ Answer questions
- ✅ Provide documentation
- ✅ Guide troubleshooting
- ✅ Escalate when needed

## Troubleshooting

### "Can't find solution in knowledge base"

**Fix:**
- Try different search terms
- Check online help center (web skill)
- Look for similar issues
- Create new documentation if gap identified

### "Documentation is outdated"

**Fix:**
- Note what's outdated
- Find current information online
- Flag for documentation team
- Use current information for customer

### "Need to access customer account"

**Fix:**
- Never access customer accounts directly
- Ask customer to check their account
- Guide them through checking
- Escalate if needs admin access

---

*These skills provide the tools needed for effective customer support. Combine with product knowledge from USER.md for best results.*
