import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete
from sqlalchemy.exc import IntegrityError
from data.models.target import Target
from utils.string_utils import clean_username


async def add_targets_bulk(
    session: AsyncSession,
    campaign_id: int,
    raw_text: str
) -> dict:
    """
    Parses raw text (comma, space, or newline separated), sanitizes each username,
    and bulk-inserts into the database. Returns import statistics.

    We use IntegrityError catching instead of a pre-check SELECT + INSERT pattern.
    A pre-check SELECT would require two round trips per username and still has a
    race condition window. Catching the constraint violation is a single atomic
    operation and is correct even under concurrent load.
    """
    # Split on commas, newlines, and spaces in one pass
    raw_list = re.split(r'[\s,]+', raw_text)

    added = 0
    duplicates = 0
    invalid = 0

    for raw in raw_list:
        if not raw:
            continue

        username = clean_username(raw)
        if not username:
            invalid += 1
            continue

        try:
            session.add(Target(campaign_id=campaign_id, username=username))
            await session.flush()  # flush per-row so we can catch IntegrityError individually
            added += 1
        except IntegrityError:
            await session.rollback()
            duplicates += 1
        except Exception:
            await session.rollback()
            invalid += 1

    await session.commit()
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
