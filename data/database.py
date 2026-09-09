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
        
        # 1. Auto-migration check for campaigns table (session_name column)
        try:
            res = await conn.execute(text("PRAGMA table_info(campaigns)"))
            campaign_cols = [row[1] for row in res.fetchall()]
            if "session_name" not in campaign_cols:
                await conn.execute(text("ALTER TABLE campaigns ADD COLUMN session_name TEXT"))
        except Exception:
            pass

        # 2. Auto-migration check for targets table (Phase 3 columns)
        try:
            res = await conn.execute(text("PRAGMA table_info(targets)"))
            target_cols = [row[1] for row in res.fetchall()]
            
            migrations = [
                ("triage_status", "ALTER TABLE targets ADD COLUMN triage_status TEXT DEFAULT 'UNCLASSIFIED'"),
                ("triage_raw_chat", "ALTER TABLE targets ADD COLUMN triage_raw_chat TEXT"),
                ("profile_notes", "ALTER TABLE targets ADD COLUMN profile_notes TEXT"),
                ("profile_confidence", "ALTER TABLE targets ADD COLUMN profile_confidence INTEGER DEFAULT 0"),
                ("source_group", "ALTER TABLE targets ADD COLUMN source_group TEXT"),
                ("handoff_status", "ALTER TABLE targets ADD COLUMN handoff_status TEXT"),
                ("handoff_attempts", "ALTER TABLE targets ADD COLUMN handoff_attempts INTEGER DEFAULT 0"),
                ("handoff_last_attempt", "ALTER TABLE targets ADD COLUMN handoff_last_attempt DATETIME"),
            ]
            
            for col_name, sql_stmt in migrations:
                if col_name not in target_cols:
                    await conn.execute(text(sql_stmt))
        except Exception:
            pass

        # 3. Auto-migration check for messages table (template_id column for analytics)
        try:
            res = await conn.execute(text("PRAGMA table_info(messages)"))
            msg_cols = [row[1] for row in res.fetchall()]
            if "template_id" not in msg_cols:
                await conn.execute(text("ALTER TABLE messages ADD COLUMN template_id INTEGER"))
        except Exception:
            pass
