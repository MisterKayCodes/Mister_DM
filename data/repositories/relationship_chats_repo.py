from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from data.models.relationship_chat import RelationshipChat

async def get_chat(session: AsyncSession, target_id: int, load_persona: bool = False) -> RelationshipChat | None:
    """Fetches the active relationship chat for a target."""
    stmt = select(RelationshipChat).where(RelationshipChat.target_id == target_id).limit(1)
    if load_persona:
        stmt = stmt.options(selectinload(RelationshipChat.persona))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_chat(
    session: AsyncSession,
    target_id: int,
    persona_id: int,
    goal: str | None = None
) -> RelationshipChat:
    """Creates a new relationship chat tracking row for a target."""
    chat = RelationshipChat(
        target_id=target_id,
        persona_id=persona_id,
        current_week=1,
        goal=goal
    )
    session.add(chat)
    await session.flush()
    return chat

async def get_or_create_chat(
    session: AsyncSession,
    target_id: int,
    persona_id: int,
    goal: str | None = None
) -> RelationshipChat:
    """Fetches existing relationship chat or creates a new one."""
    chat = await get_chat(session, target_id)
    if not chat:
        chat = await create_chat(session, target_id, persona_id, goal=goal)
    return chat

async def update_chat_state(
    session: AsyncSession,
    chat_id: int,
    current_week: int | None = None,
    goal: str | None = None
) -> int:
    """Updates current week pacing or goal for a relationship chat."""
    update_data = {}
    if current_week is not None:
        update_data["current_week"] = current_week
    if goal is not None:
        update_data["goal"] = goal
    if not update_data:
        return 0
    stmt = update(RelationshipChat).where(RelationshipChat.id == chat_id).values(**update_data)
    result = await session.execute(stmt)
    return result.rowcount
