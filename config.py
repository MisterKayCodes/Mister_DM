import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/mister_dm.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")

WAR_ROOM_GROUP_ID = os.getenv("WAR_ROOM_GROUP_ID")  # Optional Telegram Group ID or Admin User ID for War Room notifications
BOT_USERNAME = os.getenv("BOT_USERNAME", "MisterDMBot")  # Used for deep-link button URLs

# Scheduler settings — flip DRY_RUN to False and set real delays for production
DRY_RUN = True
DEV_DELAY_MIN = 1
DEV_DELAY_MAX = 3

TELETHON_API_ID = os.getenv("TELETHON_API_ID")
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH")

# API Server settings
DM_API_PORT = int(os.getenv("DM_API_PORT", "8013"))
DM_API_KEY = os.getenv("DM_API_KEY")

if not DM_API_KEY:
    raise ValueError("DM_API_KEY is not set in the environment variables.")

# Mister Simulator Integration Settings
SIMULATOR_API_URL = os.getenv("SIMULATOR_API_URL", "http://localhost:8012")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY")

if not SIMULATOR_API_KEY:
    raise ValueError("SIMULATOR_API_KEY is not set in the environment variables.")

# Groq Triage Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TRIAGE_MODEL = os.getenv("GROQ_TRIAGE_MODEL", "groq/compound-mini")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "10"))

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment variables.")

# Draft Approval Mode (Training Wheels)
APPROVAL_MODE = os.getenv("APPROVAL_MODE", "true").lower() in ("true", "1", "yes")


