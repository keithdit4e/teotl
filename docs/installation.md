# Installation

This guide covers installing Teotl on your system.

## Requirements

- **Python:** 3.11 or higher
- **Operating System:** macOS, Linux, or Windows
- **API Keys:** Anthropic Claude or OpenAI account (for LLM access)

## Installation Methods

### Method 1: From Source (Current - Required)

**Teotl is currently in alpha and must be installed from source.**

```bash
# Clone repository
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with Anthropic provider
pip install -e ".[anthropic]"
```

**Verify installation:**

```bash
python -c "import teotl; print('Teotl installed!')"
```

### Method 2: From PyPI (Coming Soon)

> **Note:** PyPI installation is not yet available. This will be enabled after Teotl reaches stable release.

```bash
# Future command (not available yet)
pip install teotl
```

### Method 3: From Source (Development)

For contributing or development:

```bash
# Clone repository
git clone https://github.com/yourusername/teotl
cd teotl

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

**Verify installation:**

```bash
python -c "import teotl; print(teotl.__version__)"
# 0.1.0
```

## Configuration

### API Keys

Teotl requires an LLM provider API key. You can use either Anthropic Claude or OpenAI.

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
3. No API key needed (runs locally)

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
- Configure your API key (stored securely)
- Set up agent preferences
- Choose skills and capabilities
- Configure security policies
- Create your first agent configuration

### Manual Setup

Alternatively, create agent configuration manually:

```bash
# Initialize Teotl
teotl init

# Creates ~/.teotl/ directory with:
# - auth/           (credential storage)
# - skills/         (custom skills)
# - agents/         (agent configurations)
```

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
git clone https://github.com/keithdit4e/teotl.git
cd teotl
pip3 install -e ".[anthropic]"
```

**Credential Storage:**
Uses macOS Keychain automatically for secure credential storage.

### Linux

**Prerequisites:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip git

# Fedora/RHEL
sudo dnf install python3.11 git

# Verify version
python3 --version
```

**Installation:**
```bash
git clone https://github.com/keithdit4e/teotl.git
cd teotl
pip3 install -e ".[anthropic]"
```

**Credential Storage:**
Uses Secret Service (GNOME Keyring, KWallet) if available, otherwise encrypted file storage.

### Windows

**Prerequisites:**
1. Install Python 3.11+ from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"

**Installation (Command Prompt or PowerShell):**
```bash
git clone https://github.com/keithdit4e/teotl.git
cd teotl
pip install -e ".[anthropic]"
```

**Credential Storage:**
Uses Windows Credential Manager automatically for secure credential storage.

## Virtual Environments (Recommended)

Using virtual environments keeps Teotl isolated from system Python:

```bash
# Clone repository
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install Teotl
pip install -e ".[anthropic]"

# When done, deactivate
deactivate
```

## Optional Dependencies

### Development Tools

For development and testing:

```bash
pip install -e ".[dev]"
```

Includes:
- pytest (testing framework)
- ruff (code formatter and linter)
- mypy (type checking)
- coverage (code coverage)

### Security Enhancements

For enhanced security features:

```bash
pip install -e ".[security]"
```

Includes:
- cryptography (encryption)
- keyring (OS credential storage)

### All Optional Dependencies

```bash
pip install -e ".[all]"
```

## Troubleshooting

### Issue: "command not found: teotl"

**Solution:**
```bash
# Check if pip installed to correct location
pip show teotl

# If installed but not in PATH, use:
python -m teotl --help
```

### Issue: "No module named 'teotl'"

**Solution:**
```bash
# Ensure you're in the teotl directory
cd /path/to/teotl

# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall
pip install -e ".[anthropic]"
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

### From Source (Current Method)

```bash
cd teotl
git pull origin main
pip install -e ".[anthropic]"
```

### From PyPI (Coming Soon)

```bash
# Future command (not available yet)
pip install --upgrade teotl
```

## Uninstallation

```bash
pip uninstall teotl

# Optional: Remove configuration
rm -rf ~/.teotl
```

## Docker (Coming Soon)

> **Note:** Docker images will be available after Teotl reaches stable release.

For now, install from source as described above.

## Next Steps

- [Quick Start Guide](quickstart.md) - Build your first agent in 5 minutes
- [Concepts](concepts.md) - Understand core concepts
- [API Reference](api_reference.md) - Complete API documentation

## Getting Help

- **Documentation:** https://github.com/yourusername/teotl/docs
- **Issues:** https://github.com/yourusername/teotl/issues
- **Discussions:** https://github.com/yourusername/teotl/discussions
