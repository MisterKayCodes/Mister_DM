# ============================================================
# deploy.ps1 — Mister DM Remote Deployer
# ============================================================
# Run this from your Windows laptop whenever you push new code.
# It SSHes into the VPS, pulls the latest code, restarts the
# bot, and shows the last 40 lines of logs — all in one shot.
#
# USAGE:
#   Right-click → Run with PowerShell
#   OR in terminal: .\deploy_scripts\deploy.ps1
# ============================================================

$VPS_HOST   = "root@67.211.221.40" # Assuming same VPS IP
$PROJECT_DIR = "~/Mister_DM"
$PM2_NAME   = "mister-dm"
$LOG_LINES  = 40

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Deploying: $PM2_NAME" -ForegroundColor Cyan
Write-Host "  VPS: $VPS_HOST" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Run all commands in a single SSH session
$commands = @"
cd $PROJECT_DIR

echo '--- Pulling latest code ---'
PULL_OUTPUT=`$(git pull origin main 2>&1)
echo "`$PULL_OUTPUT"

echo ''
# Check if the process exists in PM2
if ! pm2 describe $PM2_NAME > /dev/null 2>&1; then
    echo '--- Initializing Bot in PM2 for the first time ---'
    # We must be in the project dir where ecosystem.config.js is
    pm2 start ecosystem.config.js
    pm2 save
else
    # If it exists, only restart if we actually pulled new code
    if echo "`$PULL_OUTPUT" | grep -q "Already up to date."; then
        echo '--- Code is already up to date. Skipping PM2 restart. ---'
    else
        echo '--- New code pulled. Restarting bot ---'
        pm2 restart $PM2_NAME
    fi
fi

echo ''
echo '--- Last $LOG_LINES log lines ---'
pm2 logs $PM2_NAME --lines $LOG_LINES --nostream
"@

ssh $VPS_HOST $commands

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Deploy complete!" -ForegroundColor Green
Write-Host "  To stream live logs, SSH in and run:" -ForegroundColor Yellow
Write-Host "  pm2 logs $PM2_NAME" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
