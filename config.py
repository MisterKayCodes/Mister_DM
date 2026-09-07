import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/mister_dm.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")

# Scheduler settings — flip DRY_RUN to False and set real delays for production
DRY_RUN = True
DEV_DELAY_MIN = 1
DEV_DELAY_MAX = 3

TELETHON_API_ID = os.getenv("TELETHON_API_ID", "12345")
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH", "dummy_hash")

# API Server settings
DM_API_PORT = int(os.getenv("DM_API_PORT", "8013"))
DM_API_KEY = os.getenv("DM_API_KEY")

if not DM_API_KEY:
    raise ValueError("DM_API_KEY is not set in the environment variables.")



