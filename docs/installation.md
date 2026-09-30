# Installation

This guide covers installing Teotl on your system.

## Requirements

- **Python:** 3.11 or higher
- **Operating System:** macOS, Linux, or Windows
- **LLM access:** an Anthropic, OpenAI, or Google API key, or a local Ollama install

## Installation Methods

### Method 1: From PyPI (Recommended)

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with the Anthropic provider
pip install "teotl[anthropic]"
```

Other provider extras: `openai`, `google`, `ollama`, `litellm`. Combine extras as needed, e.g. `pip install "teotl[anthropic,memory]"`.

**Verify installation:**

```bash
teotl --version
python -c "import teotl; print(teotl.__version__)"
```

### Method 2: From Source (Contributors)

For contributing or development:

```bash
# Clone repository
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev tools and the Anthropic provider
pip install -e ".[dev,anthropic]"
```

## Configuration

### API Keys

Teotl needs access to an LLM provider: Anthropic Claude, OpenAI, Google Gemini, or a local model via Ollama. Install the matching extra (e.g. `teotl[openai]`).

#### Anthropic Claude (Recommended)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**To make permanent (add to your shell profile):**

```bash
# For bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc

# For zsh (macOS default)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

#### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

#### Ollama (Local Models)

For local models with Ollama:

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama3`
3. Install the extra: `pip install "teotl[ollama]"`
4. No API key needed (runs locally)

### Verify Configuration

```bash
# Test Anthropic
python -c "import os; print('✓ API key configured' if os.getenv('ANTHROPIC_API_KEY') else '✗ API key missing')"

# Test OpenAI
python -c "import os; print('✓ API key configured' if os.getenv('OPENAI_API_KEY') else '✗ API key missing')"
```

## First Run

### Interactive Onboarding

Run the interactive wizard to set up your first agent:

```bash
teotl onboard
```

This wizard will:
- Help you set your API key (for the current session, and optionally in your shell profile)
- Set up agent preferences
- Choose skills and capabilities
- Configure security settings
- Generate a `config.yaml` (and, for planner-worker agents, a `run_planner_worker.py` script)

`teotl wizard` is an alias for the same wizard.

### Manual Setup

Alternatively, skip the wizard and use Teotl directly from Python (see the [Quick Start Guide](quickstart.md)), or write a daemon config by hand starting from [examples/full_config_reference.yaml](../examples/full_config_reference.yaml).

## Platform-Specific Instructions

### macOS

**Prerequisites:**
```bash
# Install Python 3.11+ (using Homebrew)
brew install python@3.11

# Verify version
python3 --version
```

**Installation:**
```bash
pip3 install "teotl[anthropic]"
```

### Linux

**Prerequisites:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip

# Fedora/RHEL
sudo dnf install python3.11

# Verify version
python3 --version
```

**Installation:**
```bash
pip3 install "teotl[anthropic]"
```

### Windows

**Prerequisites:**
1. Install Python 3.11+ from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"

**Installation (Command Prompt or PowerShell):**
```bash
pip install "teotl[anthropic]"
```

### Credential Storage

Integration credentials saved through Teotl's `CredentialStore` use the OS keyring when one is available (macOS Keychain, Windows Credential Manager, or Secret Service such as GNOME Keyring/KWallet on Linux), and fall back to an encrypted file otherwise. LLM API keys are read from environment variables such as `ANTHROPIC_API_KEY`.

## Virtual Environments (Recommended)

Using virtual environments keeps Teotl isolated from system Python:

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install Teotl
pip install "teotl[anthropic]"

# When done, deactivate
deactivate
```

## Optional Dependencies

| Extra | Installs | Use for |
|-------|----------|---------|
| `anthropic` | anthropic | Claude models |
| `openai` | openai | OpenAI models |
| `google` | google-generativeai | Gemini models |
| `ollama` | ollama | Local models via Ollama |
| `litellm` | litellm | LiteLLM |
| `memory` | sentence-transformers, sqlite-vec | `LocalMemory` long-term memory |
| `security` | cryptography, keyring | Encryption and OS credential storage |
| `web` | aiohttp | Web dashboard (`python -m teotl.web`) |
| `aws` | boto3 | AWS integrations |
| `all` | all of the above | Everything |
| `dev` | pytest, pytest-asyncio, pytest-cov, ruff, mypy, pre-commit | Contributing |

Example:

```bash
pip install "teotl[anthropic,memory,security]"
```

From a source checkout, use the same extras with an editable install, e.g. `pip install -e ".[dev,anthropic]"`.

## Troubleshooting

### Issue: "command not found: teotl"

**Solution:**
```bash
# Check that pip installed the package
pip show teotl

# If installed but the script isn't on your PATH, use:
python -m teotl.cli --help
```

### Issue: "No module named 'teotl'"

**Solution:**
```bash
# Ensure your virtual environment is activated
source venv/bin/activate

# Reinstall
pip install "teotl[anthropic]"
```

### Issue: "API key not configured"

**Solution:**
```bash
# Check environment variable
echo $ANTHROPIC_API_KEY

# If empty, set it:
export ANTHROPIC_API_KEY="sk-ant-..."

# Or use the onboarding wizard:
teotl onboard
```

### Issue: Credential storage errors (Linux)

**Solution:**
```bash
# Install keyring dependencies
# Ubuntu/Debian:
sudo apt-get install gnome-keyring python3-secretstorage

# Fedora/RHEL:
sudo dnf install gnome-keyring python3-secretstorage

# Restart your session for changes to take effect
```

### Issue: SSL Certificate errors

**Solution:**
```bash
# Update certifi
pip install --upgrade certifi

# If on corporate network, set certificate path:
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
```

## Upgrading

### From PyPI

```bash
pip install --upgrade "teotl[anthropic]"
```

### From Source

```bash
cd teotl
git pull origin main
pip install -e ".[dev,anthropic]"
```

### Coming from Forge (the previous name)

Teotl was previously called Forge. Existing setups keep working without changes:

- **Data directory:** Teotl stores memory, missions, tasks, credentials, and agent workspaces in `~/.teotl` (override with `TEOTL_HOME`). If `~/.teotl` doesn't exist but `~/.forge` does, Teotl keeps using `~/.forge`. To switch, stop any running daemons and run:

  ```bash
  mv ~/.forge ~/.teotl
  ```

  Configs you created earlier may still contain `~/.forge/...` paths (for example `workspace:` or `daemon.data_dir`); update them after moving.
- **Environment variables:** use `TEOTL_SKILLS_PATH`, `TEOTL_ALLOW_ENV_AUTH`, and `TEOTL_<SERVICE>_API_KEY` / `_TOKEN` / `_ACCESS_TOKEN`. The `FORGE_*` names still work.
- **OS keyring:** new entries are stored under `teotl`. Credentials saved under `forge` are still read, and the master key is copied (not moved) the first time.

## Uninstallation

```bash
pip uninstall teotl
```

Agent workspaces and data created by the wizard or daemon live under `~/.teotl/` by default; remove them manually if you no longer need them.

## Docker

Official Docker images are not currently published. Install with pip as described above.

## Next Steps

- [Quick Start Guide](quickstart.md) - Build your first agent in 5 minutes
- [Concepts](concepts.md) - Understand core concepts
- [API Reference](api_reference.md) - Complete API documentation

## Getting Help

- **Documentation:** https://github.com/keithdit4e/teotl/tree/main/docs
- **Issues:** https://github.com/keithdit4e/teotl/issues
- **Discussions:** https://github.com/keithdit4e/teotl/discussions
