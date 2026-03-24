#!/bin/bash
# deploy.sh — Run on homeserver to deploy the twitter-gig-hunter agent
# Usage: bash deploy.sh
set -euo pipefail

echo "=== Twitter Gig Hunter Agent Deployment ==="

# Step 1: Check ZeroClaw is installed and version >= 0.5.1
echo "[1/7] Checking ZeroClaw version..."
if ! command -v zeroclaw &> /dev/null; then
    echo "ERROR: ZeroClaw not found. Install with:"
    echo "  curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash"
    exit 1
fi
ZCVER=$(zeroclaw --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1)
echo "  Found ZeroClaw v${ZCVER}"

# Parse version components for comparison
IFS='.' read -r ZC_MAJOR ZC_MINOR ZC_PATCH <<< "$ZCVER"
if [ "$ZC_MAJOR" -eq 0 ] && [ "$ZC_MINOR" -lt 5 ]; then
    echo "WARNING: ZeroClaw v${ZCVER} < 0.5.1"
    echo "  Shell tools may fail in headless/systemd mode (bug #851)."
    echo "  Upgrade: curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash"
elif [ "$ZC_MAJOR" -eq 0 ] && [ "$ZC_MINOR" -eq 5 ] && [ "$ZC_PATCH" -lt 1 ]; then
    echo "WARNING: ZeroClaw v${ZCVER} < 0.5.1"
    echo "  Shell tools may fail in headless/systemd mode (bug #851)."
    echo "  Upgrade: curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash"
fi

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

# Deploy SKILL.toml
if [ -f "${REPO_DIR}/config/skills/twitter-gig-hunter/SKILL.toml" ]; then
    cp "${REPO_DIR}/config/skills/twitter-gig-hunter/SKILL.toml" \
       ~/.zeroclaw/workspace/skills/twitter-gig-hunter/SKILL.toml
    echo "  Deployed SKILL.toml"
else
    echo "WARNING: SKILL.toml not found in repo"
fi

# Deploy Python scripts
if [ -d "${REPO_DIR}/scripts" ]; then
    cp "${REPO_DIR}"/scripts/*.py \
       ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/
    echo "  Deployed Python scripts"
else
    echo "WARNING: scripts/ directory not found in repo"
fi

# Step 5: Load secrets into ZeroClaw's encrypted store
echo "[5/7] Checking secrets in ZeroClaw encrypted store..."
echo "  The following secrets must be set for the agent to function."
echo "  If you have not set them yet, run each command manually:"
echo ""
echo "    zeroclaw secrets set MINIMAX_API_KEY <your-minimax-api-key>"
echo "    zeroclaw secrets set TWITTER_USERNAME <your-twitter-username>"
echo "    zeroclaw secrets set TWITTER_EMAIL <your-twitter-email>"
echo "    zeroclaw secrets set TWITTER_PASSWORD <your-twitter-password>"
echo "    zeroclaw secrets set OPENAI_API_KEY <your-openai-api-key>"
echo ""

# Check if secrets are already set
SECRETS_SET=true
for SECRET in MINIMAX_API_KEY TWITTER_USERNAME TWITTER_EMAIL TWITTER_PASSWORD OPENAI_API_KEY; do
    if ! zeroclaw secrets list 2>/dev/null | grep -q "$SECRET"; then
        echo "  WARNING: $SECRET is not set in ZeroClaw secrets"
        SECRETS_SET=false
    fi
done

if [ "$SECRETS_SET" = true ]; then
    echo "  All 5 secrets are loaded."
else
    echo ""
    echo "  Some secrets are missing. The agent will produce structured errors"
    echo "  (not crashes) when invoked without them, but tools will not function."
    echo "  Set missing secrets with: zeroclaw secrets set <KEY> <VALUE>"
fi

# Step 6: Initialize database schema
echo "[6/7] Initializing memory schema..."
python3 ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/init_db.py

# Step 7: Install and start systemd service
echo "[7/7] Installing systemd service..."
zeroclaw service install
systemctl --user daemon-reload
systemctl --user enable zeroclaw
systemctl --user start zeroclaw
sleep 5
systemctl --user status zeroclaw --no-pager

echo ""
echo "=== Deployment complete ==="
echo "  Gateway: http://localhost:42617"
echo "  Logs:    journalctl --user -u zeroclaw -f"
echo "  Status:  systemctl --user status zeroclaw"
echo ""
echo "Next steps:"
echo "  1. Run smoke test: python3 ~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/test_smoke.py"
echo "  2. Visit gateway: http://localhost:42617"
echo "  3. Check logs: journalctl --user -u zeroclaw -f"
