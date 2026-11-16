import logging
from data.database import AsyncSessionLocal
from data.repositories.reporting.outreach_audit_repo import OutreachAuditRepo

logger = logging.getLogger(__name__)

class TelemetryService:
    @staticmethod
    async def record_dispatch(
        session_name: str,
        target_username: str = None,
        template_id: int = None,
        outcome: str = "sent",
        error_details: str = None
    ):
        """
        Safely records an outreach attempt with telemetry metadata.
        Never raises exceptions so caller operations (like scheduler) will not fail.
        """
        if not session_name:
            session_name = "unknown_session"

        try:
            async with AsyncSessionLocal() as session:
                entry = await OutreachAuditRepo.record_attempt(
                    session=session,
                    session_name=session_name,
                    target_username=target_username,
                    template_id=template_id,
                    outcome=outcome,
                    error_details=error_details
                )
                logger.info(
                    f"[TELEMETRY] Recorded dispatch session={session_name} target=@{target_username} "
                    f"outcome={outcome} daily_index={entry.daily_index} gap={entry.gap_minutes}m"
                )
                return entry
        except Exception as e:
            logger.error(f"[TELEMETRY] Failed to record dispatch telemetry: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_dashboard_summary() -> dict:
        """
        Fetches 24h metrics, pattern alerts, and recent 5 audit logs.
        """
        try:
            async with AsyncSessionLocal() as session:
                summary_24h = await OutreachAuditRepo.get_24h_summary(session)
                recent_logs = await OutreachAuditRepo.get_recent_logs(session, limit=5)
                active_sessions = await OutreachAuditRepo.get_active_sessions_summary(session, hours=48)

                # Pattern detection logic
                alerts = []
                if summary_24h.get("flood_wait_count", 0) > 0:
                    alerts.append(f"⚠️ <b>FloodWait Detected:</b> {summary_24h['flood_wait_count']} occurrences in last 24h. Consider raising gap delays.")
                if summary_24h.get("peer_flood_count", 0) > 0:
                    alerts.append(f"🚨 <b>PeerFlood Alert:</b> {summary_24h['peer_flood_count']} occurrences. Target sessions may be restricted from messaging non-contacts.")
                if summary_24h.get("banned_count", 0) > 0:
                    alerts.append(f"🛑 <b>Account Ban Alert:</b> {summary_24h['banned_count']} sessions encountered termination/ban.")

                # Check for low gap warnings across recent logs
                low_gap_logs = [log for log in recent_logs if log.daily_index > 1 and log.gap_minutes < 15]
                if low_gap_logs:
                    alerts.append("⚡ <b>Rapid Dispatch Warning:</b> Messages sent with &lt;15m gap detected.")

                return {
                    "summary": summary_24h,
                    "recent_logs": recent_logs,
                    "active_sessions": active_sessions,
                    "alerts": alerts
                }
        except Exception as e:
            logger.error(f"[TELEMETRY] Failed to get dashboard summary: {e}", exc_info=True)
            return {
                "summary": {
                    "total_sent": 0,
                    "healthy_count": 0,
                    "healthy_rate": 100.0,
                    "flood_wait_count": 0,
                    "peer_flood_count": 0,
                    "banned_count": 0,
                    "active_sessions_count": 0
                },
                "recent_logs": [],
                "active_sessions": [],
                "alerts": [f"⚠️ Error loading telemetry data: {e}"]
            }

    @staticmethod
    async def get_session_history(session_name: str, limit: int = 10) -> list:
        """
        Returns recent logs for a specific session.
        """
        try:
            async with AsyncSessionLocal() as session:
                return await OutreachAuditRepo.get_recent_logs(session, limit=limit, session_name=session_name)
        except Exception as e:
            logger.error(f"[TELEMETRY] Failed to get session history for '{session_name}': {e}", exc_info=True)
            return []
