import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from data.database import AsyncSessionLocal
from data.repositories import campaign_repo, target_repo, template_repo
from utils.dto_builders import campaign_to_dto
from core.constants import VALID_CAMPAIGN_TRANSITIONS

logger = logging.getLogger(__name__)



class CampaignService:
    """
    Nerve layer for Campaigns. Controls transactions, validates business rules,
    returns consistent DTOs. Never leaks ORM objects upward.
    """

    # ─── CREATE ────────────────────────────────────────────────────────────────

    @staticmethod
    async def add_campaign(name: str, account_id: int, session: AsyncSession = None) -> tuple[bool, str]:
        async def _execute(sess: AsyncSession):
            name_clean = name.strip()
            if not name_clean:
                return False, "Campaign name cannot be empty."
            if len(name_clean) > 100:
                return False, "Campaign name cannot exceed 100 characters."

            # Duplicate check
            existing = await campaign_repo.get_campaign_by_name(sess, name_clean)
            if existing:
                return False, f"A campaign named '{name_clean}' already exists."

            await campaign_repo.insert_campaign(sess, name_clean, account_id)
            return True, "Campaign created successfully."

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    if result[0]:
                        await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    logger.error(f"Failed to add campaign: {e}")
                    return False, str(e)
        return await _execute(session)

    # ─── READ ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def get_all_campaigns(session: AsyncSession = None) -> list[dict]:
        async def _execute(sess: AsyncSession):
            campaigns = await campaign_repo.get_all_campaigns(sess)
            return [
                {
                    **campaign_to_dto(c),
                    "account_name": c.account.name if c.account else "Unknown",
                    "created_at_str": c.created_at.strftime('%Y-%m-%d') if c.created_at else "Unknown",
                }
                for c in campaigns
            ]

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_campaign_by_id(campaign_id: int, session: AsyncSession = None, load_templates: bool = False) -> dict | None:
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id, load_templates=load_templates)
            if not campaign:
                return None
            dto = campaign_to_dto(campaign)
            if load_templates:
                dto["templates"] = [{"id": t.id, "message": t.message} for t in campaign.templates]
            return dto

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_campaign_by_name(name: str, session: AsyncSession = None) -> dict | None:
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_name(sess, name)
            return campaign_to_dto(campaign) if campaign else None

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_campaign_summary(campaign_id: int, session: AsyncSession = None) -> dict | None:
        """
        Returns enriched campaign summary including is_ready_to_start.
        All counts derived in ONE session to guarantee consistency.
        """
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return None

            templates_count = await template_repo.get_template_count(sess, campaign_id)
            targets_count = await target_repo.get_target_count(sess, campaign_id)

            return {
                **campaign_to_dto(campaign),
                "templates_count": templates_count,
                "targets_count": targets_count,
                # Business meaning: ready only if it has both templates and targets
                "is_ready_to_start": templates_count > 0 and targets_count > 0,
            }

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    # ─── UPDATE ────────────────────────────────────────────────────────────────

    @staticmethod
    async def update_campaign_status(campaign_id: int, new_status: str, session: AsyncSession = None) -> tuple[bool, str]:
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return False, "Campaign not found."

            # Enforce valid state transitions
            allowed = VALID_CAMPAIGN_TRANSITIONS.get(campaign.status, set())
            if new_status not in allowed:
                return False, f"Cannot transition from '{campaign.status}' to '{new_status}'."

            await campaign_repo.update_campaign_status(sess, campaign_id, new_status)
            return True, f"Status updated to '{new_status}'."

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    if result[0]:
                        await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    return False, str(e)
        return await _execute(session)

    # ─── DELETE ────────────────────────────────────────────────────────────────

    @staticmethod
    async def delete_campaign(campaign_id: int, session: AsyncSession = None) -> tuple[bool, str]:
        """
        Returns (success, message). Handler is responsible for refreshing the list.
        No cross-session fetching after delete.
        """
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return False, "Campaign not found."
            if campaign.status == "running":
                return False, "Cannot delete a running campaign. Pause it first."

            rows = await campaign_repo.delete_campaign(sess, campaign_id)
            if rows > 0:
                return True, "Campaign deleted."
            return False, "Campaign not found."

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    if result[0]:
                        await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    return False, str(e)
        return await _execute(session)

    # ─── GUARDS ────────────────────────────────────────────────────────────────

    @staticmethod
    async def verify_campaign_modifiable(campaign_id: int, session: AsyncSession = None) -> tuple[bool, str, dict | None]:
        """Business rule: only draft campaigns may have targets or templates modified."""
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return False, "not_found", None
            dto = campaign_to_dto(campaign)
            if campaign.status != "draft":
                return False, campaign.status, dto
            return True, "draft", dto

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def verify_campaign_deletable(campaign_id: int, session: AsyncSession = None) -> tuple[bool, str]:
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return False, "not_found"
            if campaign.status != "draft":
                return False, campaign.status
            return True, "draft"

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    # ─── SYSTEM ────────────────────────────────────────────────────────────────

    @staticmethod
    async def recover_running_campaigns() -> int:
        """Called on bot startup to revert ghost 'running' campaigns to 'paused'."""
        async with AsyncSessionLocal() as session:
            try:
                count = await campaign_repo.recover_running_campaigns(session)
                await session.commit()
                logger.info(f"Startup recovery: reverted {count} running campaign(s) to paused.")
                return count
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to recover running campaigns: {e}")
                return 0
