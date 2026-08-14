from data.models.campaign import Campaign

def campaign_to_dto(campaign: Campaign) -> dict:
    """
    Single source of truth for the Campaign DTO shape.
    Used by CampaignService to ensure consistent return structure across all methods.
    """
    return {
        "id": campaign.id,
        "name": campaign.name,
        "account_id": campaign.account_id,
        "status": campaign.status,
        "created_at": campaign.created_at,
    }
