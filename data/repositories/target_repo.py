from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from data.models.target import Target

async def add_targets_bulk(
    session: AsyncSession,
    campaign_id: int,
    valid_usernames: list[str]
) -> int:
    """
    Bulk-inserts a list of pre-validated usernames into the database.
    Ignores duplicates using SQLite ON CONFLICT DO NOTHING.
    Returns the number of rows inserted.
    """
    if not valid_usernames:
        return 0

    insert_data_list = [{"campaign_id": campaign_id, "username": u} for u in valid_usernames]
    
    stmt = sqlite_insert(Target).values(insert_data_list).on_conflict_do_nothing(index_elements=['campaign_id', 'username'])
    result = await session.execute(stmt)
    return result.rowcount


async def get_targets_by_campaign(session: AsyncSession, campaign_id: int) -> list[Target]:
    """Fetches all targets for a campaign."""
    result = await session.execute(
        select(Target).where(Target.campaign_id == campaign_id)
    )
    return list(result.scalars().all())


async def get_target_count(session: AsyncSession, campaign_id: int) -> int:
    """Returns the total number of targets for a campaign."""
    result = await session.execute(
        select(func.count()).where(Target.campaign_id == campaign_id)
    )
    return result.scalar() or 0


async def clear_targets(session: AsyncSession, campaign_id: int) -> int:
    """Bulk-deletes all targets for a campaign. Returns the number of rows deleted."""
    result = await session.execute(
        delete(Target).where(Target.campaign_id == campaign_id)
    )
    return result.rowcount


async def get_next_pending_target(session: AsyncSession, campaign_id: int) -> Target | None:
    """Fetches the next target with status='pending' for the scheduler."""
    result = await session.execute(
        select(Target)
        .where(Target.campaign_id == campaign_id, Target.status == "pending")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_target(session: AsyncSession, target_id: int, update_data: dict) -> int:
    """
    Executes a single UPDATE statement for the given fields.
    Returns the number of rows affected.
    """
    if not update_data:
        return 0
        
    stmt = (
        update(Target)
        .where(Target.id == target_id)
        .values(**update_data)
    )
    result = await session.execute(stmt)
    return result.rowcount


async def mark_targets_as_replied(session: AsyncSession, telegram_user_id: int, campaign_ids: list[int]) -> int:
    """
    Marks targets as 'replied' if they match the telegram_user_id and belong to the specified campaigns.
    Returns the number of rows updated.
    """
    if not campaign_ids:
        return 0
        
    stmt = (
        update(Target)
        .where(Target.telegram_user_id == telegram_user_id)
        .where(Target.status == "sent")
        .where(Target.campaign_id.in_(campaign_ids))
        .values(status="replied", replied_at=func.now())
    )
    result = await session.execute(stmt)
    return result.rowcount


async def get_target_by_id(session: AsyncSession, target_id: int, load_pain_tags: bool = False) -> Target | None:
    """Fetches a single target by ID, optionally eager-loading pain tags."""
    stmt = select(Target).where(Target.id == target_id)
    
    if load_pain_tags:
        stmt = stmt.options(selectinload(Target.pain_tags))
        
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_target_by_username(session: AsyncSession, username: str, load_pain_tags: bool = False) -> Target | None:
    """Fetches a single target by exact username, optionally eager-loading pain tags."""
    stmt = select(Target).where(Target.username == username).limit(1)
    
    if load_pain_tags:
        stmt = stmt.options(selectinload(Target.pain_tags))
        
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_replied_targets(session: AsyncSession) -> list[Target]:
    """Fetches all targets that have replied across the entire system."""
    stmt = (
        select(Target)
        .where(Target.status == "replied")
        .order_by(Target.replied_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
