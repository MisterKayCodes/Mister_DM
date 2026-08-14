# LAYER: Repository — no commits, no rollbacks, no business logic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from data.models.message import MessageLog

async def insert_message(
    session: AsyncSession,
    account_id: int,
    target_id: int,
    direction: str,
    message_type: str,
    text: str | None = None,
    telegram_message_id: int | None = None,
    campaign_id: int | None = None,
) -> MessageLog:
    """Inserts a new message log. Caller must commit."""
    msg = MessageLog(
        account_id=account_id,
        target_id=target_id,
        direction=direction,
        message_type=message_type,
        text=text,
        telegram_message_id=telegram_message_id,
        campaign_id=campaign_id
    )
    session.add(msg)
    await session.flush()
    return msg

async def get_messages_for_target(session: AsyncSession, target_id: int) -> list[MessageLog]:
    """Retrieves all messages for a specific target, ordered chronologically."""
    result = await session.execute(
        select(MessageLog)
        .where(MessageLog.target_id == target_id)
        .order_by(asc(MessageLog.timestamp))
    )
    return list(result.scalars().all())

async def get_messages_for_campaign(session: AsyncSession, campaign_id: int) -> list[MessageLog]:
    """Retrieves all messages for a specific campaign, ordered chronologically."""
    result = await session.execute(
        select(MessageLog)
        .where(MessageLog.campaign_id == campaign_id)
        .order_by(asc(MessageLog.timestamp))
    )
    return list(result.scalars().all())
