# Agent Missions

Recurring tasks that run on a schedule to keep things running smoothly.

---

## Example: Email Monitoring

**Schedule:** Every 30 minutes
**Can be interrupted:** Yes (by URGENT+ priority tasks)
**Description:** Monitor inbox and flag important emails

### Parameters

```yaml
max_emails: 50
vip_senders:
  - boss@company.com
  - client@customer.com
auto_archive_categories:
  - newsletters
  - promotions
flag_keywords:
  - urgent
  - asap
  - deadline
  - approval needed
```

### Execution Steps

1. Check inbox for new emails since last check
2. Identify emails from VIP senders
3. Scan subject and body for urgent keywords
4. Draft brief summaries of important emails
5. Archive routine/promotional emails
6. Create HIGH priority task for emails needing response
7. Notify user only if truly urgent items found

### Success Criteria

- All VIP emails flagged within 5 minutes of receipt
- Inbox size reduced by archiving routine mail
- User notified only of truly urgent items (not noise)
- No false positives on urgent classification

---

## Example: Daily Standup

**Schedule:** Daily at 8:00 AM
**Can be interrupted:** No
**Description:** Generate daily plan and priorities

### Parameters

```yaml
review_window_hours: 24
max_priorities: 5
output_format: markdown_checklist
include_calendar: true
```

### Execution Steps

1. Review completed tasks from last 24 hours
2. Check calendar for today's meetings
3. List all pending HIGH/URGENT tasks
4. Analyze task dependencies and deadlines
5. Suggest 3-5 priorities for today
6. Flag potential scheduling conflicts
7. Estimate time required vs. available time

### Success Criteria

- Plan delivered by 8:00 AM sharp
- Priorities are specific and actionable
- No more than 5 priorities (focus over breadth)
- Conflicts flagged proactively
- Realistic given available time

---

## Example: Research Digest

**Schedule:** Daily at 6:00 PM
**Can be interrupted:** Yes (by URGENT+ priority)
**Description:** Summarize relevant news and research

### Parameters

```yaml
topics:
  - AI
  - machine learning
  - autonomous agents
  - LLM research
sources:
  - arxiv
  - hackernews
  - twitter:@karpathy
  - twitter:@ylecun
max_articles: 10
min_relevance_score: 7
```

### Execution Steps

1. Scan configured sources for new content
2. Filter content matching specified topics
3. Score each item for relevance (1-10)
4. Select top 5-10 items above threshold
5. Summarize each with key insights (2-3 sentences)
6. Highlight actionable takeaways
7. Store full digest in memory/daily/YYYY-MM-DD.md
8. Send notification with summary

### Success Criteria

- Digest contains 5-10 high-quality items
- Each summary is concise (2-3 sentences)
- At least 1 actionable insight per digest
- Sources cited with clickable links
- Delivered by 6:00 PM daily

---

## Writing Your Own Missions

### Mission Template

```markdown
## Mission Name

**Schedule:** [interval or cron expression]
**Can be interrupted:** [Yes/No]
**Description:** [One sentence describing what this mission does]

### Parameters

[YAML block with mission-specific configuration]

### Execution Steps

1. [Step 1]
2. [Step 2]
...

### Success Criteria

- [Criterion 1]
- [Criterion 2]
...
```

### Schedule Options

- **MINUTES_5** - Every 5 minutes
- **MINUTES_10** - Every 10 minutes
- **MINUTES_15** - Every 15 minutes
- **MINUTES_30** - Every 30 minutes
- **HOURLY** - Every hour
- **HOURS_2** - Every 2 hours
- **HOURS_6** - Every 6 hours
- **DAILY** - Once per day (specify time in parameters)
- **WEEKLY** - Once per week (specify day/time in parameters)

### Common Mission Types

**Monitoring Missions:**
- Email, Slack, GitHub notifications
- Server health, error logs
- Social media mentions
- News and research updates

**Reporting Missions:**
- Daily standup / weekly review
- Status reports
- Metrics summaries
- Progress tracking

**Maintenance Missions:**
- Cleanup old files
- Archive completed tasks
- Update documentation
- Sync data between systems

**Reminder Missions:**
- Break reminders
- Meeting prep
- Deadline warnings
- Habit tracking

---

## Tips for Effective Missions

1. **Be specific** - Clear parameters lead to consistent results
2. **Set success criteria** - Define what "done" looks like
3. **Start conservative** - Begin with longer intervals, speed up if needed
4. **Allow interruption** - Most missions should yield to urgent tasks
5. **Monitor and iterate** - Review mission results, adjust as needed
