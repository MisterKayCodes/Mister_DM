import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/mister_dm.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")
