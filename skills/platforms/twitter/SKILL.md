---
name: twitter
version: 1.0.0
description: "Post tweets, threads, and engage on X (Twitter)"
auth: browser-session
triggers:
  - twitter
  - x.com
  - tweet
  - thread
---

# X (Twitter) Automation

Deterministic browser automation for X/Twitter posting and engagement.

## Prerequisites

Ensure browser session is active:
```python
browser = BrowserTool()
await browser.launch()

if not await browser.ensure_logged_in("twitter"):
    await browser.login("twitter")
```

## Selectors Reference (Updated: 2026-06)

```yaml
# URLs
home_url: "https://x.com/home"
compose_url: "https://x.com/compose/tweet"
profile_url: "https://x.com/me"

# Tweet Composition
compose_button: "a[href='/compose/tweet']"
tweet_editor: "div[data-testid='tweetTextarea_0']"
tweet_editor_nth: "div[data-testid='tweetTextarea_{n}']"  # For threads
post_button: "button[data-testid='tweetButton']"
add_tweet_button: "button[data-testid='addButton']"

# Media Upload
media_button: "button[aria-label='Add photos or video']"
media_input: "input[type='file'][accept='image/*,video/*']"
media_preview: "div[data-testid='attachments']"
gif_button: "button[aria-label='Add a GIF']"

# Post Success
tweet_success: "div[data-testid='toast']"

# Feed Reading
timeline: "div[data-testid='primaryColumn']"
tweet_article: "article[data-testid='tweet']"
tweet_text: "div[data-testid='tweetText']"
tweet_author: "div[data-testid='User-Name']"

# Engagement
like_button: "button[data-testid='like']"
unlike_button: "button[data-testid='unlike']"
retweet_button: "button[data-testid='retweet']"
reply_button: "button[data-testid='reply']"
bookmark_button: "button[data-testid='bookmark']"

# Reply/Quote
reply_editor: "div[data-testid='tweetTextarea_0']"
quote_tweet_option: "a[href*='/compose/tweet']"
```

## Create Tweets

### Single Tweet

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/compose/tweet"),
    BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=TWEET_CONTENT),
    BrowserAction(action="click", selector="button[data-testid='tweetButton']"),
    BrowserAction(action="wait_for", selector="div[data-testid='toast']", timeout=10),
]

result = await browser.execute(actions)
```

### Tweet with Image

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/compose/tweet"),
    BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    BrowserAction(action="upload", selector="input[type='file'][accept='image/*,video/*']", value=IMAGE_PATH),
    BrowserAction(action="wait_for", selector="div[data-testid='attachments']"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=TWEET_CONTENT),
    BrowserAction(action="click", selector="button[data-testid='tweetButton']"),
    BrowserAction(action="wait_for", selector="div[data-testid='toast']", timeout=15),
]
```

### Tweet with Multiple Images (up to 4)

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/compose/tweet"),
    BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    # Upload multiple images
    BrowserAction(action="upload", selector="input[type='file']", value=IMAGE_PATHS),  # List of paths
    BrowserAction(action="wait_for", selector="div[data-testid='attachments']"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=TWEET_CONTENT),
    BrowserAction(action="click", selector="button[data-testid='tweetButton']"),
]
```

## Create Thread

```python
async def create_thread(browser, tweets: list[str]):
    """Create a Twitter thread with multiple tweets."""

    actions = [
        BrowserAction(action="goto", value="https://x.com/compose/tweet"),
        BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    ]

    for i, tweet_content in enumerate(tweets):
        # Fill current tweet
        actions.append(
            BrowserAction(
                action="fill",
                selector=f"div[data-testid='tweetTextarea_{i}']",
                value=tweet_content
            )
        )

        # Add next tweet (except for last one)
        if i < len(tweets) - 1:
            actions.append(
                BrowserAction(action="click", selector="button[data-testid='addButton']")
            )
            actions.append(
                BrowserAction(
                    action="wait_for",
                    selector=f"div[data-testid='tweetTextarea_{i+1}']"
                )
            )

    # Post the thread
    actions.append(
        BrowserAction(action="click", selector="button[data-testid='tweetButton']")
    )
    actions.append(
        BrowserAction(action="wait_for", selector="div[data-testid='toast']", timeout=15)
    )

    return await browser.execute(actions)
```

### Thread Example

```python
thread_tweets = [
    "1/ Here's what I learned building AI agents this week:",
    "2/ First insight: Keep your prompts simple. Complex prompts often confuse the model more than they help.",
    "3/ Second insight: Tool calls are powerful but expensive. Cache when possible.",
    "4/ Third insight: Always have a human in the loop for critical decisions.",
    "5/ That's it! Follow for more AI engineering insights."
]

await create_thread(browser, thread_tweets)
```

## Read Timeline

### Get Recent Tweets

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/home"),
    BrowserAction(action="wait_for", selector="article[data-testid='tweet']"),
    BrowserAction(action="query_all", selector="article[data-testid='tweet']"),
]

result = await browser.execute(actions)
```

### Extract Tweet Content

```python
# For each tweet article
tweet_actions = [
    BrowserAction(action="query", selector="article:nth-child(1) div[data-testid='tweetText']"),
    BrowserAction(action="query", selector="article:nth-child(1) div[data-testid='User-Name']"),
]
```

## Engagement

### Like a Tweet

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/home"),
    BrowserAction(action="wait_for", selector="article[data-testid='tweet']"),
    BrowserAction(action="click", selector="article:first-child button[data-testid='like']"),
]
```

### Retweet

```python
actions = [
    BrowserAction(action="click", selector="article:first-child button[data-testid='retweet']"),
    BrowserAction(action="wait_for", selector="div[data-testid='Dropdown']"),
    BrowserAction(action="click", selector="div[data-testid='retweetConfirm']"),
]
```

### Reply to Tweet

```python
actions = [
    BrowserAction(action="click", selector="article:first-child button[data-testid='reply']"),
    BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=REPLY_TEXT),
    BrowserAction(action="click", selector="button[data-testid='tweetButton']"),
]
```

### Quote Tweet

```python
actions = [
    BrowserAction(action="click", selector="article:first-child button[data-testid='retweet']"),
    BrowserAction(action="wait_for", selector="div[data-testid='Dropdown']"),
    BrowserAction(action="click", selector="a[href*='/compose/tweet']"),  # Quote option
    BrowserAction(action="wait_for", selector="div[data-testid='tweetTextarea_0']"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=QUOTE_COMMENT),
    BrowserAction(action="click", selector="button[data-testid='tweetButton']"),
]
```

## Content Guidelines

### Character Limits
- Standard accounts: 280 characters
- Premium accounts: 25,000 characters
- Thread tweets: Each limited to account limit

### Thread Best Practices
1. **Number your tweets** - "1/", "2/", etc.
2. **First tweet is hook** - Most important, sets thread tone
3. **Each tweet standalone** - Should make sense alone
4. **Natural breakpoints** - Split at complete thoughts
5. **Last tweet CTA** - Ask for follow/engagement

### Tweet Format Templates

**Single Tweet:**
```
[Hook/insight]

[Supporting detail or data]

[Call to action or question]
```

**Thread Opener:**
```
[Number]/ [Compelling hook or question]

A thread:
```

### Optimal Timing
- Weekdays: 8-10am, 12-1pm, 5-6pm
- Weekends: 9-11am
- Best days: Tuesday, Wednesday, Thursday

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Editor not found | Page not loaded | Wait for networkidle |
| Post button disabled | Content empty/invalid | Check content length |
| Rate limited | Too many actions | Wait 15+ minutes |
| Tweet failed | Duplicate content | Modify tweet text |

### Check for Rate Limit

```python
# After posting, check for error toast
error_check = [
    BrowserAction(action="query", selector="div[data-testid='toast'][role='alert']"),
]
result = await browser.execute(error_check)

if "rate limit" in result.get("text", "").lower():
    raise RateLimitError("Twitter rate limit reached")
```

## Scheduling (via UI)

X Premium users can schedule tweets:

```python
actions = [
    BrowserAction(action="goto", value="https://x.com/compose/tweet"),
    BrowserAction(action="fill", selector="div[data-testid='tweetTextarea_0']", value=TWEET_CONTENT),
    BrowserAction(action="click", selector="button[aria-label='Schedule']"),
    BrowserAction(action="wait_for", selector="div[aria-label='Schedule']"),
    # Select date/time...
    BrowserAction(action="click", selector="button[data-testid='scheduleConfirm']"),
]
```

## Session Management

### Persist Login
```python
await browser.login("twitter", credentials)
await browser.save_session("twitter")
```

### Handle MFA
```python
async def mfa_callback(prompt):
    # Get MFA code from user
    return input(prompt)

await browser.login("twitter", credentials, mfa_callback=mfa_callback)
```

## Security Considerations

1. **Rate limits** - Max ~300 tweets/day, lower for new accounts
2. **Account standing** - Automation can trigger reviews
3. **Human-like delays** - Add 1-3 second delays between actions
4. **Session rotation** - Don't run 24/7 from same session
5. **Content policies** - Respect Twitter's terms of service

---

**Remember**: X has strict automation policies. Excessive automation may result in account restrictions.
