# Mister DM Deployment Scripts

This folder contains scripts to manage deployment from your local Windows machine to your Linux VPS.

## 1. Initial Setup (Run ONCE)

When you buy a fresh VPS (Ubuntu/Debian), you need to install Python, Node, PM2, and clone the bot.

1. SSH into your VPS:
   ```bash
   ssh root@YOUR_VPS_IP
   ```
2. Download and run the setup script:
   ```bash
   curl -O https://raw.githubusercontent.com/MisterKayCodes/Mister_DM/main/deploy_scripts/first_time_setup.sh
   chmod +x first_time_setup.sh
   ./first_time_setup.sh
   ```
3. Follow the on-screen instructions to add your `BOT_TOKEN` to `.env` and start the bot with `pm2`.

## 2. Continuous Deployment (Run OFTEN)

Once the bot is running on the VPS, you never need to SSH in to update it again.

Whenever you push new code from your laptop to GitHub, simply run the PowerShell script on your laptop:

1. Right-click `deploy.ps1` and select **Run with PowerShell**.
2. Or run it from your terminal:
   ```powershell
   .\deploy_scripts\deploy.ps1
   ```

It will automatically:
- Connect to your VPS
- Pull the latest code from GitHub
- Restart the bot using PM2
- Show you the latest logs to confirm it started successfully
