from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from data.models.target import Target
from data.models.message import MessageLog
from data.models.campaign import Campaign


async def get_campaign_target_counts(session: AsyncSession, campaign_id: int) -> dict:
    """Returns target status counts for a campaign via GROUP BY — no Python loops."""
    result = await session.execute(
        select(Target.status, func.count(Target.id).label("count"))
        .where(Target.campaign_id == campaign_id)
        .group_by(Target.status)
    )
    rows = result.all()
    counts = {row.status: row.count for row in rows}
    return {
        "total":   sum(counts.values()),
        "pending": counts.get("pending", 0),
        "sent":    counts.get("sent", 0),
        "replied": counts.get("replied", 0),
        "failed":  counts.get("failed", 0),
    }


async def get_campaign_message_counts(session: AsyncSession, campaign_id: int) -> dict:
    """Returns message direction counts for a campaign via GROUP BY."""
    result = await session.execute(
        select(MessageLog.direction, func.count(MessageLog.id).label("count"))
        .where(MessageLog.campaign_id == campaign_id)
        .group_by(MessageLog.direction)
    )
    rows = result.all()
    counts = {row.direction: row.count for row in rows}
    return {
        "outbound": counts.get("OUTBOUND", 0),
        "inbound":  counts.get("INBOUND", 0),
    }


async def get_campaign_last_activity(session: AsyncSession, campaign_id: int):
    """Returns the most recent message timestamp for a campaign."""
    result = await session.execute(
        select(func.max(MessageLog.timestamp))
        .where(MessageLog.campaign_id == campaign_id)
    )
    return result.scalar_one_or_none()


async def get_global_campaign_counts(session: AsyncSession) -> dict:
    """Returns campaign counts grouped by status via GROUP BY."""
    result = await session.execute(
        select(Campaign.status, func.count(Campaign.id).label("count"))
        .group_by(Campaign.status)
    )
    rows = result.all()
    counts = {row.status: row.count for row in rows}
    return {
        "total":     sum(counts.values()),
        "draft":     counts.get("draft", 0),
        "running":   counts.get("running", 0),
        "paused":    counts.get("paused", 0),
        "completed": counts.get("completed", 0),
        "stopped":   counts.get("stopped", 0),
    }


async def get_global_target_counts(session: AsyncSession) -> dict:
    """Returns system-wide target status counts via GROUP BY."""
    result = await session.execute(
        select(Target.status, func.count(Target.id).label("count"))
        .group_by(Target.status)
    )
    rows = result.all()
    counts = {row.status: row.count for row in rows}
    return {
        "total":   sum(counts.values()),
        "sent":    counts.get("sent", 0),
        "replied": counts.get("replied", 0),
        "failed":  counts.get("failed", 0),
    }


async def get_global_message_count(session: AsyncSession) -> int:
    """Returns total messages logged across the entire system."""
    result = await session.execute(select(func.count(MessageLog.id)))
    return result.scalar_one() or 0


async def get_global_stats(session: AsyncSession) -> dict:
    """Returns aggregated global statistics for the system."""
    campaigns = await get_global_campaign_counts(session)
    targets = await get_global_target_counts(session)
    messages = await get_global_message_count(session)
    reply_rate = (targets["replied"] / targets["sent"] * 100) if targets["sent"] > 0 else 0.0
    failure_rate = (targets["failed"] / targets["total"] * 100) if targets["total"] > 0 else 0.0
    return {
        "campaigns": campaigns,
        "targets": targets,
        "total_messages": messages,
        "reply_rate_percent": round(reply_rate, 2),
        "failure_rate_percent": round(failure_rate, 2)
    }


async def get_template_performance_stats(session: AsyncSession) -> list[dict]:
    """
    Returns reply rate performance metrics for each opening template.
    Joins MessageLog (OUTBOUND) with Target to measure total sent vs total replied.
    """
    stmt = (
        select(
            MessageLog.template_id,
            func.count(MessageLog.id).label("total_sent"),
            func.count(func.nullif(Target.status != "replied", True)).label("total_replied")
        )
        .join(Target, MessageLog.target_id == Target.id)
        .where(MessageLog.direction == "OUTBOUND")
        .where(MessageLog.template_id.isnot(None))
        .group_by(MessageLog.template_id)
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    stats = []
    for row in rows:
        sent = row.total_sent or 0
        replied = row.total_replied or 0
        rate = round((replied / sent * 100), 2) if sent > 0 else 0.0
        stats.append({
            "template_id": row.template_id,
            "total_sent": sent,
            "total_replied": replied,
            "reply_rate_percent": rate
        })
    return stats
