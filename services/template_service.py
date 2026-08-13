from data.database import AsyncSessionLocal
from data.repositories import template_repo


class TemplateService:
    """
    Coordinates business logic and database sessions for Templates.
    """

    @staticmethod
    async def add_template(campaign_id: int, content: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session:
            return await template_repo.add_template(session, campaign_id, content)

    # #FIXED: Compact Retrieval Into the Live Context
    # Handles dictionary conversion natively inside its active session block.
    # Returns purely decoupled python dict arrays.
    # Blocks DetachedInstanceError execution drops and totally isolates ORM entity access.
    @staticmethod
    async def get_templates_by_campaign(campaign_id: int) -> list[dict]:
        async with AsyncSessionLocal() as session:
            templates = await template_repo.get_templates_by_campaign(session, campaign_id)
            return [
                {
                    "id": t.id,
                    "campaign_id": t.campaign_id,
                    "content": t.content,
                    "created_at": t.created_at
                } for t in templates
            ]

    # #FIXED: Consolidate Single-Context Transaction Piles
    # The database validation check, deletion call, and the query fetching the fresh state list 
    # now occur sequentially within the EXACT SAME single session block window.
    # Passes properties out only as pure serialized list elements, blocking ORM leaks.
    @staticmethod
    async def delete_template(template_id: int) -> tuple[bool, str, list[dict]]:
        """
        Deletes a template and returns the fresh list of remaining templates atomically.
        The campaign_id is fetched from the template record before deletion so the 
        Mouth never has to manage the refetch itself.
        """
        async with AsyncSessionLocal() as session:
            # Fetch the template first so we know which campaign to refresh
            template = await template_repo.get_template_by_id(session, template_id)
            campaign_id = template.campaign_id if template else None
            
            deleted, msg = await template_repo.delete_template(session, template_id)
            
            if campaign_id:
                templates = await template_repo.get_templates_by_campaign(session, campaign_id)
                fresh_templates = [
                    {
                        "id": t.id,
                        "campaign_id": t.campaign_id,
                        "content": t.content,
                        "created_at": t.created_at
                    } for t in templates
                ]
            else:
                fresh_templates = []
                
            return deleted, msg, fresh_templates
