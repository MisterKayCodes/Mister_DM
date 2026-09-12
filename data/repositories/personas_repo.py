from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from data.models.persona import Persona

async def get_persona(session: AsyncSession, persona_id: int) -> Persona | None:
    """Fetches a persona by ID."""
    stmt = select(Persona).where(Persona.id == persona_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_persona_by_name(session: AsyncSession, name: str) -> Persona | None:
    """Fetches a persona by name."""
    stmt = select(Persona).where(Persona.name == name).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_all_personas(session: AsyncSession) -> list[Persona]:
    """Fetches all personas ordered by ID."""
    stmt = select(Persona).order_by(Persona.id.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def create_persona(session: AsyncSession, **kwargs) -> Persona:
    """Creates a new persona record."""
    persona = Persona(**kwargs)
    session.add(persona)
    await session.flush()
    return persona
