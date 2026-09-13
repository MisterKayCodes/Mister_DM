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
    # TODO(BUG-2): rowcount on bulk ON CONFLICT DO NOTHING is not 100% consistent across
    # SQLAlchemy + aiosqlite driver versions. Some versions return the number of *attempted*
    # rows instead of *actually inserted* rows. The SQL logic is correct and data will never
    # be corrupted, but the returned count here may be inaccurate in edge cases.
    # Spot-check: insert 5 usernames where 2 already exist — confirm you get back 3, not 5.
    # Fix when needed: run a COUNT query before/after instead of relying on result.rowcount.
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
    """
    Fetches a single target by exact username, optionally eager-loading pain tags.

    BUG-1 FIX: The unique constraint is (campaign_id, username), meaning the same
    username CAN appear across multiple campaigns. This function has no campaign_id
    filter, so it could return a row from ANY campaign. We now enforce ORDER BY
    created_at DESC so the result is at least deterministic (most recently added row
    wins). Prefer get_target_by_campaign_and_username() wherever campaign_id is known.
    """
    stmt = select(Target).where(Target.username == username).order_by(Target.created_at.desc()).limit(1)

    if load_pain_tags:
        stmt = stmt.options(selectinload(Target.pain_tags))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_target_by_campaign_and_username(session: AsyncSession, campaign_id: int, username: str) -> Target | None:
    """Fetches a single target by campaign ID and username."""
    stmt = select(Target).where(Target.campaign_id == campaign_id, Target.username == username).limit(1)
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

async def get_targets_by_telegram_id_and_campaigns(session: AsyncSession, telegram_user_id: int, campaign_ids: list[int]) -> list[Target]:
    """Fetches all targets matching the telegram ID across the given campaigns."""
    if not campaign_ids:
        return []
    stmt = (
        select(Target)
        .where(Target.telegram_user_id == telegram_user_id)
        .where(Target.campaign_id.in_(campaign_ids))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ==========================================
# PHASE 3: Lead Intelligence Helper Methods
# ==========================================

async def update_triage(session: AsyncSession, target_id: int, triage_status: str, raw_chat: str | None = None) -> int:
    """Updates the triage verdict and raw chat snippet for a target."""
    stmt = (
        update(Target)
        .where(Target.id == target_id)
        .values(triage_status=triage_status, triage_raw_chat=raw_chat)
    )
    result = await session.execute(stmt)
    return result.rowcount


async def update_profile(session: AsyncSession, target_id: int, profile_notes: str | None, profile_confidence: int, source_group: str | None = None) -> int:
    """Updates the lead intelligence profile notes, confidence score, and source group."""
    update_data = {
        "profile_notes": profile_notes,
        "profile_confidence": profile_confidence
    }
    if source_group:
        update_data["source_group"] = source_group
        
    stmt = (
        update(Target)
        .where(Target.id == target_id)
        .values(**update_data)
    )
    result = await session.execute(stmt)
    return result.rowcount


async def get_targets_by_triage(session: AsyncSession, triage_status: str) -> list[Target]:
    """Fetches all targets matching a specific triage status (e.g. RELATIONAL or TRANSACTIONAL)."""
    stmt = (
        select(Target)
        .where(Target.triage_status == triage_status)
        .order_by(Target.id.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_failed_handoffs(session: AsyncSession) -> list[Target]:
    """Fetches targets where handoff to Mister AI failed."""
    stmt = (
        select(Target)
        .where(Target.handoff_status == "handoff_failed")
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_target_relational_data(
    session: AsyncSession,
    target_id: int,
    trust_score: int | None = None,
    timezone: str | None = None,
    goal: str | None = None,
    mirror_profile_json: str | None = None,
    mirror_confidence: int | None = None,
    assigned_persona_id: int | None = None
) -> int:
    """
    Updates relational engine fields on a target.

    TODO(BUG-3): Every param uses `None` as the signal to "don't update this column".
    This means there is no way to intentionally CLEAR/reset a field back to NULL via
    this function — passing None just silently skips the column instead of writing NULL.
    Example: you cannot wipe `mirror_profile_json` to force a fresh mirror analysis.
    Fix when needed: add a `clear_fields: list[str]` parameter and explicitly set those
    columns to None in update_data, e.g.:
        for field in (clear_fields or []):
            update_data[field] = None
    """
    update_data = {}
    if trust_score is not None:
        update_data["trust_score"] = trust_score
    if timezone is not None:
        update_data["timezone"] = timezone
    if goal is not None:
        update_data["goal"] = goal
    if mirror_profile_json is not None:
        update_data["mirror_profile_json"] = mirror_profile_json
    if mirror_confidence is not None:
        update_data["mirror_confidence"] = mirror_confidence
    if assigned_persona_id is not None:
        update_data["assigned_persona_id"] = assigned_persona_id

    if not update_data:
        return 0

    stmt = update(Target).where(Target.id == target_id).values(**update_data)
    result = await session.execute(stmt)
    return result.rowcount


async def set_target_needs_human(session: AsyncSession, target_id: int, needs_human: bool = True) -> int:
    """Updates the needs_human flag on a target."""
    stmt = update(Target).where(Target.id == target_id).values(needs_human=needs_human)
    result = await session.execute(stmt)
    return result.rowcount


async def get_targets_needing_human(session: AsyncSession) -> list[Target]:
    """Fetches all targets that currently have needs_human = True."""
    stmt = select(Target).where(Target.needs_human == True).order_by(Target.id.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


