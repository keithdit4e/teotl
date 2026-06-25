---
name: substack
version: 1.0.0
description: "Publish newsletters and posts on Substack"
auth: browser-session
triggers:
  - substack
  - newsletter
  - email subscribers
---

# Substack Automation

Deterministic browser automation for publishing newsletters on Substack.

## Prerequisites

Ensure browser session is active:
```python
browser = BrowserTool()
await browser.launch()

if not await browser.ensure_logged_in("substack"):
    await browser.login("substack")
```

## Selectors Reference (Updated: 2026-06)

```yaml
# URLs (replace {publication} with your subdomain)
dashboard_url: "https://{publication}.substack.com/publish"
new_post_url: "https://{publication}.substack.com/publish/post"
drafts_url: "https://{publication}.substack.com/publish/posts?status=draft"
published_url: "https://{publication}.substack.com/publish/posts?status=published"
settings_url: "https://{publication}.substack.com/publish/settings"

# Post Editor
title_input: "textarea[placeholder='Title']"
subtitle_input: "textarea[placeholder='Write a subtitle…']"
body_editor: "div.ProseMirror"
body_paragraph: "div.ProseMirror p"

# Media
add_image_button: "button[aria-label='Add image']"
image_input: "input[type='file'][accept='image/*']"
image_block: "figure.image-block"
add_embed_button: "button[aria-label='Add embed']"
embed_input: "input[placeholder='Paste URL']"

# Formatting Toolbar
bold_button: "button[aria-label='Bold']"
italic_button: "button[aria-label='Italic']"
link_button: "button[aria-label='Add link']"
heading_button: "button[aria-label='Heading']"
quote_button: "button[aria-label='Quote']"
code_button: "button[aria-label='Code']"
bullet_list: "button[aria-label='Bullet list']"
numbered_list: "button[aria-label='Numbered list']"

# Publishing
continue_button: "button:has-text('Continue')"
publish_settings: "div[data-testid='publish-settings']"

# Audience Selection
everyone_radio: "input[value='everyone']"
paid_only_radio: "input[value='paid']"
free_only_radio: "input[value='free']"

# Email Options
send_email_checkbox: "input[name='send_email']"
email_preview: "textarea[placeholder='Preview text']"

# Schedule
schedule_toggle: "button[aria-label='Schedule']"
schedule_date: "input[type='date']"
schedule_time: "input[type='time']"

# Publish Buttons
publish_now_button: "button:has-text('Publish now')"
schedule_button: "button:has-text('Schedule')"
save_draft_button: "button:has-text('Save draft')"

# Success
publish_success: "div[data-testid='publish-success']"
post_link: "a[data-testid='view-post']"
```

## Create Newsletter Post

### New Post

```python
# Replace with your publication subdomain
PUBLICATION = "yourpublication"

actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/post"),
    BrowserAction(action="wait_for", selector="textarea[placeholder='Title']"),

    # Enter title
    BrowserAction(action="fill", selector="textarea[placeholder='Title']", value=TITLE),

    # Enter subtitle (optional but recommended)
    BrowserAction(action="fill", selector="textarea[placeholder='Write a subtitle…']", value=SUBTITLE),

    # Enter body
    BrowserAction(action="click", selector="div.ProseMirror"),
    BrowserAction(action="wait", value="0.5"),
]

# Add body content
for paragraph in BODY_PARAGRAPHS:
    actions.extend([
        BrowserAction(action="type", selector="div.ProseMirror", value=paragraph),
        BrowserAction(action="press", value="Enter"),
        BrowserAction(action="press", value="Enter"),  # Double enter for paragraph break
    ])

result = await browser.execute(actions)
```

### Add Image

```python
image_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="click", selector="button[aria-label='Add image']"),
    BrowserAction(action="upload", selector="input[type='file'][accept='image/*']", value=IMAGE_PATH),
    BrowserAction(action="wait_for", selector="figure.image-block", timeout=30),
]
```

### Add Heading

```python
# Use keyboard shortcuts
heading_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="div.ProseMirror", value="## Section Heading"),
    BrowserAction(action="press", value="Enter"),
]
```

### Add Code Block

```python
code_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="div.ProseMirror", value="```"),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="div.ProseMirror pre", value=CODE_CONTENT),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="div.ProseMirror", value="```"),
]
```

### Add YouTube/Tweet Embed

```python
embed_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="click", selector="button[aria-label='Add embed']"),
    BrowserAction(action="fill", selector="input[placeholder='Paste URL']", value=EMBED_URL),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="wait_for", selector="div.embed-block", timeout=10),
]
```

## Publish Post

### Publish Immediately (To All Subscribers)

```python
publish_actions = [
    # Click Continue to get to publish settings
    BrowserAction(action="click", selector="button:has-text('Continue')"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-settings']"),

    # Select audience (everyone, paid, or free)
    BrowserAction(action="click", selector="input[value='everyone']"),

    # Ensure email is enabled
    BrowserAction(action="click", selector="input[name='send_email']"),  # Toggle if needed

    # Add email preview text
    BrowserAction(action="fill", selector="textarea[placeholder='Preview text']", value=EMAIL_PREVIEW),

    # Publish
    BrowserAction(action="click", selector="button:has-text('Publish now')"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-success']", timeout=15),
]

result = await browser.execute(publish_actions)
```

### Publish to Paid Subscribers Only

```python
paid_only_actions = [
    BrowserAction(action="click", selector="button:has-text('Continue')"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-settings']"),
    BrowserAction(action="click", selector="input[value='paid']"),
    BrowserAction(action="click", selector="button:has-text('Publish now')"),
]
```

### Schedule for Later

```python
schedule_actions = [
    BrowserAction(action="click", selector="button:has-text('Continue')"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-settings']"),

    # Enable scheduling
    BrowserAction(action="click", selector="button[aria-label='Schedule']"),

    # Set date and time
    BrowserAction(action="fill", selector="input[type='date']", value="2026-07-01"),
    BrowserAction(action="fill", selector="input[type='time']", value="09:00"),

    # Schedule
    BrowserAction(action="click", selector="button:has-text('Schedule')"),
    BrowserAction(action="wait_for", selector="div[data-testid='schedule-success']", timeout=10),
]
```

### Save as Draft

```python
draft_actions = [
    # Just navigate away - auto-saves
    BrowserAction(action="wait", value="2"),  # Let auto-save complete
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/posts?status=draft"),
]
```

## Manage Posts

### View Drafts

```python
actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/posts?status=draft"),
    BrowserAction(action="wait_for", selector="div[data-testid='post-list']"),
    BrowserAction(action="query_all", selector="div[data-testid='post-item']"),
]
```

### View Published Posts

```python
actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/posts?status=published"),
    BrowserAction(action="wait_for", selector="div[data-testid='post-list']"),
    BrowserAction(action="query_all", selector="div[data-testid='post-item']"),
]
```

### Edit Existing Post

```python
# From drafts list, click on a post to edit
edit_actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/posts?status=draft"),
    BrowserAction(action="click", selector="div[data-testid='post-item']:first-child"),
    BrowserAction(action="wait_for", selector="textarea[placeholder='Title']"),
    # Now edit as normal...
]
```

## Content Guidelines

### Newsletter Structure
1. **Subject line/Title** - Clear, compelling, curiosity-driving
2. **Subtitle** - Expand on title, include keywords
3. **Preview text** - First 100 chars shown in email
4. **Opening hook** - Personal or compelling start
5. **Body** - Value-packed content
6. **Call to action** - Subscribe, share, comment

### Best Practices
- **Consistency** - Regular publishing schedule
- **Length** - 500-2000 words optimal
- **Formatting** - Headers, lists, images
- **Personal voice** - Substack rewards authenticity
- **Engagement** - End with questions

### Email Preview Text
The preview text appears in email clients:
```
Good: "3 lessons I learned from failing publicly (and why you should fail too)"
Bad: "Click here to read more..."
```

### Optimal Posting Times
- **Weekday mornings** - Tue/Wed/Thu 7-9am
- **Weekend mornings** - Sat 8-10am
- **Avoid** - Friday afternoon, Sunday evening

## Paid vs Free Content

### Content Strategy
- Free: Hooks, previews, community building
- Paid: Deep dives, exclusive content, archives

### Paywall Placement
```python
# Insert paywall break
paywall_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="click", selector="button[aria-label='Add paywall']"),
    # Content below is for paid subscribers only
]
```

## Subscriber Management

### View Subscribers

```python
actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/subscribers"),
    BrowserAction(action="wait_for", selector="div[data-testid='subscriber-list']"),
]
```

### View Stats

```python
actions = [
    BrowserAction(action="goto", value=f"https://{PUBLICATION}.substack.com/publish/stats"),
    BrowserAction(action="wait_for", selector="div[data-testid='stats-dashboard']"),
]
```

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Editor not loading | Session expired | Re-login |
| Image upload fails | File too large | Max 10MB |
| Publish fails | Validation error | Check required fields |
| Email send fails | Rate limit | Wait and retry |

### Check for Errors

```python
error_check = [
    BrowserAction(action="query", selector="div[role='alert']"),
]
result = await browser.execute(error_check)

if result["results"][0]:
    raise PublishError(result["results"][0]["text"])
```

## Session Management

```python
# Login
login_actions = [
    BrowserAction(action="goto", value="https://substack.com/sign-in"),
    BrowserAction(action="fill", selector="input[type='email']", value=EMAIL),
    BrowserAction(action="fill", selector="input[type='password']", value=PASSWORD),
    BrowserAction(action="click", selector="button[type='submit']"),
    BrowserAction(action="wait_for", selector="div[data-testid='dashboard']", timeout=15),
]

await browser.execute(login_actions)
await browser.save_session("substack")
```

### Restore Session
```python
if await browser.ensure_logged_in("substack"):
    # Ready to publish
    pass
else:
    await browser.login("substack", credentials)
```

## Complete Publishing Flow

```python
async def publish_to_substack(
    browser,
    publication: str,
    title: str,
    subtitle: str,
    body: str,
    audience: str = "everyone",  # "everyone", "paid", "free"
    send_email: bool = True,
    email_preview: str = "",
):
    """Complete flow to publish a Substack newsletter."""

    # Ensure logged in
    if not await browser.ensure_logged_in("substack"):
        raise LoginRequired("substack")

    # Create post
    actions = [
        BrowserAction(action="goto", value=f"https://{publication}.substack.com/publish/post"),
        BrowserAction(action="wait_for", selector="textarea[placeholder='Title']"),
        BrowserAction(action="fill", selector="textarea[placeholder='Title']", value=title),
        BrowserAction(action="fill", selector="textarea[placeholder='Write a subtitle…']", value=subtitle),
        BrowserAction(action="click", selector="div.ProseMirror"),
    ]

    # Add body paragraphs
    for paragraph in body.split("\n\n"):
        actions.extend([
            BrowserAction(action="type", selector="div.ProseMirror", value=paragraph),
            BrowserAction(action="press", value="Enter"),
            BrowserAction(action="press", value="Enter"),
        ])

    # Publish settings
    actions.extend([
        BrowserAction(action="click", selector="button:has-text('Continue')"),
        BrowserAction(action="wait_for", selector="div[data-testid='publish-settings']"),
        BrowserAction(action="click", selector=f"input[value='{audience}']"),
    ])

    # Email options
    if send_email:
        actions.append(BrowserAction(action="click", selector="input[name='send_email']"))
        if email_preview:
            actions.append(
                BrowserAction(
                    action="fill",
                    selector="textarea[placeholder='Preview text']",
                    value=email_preview
                )
            )

    # Publish
    actions.extend([
        BrowserAction(action="click", selector="button:has-text('Publish now')"),
        BrowserAction(action="wait_for", selector="div[data-testid='publish-success']", timeout=15),
        BrowserAction(action="query", selector="a[data-testid='view-post']"),
    ])

    result = await browser.execute(actions)
    return result
```

## Multiple Publications

If you manage multiple Substack publications:

```python
async def switch_publication(browser, publication: str):
    """Switch to a different publication."""
    actions = [
        BrowserAction(action="goto", value=f"https://{publication}.substack.com/publish"),
        BrowserAction(action="wait_for", selector="div[data-testid='dashboard']"),
    ]
    return await browser.execute(actions)
```

---

**Remember**: Consistency and quality matter more than frequency on Substack.
