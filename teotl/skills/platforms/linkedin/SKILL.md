---
name: linkedin
version: 1.0.0
description: "Post, engage, and manage content on LinkedIn"
auth: browser-session
triggers:
  - linkedin
  - professional network
  - career
  - business post
---

# LinkedIn Automation

Deterministic browser automation for LinkedIn posting and engagement.

## Prerequisites

Ensure browser session is active:
```python
browser = BrowserTool()
await browser.launch()

if not await browser.ensure_logged_in("linkedin"):
    await browser.login("linkedin")
```

## Selectors Reference (Updated: 2026-06)

```yaml
# URLs
feed_url: "https://www.linkedin.com/feed/"
profile_url: "https://www.linkedin.com/in/me/"
post_url: "https://www.linkedin.com/feed/?shareActive=true"

# Post Creation
post_trigger: "button.share-box-feed-entry__trigger"
post_modal: "div.share-box"
post_editor: "div.ql-editor[data-placeholder]"
post_submit: "button.share-actions__primary-action"
post_success: "div.artdeco-toast-item--visible"

# Media Upload
media_button: "button[aria-label='Add media']"
image_input: "input[type='file'][accept='image/*']"
document_input: "input[type='file'][accept='.pdf,.ppt,.pptx,.doc,.docx']"
image_preview: "div.share-box-image-preview"

# Post Options
visibility_button: "button.share-state-button"
visibility_anyone: "button[data-test-share-to-visibility-option='PUBLIC']"
visibility_connections: "button[data-test-share-to-visibility-option='CONNECTIONS']"

# Feed Reading
feed_posts: "div.feed-shared-update-v2"
post_author: "span.feed-shared-actor__name"
post_content: "div.feed-shared-text"
post_time: "span.feed-shared-actor__sub-description"
like_button: "button[aria-label*='Like']"
comment_button: "button[aria-label*='Comment']"
```

## Create Posts

### Text Post

```python
actions = [
    BrowserAction(action="goto", value="https://www.linkedin.com/feed/"),
    BrowserAction(action="click", selector="button.share-box-feed-entry__trigger"),
    BrowserAction(action="wait_for", selector="div.ql-editor"),
    BrowserAction(action="fill", selector="div.ql-editor", value=POST_CONTENT),
    BrowserAction(action="click", selector="button.share-actions__primary-action"),
    BrowserAction(action="wait_for", selector="div.artdeco-toast-item--visible", timeout=10),
]

result = await browser.execute(actions)
```

### Post with Image

```python
actions = [
    BrowserAction(action="goto", value="https://www.linkedin.com/feed/"),
    BrowserAction(action="click", selector="button.share-box-feed-entry__trigger"),
    BrowserAction(action="wait_for", selector="div.share-box"),
    BrowserAction(action="click", selector="button[aria-label='Add media']"),
    BrowserAction(action="upload", selector="input[type='file'][accept='image/*']", value=IMAGE_PATH),
    BrowserAction(action="wait_for", selector="div.share-box-image-preview"),
    BrowserAction(action="fill", selector="div.ql-editor", value=POST_CONTENT),
    BrowserAction(action="click", selector="button.share-actions__primary-action"),
    BrowserAction(action="wait_for", selector="div.artdeco-toast-item--visible", timeout=15),
]
```

### Post with Document (PDF/PPT)

```python
actions = [
    BrowserAction(action="goto", value="https://www.linkedin.com/feed/"),
    BrowserAction(action="click", selector="button.share-box-feed-entry__trigger"),
    BrowserAction(action="wait_for", selector="div.share-box"),
    BrowserAction(action="click", selector="button[aria-label='Add document']"),
    BrowserAction(action="upload", selector="input[type='file'][accept='.pdf,.ppt,.pptx']", value=DOC_PATH),
    BrowserAction(action="wait_for", selector="div.share-box-document-preview", timeout=30),
    BrowserAction(action="fill", selector="input[placeholder='Add a title']", value=DOC_TITLE),
    BrowserAction(action="fill", selector="div.ql-editor", value=POST_CONTENT),
    BrowserAction(action="click", selector="button.share-actions__primary-action"),
]
```

### Set Post Visibility

```python
# Before submitting, change visibility
actions = [
    # ... post creation actions ...
    BrowserAction(action="click", selector="button.share-state-button"),
    BrowserAction(action="click", selector="button[data-test-share-to-visibility-option='CONNECTIONS']"),
    # Then submit
    BrowserAction(action="click", selector="button.share-actions__primary-action"),
]
```

## Read Feed

### Get Recent Posts

```python
actions = [
    BrowserAction(action="goto", value="https://www.linkedin.com/feed/"),
    BrowserAction(action="wait_for", selector="div.feed-shared-update-v2"),
    BrowserAction(action="query_all", selector="div.feed-shared-update-v2"),
]

result = await browser.execute(actions)

# Parse individual posts
for i in range(min(10, len(posts))):
    post_actions = [
        BrowserAction(action="query", selector=f"div.feed-shared-update-v2:nth-child({i+1}) span.feed-shared-actor__name"),
        BrowserAction(action="query", selector=f"div.feed-shared-update-v2:nth-child({i+1}) div.feed-shared-text"),
    ]
```

## Engagement

### Like a Post

```python
# Like the first post in feed
actions = [
    BrowserAction(action="goto", value="https://www.linkedin.com/feed/"),
    BrowserAction(action="wait_for", selector="div.feed-shared-update-v2"),
    BrowserAction(action="click", selector="div.feed-shared-update-v2:first-child button[aria-label*='Like']"),
]
```

### Comment on a Post

```python
actions = [
    BrowserAction(action="click", selector="div.feed-shared-update-v2:first-child button[aria-label*='Comment']"),
    BrowserAction(action="wait_for", selector="div.comments-comment-box__form"),
    BrowserAction(action="fill", selector="div.ql-editor[data-placeholder='Add a comment']", value=COMMENT_TEXT),
    BrowserAction(action="click", selector="button.comments-comment-box__submit-button"),
]
```

## Content Guidelines

### Character Limits
- Post: 3,000 characters max
- First line: Keep under 140 chars (preview cutoff)
- Headline hook: First 2 lines visible without "see more"

### Best Practices
1. **Hook in first line** - Stop the scroll
2. **Line breaks** - Use whitespace for readability
3. **Hashtags** - 3-5 relevant hashtags at end
4. **Call to action** - Ask a question or invite engagement
5. **Optimal timing** - Tue-Thu, 8-10am local time

### Post Format Template
```
[Hook - compelling first line]

[Body - 2-3 short paragraphs]

[Call to action - question or invitation]

#hashtag1 #hashtag2 #hashtag3
```

## Error Handling

### Common Issues

| Error | Selector | Solution |
|-------|----------|----------|
| Modal not opening | `button.share-box-feed-entry__trigger` | Refresh page, try again |
| Image upload stuck | `div.share-box-image-preview` | Check file size (<10MB) |
| Post button disabled | `button.share-actions__primary-action` | Ensure content is entered |
| Rate limited | `div.artdeco-toast-item--error` | Wait 15-30 minutes |

### Retry Pattern

```python
async def post_with_retry(browser, content, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await browser.execute(post_actions)
            if result["success"]:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                raise
```

## Session Management

### Save Session After Login
```python
await browser.login("linkedin", credentials)
await browser.save_session("linkedin")  # Persists cookies
```

### Restore Session
```python
if await browser.ensure_logged_in("linkedin"):
    # Session valid, proceed
    pass
else:
    # Need fresh login
    await browser.login("linkedin")
```

## Security Considerations

1. **Never hardcode credentials** - Use credential store
2. **Rate limiting** - Max 20-30 posts per day
3. **Human-like behavior** - Add delays between actions
4. **Session security** - Sessions stored in ~/.teotl/browser/sessions/
5. **MFA handling** - Prompt user for MFA codes

---

**Remember**: LinkedIn has strict automation policies. Use responsibly and within their terms of service.
