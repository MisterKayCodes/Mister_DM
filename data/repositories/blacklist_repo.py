# LAYER: Repository (Memory) — No commits, no business logic, session injected, returns raw ORM/primitives.
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from data.models.blacklist import Blacklist

async def add_to_blacklist(
    session: AsyncSession, 
    telegram_user_id: int | None, 
    username: str | None, 
    reason: str | None
) -> Blacklist:
    """Inserts a target into the blacklist."""
    entry = Blacklist(
        telegram_user_id=telegram_user_id,
        username=username,
        reason=reason
    )
    session.add(entry)
    return entry

async def remove_from_blacklist_by_username(session: AsyncSession, username: str) -> int:
    """Removes an entry by username."""
    result = await session.execute(
        delete(Blacklist).where(Blacklist.username == username)
    )
    return result.rowcount

async def remove_from_blacklist_by_id(session: AsyncSession, telegram_user_id: int) -> int:
    """Removes an entry by telegram ID."""
    result = await session.execute(
        delete(Blacklist).where(Blacklist.telegram_user_id == telegram_user_id)
    )
    return result.rowcount

async def get_all_blacklisted(session: AsyncSession) -> list[Blacklist]:
    """Returns all blacklisted entries."""
    result = await session.execute(select(Blacklist).order_by(Blacklist.created_at.desc()))
    return result.scalars().all()

async def is_blacklisted(
    session: AsyncSession, 
    telegram_user_id: int | None, 
    username: str | None
) -> bool:
    """Checks if a target is blacklisted by either ID or username."""
    conditions = []
    if telegram_user_id is not None:
        conditions.append(Blacklist.telegram_user_id == telegram_user_id)
    if username is not None:
        conditions.append(Blacklist.username == username)
        
    if not conditions:
        return False
        
    result = await session.execute(
        select(Blacklist).where(or_(*conditions))
    )
    return result.scalar_one_or_none() is not None
