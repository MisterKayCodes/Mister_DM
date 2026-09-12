from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.intel_entry import IntelEntry

async def get_intel_for_target(session: AsyncSession, target_id: int) -> list[IntelEntry]:
    """Fetches all intelligence entries gathered for a specific target."""
    stmt = select(IntelEntry).where(IntelEntry.target_id == target_id).order_by(IntelEntry.id.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def add_intel_entry(
    session: AsyncSession,
    target_id: int,
    category: str,
    key: str,
    value: str,
    source: str = "chat"
) -> IntelEntry:
    """Adds a single intel entry for a target."""
    entry = IntelEntry(
        target_id=target_id,
        category=category,
        key=key,
        value=value,
        source=source
    )
    session.add(entry)
    await session.flush()
    return entry

async def bulk_add_intel(session: AsyncSession, target_id: int, entries: list[dict], source: str = "chat") -> int:
    """Bulk-inserts intel entries from parsed Groq JSON array. Returns inserted count."""
    if not entries:
        return 0
    added_count = 0
    for item in entries:
        category = item.get("category", "misc")
        key = item.get("key")
        value = item.get("value")
        if key and value:
            entry = IntelEntry(
                target_id=target_id,
                category=category,
                key=key,
                value=value,
                source=source
            )
            session.add(entry)
            added_count += 1
    await session.flush()
    return added_count
