---
name: social-media
version: 1.0.0
description: "Cross-post and manage content across LinkedIn, X, Medium, Substack"
auth: browser-session
triggers:
  - social media
  - cross-post
  - publish everywhere
  - content distribution
---

# Social Media Orchestration

Coordinate content publishing across multiple platforms with platform-specific adaptation.

## Prerequisites

```python
from teotl.core.tools.browser import BrowserTool

browser = BrowserTool()
await browser.launch()
```

## Platform Overview

| Platform | Content Type | Max Length | Best For |
|----------|--------------|------------|----------|
| LinkedIn | Professional posts | 3,000 chars | B2B, career, thought leadership |
| X/Twitter | Short-form, threads | 280/25K chars | Real-time, engagement, reach |
| Medium | Long-form articles | Unlimited | SEO, evergreen content |
| Substack | Newsletters | Unlimited | Direct audience, monetization |

## Cross-Posting Strategy

### Content Adaptation Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Original Content                       │
│              (Article, Thread, or Post)                  │
└─────────────────────────┬───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Long-form │   │  Mid-form   │   │ Short-form  │
│   Platforms │   │  Platforms  │   │  Platforms  │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Medium    │   │  LinkedIn   │   │   X/Twitter │
│   Substack  │   │             │   │             │
└─────────────┘   └─────────────┘   └─────────────┘
```

### Recommended Publishing Order

1. **Medium/Substack first** - Establishes canonical URL
2. **LinkedIn second** - Professional summary + link
3. **X/Twitter last** - Thread or teaser + link

This order ensures:
- SEO benefit goes to your owned content
- Links are available for other platforms
- Engagement funnels back to main content

## Content Transformation

### Article → Multi-Platform

```python
async def cross_post_article(
    browser,
    title: str,
    body: str,
    summary: str,  # 2-3 sentences
    key_points: list[str],  # 3-5 bullet points
    tags: list[str],
    image_path: str | None = None,
):
    """Cross-post an article to all platforms."""

    results = {}

    # 1. Publish to Medium (canonical)
    await browser.ensure_logged_in("medium")
    medium_result = await publish_to_medium(browser, title, body, tags, image_path)
    results["medium"] = medium_result
    medium_url = extract_url(medium_result)

    # 2. Publish to Substack (newsletter)
    await browser.ensure_logged_in("substack")
    substack_result = await publish_to_substack(
        browser,
        publication="yourpub",
        title=title,
        subtitle=summary,
        body=body,
    )
    results["substack"] = substack_result

    # 3. Post to LinkedIn (professional summary)
    linkedin_content = format_for_linkedin(title, summary, key_points, medium_url, tags)
    await browser.ensure_logged_in("linkedin")
    linkedin_result = await post_to_linkedin(browser, linkedin_content, image_path)
    results["linkedin"] = linkedin_result

    # 4. Post to X (thread or teaser)
    twitter_thread = format_for_twitter(title, key_points, medium_url)
    await browser.ensure_logged_in("twitter")
    twitter_result = await post_thread(browser, twitter_thread)
    results["twitter"] = twitter_result

    return results
```

### Format Transformers

#### For LinkedIn

```python
def format_for_linkedin(title, summary, key_points, url, tags):
    """Transform content for LinkedIn."""

    # Hook (first line visible in feed)
    hook = f"{title}\n\n"

    # Summary
    body = f"{summary}\n\n"

    # Key points as bullets
    body += "Key takeaways:\n"
    for point in key_points[:5]:
        body += f"→ {point}\n"
    body += "\n"

    # Call to action
    body += f"Read the full article: {url}\n\n"

    # Hashtags (3-5)
    hashtags = " ".join(f"#{tag.replace(' ', '')}" for tag in tags[:5])
    body += hashtags

    return hook + body
```

#### For X/Twitter

```python
def format_for_twitter(title, key_points, url):
    """Transform content into a Twitter thread."""

    tweets = []

    # Tweet 1: Hook
    tweets.append(f"🧵 {title}\n\nA thread:")

    # Middle tweets: Key points
    for i, point in enumerate(key_points, 1):
        tweet = f"{i}/ {point}"
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        tweets.append(tweet)

    # Final tweet: CTA
    tweets.append(f"Read the full breakdown here:\n\n{url}\n\nFollow for more insights!")

    return tweets
```

#### For Medium (from thread/post)

```python
def format_for_medium(title, thread_tweets, expanded_content):
    """Transform a thread into a Medium article."""

    body = f"# {title}\n\n"

    # Expand each tweet into a section
    for i, tweet in enumerate(thread_tweets[1:-1], 1):  # Skip intro and outro
        # Remove numbering
        content = tweet.lstrip("0123456789/").strip()
        body += f"## Point {i}\n\n{expanded_content.get(i, content)}\n\n"

    return body
```

## Authentication Orchestration

### Check All Sessions

```python
async def check_all_sessions(browser):
    """Check login status for all platforms."""

    platforms = ["linkedin", "twitter", "medium", "substack"]
    status = {}

    for platform in platforms:
        try:
            logged_in = await browser.ensure_logged_in(platform)
            status[platform] = "ready" if logged_in else "login_required"
        except Exception as e:
            status[platform] = f"error: {e}"

    return status
```

### Login to All Platforms

```python
async def login_all_platforms(browser, mfa_callback=None):
    """Login to all platforms, handling MFA prompts."""

    platforms = ["linkedin", "twitter", "medium", "substack"]

    for platform in platforms:
        if not await browser.ensure_logged_in(platform):
            print(f"Logging into {platform}...")
            try:
                await browser.login(platform, mfa_callback=mfa_callback)
                print(f"✓ {platform} logged in")
            except MFARequired as e:
                if mfa_callback:
                    code = await mfa_callback(f"Enter MFA code for {platform}:")
                    # Retry with MFA
                    await browser.login(platform, mfa_code=code)
                else:
                    print(f"✗ {platform} requires MFA")
            except LoginRequired:
                print(f"✗ {platform} needs credentials")
```

## Scheduling Strategy

### Optimal Posting Times

```yaml
linkedin:
  best_days: [Tuesday, Wednesday, Thursday]
  best_times: ["08:00", "10:00", "12:00"]
  timezone: "America/New_York"

twitter:
  best_days: [Monday, Tuesday, Wednesday, Thursday, Friday]
  best_times: ["09:00", "12:00", "17:00"]
  timezone: "America/New_York"

medium:
  best_days: [Tuesday, Wednesday, Saturday]
  best_times: ["07:00", "10:00"]
  timezone: "America/New_York"

substack:
  best_days: [Tuesday, Wednesday, Thursday]
  best_times: ["07:00", "09:00"]
  timezone: "America/New_York"
```

### Staggered Posting

```python
async def staggered_cross_post(browser, content, delays_minutes=None):
    """Post to platforms with time delays."""

    if delays_minutes is None:
        delays_minutes = {
            "medium": 0,       # Post immediately
            "substack": 5,     # 5 minutes later
            "linkedin": 30,    # 30 minutes later
            "twitter": 60,     # 1 hour later
        }

    results = {}

    for platform, delay in sorted(delays_minutes.items(), key=lambda x: x[1]):
        if delay > 0:
            print(f"Waiting {delay} minutes before posting to {platform}...")
            await asyncio.sleep(delay * 60)

        result = await post_to_platform(browser, platform, content)
        results[platform] = result

    return results
```

## Content Calendar

### Weekly Schedule Template

```yaml
monday:
  - platform: twitter
    type: engagement
    content: "Reply to industry discussions"

tuesday:
  - platform: linkedin
    type: original_post
    content: "Weekly insight post"
  - platform: twitter
    type: thread
    content: "Thread version of LinkedIn post"

wednesday:
  - platform: medium
    type: article
    content: "Deep-dive article"
  - platform: substack
    type: newsletter
    content: "Weekly newsletter"

thursday:
  - platform: linkedin
    type: engagement
    content: "Comment on others' posts"
  - platform: twitter
    type: curated
    content: "Share interesting finds"

friday:
  - platform: twitter
    type: casual
    content: "Weekend thoughts, personal"
```

## Error Handling

### Retry Logic

```python
async def post_with_retry(browser, platform, content, max_retries=3):
    """Post with automatic retry on failure."""

    for attempt in range(max_retries):
        try:
            result = await post_to_platform(browser, platform, content)
            if result.get("success"):
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 30  # 30, 60, 90 seconds
                print(f"Retry {attempt + 1}/{max_retries} for {platform} in {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise

    return {"success": False, "error": "Max retries exceeded"}
```

### Rate Limit Handling

```python
RATE_LIMITS = {
    "linkedin": {"posts_per_day": 20, "delay_seconds": 60},
    "twitter": {"posts_per_day": 50, "delay_seconds": 30},
    "medium": {"posts_per_day": 5, "delay_seconds": 300},
    "substack": {"posts_per_day": 3, "delay_seconds": 600},
}

async def check_rate_limit(platform, posts_today):
    """Check if rate limit allows posting."""
    limit = RATE_LIMITS.get(platform, {}).get("posts_per_day", 10)
    return posts_today < limit
```

## Analytics Tracking

### Post Performance

```python
async def get_post_stats(browser, platform, post_url):
    """Get engagement stats for a post."""

    if platform == "linkedin":
        # Navigate to post, extract stats
        pass
    elif platform == "twitter":
        # Use Twitter analytics
        pass
    # etc.
```

### Cross-Platform Summary

```python
def summarize_campaign(results):
    """Summarize cross-post campaign results."""

    summary = {
        "platforms_posted": [],
        "platforms_failed": [],
        "total_reach": 0,
        "urls": {},
    }

    for platform, result in results.items():
        if result.get("success"):
            summary["platforms_posted"].append(platform)
            summary["urls"][platform] = result.get("url")
        else:
            summary["platforms_failed"].append(platform)

    return summary
```

## Complete Cross-Post Workflow

```python
async def full_cross_post_workflow(
    browser,
    title: str,
    full_article: str,
    summary: str,
    key_points: list[str],
    tags: list[str],
    image_path: str | None = None,
    substack_publication: str = "default",
):
    """Complete workflow to cross-post content everywhere."""

    print("Starting cross-post workflow...")

    # 1. Check all sessions
    status = await check_all_sessions(browser)
    print(f"Session status: {status}")

    # 2. Login where needed
    for platform, state in status.items():
        if state == "login_required":
            print(f"Logging into {platform}...")
            await browser.login(platform)

    results = {}

    # 3. Medium (canonical)
    print("\n📝 Publishing to Medium...")
    try:
        results["medium"] = await publish_to_medium(
            browser, title, full_article, tags, image_path
        )
        medium_url = results["medium"].get("url")
        print(f"✓ Medium: {medium_url}")
    except Exception as e:
        print(f"✗ Medium failed: {e}")
        medium_url = None

    # 4. Substack (newsletter)
    print("\n📧 Publishing to Substack...")
    try:
        results["substack"] = await publish_to_substack(
            browser,
            substack_publication,
            title,
            summary,
            full_article,
        )
        print(f"✓ Substack published")
    except Exception as e:
        print(f"✗ Substack failed: {e}")

    # 5. LinkedIn (professional post)
    print("\n💼 Posting to LinkedIn...")
    try:
        linkedin_content = format_for_linkedin(
            title, summary, key_points, medium_url or "", tags
        )
        results["linkedin"] = await post_to_linkedin(browser, linkedin_content, image_path)
        print(f"✓ LinkedIn posted")
    except Exception as e:
        print(f"✗ LinkedIn failed: {e}")

    # 6. X/Twitter (thread)
    print("\n🐦 Posting thread to X...")
    try:
        thread = format_for_twitter(title, key_points, medium_url or "")
        results["twitter"] = await create_thread(browser, thread)
        print(f"✓ X thread posted ({len(thread)} tweets)")
    except Exception as e:
        print(f"✗ X failed: {e}")

    # 7. Summary
    print("\n" + "="*50)
    print("Cross-post complete!")
    summary = summarize_campaign(results)
    print(f"Posted to: {', '.join(summary['platforms_posted'])}")
    if summary['platforms_failed']:
        print(f"Failed: {', '.join(summary['platforms_failed'])}")

    return results
```

## Quick Reference

### Activate Platform Skills

```python
# Load platform-specific selectors and workflows
await agent.activate_skill("linkedin")
await agent.activate_skill("twitter")
await agent.activate_skill("medium")
await agent.activate_skill("substack")
```

### Platform-Specific Actions

| Action | LinkedIn | X/Twitter | Medium | Substack |
|--------|----------|-----------|--------|----------|
| New post | Click share box | /compose/tweet | /new-story | /publish/post |
| Add image | Media button | File upload | Add media | Add image |
| Publish | Post button | Tweet button | Publish | Publish now |
| Schedule | Via scheduler | Native | No | Native |

---

**Remember**: Each platform has its own culture. Adapt tone and format accordingly.
