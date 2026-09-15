import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, text
from data.models.draft_reply import DraftReply

async def create_draft(
    session: AsyncSession,
    target_id: int,
    chat_id: int,
    draft_text: str,
    intent_text: str | None = None,
    confidence_score: int = 75,
    session_name: str | None = None,
    pending_arc_chapter: int | None = None,
    pending_media_json: str | None = None
) -> DraftReply:
    """Creates a new pending reply draft for operator approval."""
    draft = DraftReply(
        target_id=target_id,
        chat_id=chat_id,
        draft_text=draft_text,
        intent_text=intent_text,
        confidence_score=confidence_score,
        session_name=session_name,
        pending_arc_chapter=pending_arc_chapter,
        pending_media_json=pending_media_json,
        status="pending"
    )
    session.add(draft)
    await session.flush()
    return draft

async def get_draft_by_id(session: AsyncSession, draft_id: int) -> Optional[DraftReply]:
    """Fetches a draft by its primary key ID."""
    stmt = select(DraftReply).where(DraftReply.id == draft_id)
    res = await session.execute(stmt)
    return res.scalars().first()

async def get_pending_draft_for_target(session: AsyncSession, target_id: int) -> Optional[DraftReply]:
    """Fetches any existing active pending draft for a specific target."""
    stmt = (
        select(DraftReply)
        .where(DraftReply.target_id == target_id, DraftReply.status == "pending")
        .order_by(DraftReply.id.desc())
    )
    res = await session.execute(stmt)
    return res.scalars().first()

async def mark_draft_superseded(session: AsyncSession, draft_id: int) -> bool:
    """Marks an older pending draft as superseded by a newer inbound message."""
    stmt = (
        update(DraftReply)
        .where(DraftReply.id == draft_id, DraftReply.status == "pending")
        .values(status="superseded")
    )
    res = await session.execute(stmt)
    await session.flush()
    return getattr(res, "rowcount", 0) > 0

async def atomic_claim_draft(session: AsyncSession, draft_id: int, admin_name: str = "Operator") -> bool:
    """
    Atomically claims a pending draft for processing.
    Returns True if successfully claimed (prevents race conditions across multiple admins).
    Returns False if already claimed, approved, or rejected.
    """
    stmt = (
        update(DraftReply)
        .where(DraftReply.id == draft_id, DraftReply.status == "pending")
        .values(status="processing", processed_by=admin_name)
    )
    res = await session.execute(stmt)
    await session.flush()
    return getattr(res, "rowcount", 0) > 0

async def mark_draft_completed(session: AsyncSession, draft_id: int, status: str, admin_name: str = "Operator") -> bool:
    """Marks a draft as final status ('approved' or 'rejected')."""
    stmt = (
        update(DraftReply)
        .where(DraftReply.id == draft_id)
        .values(status=status, processed_by=admin_name)
    )
    res = await session.execute(stmt)
    await session.flush()
    return getattr(res, "rowcount", 0) > 0

async def update_war_room_message_id(session: AsyncSession, draft_id: int, war_room_message_id: int) -> bool:
    """Stores the Telegram Message ID of the War Room approval card for UI updates."""
    stmt = (
        update(DraftReply)
        .where(DraftReply.id == draft_id)
        .values(war_room_message_id=war_room_message_id)
    )
    res = await session.execute(stmt)
    await session.flush()
    return getattr(res, "rowcount", 0) > 0
