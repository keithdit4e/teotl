---
name: medium
version: 1.0.0
description: "Publish articles and stories on Medium"
auth: browser-session
triggers:
  - medium
  - article
  - blog post
  - story
---

# Medium Automation

Deterministic browser automation for publishing articles on Medium.

## Prerequisites

Ensure browser session is active:
```python
browser = BrowserTool()
await browser.launch()

if not await browser.ensure_logged_in("medium"):
    await browser.login("medium")
```

**Note:** Medium uses email magic links or OAuth (Google/Twitter/Facebook). Session persistence is especially important here.

## Selectors Reference (Updated: 2026-06)

```yaml
# URLs
home_url: "https://medium.com/"
new_story_url: "https://medium.com/new-story"
drafts_url: "https://medium.com/me/stories/drafts"
published_url: "https://medium.com/me/stories/public"

# Story Editor
title_editor: "h3[data-placeholder='Title']"
subtitle_editor: "h4[data-placeholder='Subtitle']"  # Optional
body_editor: "div[data-placeholder='Tell your story…']"
body_paragraphs: "div.graf"

# Media
add_media_button: "button[data-action='add-media']"
image_input: "input[type='file'][accept='image/*']"
image_preview: "figure.graf--figure"
embed_input: "input[placeholder='Paste a link to embed content']"

# Formatting (selection-based)
bold_button: "button[data-action='inline-bold']"
italic_button: "button[data-action='inline-italic']"
link_button: "button[data-action='inline-link']"
h1_button: "button[data-action='block-h3']"
h2_button: "button[data-action='block-h4']"
quote_button: "button[data-action='block-quote']"
code_button: "button[data-action='inline-code']"

# Publishing
publish_button: "button[data-testid='publishButton']"
publish_menu: "button[data-action='show-post-menu']"
schedule_button: "button[data-action='schedule']"
publish_confirm: "button[data-action='publish']"

# Post Settings (before publish)
add_tags: "input[placeholder='Add a tag…']"
tag_suggestions: "div[data-testid='tag-suggestions']"
subtitle_input: "textarea[placeholder='Add a subtitle']"
preview_subtitle: "textarea[placeholder='Preview subtitle']"

# Success
publish_success: "div[data-testid='post-published-modal']"
story_link: "a[data-testid='story-link']"
```

## Create Article

### New Story

```python
actions = [
    BrowserAction(action="goto", value="https://medium.com/new-story"),
    BrowserAction(action="wait_for", selector="h3[data-placeholder='Title']"),

    # Enter title
    BrowserAction(action="click", selector="h3[data-placeholder='Title']"),
    BrowserAction(action="type", selector="h3[data-placeholder='Title']", value=TITLE),
    BrowserAction(action="press", value="Enter"),

    # Enter body content
    BrowserAction(action="wait_for", selector="div[data-placeholder='Tell your story…']"),
    BrowserAction(action="click", selector="div[data-placeholder='Tell your story…']"),
]

# Add body content paragraph by paragraph
for paragraph in BODY_PARAGRAPHS:
    actions.append(BrowserAction(action="type", selector="div.graf:last-child", value=paragraph))
    actions.append(BrowserAction(action="press", value="Enter"))
    actions.append(BrowserAction(action="wait", value="0.5"))

result = await browser.execute(actions)
```

### Add Image

```python
# Position cursor where image should go, then:
image_actions = [
    BrowserAction(action="press", value="Enter"),  # New line
    BrowserAction(action="click", selector="button[data-action='add-media']"),
    BrowserAction(action="upload", selector="input[type='file'][accept='image/*']", value=IMAGE_PATH),
    BrowserAction(action="wait_for", selector="figure.graf--figure", timeout=30),
]
```

### Add Code Block

```python
code_actions = [
    BrowserAction(action="press", value="Enter"),
    # Type triple backticks for code block
    BrowserAction(action="type", selector="div.graf:last-child", value="```"),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="pre.graf", value=CODE_CONTENT),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="type", selector="div.graf:last-child", value="```"),
]
```

### Add Embed (YouTube, Tweet, etc.)

```python
embed_actions = [
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="click", selector="button[data-action='add-media']"),
    BrowserAction(action="click", selector="button[data-action='add-embed']"),
    BrowserAction(action="fill", selector="input[placeholder='Paste a link']", value=EMBED_URL),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="wait_for", selector="figure.graf--iframe", timeout=10),
]
```

## Publish Article

### Publish Immediately

```python
publish_actions = [
    # Click publish button (top right)
    BrowserAction(action="click", selector="button[data-testid='publishButton']"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-modal']"),

    # Add tags (important for discoverability)
    BrowserAction(action="fill", selector="input[placeholder='Add a tag…']", value=TAGS[0]),
    BrowserAction(action="press", value="Enter"),
    BrowserAction(action="wait", value="0.5"),
]

# Add more tags (up to 5)
for tag in TAGS[1:5]:
    publish_actions.extend([
        BrowserAction(action="fill", selector="input[placeholder='Add a tag…']", value=tag),
        BrowserAction(action="press", value="Enter"),
        BrowserAction(action="wait", value="0.5"),
    ])

# Confirm publish
publish_actions.extend([
    BrowserAction(action="click", selector="button[data-action='publish']"),
    BrowserAction(action="wait_for", selector="div[data-testid='post-published-modal']", timeout=15),
])

result = await browser.execute(publish_actions)
```

### Get Published URL

```python
# After successful publish
url_actions = [
    BrowserAction(action="query", selector="a[data-testid='story-link']"),
]
result = await browser.execute(url_actions)
published_url = result["results"][0]["href"]
```

## Save as Draft

```python
# Stories auto-save, but to explicitly save:
save_actions = [
    BrowserAction(action="wait", value="3"),  # Auto-save triggers
    # Navigate away confirms save
    BrowserAction(action="goto", value="https://medium.com/me/stories/drafts"),
]
```

## Read Stories

### Get Your Drafts

```python
actions = [
    BrowserAction(action="goto", value="https://medium.com/me/stories/drafts"),
    BrowserAction(action="wait_for", selector="div[data-testid='story-list']"),
    BrowserAction(action="query_all", selector="div[data-testid='story-card']"),
]
```

### Get Published Stories

```python
actions = [
    BrowserAction(action="goto", value="https://medium.com/me/stories/public"),
    BrowserAction(action="wait_for", selector="div[data-testid='story-list']"),
    BrowserAction(action="query_all", selector="div[data-testid='story-card']"),
]
```

## Content Guidelines

### Article Structure
1. **Title** - Clear, compelling, SEO-friendly
2. **Subtitle** - Optional but recommended
3. **Featured Image** - First image becomes preview
4. **Introduction** - Hook in first paragraph
5. **Body** - Use headers, images, code blocks
6. **Conclusion** - Summary + call to action

### Formatting Best Practices
- Use H1 sparingly (section breaks)
- Use H2 for main sections
- Keep paragraphs short (2-4 sentences)
- Add images every 300-400 words
- Use pull quotes for key insights
- Code blocks for technical content

### Tags (Important!)
- Add 5 tags maximum
- First tag is most important
- Mix popular + niche tags
- Check tag follower counts

### Medium Partner Program
- Metered paywall option
- Friend links for free access
- Publication submission

## Publication Submission

```python
# When publishing, select a publication:
publication_actions = [
    BrowserAction(action="click", selector="button[data-testid='publishButton']"),
    BrowserAction(action="wait_for", selector="div[data-testid='publish-modal']"),
    BrowserAction(action="click", selector="button[data-action='add-to-publication']"),
    BrowserAction(action="click", selector=f"div[data-publication='{PUBLICATION_NAME}']"),
    # Continue with tags and publish...
]
```

## Error Handling

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Editor not loading | Auth expired | Re-login, restore session |
| Image upload fails | File too large | Max 25MB |
| Publish button disabled | Title empty | Add title content |
| Tags not accepting | Invalid tag | Try different phrasing |

### Check for Errors

```python
error_check = [
    BrowserAction(action="query", selector="div[data-testid='error-message']"),
]
result = await browser.execute(error_check)

if result["results"][0]:
    raise PublishError(result["results"][0]["text"])
```

## Session Management

Medium primarily uses OAuth or magic links:

```python
# Login flow (magic link)
login_actions = [
    BrowserAction(action="goto", value="https://medium.com/m/signin"),
    BrowserAction(action="click", selector="button:has-text('Sign in with email')"),
    BrowserAction(action="fill", selector="input[type='email']", value=EMAIL),
    BrowserAction(action="click", selector="button[type='submit']"),
]

# User must click magic link in email
# Then save session:
await browser.save_session("medium")
```

### Session Persistence
```python
# Restore session (avoids magic link)
if await browser.ensure_logged_in("medium"):
    # Ready to write
    pass
else:
    # Need magic link login
    print("Check email for Medium login link")
```

## Complete Publishing Flow

```python
async def publish_to_medium(browser, title, body, tags, image_path=None):
    """Complete flow to publish an article to Medium."""

    # Ensure logged in
    if not await browser.ensure_logged_in("medium"):
        raise LoginRequired("medium")

    # Create story
    actions = [
        BrowserAction(action="goto", value="https://medium.com/new-story"),
        BrowserAction(action="wait_for", selector="h3[data-placeholder='Title']"),
        BrowserAction(action="click", selector="h3[data-placeholder='Title']"),
        BrowserAction(action="type", selector="h3", value=title),
        BrowserAction(action="press", value="Enter"),
    ]

    # Add image if provided
    if image_path:
        actions.extend([
            BrowserAction(action="click", selector="button[data-action='add-media']"),
            BrowserAction(action="upload", selector="input[type='file']", value=image_path),
            BrowserAction(action="wait_for", selector="figure.graf--figure", timeout=30),
            BrowserAction(action="press", value="Enter"),
        ])

    # Add body content
    actions.append(BrowserAction(action="wait_for", selector="div[data-placeholder='Tell your story…']"))
    for paragraph in body.split("\n\n"):
        actions.extend([
            BrowserAction(action="type", selector="div.graf:last-child", value=paragraph),
            BrowserAction(action="press", value="Enter"),
        ])

    # Publish
    actions.extend([
        BrowserAction(action="click", selector="button[data-testid='publishButton']"),
        BrowserAction(action="wait_for", selector="div[data-testid='publish-modal']"),
    ])

    # Add tags
    for tag in tags[:5]:
        actions.extend([
            BrowserAction(action="fill", selector="input[placeholder='Add a tag…']", value=tag),
            BrowserAction(action="press", value="Enter"),
            BrowserAction(action="wait", value="0.5"),
        ])

    # Confirm publish
    actions.extend([
        BrowserAction(action="click", selector="button[data-action='publish']"),
        BrowserAction(action="wait_for", selector="div[data-testid='post-published-modal']", timeout=15),
        BrowserAction(action="query", selector="a[data-testid='story-link']"),
    ])

    result = await browser.execute(actions)
    return result
```

---

**Remember**: Quality content performs better on Medium. Focus on value over quantity.
