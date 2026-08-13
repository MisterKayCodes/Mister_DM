from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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

# #FIXED: Removed get_session() asynchronous generator.
# WHAT WAS ADJUSTED: Completely expunged the `get_session()` generator function from this module.
# PREVENTED FAILURE: Aiogram does not natively tear down request-scoped dependencies. Using loose 
# generators here invites view components to spawn hanging connection streams, eventually leading 
# to catastrophic Connection Pool Exhaustion under live load. Services are now strictly forced to 
# handle session allocations explicitly using atomic context manager blocks via AsyncSessionLocal.
