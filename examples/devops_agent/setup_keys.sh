#!/bin/bash
# Setup script for DevOps Agent API keys

set -e

echo ""
echo "=========================================="
echo "  DevOps Agent - API Keys Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a key is set
check_key() {
    local key_name=$1
    local key_value=$2

    if [ -z "$key_value" ]; then
        echo -e "${RED}❌ $key_name is not set${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $key_name is set${NC}"
        # Show first few characters
        echo "   ${key_value:0:15}..."
        return 0
    fi
}

# Check current status
echo "Current status:"
echo ""

anthropic_set=0
github_set=0

if check_key "ANTHROPIC_API_KEY" "$ANTHROPIC_API_KEY"; then
    anthropic_set=1
fi

if check_key "GITHUB_TOKEN" "$GITHUB_TOKEN"; then
    github_set=1
fi

echo ""

# If both are set, we're done
if [ $anthropic_set -eq 1 ] && [ $github_set -eq 1 ]; then
    echo -e "${GREEN}✅ All API keys are configured!${NC}"
    echo ""
    echo "You're ready to run:"
    echo "  python test_mcp_agent.py"
    echo "  python main.py --repo owner/repo --issue N --dry-run"
    echo ""
    exit 0
fi

# Otherwise, guide user to set them
echo "=========================================="
echo "  Setup Instructions"
echo "=========================================="
echo ""

if [ $anthropic_set -eq 0 ]; then
    echo -e "${YELLOW}📝 ANTHROPIC_API_KEY not set${NC}"
    echo ""
    echo "1. Get your API key:"
    echo "   → Visit: https://console.anthropic.com/settings/keys"
    echo "   → Click 'Create Key'"
    echo "   → Copy the key (starts with sk-ant-)"
    echo ""
    echo "2. Set the key:"
    echo "   export ANTHROPIC_API_KEY=\"sk-ant-your-key-here\""
    echo ""
    echo "3. Make it permanent (optional):"
    echo "   echo 'export ANTHROPIC_API_KEY=\"sk-ant-your-key-here\"' >> ~/.zshrc"
    echo "   source ~/.zshrc"
    echo ""
fi

if [ $github_set -eq 0 ]; then
    echo -e "${YELLOW}📝 GITHUB_TOKEN not set${NC}"
    echo ""
    echo "1. Get your GitHub token:"
    echo "   → Visit: https://github.com/settings/tokens"
    echo "   → Click 'Generate new token (classic)'"
    echo "   → Select scopes: repo, workflow, read:org"
    echo "   → Copy the token (starts with ghp_)"
    echo ""
    echo "2. Set the token:"
    echo "   export GITHUB_TOKEN=\"ghp_your-token-here\""
    echo ""
    echo "3. Make it permanent (optional):"
    echo "   echo 'export GITHUB_TOKEN=\"ghp_your-token-here\"' >> ~/.zshrc"
    echo "   source ~/.zshrc"
    echo ""
fi

echo "=========================================="
echo ""
echo "After setting keys, run this script again to verify:"
echo "  ./setup_keys.sh"
echo ""
echo "Or check manually:"
echo "  echo \$ANTHROPIC_API_KEY"
echo "  echo \$GITHUB_TOKEN"
echo ""
echo "For detailed instructions, see: API_KEYS_SETUP.md"
echo ""
