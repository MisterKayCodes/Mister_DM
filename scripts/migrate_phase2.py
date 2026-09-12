import asyncio
import sqlite3
import os
import sys

# Ensure we can import from the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.database import engine, Base
# Import all models so they register with Base
from data.models import *

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'mister_dm.db'))

async def migrate():
    print("Starting Phase 2 Database Migration...")
    
    # 1. Add new columns to existing 'targets' table safely
    if os.path.exists(DB_PATH):
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if targets table actually exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='targets';")
            if cursor.fetchone():
                print("Found 'targets' table. Applying ALTER TABLE...")
                
                cursor.execute("PRAGMA table_info(targets);")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Full list of legacy + new columns to ensure DB is whole
                updates = [
                    # Legacy missing columns (Safety net)
                    ("triage_status", "VARCHAR NOT NULL DEFAULT 'UNCLASSIFIED'"),
                    ("triage_raw_chat", "TEXT"),
                    ("profile_notes", "TEXT"),
                    ("profile_confidence", "INTEGER NOT NULL DEFAULT 0"),
                    ("source_group", "VARCHAR"),
                    ("handoff_status", "VARCHAR"),
                    ("handoff_attempts", "INTEGER NOT NULL DEFAULT 0"),
                    ("handoff_last_attempt", "DATETIME"),
                    
                    # Phase 2 Relational columns
                    ("trust_score", "INTEGER NOT NULL DEFAULT 0"),
                    ("timezone", "VARCHAR NOT NULL DEFAULT 'Unknown'"),
                    ("goal", "VARCHAR"),
                    ("mirror_profile_json", "TEXT"),
                    ("assigned_persona_id", "INTEGER REFERENCES personas(id)")
                ]
                
                for col_name, col_def in updates:
                    if col_name not in columns:
                        print(f"   [+] Adding column '{col_name}' to targets table...")
                        cursor.execute(f"ALTER TABLE targets ADD COLUMN {col_name} {col_def};")
                    else:
                        print(f"   [=] Column '{col_name}' already exists in targets. Skipping.")
                        
                conn.commit()
            else:
                print("Table 'targets' does not exist yet in the database file. Skipping ALTER TABLE.")
                
        except Exception as e:
            print(f"[!] Migration error during ALTER TABLE: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    else:
        print("No existing database found. It will be created fresh.")

    # 2. Create the brand new tables
    print("Creating new tables via SQLAlchemy Base.metadata.create_all()...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Phase 2 Database Migration Complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
