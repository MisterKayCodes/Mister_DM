from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from data.models.reporting.outreach_audit_log import OutreachAuditLog

class OutreachAuditRepo:
    @staticmethod
    async def record_attempt(
        session: AsyncSession,
        session_name: str,
        target_username: str = None,
        template_id: int = None,
        outcome: str = "sent",
        error_details: str = None
    ) -> OutreachAuditLog:
        """
        Records a dispatch attempt, calculating gap_minutes since previous attempt
        and daily_index for the session today.
        """
        now = datetime.utcnow()
        start_of_today = datetime(now.year, now.month, now.day)

        # 1. Query most recent log for session_name to calculate gap_minutes
        recent_stmt = (
            select(OutreachAuditLog)
            .where(OutreachAuditLog.session_name == session_name)
            .order_by(desc(OutreachAuditLog.created_at))
            .limit(1)
        )
        recent_res = await session.execute(recent_stmt)
        last_log = recent_res.scalar_one_or_none()

        gap_minutes = 0
        if last_log and last_log.created_at:
            delta = now - last_log.created_at
            gap_minutes = max(0, int(delta.total_seconds() / 60))

        # 2. Query count of logs for session_name today to calculate daily_index
        count_stmt = (
            select(func.count(OutreachAuditLog.id))
            .where(
                OutreachAuditLog.session_name == session_name,
                OutreachAuditLog.created_at >= start_of_today
            )
        )
        count_res = await session.execute(count_stmt)
        daily_count = count_res.scalar_one() or 0
        daily_index = daily_count + 1

        # 3. Create entry
        audit_entry = OutreachAuditLog(
            session_name=session_name,
            target_username=target_username,
            template_id=template_id,
            daily_index=daily_index,
            gap_minutes=gap_minutes,
            outcome=outcome,
            error_details=error_details,
            created_at=now
        )
        session.add(audit_entry)
        await session.commit()
        await session.refresh(audit_entry)
        return audit_entry

    @staticmethod
    async def get_24h_summary(session: AsyncSession) -> dict:
        """
        Calculates totals for last 24 hours: total_sent, healthy_count,
        flood_wait_count, peer_flood_count, banned_count, active_sessions_count.
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Total counts by outcome in last 24h
        outcome_stmt = (
            select(OutreachAuditLog.outcome, func.count(OutreachAuditLog.id))
            .where(OutreachAuditLog.created_at >= cutoff)
            .group_by(OutreachAuditLog.outcome)
        )
        outcome_res = await session.execute(outcome_stmt)
        outcome_counts = {row[0]: row[1] for row in outcome_res.all()}

        total_sent = sum(outcome_counts.values())
        healthy_count = outcome_counts.get("sent", 0)
        flood_wait_count = outcome_counts.get("flood_wait", 0)
        peer_flood_count = outcome_counts.get("peer_flood", 0)
        banned_count = outcome_counts.get("banned", 0)

        # Active distinct sessions in last 24h
        sessions_stmt = (
            select(func.count(func.distinct(OutreachAuditLog.session_name)))
            .where(OutreachAuditLog.created_at >= cutoff)
        )
        sess_res = await session.execute(sessions_stmt)
        active_sessions_count = sess_res.scalar_one() or 0

        healthy_rate = round((healthy_count / total_sent * 100), 1) if total_sent > 0 else 100.0

        return {
            "total_sent": total_sent,
            "healthy_count": healthy_count,
            "healthy_rate": healthy_rate,
            "flood_wait_count": flood_wait_count,
            "peer_flood_count": peer_flood_count,
            "banned_count": banned_count,
            "active_sessions_count": active_sessions_count
        }

    @staticmethod
    async def get_recent_logs(
        session: AsyncSession,
        limit: int = 5,
        session_name: str = None
    ) -> list[OutreachAuditLog]:
        """
        Returns list of recent OutreachAuditLog records ordered by created_at DESC.
        """
        query = select(OutreachAuditLog)
        if session_name:
            query = query.where(OutreachAuditLog.session_name == session_name)
        query = query.order_by(desc(OutreachAuditLog.created_at)).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_active_sessions_summary(session: AsyncSession, hours: int = 48) -> list[dict]:
        """
        Groups by session_name in the last N hours (default 48h), returning:
        session_name, total_dms, highest risk outcome, last_active.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        stmt = (
            select(
                OutreachAuditLog.session_name,
                func.count(OutreachAuditLog.id).label("total_dms"),
                func.max(OutreachAuditLog.created_at).label("last_active")
            )
            .where(OutreachAuditLog.created_at >= cutoff)
            .group_by(OutreachAuditLog.session_name)
            .order_by(desc("last_active"))
        )
        res = await session.execute(stmt)
        rows = res.all()

        results = []
        # Risk hierarchy: banned > peer_flood > flood_wait > error > sent
        risk_priority = {"banned": 4, "peer_flood": 3, "flood_wait": 2, "error": 1, "sent": 0}

        for row in rows:
            s_name = row.session_name
            total_dms = row.total_dms
            last_active = row.last_active

            # Find worst outcome for this session in the window
            worst_stmt = (
                select(OutreachAuditLog.outcome)
                .where(OutreachAuditLog.session_name == s_name, OutreachAuditLog.created_at >= cutoff)
            )
            worst_res = await session.execute(worst_stmt)
            outcomes = [r[0] for r in worst_res.all()]
            
            worst_outcome = "sent"
            if outcomes:
                worst_outcome = max(outcomes, key=lambda o: risk_priority.get(o, 0))

            results.append({
                "session_name": s_name,
                "total_dms": total_dms,
                "highest_risk": worst_outcome,
                "last_active": last_active
            })

        return results
