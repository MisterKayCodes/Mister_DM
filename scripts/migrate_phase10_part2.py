import asyncio
import logging
from sqlalchemy import text
from data.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_phase10_part2")

async def migrate():
    logger.info("Starting Phase 10 Part 2 migration (adding timezone and active_hours to personas)...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE personas ADD COLUMN timezone VARCHAR DEFAULT 'UTC';"))
            logger.info("✅ Added timezone column to personas table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("ℹ️ timezone column already exists.")
            else:
                logger.error(f"❌ Error adding timezone column: {e}")
                
        try:
            await conn.execute(text("ALTER TABLE personas ADD COLUMN active_hours VARCHAR DEFAULT '08-22';"))
            logger.info("✅ Added active_hours column to personas table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("ℹ️ active_hours column already exists.")
            else:
                logger.error(f"❌ Error adding active_hours column: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
