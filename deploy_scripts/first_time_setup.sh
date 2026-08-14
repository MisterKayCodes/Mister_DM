#!/bin/bash
# ============================================================
# first_time_setup.sh — Mister DM VPS Initializer
# ============================================================
# Run this ONCE on your VPS to set up Mister DM from scratch.
#
# USAGE (Run on VPS):
#   chmod +x first_time_setup.sh
#   ./first_time_setup.sh
# ============================================================

set -e # Exit on error

REPO_URL="https://github.com/MisterKayCodes/Mister_DM.git"
PROJECT_DIR="$HOME/Mister_DM"
PM2_NAME="mister-dm"

echo "======================================"
echo "  Starting Mister DM VPS Setup..."
echo "======================================"
echo ""

# 1. Update system and install dependencies
echo "[1/6] Checking system dependencies..."
DEPENDENCIES_TO_INSTALL=""

for cmd in python3 python3-venv python3-pip git curl node npm; do
    if ! command -v $cmd &> /dev/null; then
        DEPENDENCIES_TO_INSTALL="$DEPENDENCIES_TO_INSTALL $cmd"
    fi
done

if [ -n "$DEPENDENCIES_TO_INSTALL" ]; then
    echo "Missing dependencies found. Installing:$DEPENDENCIES_TO_INSTALL"
    sudo apt update -y
    sudo apt install -y $DEPENDENCIES_TO_INSTALL
else
    echo "✅ All system dependencies are already installed."
fi

# 2. Install PM2 globally (Process Manager)
echo "[2/6] Checking PM2 process manager..."
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    sudo npm install -g pm2
    pm2 startup | tail -n 1 > /tmp/pm2_startup.sh
    chmod +x /tmp/pm2_startup.sh
    sudo /tmp/pm2_startup.sh || true
    pm2 save
else
    echo "✅ PM2 is already installed."
fi

# 3. Clone Repository
echo "[3/6] Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "Directory $PROJECT_DIR already exists. Pulling latest..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# 4. Setup Python Virtual Environment
echo "[4/6] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Environment Variables
echo "[5/6] Environment Variables..."
echo "⚠️  ACTION REQUIRED: You must upload your .env file via WinSCP or create it manually."
echo "   It should be placed at: $PROJECT_DIR/.env"

# 6. PM2 Ecosystem File
echo "[6/6] Generating PM2 ecosystem configuration..."
cat << EOF > ecosystem.config.js
module.exports = {
  apps : [{
    name   : "$PM2_NAME",
    script : "main.py",
    interpreter: "venv/bin/python",
    watch  : false,
    autorestart: true,
    max_restarts: 10,
    env: {
      NODE_ENV: "production"
    }
  }]
}
EOF

echo ""
echo "======================================"
echo "  Setup Complete! 🎉"
echo "======================================"
echo ""
echo "NEXT STEPS:"
echo "1. Upload your .env file via WinSCP to $PROJECT_DIR"
echo "2. Start the bot:       cd $PROJECT_DIR && pm2 start ecosystem.config.js && pm2 save"
echo "3. View live logs:      pm2 logs $PM2_NAME"
echo ""
echo "Once running, you can use deploy.ps1 from your laptop to deploy updates."
