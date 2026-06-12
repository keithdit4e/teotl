# API Keys Setup Guide

This guide shows you how to obtain and configure the API keys needed for the DevOps Agent.

---

## Required API Keys

The DevOps Agent requires two API keys:
1. **ANTHROPIC_API_KEY** - For Claude AI model access
2. **GITHUB_TOKEN** - For GitHub operations via MCP

---

## 1. ANTHROPIC_API_KEY

### Get Your API Key

1. **Sign up / Log in to Anthropic Console:**
   - Visit: https://console.anthropic.com/
   - Create account or log in

2. **Create an API Key:**
   - Go to "API Keys" section: https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Give it a name (e.g., "DevOps Agent - Dev")
   - Copy the key (starts with `sk-ant-`)
   - **Important:** Save it immediately - you won't see it again!

3. **Add Credits (if needed):**
   - Go to "Billing": https://console.anthropic.com/settings/billing
   - Add credit ($5-20 recommended for testing)
   - Each agent run typically costs $0.10-0.50

### Set the Environment Variable

**Option A: Temporary (current terminal session only)**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Option B: Permanent (recommended)**

Add to your shell configuration file:

**For Zsh (macOS default):**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**For Bash:**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**For Fish:**
```bash
set -Ux ANTHROPIC_API_KEY "sk-ant-api03-your-key-here"
```

### Verify It's Set

```bash
echo $ANTHROPIC_API_KEY
# Should output: sk-ant-api03-your-key-here
```

---

## 2. GITHUB_TOKEN

### Get Your GitHub Token

1. **Log in to GitHub:**
   - Visit: https://github.com

2. **Generate Personal Access Token:**
   - Go to Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Direct link: https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"

3. **Configure Token:**
   - **Note:** "DevOps Agent - MCP Access"
   - **Expiration:** 90 days (or custom)
   - **Select scopes:**
     - ✅ `repo` (Full control of private repositories)
       - Includes: repo:status, repo_deployment, public_repo, repo:invite
     - ✅ `workflow` (Update GitHub Action workflows)
     - ✅ `read:org` (Read org and team membership)
     - ✅ `gist` (Create gists)

4. **Generate and Copy:**
   - Click "Generate token" at bottom
   - Copy the token (starts with `ghp_` or `github_pat_`)
   - **Important:** Save it immediately - you won't see it again!

### Set the Environment Variable

**Option A: Temporary (current terminal session only)**

```bash
export GITHUB_TOKEN="ghp_your_github_token_here"
```

**Option B: Permanent (recommended)**

**For Zsh (macOS default):**
```bash
echo 'export GITHUB_TOKEN="ghp_your_github_token_here"' >> ~/.zshrc
source ~/.zshrc
```

**For Bash:**
```bash
echo 'export GITHUB_TOKEN="ghp_your_github_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**For Fish:**
```bash
set -Ux GITHUB_TOKEN "ghp_your_github_token_here"
```

### Verify It's Set

```bash
echo $GITHUB_TOKEN
# Should output: ghp_your_github_token_here
```

---

## 3. Verify Both Keys Are Set

Run this command to check both keys:

```bash
if [ -n "$ANTHROPIC_API_KEY" ] && [ -n "$GITHUB_TOKEN" ]; then
    echo "✅ Both API keys are set!"
    echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:15}..."
    echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
else
    [ -z "$ANTHROPIC_API_KEY" ] && echo "❌ ANTHROPIC_API_KEY is not set"
    [ -z "$GITHUB_TOKEN" ] && echo "❌ GITHUB_TOKEN is not set"
fi
```

---

## 4. Test the Setup

### Test 1: Run Test Suite

```bash
cd ~/teotl/examples/devops_agent
python test.py
```

**Expected output:**
```
======================================================================
MCP Agent Integration Test
======================================================================

Testing MCP Tools Registration...

Creating MCP bridge...
✓ MCP bridge created with 2 tools
  - mcp_discover: Discover available tools from an MCP server...
  - mcp_execute: Execute a tool on an MCP server...

Creating agent with MCP tools...
✓ Agent created successfully

Testing MCP tool discovery...

Agent Response:
[Agent lists GitHub tools discovered via MCP]

✓ MCP bridge closed
✓ Agent successfully used MCP tools

======================================================================
✅ MCP agent integration working!
======================================================================
```

### Test 2: Dry Run Mode (No API Usage)

```bash
python main.py --repo anthropics/anthropic-sdk-python --issue 1 --dry-run
```

This tests GitHub token without using Anthropic API credits.

### Test 3: Full Agent Run (Uses API Credits)

```bash
python main.py --repo owner/repo --issue NUMBER
```

Replace `owner/repo` and `NUMBER` with a real repository and issue.

---

## Security Best Practices

### ✅ DO:
- Use environment variables (not hardcoded in files)
- Add keys to `.gitignore` if stored in files
- Set appropriate token expiration dates
- Use minimal required scopes for GitHub token
- Rotate keys periodically
- Delete unused tokens

### ❌ DON'T:
- Commit keys to Git repositories
- Share keys in public forums
- Use production tokens for testing
- Grant more permissions than needed
- Leave unused tokens active

### Protect Your Keys

If you accidentally expose a key:

**Anthropic API Key:**
1. Go to https://console.anthropic.com/settings/keys
2. Delete the exposed key
3. Generate a new one

**GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Delete the exposed token
3. Generate a new one

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set" Error

**Check if key is set:**
```bash
echo $ANTHROPIC_API_KEY
```

**If empty, set it:**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

**If still doesn't work:**
- Make sure you sourced your shell config: `source ~/.zshrc`
- Try opening a new terminal window
- Check for typos in the key

### "GITHUB_TOKEN not set" Error

**Check if key is set:**
```bash
echo $GITHUB_TOKEN
```

**If empty, set it:**
```bash
export GITHUB_TOKEN="ghp_your_token"
```

**If still doesn't work:**
- Verify token hasn't expired: https://github.com/settings/tokens
- Check token has correct scopes (repo, workflow, etc.)
- Try regenerating the token

### "Invalid API Key" Error

**Anthropic:**
- Verify key starts with `sk-ant-`
- Check for extra spaces or quotes
- Ensure you copied the full key
- Verify account has credits: https://console.anthropic.com/settings/billing

**GitHub:**
- Verify token starts with `ghp_` or `github_pat_`
- Check token hasn't expired
- Ensure correct scopes are selected
- Try with a fresh token

### MCP Server Errors

If you see `npx: command not found`:
```bash
# Install Node.js
brew install node

# Verify installation
node --version  # Should be v18 or higher
npx --version
```

If GitHub MCP server fails:
```bash
# Reinstall MCP server
npm install -g @modelcontextprotocol/server-github

# Verify installation
npx -y @modelcontextprotocol/server-github --version
```

---

## Alternative: Using .env File (Optional)

You can also use a `.env` file for local development:

1. **Create `.env` file:**
   ```bash
   cat > .env <<EOF
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   GITHUB_TOKEN=ghp_your_token_here
   EOF
   ```

2. **Add to .gitignore:**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Load before running:**
   ```bash
   export $(cat .env | xargs)
   python main.py --repo owner/repo --issue 1
   ```

**Or install python-dotenv:**
```bash
pip install python-dotenv
```

Then add to your Python script:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file
```

---

## Cost Estimates

### Anthropic API Costs

**Claude Sonnet 4:**
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Typical agent run (investigating + fixing one issue):**
- Input tokens: 50,000-100,000
- Output tokens: 5,000-10,000
- **Cost: $0.10-0.50 per issue**

**Recommended budget for testing:**
- Start with $5-10 for initial testing
- Add $20-50 for extensive testing

### GitHub Token Costs

GitHub tokens are **FREE** - no cost for API access.

---

## Quick Reference

```bash
# Set keys (temporary - current session only)
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_TOKEN="ghp_..."

# Set keys (permanent - add to shell config)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
echo 'export GITHUB_TOKEN="ghp_..."' >> ~/.zshrc
source ~/.zshrc

# Verify keys
echo $ANTHROPIC_API_KEY
echo $GITHUB_TOKEN

# Test setup
python examples/devops_agent/test_mcp_agent.py

# Run agent (dry run - no API usage)
python examples/devops_agent/main.py --repo owner/repo --issue N --dry-run

# Run agent (full - uses API credits)
python examples/devops_agent/main.py --repo owner/repo --issue N
```

---

## Ready to Go!

Once both keys are set and verified, you're ready to:

1. ✅ Test MCP integration: `python test_mcp_agent.py`
2. ✅ Try dry-run mode: `python main.py --repo ... --issue ... --dry-run`
3. ✅ Run on real issues: `python main.py --repo ... --issue ...`

**Next Steps:**
- See `README.md` for full usage guide
- See `GOOGLE_CHALLENGE_PLAN.md` for Day 11 testing plan
- See `SESSION_SUMMARY.md` for current status

---

**Need Help?**
- Anthropic Console: https://console.anthropic.com/
- GitHub Tokens: https://github.com/settings/tokens
- Project Issues: https://github.com/yourusername/forge-agent/issues
