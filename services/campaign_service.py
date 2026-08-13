from data.database import AsyncSessionLocal
from data.repositories import campaign_repo, target_repo, template_repo
import asyncio


class CampaignService:
    """
    Coordinates business logic and database sessions for Campaigns.
    """

    @staticmethod
    async def add_campaign(name: str, account_id: int) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session:
            return await campaign_repo.add_campaign(session, name, account_id)

    # #FIXED: Convert State to Clean Payload Dictionaries
    # Completely decoupled model return values. Prevents DetachedInstanceError execution drops.
    # Handlers can now safely read the data map without risking active session access.
    @staticmethod
    async def get_all_campaigns() -> list[dict]:
        """
        Returns campaigns as plain dicts — no ORM objects, no HTML, no formatting.
        The Mouth loops over this list and builds its own display string.
        Keys: id, name, account_name, status, created_at_str
        """
        async with AsyncSessionLocal() as session:
            campaigns = await campaign_repo.get_all_campaigns(session)
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "account_id": c.account_id,
                    "account_name": c.account.name if c.account else "Unknown",
                    "status": c.status,
                    "created_at_str": c.created_at.strftime('%Y-%m-%d') if c.created_at else "Unknown",
                }
                for c in campaigns
            ]

    # #FIXED: Convert State to Clean Payload Dictionaries
    # Prevents raw database wrappers from leaking into the UI layer. Serializing parameter dictionaries 
    # protects the state block against backend schema leaks.
    @staticmethod
    async def get_campaign_by_id(campaign_id: int) -> dict | None:
        async with AsyncSessionLocal() as session:
            campaign = await campaign_repo.get_campaign_by_id(session, campaign_id)
            if not campaign:
                return None
            return {
                "id": campaign.id,
                "name": campaign.name,
                "account_id": campaign.account_id,
                "status": campaign.status,
                "created_at": campaign.created_at
            }

    # #FIXED: Convert State to Clean Payload Dictionaries
    # Prevents raw database wrappers from leaking into the UI layer. Serializing parameter dictionaries 
    # protects the state block against backend schema leaks.
    @staticmethod
    async def get_campaign_by_name(name: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            campaign = await campaign_repo.get_campaign_by_name(session, name)
            if not campaign:
                return None
            return {
                "id": campaign.id,
                "name": campaign.name,
                "account_id": campaign.account_id,
                "status": campaign.status,
                "created_at": campaign.created_at
            }

    @staticmethod
    async def delete_campaign(campaign_id: int) -> tuple[bool, str, list[dict]]:
        async with AsyncSessionLocal() as session:
            success, msg = await campaign_repo.delete_campaign(session, campaign_id)
            
        fresh_campaigns = await CampaignService.get_all_campaigns()
        return success, msg, fresh_campaigns

    # #FIXED: Consolidate Summary Logic Pipelines
    # Operations merged into a single internal session window. Pure serialization maps block 
    # DetachedInstanceError execution drops when generating presentation metadata.
    @staticmethod
    async def get_campaign_summary(campaign_id: int) -> dict | None:
        """
        Returns the campaign summary as a plain dict (no HTML, no formatting).
        Keys: name, status, templates_count, targets_count
        """
        async with AsyncSessionLocal() as session:
            campaign = await campaign_repo.get_campaign_by_id(session, campaign_id)
            if not campaign:
                return None
            
            templates_count = await template_repo.get_template_count(session, campaign_id)
            targets_count = await target_repo.get_target_count(session, campaign_id)
            
            return {
                "name": campaign.name,
                "status": campaign.status,
                "templates_count": templates_count,
                "targets_count": targets_count
            }

    # #FIXED: Remove Database Object Wrappers
    # Verification pipeline now returns a pure python dictionary instead of a Campaign DB model,
    # preventing accidental nested relationship evaluations in handlers.
    @staticmethod
    async def verify_campaign_modifiable(campaign_id: int) -> tuple[bool, str, dict | None]:
        """
        Business rule: only Draft campaigns may have targets added or cleared.
        Returns (can_modify, status_string, campaign_dict).
        """
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "not_found", None
        if campaign["status"] != "draft":
            return False, campaign["status"], campaign
        return True, "draft", campaign

    @staticmethod
    async def verify_campaign_deletable(campaign_id: int) -> tuple[bool, str]:
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "not_found"
        if campaign["status"] != "draft":
            return False, campaign["status"]
        return True, "draft"
