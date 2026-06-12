# Installation Options

**How to install Teotl (Current & Future)**

Last Updated: March 25, 2026

---

## Current Installation Method (Alpha)

**Teotl is currently in ALPHA and must be installed from source.**

### Option 1: Install from GitHub (Current - Required)

This is currently the ONLY way to install Teotl.

```bash
# 1. Clone the repository
git clone https://github.com/keithdit4e/teotl.git
cd teotl

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# 3. Install in development mode
pip install -e ".[anthropic]"

# 4. Verify installation
python -c "import teotl; print('Teotl installed!')"
```

**Pros:**
- ✅ Always get the latest code
- ✅ Can contribute back changes
- ✅ Easy to update (`git pull`)
- ✅ Can modify source code

**Cons:**
- ❌ Requires Git
- ❌ More steps than PyPI
- ❌ Must be in the directory to use

---

## Future Installation Method (Post-Launch)

### Option 2: Install from PyPI (Coming Soon)

**NOT AVAILABLE YET** - This will be available when Teotl reaches beta/stable.

```bash
# Future command (doesn't work yet!)
pip install teotl[anthropic]

# Then use anywhere
python -m teotl.cli.wizard
```

**When will this be available?**
- After beta release
- After comprehensive testing
- After stable API is established
- Estimated: Q2-Q3 2026

---

## Installation for Different Use Cases

### For Personal Use (Recommended: GitHub)

```bash
# Install from source
git clone https://github.com/keithdit4e/teotl.git
cd teotl
pip install -e ".[anthropic]"
```

**Why:** Always get latest features, easy to update

### For Development (Required: GitHub)

```bash
# Clone with development extras
git clone https://github.com/keithdit4e/teotl.git
cd teotl
pip install -e ".[dev]"  # Includes testing tools

# Or install everything
pip install -e ".[all]"  # All providers + dev tools
```

### For Production (Wait for PyPI)

**Not recommended yet** - Teotl is in alpha. Wait for stable release on PyPI.

---

## Provider-Specific Installation

Teotl supports multiple LLM providers:

### Anthropic (Claude)

```bash
pip install -e ".[anthropic]"
# OR
pip install anthropic pyyaml aiohttp pydantic
```

### OpenAI (GPT)

```bash
pip install -e ".[openai]"
# OR
pip install openai pyyaml aiohttp pydantic
```

### Ollama (Local)

```bash
pip install -e ".[ollama]"
# OR
pip install ollama pyyaml aiohttp pydantic
```

### All Providers

```bash
pip install -e ".[all]"
```

---

## Updating Teotl

### From GitHub (Current Method)

```bash
cd /path/to/teotl
git pull origin main
pip install -e ".[anthropic]"  # Reinstall in case of new dependencies
```

### From PyPI (Future Method)

```bash
pip install --upgrade teotl[anthropic]
```

---

## Uninstalling

### From GitHub Installation

```bash
# 1. Uninstall package
pip uninstall teotl

# 2. Remove cloned directory
rm -rf /path/to/teotl

# 3. (Optional) Remove user data
rm -rf ~/.teotl/
```

### From PyPI (Future)

```bash
# Uninstall package
pip uninstall teotl

# (Optional) Remove user data
rm -rf ~/.teotl/
```

---

## Installation Verification

After installation, verify Teotl works:

```bash
# Check Python can import Teotl
python -c "import teotl; print('✓ Teotl imported successfully')"

# Check version (if set)
python -c "import teotl; print(f'Teotl version: {teotl.__version__}')"

# Run wizard
python -m teotl.cli.wizard
```

---

## Troubleshooting Installation

### Issue: ModuleNotFoundError: No module named 'teotl'

**Solution:**
```bash
# Make sure you're in the teotl directory
cd /path/to/teotl

# Reinstall
pip install -e ".[anthropic]"

# Verify virtual environment is activated
which python  # Should point to venv/bin/python
```

### Issue: Permission Denied

**Solution:**
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install -e ".[anthropic]"

# OR use --user flag (not recommended)
pip install --user -e ".[anthropic]"
```

### Issue: Git Not Found

**Solution:**
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Windows
# Download from https://git-scm.com/downloads
```

### Issue: Python Version Too Old

```bash
# Check version
python --version

# Need Python 3.10+
# Install newer Python from https://www.python.org/downloads/
```

---

## Docker Installation (Advanced)

**Coming soon** - Docker images will be available after stable release.

Future command:
```bash
docker pull teotl:latest
docker run -it teotl:latest
```

---

## Next Steps After Installation

1. ✅ Verify installation works
2. 📖 Read [Getting Started Guide](GETTING_STARTED.md)
3. 🔑 Set up API key
4. 🚀 Run wizard: `python -m teotl.cli.wizard`
5. 🤖 Start your first agent

---

## Getting Help

- **Installation Issues:** https://github.com/keithdit4e/teotl/issues
- **Documentation:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Quick Reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
