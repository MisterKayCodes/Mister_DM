from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from data.models.pain_tag import PainTag, target_pain_tags
from data.models.target import Target

async def get_all_pain_tags_with_counts(session: AsyncSession) -> list[dict]:
    """
    Returns a list of all pain tags and the count of targets assigned to them.
    We use a GROUP BY query to count in the DB, avoiding loading all targets into Python.
    """
    stmt = (
        select(PainTag, func.count(target_pain_tags.c.target_id).label("target_count"))
        .outerjoin(target_pain_tags, PainTag.id == target_pain_tags.c.pain_tag_id)
        .group_by(PainTag.id)
        .order_by(func.count(target_pain_tags.c.target_id).desc())
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": row.PainTag.id,
            "display_name": row.PainTag.display_name,
            "count": row.target_count
        }
        for row in rows
    ]

async def get_pain_tag_by_name(session: AsyncSession, name_normalized: str) -> PainTag | None:
    """Fetches a pain tag by its normalized name."""
    result = await session.execute(
        select(PainTag).where(PainTag.name_normalized == name_normalized)
    )
    return result.scalar_one_or_none()

async def insert_pain_tag(session: AsyncSession, name_normalized: str, display_name: str) -> PainTag:
    """
    Inserts a new pain tag.
    The caller must catch IntegrityError if the tag already exists.
    """
    new_tag = PainTag(name_normalized=name_normalized, display_name=display_name)
    session.add(new_tag)
    await session.flush() # Ensure it gets an ID without committing
    return new_tag

async def get_targets_for_pain_tag(session: AsyncSession, pain_tag_id: int) -> list[Target]:
    """Fetches all targets that have been assigned a specific pain tag."""
    stmt = (
        select(Target)
        .join(target_pain_tags, Target.id == target_pain_tags.c.target_id)
        .where(target_pain_tags.c.pain_tag_id == pain_tag_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def tag_target(session: AsyncSession, target_id: int, pain_tag_id: int) -> None:
    """
    Assigns a pain tag to a target using raw insert.
    The caller must catch IntegrityError if it was already tagged.
    """
    stmt = target_pain_tags.insert().values(target_id=target_id, pain_tag_id=pain_tag_id)
    await session.execute(stmt)
