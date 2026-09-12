from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.relationship_message import RelationshipMessage

async def add_message(
    session: AsyncSession,
    chat_id: int,
    role: str,
    content: str
) -> RelationshipMessage:
    """Adds a single roleplay message to history and returns the created object."""
    msg = RelationshipMessage(
        chat_id=chat_id,
        role=role,
        content=content
    )
    session.add(msg)
    await session.flush()
    return msg

async def get_recent_messages(
    session: AsyncSession,
    chat_id: int,
    limit: int = 30
) -> list[RelationshipMessage]:
    """Fetches recent conversation history ordered chronologically (oldest to newest)."""
    stmt = (
        select(RelationshipMessage)
        .where(RelationshipMessage.chat_id == chat_id)
        .order_by(RelationshipMessage.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = list(result.scalars().all())
    messages.reverse()  # Reverse to restore chronological context for Groq
    return messages
