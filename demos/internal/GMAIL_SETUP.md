# Gmail Integration Setup

**Time:** 15-20 minutes one-time setup

## Quick Start

1. **Google Cloud Setup** (10 min)
   - Create project at https://console.cloud.google.com/
   - Enable Gmail API
   - Create OAuth credentials
   - Download `gmail_credentials.json`

2. **Install Credentials**
   ```bash
   mkdir -p ~/.teotl/credentials/
   cp ~/Downloads/gmail_credentials.json ~/.teotl/credentials/
   ```

3. **Install Dependencies**
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

4. **Authenticate**
   ```bash
   python auth_gmail.py
   # Opens browser for OAuth flow
   ```

5. **Run Demo**
   ```bash
   python demo_with_config.py
   ```

## Detailed Setup Guide

See REAL_SETUP.md for complete step-by-step instructions including:
- Google Cloud project creation
- OAuth consent screen configuration  
- Credential download
- Token management
- Troubleshooting

## Safety Configuration

Edit `config.yaml`:

```yaml
integrations:
  gmail:
    enabled: true
    credentials_path: ~/.teotl/credentials/gmail_credentials.json
    confirm_sends: true  # Require approval for sends
    allowed_recipients:  # Whitelist
      - your-email@gmail.com
```

## What the Agent Can Do

- **Read emails**: List inbox, search, get content
- **Send emails**: Compose and send (with safety controls)
- **Organize**: Mark read, archive, label
- **Search**: Query by sender, subject, date

## Demo Tasks

The demo includes these Gmail tasks:
1. Check for new emails (mission - runs hourly)
2. Send welcome email (task - runs once)
3. Reply to support ticket (task - urgent priority)
4. Clean up spam (mission - runs daily)

Agent executes these autonomously based on priority and schedule.
