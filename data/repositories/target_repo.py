import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from data.models.target import Target
from data.models.campaign import Campaign
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

async def get_next_pending_target(session: AsyncSession, campaign_id: int) -> Target | None:
    """Fetches the next target with status='pending' for the scheduler."""
    result = await session.execute(
        select(Target)
        .where(Target.campaign_id == campaign_id, Target.status == "pending")
        .limit(1)
    )
    return result.scalar_one_or_none()

#FIXED: Populate missing target metrics during state transitions.
# WHY: The scheduler needs to stamp exactly when a target was sent and log their permanent ID. 
# Without `sent_at` and `telegram_user_id`, we can never measure campaign velocity or detect their replies.
async def update_target_status(session: AsyncSession, target_id: int, new_status: str, telegram_user_id: int | None = None) -> None:
    """Updates a single target's status, tracking send time and their immutable Telegram user ID."""
    result = await session.execute(
        select(Target).where(Target.id == target_id)
    )
    target = result.scalar_one_or_none()
    if target:
        target.status = new_status
        if new_status == "sent":
            target.sent_at = func.now()
            if telegram_user_id:
                target.telegram_user_id = telegram_user_id
        await session.commit()

#FIXED: Bulk multi-campaign status updates for replies.
# WHY: If John is in Campaign A and Campaign B on the same account, loading both into Python to 
# check and save them is slow. A single bulk SQL update marks them both instantly in one round trip.
async def mark_targets_as_replied(session: AsyncSession, telegram_user_id: int, account_id: int) -> int:
    """
    Marks all 'sent' targets across all campaigns for a specific account as 'replied'.
    Matches securely on immutable telegram_user_id, not mutable username.
    Returns the number of rows updated.
    """
    subq = select(Campaign.id).where(Campaign.account_id == account_id).scalar_subquery()
    
    stmt = (
        update(Target)
        .where(Target.telegram_user_id == telegram_user_id)
        .where(Target.status == "sent")
        .where(Target.campaign_id.in_(subq))
        .values(status="replied", replied_at=func.now())
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount
