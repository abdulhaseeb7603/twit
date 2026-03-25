#!/bin/bash
# deploy.sh — Run on homeserver to deploy the twitter-gig-hunter agent
# Usage: bash deploy.sh
set -euo pipefail

echo "=== Twitter Gig Hunter Agent Deployment ==="

# Step 1: Check ZeroClaw is installed
echo "[1/7] Checking ZeroClaw..."
if ! command -v zeroclaw &> /dev/null; then
    echo "ERROR: ZeroClaw not found. Install with:"
    echo "  curl -fsSL https://zeroclawlabs.ai/install.sh | bash"
    echo ""
    echo "Or build from source:"
    echo "  git clone https://github.com/openagen/zeroclaw.git"
    echo "  cd zeroclaw && ./bootstrap.sh"
    exit 1
fi
ZCVER=$(zeroclaw --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1)
echo "  Found ZeroClaw v${ZCVER}"

# Step 2: Install Python dependencies
echo "[2/7] Installing Python dependencies..."
pip install twikit==2.3.3 httpx --break-system-packages -q

# Step 3: Ensure directory structure exists
echo "[3/7] Creating directory structure..."
mkdir -p ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts
mkdir -p ~/.zeroclaw/workspace/memory

# Step 4: Copy config and skill files
echo "[4/7] Deploying config and skill files..."
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Deploy config.toml (preserve existing if user has customized it)
if [ -f "${REPO_DIR}/config/config.toml" ]; then
    if [ ! -f ~/.zeroclaw/config.toml ]; then
        cp "${REPO_DIR}/config/config.toml" ~/.zeroclaw/config.toml
        echo "  Deployed config.toml"
    else
        echo "  config.toml already exists (not overwritten)"
    fi
else
    echo "WARNING: config/config.toml not found in repo"
fi

# Deploy SKILL.md
if [ -f "${REPO_DIR}/config/skills/twitter-gig-hunter/SKILL.md" ]; then
    cp "${REPO_DIR}/config/skills/twitter-gig-hunter/SKILL.md" \
       ~/.zeroclaw/workspace/skills/twitter-gig-hunter/SKILL.md
    echo "  Deployed SKILL.md"
else
    echo "WARNING: SKILL.md not found in repo"
fi

# Deploy Python scripts
if [ -d "${REPO_DIR}/scripts" ]; then
    cp "${REPO_DIR}"/scripts/*.py \
       ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/
    echo "  Deployed Python scripts"
else
    echo "WARNING: scripts/ directory not found in repo"
fi

# Step 5: Environment variables for secrets
echo "[5/7] Checking environment variables..."
echo "  The following env vars must be set for the agent to function."
echo "  Add them to ~/.bashrc or ~/.profile, then re-login:"
echo ""
echo "    export MINIMAX_API_KEY='your-minimax-api-key'"
echo "    export TWITTER_USERNAME='your-twitter-username'"
echo "    export TWITTER_EMAIL='your-twitter-email'"
echo "    export TWITTER_PASSWORD='your-twitter-password'"
echo "    export OPENAI_API_KEY='your-openai-api-key'"
echo ""

SECRETS_SET=true
for SECRET in MINIMAX_API_KEY TWITTER_USERNAME TWITTER_EMAIL TWITTER_PASSWORD OPENAI_API_KEY; do
    if [ -z "${!SECRET:-}" ]; then
        echo "  WARNING: $SECRET is not set"
        SECRETS_SET=false
    fi
done

if [ "$SECRETS_SET" = true ]; then
    echo "  All 5 env vars are set."
else
    echo ""
    echo "  Some env vars are missing. The agent will produce structured errors"
    echo "  (not crashes) when invoked without them, but tools will not function."
fi

# Step 6: Initialize database schema
echo "[6/7] Initializing memory schema..."
python3 ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/init_db.py

# Step 7: Install and start systemd service
echo "[7/7] Installing ZeroClaw service..."
zeroclaw service install
zeroclaw service start
sleep 3
zeroclaw service status || systemctl --user status zeroclaw --no-pager

echo ""
echo "=== Deployment complete ==="
echo "  Gateway: http://localhost:42617"
echo "  Logs:    journalctl --user -u zeroclaw -f"
echo "  Status:  zeroclaw service status"
echo ""
echo "Next steps:"
echo "  1. Run smoke test: python3 ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/test_smoke.py"
echo "  2. Visit gateway: http://localhost:42617"
echo "  3. Check logs: journalctl --user -u zeroclaw -f"
