import asyncio
import logging
from sqlalchemy import text
from data.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_phase11_part1")

async def migrate():
    logger.info("Starting Phase 11 Part 1 migration (story_arcs, arc_media, target.arc_chapter)...")
    async with engine.begin() as conn:
        # 1. Create story_arcs table
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS story_arcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    delay_days INTEGER NOT NULL DEFAULT 0,
                    theme_text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(persona_id) REFERENCES personas(id)
                );
            """))
            logger.info("✅ Created story_arcs table.")
        except Exception as e:
            logger.error(f"❌ Error creating story_arcs table: {e}")

        # 2. Create arc_media table
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS arc_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arc_id INTEGER NOT NULL,
                    telegram_file_id VARCHAR NOT NULL,
                    media_type VARCHAR NOT NULL DEFAULT 'photo',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(arc_id) REFERENCES story_arcs(id) ON DELETE CASCADE
                );
            """))
            logger.info("✅ Created arc_media table.")
        except Exception as e:
            logger.error(f"❌ Error creating arc_media table: {e}")

        # 3. Add arc_chapter to targets table
        try:
            await conn.execute(text("ALTER TABLE targets ADD COLUMN arc_chapter INTEGER DEFAULT 0;"))
            logger.info("✅ Added arc_chapter column to targets table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("ℹ️ arc_chapter column already exists.")
            else:
                logger.error(f"❌ Error adding arc_chapter column: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
