from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from data.models import Base
from config import DATABASE_URL
import os

# Ensure the storage directory exists if using SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split("///")[-1]
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Auto-migration check for SQLite session_name column
        try:
            res = await conn.execute(text("PRAGMA table_info(campaigns)"))
            columns = [row[1] for row in res.fetchall()]
            if "session_name" not in columns:
                await conn.execute(text("ALTER TABLE campaigns ADD COLUMN session_name TEXT"))
        except Exception:
            pass
