from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from data.models.campaign import Campaign

async def add_campaign(session: AsyncSession, name: str, account_id: int) -> tuple[bool, str]:
    """Adds a new campaign. Returns (success, message)."""
    new_campaign = Campaign(
        name=name,
        account_id=account_id,
        status="draft"
    )
    session.add(new_campaign)
    try:
        await session.commit()
        return True, "Campaign created successfully."
    except IntegrityError:
        await session.rollback()
        return False, f"Campaign with name '{name}' already exists."
    except Exception as e:
        await session.rollback()
        return False, f"Error creating campaign: {e}"

async def get_all_campaigns(session: AsyncSession) -> list[Campaign]:
    """Retrieves all campaigns, loading the associated account and templates."""
    result = await session.execute(
        select(Campaign)
        .options(selectinload(Campaign.account), selectinload(Campaign.templates))
    )
    return list(result.scalars().all())

async def get_campaign_by_id(session: AsyncSession, campaign_id: int) -> Campaign | None:
    """Retrieves a campaign by its ID, loading the associated account."""
    result = await session.execute(
        select(Campaign).options(selectinload(Campaign.account)).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()

async def delete_campaign(session: AsyncSession, campaign_id: int) -> tuple[bool, str]:
    """Deletes a campaign by its ID ONLY if status is draft. Returns (success, message)."""
    campaign = await get_campaign_by_id(session, campaign_id)
    if not campaign:
        return False, "Campaign not found."
        
    if campaign.status != "draft":
        return False, f"Cannot delete a campaign with status '{campaign.status}'. Only drafts can be deleted."
        
    await session.delete(campaign)
    await session.commit()
    return True, "Deleted."
