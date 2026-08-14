# LAYER: Service (Nerves) — Controls session, computes ratios, returns plain dicts (DTOs). No UI, no raw ORM.
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from data.database import AsyncSessionLocal
from data.repositories import stats_repo

logger = logging.getLogger(__name__)

# Reply rate industry standard: replied / sent (not replied / total).
# Pending targets haven't been contacted — including them deflates the rate unfairly.
def _reply_rate(replied: int, sent: int) -> float:
    return round((replied / sent) * 100, 1) if sent > 0 else 0.0

# Failure rate: failed / (sent + failed) — how many contact attempts bounced.
def _failure_rate(failed: int, sent: int) -> float:
    attempted = sent + failed
    return round((failed / attempted) * 100, 1) if attempted > 0 else 0.0


class StatsService:
    """Read-only analytics layer. Returns clean DTOs — no mutation, no side effects."""

    @staticmethod
    async def get_campaign_stats(campaign_id: int, session: AsyncSession = None) -> dict | None:
        """
        Returns a full stats DTO for a single campaign.
        reply_rate = replied / sent (industry standard).
        """
        async def _execute(sess: AsyncSession):
            targets  = await stats_repo.get_campaign_target_counts(sess, campaign_id)
            messages = await stats_repo.get_campaign_message_counts(sess, campaign_id)
            last_activity = await stats_repo.get_campaign_last_activity(sess, campaign_id)

            sent    = targets["sent"]
            replied = targets["replied"]
            failed  = targets["failed"]

            return {
                "targets":      targets,
                "messages":     messages,
                "reply_rate":   _reply_rate(replied, sent),
                "failure_rate": _failure_rate(failed, sent),
                "last_activity": (
                    last_activity.strftime("%Y-%m-%d %H:%M") if last_activity else "No activity yet"
                ),
            }

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_global_stats(session: AsyncSession = None) -> dict:
        """Returns system-wide stats DTO across all campaigns and targets."""
        async def _execute(sess: AsyncSession):
            campaigns = await stats_repo.get_global_campaign_counts(sess)
            targets   = await stats_repo.get_global_target_counts(sess)
            total_msgs = await stats_repo.get_global_message_count(sess)

            sent    = targets["sent"]
            replied = targets["replied"]
            failed  = targets["failed"]

            return {
                "campaigns":    campaigns,
                "targets":      targets,
                "total_messages": total_msgs,
                "reply_rate":   _reply_rate(replied, sent),
                "failure_rate": _failure_rate(failed, sent),
            }

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)
