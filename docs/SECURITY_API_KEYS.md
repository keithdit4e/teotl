# API Key Security Best Practices

## Overview

Teotl supports multiple ways to provide API keys. This guide explains the security implications and recommends best practices.

## ⚠️ Security Priority Order

From **most secure** to **least secure**:

1. ✅ **Environment Variables** (Recommended)
2. ⚠️ **Protected Config File** (`~/.teotl/config.yaml` with restrictive permissions)
3. ❌ **Direct Code** (Never do this)

## 🔐 Recommended: Environment Variables

### Why Environment Variables?

- ✅ **Not in git repositories** - Can't be accidentally committed
- ✅ **Not in config files** - Won't be backed up or shared
- ✅ **Standard practice** - Used by most production systems
- ✅ **Easy to rotate** - Change without modifying code
- ✅ **Separate per environment** - Different keys for dev/prod

### Setup: Persistent Environment Variable

#### For Bash (Linux, macOS default)

Add to `~/.bashrc` or `~/.bash_profile`:

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

Then reload:
```bash
source ~/.bashrc
```

#### For Zsh (macOS Catalina+)

Add to `~/.zshrc`:

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

Then reload:
```bash
source ~/.zshrc
```

#### For Fish Shell

Add to `~/.config/fish/config.fish`:

```fish
set -Ux ANTHROPIC_API_KEY "sk-ant-api03-your-key-here"
```

#### Verify It's Set

```bash
echo $ANTHROPIC_API_KEY
# Should show: sk-ant-api03-your-key-here
```

### Usage with Teotl

Once the environment variable is set, Teotl automatically uses it:

```python
from teotl.core.provider import AnthropicProvider

# No api_key needed - automatically uses ANTHROPIC_API_KEY
provider = AnthropicProvider()
```

## 🔧 Alternative: Config File

If you must use a config file, ensure it has restrictive permissions.

### Setup

Create `~/.teotl/config.yaml`:

```yaml
anthropic:
  api_key: sk-ant-api03-your-key-here
```

### Secure the File

**CRITICAL**: Set restrictive permissions (owner read/write only):

```bash
chmod 600 ~/.teotl/config.yaml
```

This prevents other users on the system from reading your API key.

### Verify Permissions

```bash
ls -l ~/.teotl/config.yaml
# Should show: -rw------- (600)
```

### Usage

```python
import yaml
from pathlib import Path

config_path = Path.home() / ".teotl" / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)
    api_key = config["anthropic"]["api_key"]

provider = AnthropicProvider(api_key=api_key)
```

## ❌ Never Do This

### Don't Hardcode in Code

```python
# ❌ BAD - Key is in source code
provider = AnthropicProvider(api_key="sk-ant-api03-...")
```

**Why this is dangerous:**
- Will be committed to git
- Visible in git history forever
- Exposed to anyone with repo access
- Can't be easily rotated

### Don't Commit Config Files with Keys

```bash
# ❌ BAD - Config file with key in git
git add ~/.teotl/config.yaml
git commit -m "Add config"
```

**Prevention:**
Add to `.gitignore`:
```
.env
config.yaml
*.key
*.pem
```

### Don't Share Keys

- ❌ Don't paste in chat/email
- ❌ Don't include in screenshots
- ❌ Don't commit to public repos
- ❌ Don't share with unauthorized users

## 🎯 Production Best Practices

### 1. Use Secret Management Systems

For production deployments:
- **AWS**: AWS Secrets Manager or Systems Manager Parameter Store
- **GCP**: Google Secret Manager
- **Azure**: Azure Key Vault
- **Kubernetes**: Kubernetes Secrets
- **Docker**: Docker Secrets

### 2. Rotate Keys Regularly

```bash
# Update environment variable
export ANTHROPIC_API_KEY="sk-ant-new-key-here"

# Or update config file
vim ~/.teotl/config.yaml
```

### 3. Use Separate Keys Per Environment

```bash
# Development
export ANTHROPIC_API_KEY="sk-ant-dev-key"

# Production
export ANTHROPIC_API_KEY="sk-ant-prod-key"
```

### 4. Monitor API Usage

Check your Anthropic dashboard regularly:
- https://console.anthropic.com/settings/usage

Look for:
- Unexpected usage spikes
- Requests from unknown IPs
- Unusual API call patterns

### 5. Revoke Compromised Keys Immediately

If a key is exposed:
1. Go to https://console.anthropic.com/settings/keys
2. Delete the compromised key
3. Generate a new key
4. Update your environment variable/config
5. Restart all services

## 🔍 Checking Your Setup

### Environment Variable Method

```bash
# Check if set
env | grep ANTHROPIC_API_KEY

# Test with Teotl
python3 << EOF
from teotl.core.provider import AnthropicProvider
provider = AnthropicProvider()  # Should work without error
print("✅ API key loaded from environment variable")
EOF
```

### Config File Method

```bash
# Check file exists and is secure
ls -l ~/.teotl/config.yaml

# Should show: -rw------- (only you can read/write)
# If not: chmod 600 ~/.teotl/config.yaml

# Test with Teotl
python3 << EOF
import yaml
from pathlib import Path
from teotl.core.provider import AnthropicProvider

config_path = Path.home() / ".teotl" / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)
    api_key = config["anthropic"]["api_key"]

provider = AnthropicProvider(api_key=api_key)
print("✅ API key loaded from config file")
EOF
```

## 📝 Teotl Onboarding Wizard

The Teotl onboarding wizard (`teotl onboard`) prompts for your API key and:

1. **Stores in config file** with secure permissions (600)
2. **Recommends** moving to environment variable for production
3. **Never logs** or displays the key after entry
4. **Validates** the key works before continuing

For enhanced security, **manually set the environment variable** instead of using the wizard's config file storage.

## 🛡️ CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: pytest tests/
```

Add secret at: Repository Settings → Secrets → Actions → New repository secret

### GitLab CI

```yaml
# .gitlab-ci.yml
test:
  script:
    - pytest tests/
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

Add variable at: Settings → CI/CD → Variables

### CircleCI

```yaml
# .circleci/config.yml
jobs:
  test:
    steps:
      - run: pytest tests/
```

Add variable at: Project Settings → Environment Variables

## 🚨 Security Checklist

Before deploying:

- [ ] API key is in environment variable or protected config file
- [ ] API key is NOT in git repository
- [ ] API key is NOT hardcoded in source files
- [ ] Config file has restrictive permissions (600)
- [ ] `.env` and `config.yaml` are in `.gitignore`
- [ ] Different keys used for dev/staging/prod
- [ ] API usage is monitored
- [ ] Team knows how to rotate keys

## 📚 Additional Resources

- [Anthropic API Keys](https://console.anthropic.com/settings/keys)
- [Anthropic Best Practices](https://docs.anthropic.com/claude/reference/getting-started)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Remember**: Treat API keys like passwords. Never commit, share, or expose them! 🔐
