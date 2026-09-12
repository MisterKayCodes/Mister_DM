from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.ai_intent import AIIntent

async def log_intent(
    session: AsyncSession,
    message_id: int,
    intent_text: str,
    confidence_score: int,
    needs_human: bool = False
) -> AIIntent:
    """Logs the AI's internal reasoning and confidence for a generated message."""
    intent = AIIntent(
        message_id=message_id,
        intent_text=intent_text,
        confidence_score=confidence_score,
        needs_human=needs_human
    )
    session.add(intent)
    await session.flush()
    return intent

async def get_intent_by_message_id(session: AsyncSession, message_id: int) -> AIIntent | None:
    """Fetches logged intent associated with a specific message ID."""
    stmt = select(AIIntent).where(AIIntent.message_id == message_id).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
