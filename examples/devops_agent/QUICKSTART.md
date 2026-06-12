# Quick Start Guide

Get the DevOps Agent running in **3 easy steps**.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

---

## Step 1: Install Dependencies

```bash
# Navigate to the directory
cd ~/teotl/examples/devops_agent

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js (if not installed)
brew install node  # macOS
# or: sudo apt install nodejs npm  # Linux

# Install GitHub MCP Server
npm install -g @modelcontextprotocol/server-github
```

---

## Step 2: Set Up API Keys

### Get Anthropic API Key (1 minute)

1. Visit: https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key (starts with `sk-ant-`)
4. Set it:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"
   ```

### Get GitHub Token (1 minute)

1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `read:org`
4. Copy the token (starts with `ghp_`)
5. Set it:
   ```bash
   export GITHUB_TOKEN="ghp_paste-your-token-here"
   ```

### Verify Both Keys Are Set

```bash
./setup_keys.sh
```

Should show ✅ for both keys.

---

## Step 3: Test the Agent

### Run Test Suite

```bash
python test.py
```

**Expected output:**
```
✅ All tests passed!
```

### Try a Dry Run (No API Usage)

```bash
python main.py --repo anthropics/anthropic-sdk-python --issue 1 --dry-run
```

This shows what the agent would do without actually running it.

### Run on a Real Issue

```bash
python main.py --repo OWNER/REPO --issue NUMBER
```

The agent will:
1. Fetch the issue from GitHub
2. Investigate the problem
3. Create a fix
4. Add tests
5. Create a pull request

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
echo $ANTHROPIC_API_KEY  # Check if set
export ANTHROPIC_API_KEY="sk-ant-..."  # Set it
```

### "GITHUB_TOKEN not set"

```bash
echo $GITHUB_TOKEN  # Check if set
export GITHUB_TOKEN="ghp_..."  # Set it
```

### "npx: command not found"

```bash
brew install node  # macOS
# or: sudo apt install nodejs npm  # Linux
```

### "MCP bridge creation failed"

```bash
npm install -g @modelcontextprotocol/server-github
```

### Can't find test.py?

```bash
pwd  # Check your current directory
# You should be in ~/teotl/examples/devops_agent
```

---

## What's Next?

- See `API_KEYS_SETUP.md` for detailed key setup instructions
- See `AUTONOMOUS_MODE.md` to run the agent in autonomous mode
- See `ARCHITECTURE.md` for technical details
- See `README.md` for full documentation

---

## Cost Estimate

**Testing (10-20 issues):** $5-10
**Full development:** $20-50

Each issue fix costs approximately $0.10-0.50 in API usage.

---

**Ready? Run `python test.py` now!** ⚡
