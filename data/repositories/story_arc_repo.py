import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from data.models.story_arc import StoryArc
from data.models.arc_media import ArcMedia

logger = logging.getLogger(__name__)

async def create_story_arc(
    session: AsyncSession,
    persona_id: int,
    chapter_number: int,
    delay_days: int,
    theme_text: str
) -> StoryArc:
    arc = StoryArc(
        persona_id=persona_id,
        chapter_number=chapter_number,
        delay_days=delay_days,
        theme_text=theme_text
    )
    session.add(arc)
    await session.flush()
    return arc

async def get_arcs_for_persona(session: AsyncSession, persona_id: int) -> List[StoryArc]:
    stmt = (
        select(StoryArc)
        .where(StoryArc.persona_id == persona_id)
        .order_by(StoryArc.chapter_number.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def get_arc_by_chapter(session: AsyncSession, persona_id: int, chapter_number: int) -> Optional[StoryArc]:
    stmt = (
        select(StoryArc)
        .where(StoryArc.persona_id == persona_id)
        .where(StoryArc.chapter_number == chapter_number)
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def add_arc_media(
    session: AsyncSession,
    arc_id: int,
    telegram_file_id: str,
    media_type: str = "photo"
) -> ArcMedia:
    media = ArcMedia(
        arc_id=arc_id,
        telegram_file_id=telegram_file_id,
        media_type=media_type
    )
    session.add(media)
    await session.flush()
    return media

async def get_chapter_media(session: AsyncSession, arc_id: int) -> List[ArcMedia]:
    stmt = select(ArcMedia).where(ArcMedia.arc_id == arc_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())
