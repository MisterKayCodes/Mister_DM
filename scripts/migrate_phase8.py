import asyncio
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mister_dm.db")

async def migrate_phase8():
    db_file = os.path.abspath(DB_PATH)
    print(f"Migrating database at: {db_file}")

    async with aiosqlite.connect(db_file) as db:
        # Check existing columns in targets table
        async with db.execute("PRAGMA table_info(targets)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]

        if "mirror_confidence" not in columns:
            print("Adding column 'mirror_confidence' to 'targets' table...")
            await db.execute("ALTER TABLE targets ADD COLUMN mirror_confidence INTEGER DEFAULT 0")

        if "needs_human" not in columns:
            print("Adding column 'needs_human' to 'targets' table...")
            await db.execute("ALTER TABLE targets ADD COLUMN needs_human BOOLEAN DEFAULT 0")

        await db.commit()
        print("[SUCCESS] Phase 8 Database Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate_phase8())
