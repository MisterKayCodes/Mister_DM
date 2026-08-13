import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from data.models.target import Target
from utils.string_utils import clean_username


# #FIXED: Implement Atomic Batch Insert Plugins & Expunge Looped Flushes
# Replaced row-by-row session.add() + flush() loop with a single high-performance batch insert.
# Protects the asyncio event loop thread from network freeze lockups and RAM exhaustion.
# Also safely computes clean delta deliveries by subtracting rowcount from valid unique list size.
async def add_targets_bulk(
    session: AsyncSession,
    campaign_id: int,
    raw_text: str
) -> dict:
    """
    Parses raw text (comma, space, or newline separated), sanitizes each username,
    and bulk-inserts into the database. Returns import statistics.
    """
    # Split on commas, newlines, and spaces in one pass
    raw_list = re.split(r'[\s,]+', raw_text)

    valid_usernames = set()
    invalid = 0

    for raw in raw_list:
        if not raw:
            continue
        username = clean_username(raw)
        if not username:
            invalid += 1
            continue
        valid_usernames.add(username)

    if not valid_usernames:
        return {"added": 0, "duplicates": 0, "invalid": invalid}

    insert_data_list = [{"campaign_id": campaign_id, "username": u} for u in valid_usernames]

    stmt = sqlite_insert(Target).values(insert_data_list).on_conflict_do_nothing(index_elements=['campaign_id', 'username'])
    result = await session.execute(stmt)
    await session.commit()

    added = result.rowcount
    duplicates = len(valid_usernames) - added

    return {"added": added, "duplicates": duplicates, "invalid": invalid}


async def get_targets_by_campaign(session: AsyncSession, campaign_id: int) -> list[Target]:
    """Fetches all targets for a campaign."""
    result = await session.execute(
        select(Target).where(Target.campaign_id == campaign_id)
    )
    return list(result.scalars().all())


async def get_target_count(session: AsyncSession, campaign_id: int) -> int:
    """
    Returns the total number of targets for a campaign using SELECT COUNT(*).

    We deliberately never store targets_count as a column on the Campaign model.
    A stored count becomes wrong the moment a delete or clear runs and the
    counter is not decremented. A derived count like this is always correct
    because it reads directly from the source of truth every single time.
    """
    result = await session.execute(
        select(func.count()).where(Target.campaign_id == campaign_id)
    )
    return result.scalar() or 0


async def clear_targets(session: AsyncSession, campaign_id: int) -> int:
    """
    Bulk-deletes all targets for a campaign. Returns the number of rows deleted.

    We use a single DELETE WHERE statement instead of loading each target and
    calling session.delete() in a loop. Row-by-row deletion makes N database
    round trips. A bulk DELETE makes exactly 1, regardless of how many targets exist.
    """
    result = await session.execute(
        delete(Target).where(Target.campaign_id == campaign_id)
    )
    await session.commit()
    return result.rowcount
