import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup logger for config validation
logger = logging.getLogger("mister_dm.config")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/mister_dm.db")

WAR_ROOM_GROUP_ID = os.getenv("WAR_ROOM_GROUP_ID")  # Optional Telegram Group ID or Admin User ID for War Room notifications
BOT_USERNAME = os.getenv("BOT_USERNAME", "MisterDMBot")  # Used for deep-link button URLs

# Scheduler settings — flip DRY_RUN to False and set real delays for production
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
DEV_DELAY_MIN = int(os.getenv("DEV_DELAY_MIN", "1"))
DEV_DELAY_MAX = int(os.getenv("DEV_DELAY_MAX", "3"))

TELETHON_API_ID = os.getenv("TELETHON_API_ID", "")
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH", "")

# API Server settings
DM_API_PORT = int(os.getenv("DM_API_PORT", "8013"))
DM_API_KEY = os.getenv("DM_API_KEY", "")

# Mister Simulator Integration Settings
SIMULATOR_API_URL = os.getenv("SIMULATOR_API_URL", "http://localhost:8012")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY", "")

# Groq Triage Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_TRIAGE_MODEL = os.getenv("GROQ_TRIAGE_MODEL", "groq/compound-mini")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "10"))

# Draft Approval Mode (Training Wheels)
APPROVAL_MODE = os.getenv("APPROVAL_MODE", "true").lower() in ("true", "1", "yes")


def validate_env() -> bool:
    """
    Validates Mister_DM environment configuration on boot (Fail-Fast pattern).
    Logs warnings for missing optional keys and critical errors for missing required keys.
    """
    print("[ENV VALIDATOR] Checking Mister_DM environment configuration...")
    missing_required = []
    warnings = []

    # Required keys for Mister_DM
    if not BOT_TOKEN:
        missing_required.append("BOT_TOKEN")
    if not DM_API_KEY:
        missing_required.append("DM_API_KEY")
    if not SIMULATOR_API_KEY:
        missing_required.append("SIMULATOR_API_KEY")
    if not GROQ_API_KEY:
        missing_required.append("GROQ_API_KEY")

    # Optional / Recommended keys
    if not TELETHON_API_ID or not TELETHON_API_HASH:
        warnings.append("TELETHON_API_ID / TELETHON_API_HASH not set. Telethon direct fallbacks will be limited.")
    if not WAR_ROOM_GROUP_ID:
        warnings.append("WAR_ROOM_GROUP_ID not set. War Room admin notifications will be muted.")
    if DRY_RUN:
        warnings.append("DRY_RUN mode is currently TRUE in config. Outbound cold DMs will be simulated.")

    for w in warnings:
        print(f"[ENV VALIDATOR WARNING] {w}")

    if missing_required:
        err_msg = f"[ENV VALIDATOR CRITICAL ERROR] Missing required variables in .env: {', '.join(missing_required)}!"
        print(err_msg)
        raise ValueError(err_msg)

    print("[ENV VALIDATOR SUCCESS] Mister_DM environment validation complete. All critical variables present.")
    return True


# Run validation at boot import time
validate_env()
