from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.intel_entry import IntelEntry

HIGH_PRIORITY_CATEGORIES = {"fears", "desires", "relationships", "finances"}

# TODO (Phase 12+, deferred): Replace recency/priority cap with AI-assisted
# summarization/compaction of accumulated intel once conversations run
# long-term (6+ months). Goal: compress older facts into a dense summary
# instead of dropping them, so nothing important is lost as intel_list
# grows. Needs: periodic background job + a cheap LLM call + logic for
# when to trigger a compaction pass. Not needed at current campaign scale.
async def get_intel_for_target(session: AsyncSession, target_id: int, standard_cap: int = 20) -> list[IntelEntry]:
    """
    Fetches intelligence entries for a target with priority-based retention.
    High-priority categories (fears, desires, relationships, finances) are NEVER truncated.
    Standard categories (hobbies, career, misc) are capped to standard_cap entries (most recent first).
    """
    stmt = select(IntelEntry).where(IntelEntry.target_id == target_id).order_by(IntelEntry.id.desc())
    result = await session.execute(stmt)
    all_entries = list(result.scalars().all())

    if not all_entries:
        return []

    # 1. Partition entries into High-Priority vs Standard
    high_prio = [e for e in all_entries if (e.category or "").lower() in HIGH_PRIORITY_CATEGORIES]
    standard = [e for e in all_entries if (e.category or "").lower() not in HIGH_PRIORITY_CATEGORIES]

    # 2. Retain ALL High-Priority items (never dropped), plus up to standard_cap Standard items
    selected = list(high_prio) # Uncapped retain
    selected.extend(standard[:standard_cap]) # Most recent standard items up to cap

    # 3. Sort chronologically by ID for natural system prompt ordering
    selected.sort(key=lambda x: x.id)
    return selected

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
