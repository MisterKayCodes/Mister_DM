import asyncio
import logging
from sqlalchemy import text
from data.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_phase10")

async def migrate():
    logger.info("Starting Phase 10 migration (adding assigned_session column to targets table)...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE targets ADD COLUMN assigned_session VARCHAR;"))
            logger.info("✅ Added assigned_session column to targets table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("ℹ️ assigned_session column already exists.")
            else:
                logger.error(f"❌ Error adding assigned_session column: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
