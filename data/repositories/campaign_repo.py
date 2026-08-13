from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
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

# #FIXED: Optimize Over-Eager Memory Loading
# Removed .options(selectinload(Campaign.templates)). The index list handler only needs 
# core properties. Pulling down the massive array of child templates here introduces severe 
# memory thrashing. Templates are kept scoped strictly inside single-entity fetches.
async def get_all_campaigns(session: AsyncSession) -> list[Campaign]:
    """Retrieves all campaigns, loading the associated account."""
    result = await session.execute(
        select(Campaign).options(selectinload(Campaign.account))
    )
    return list(result.scalars().all())

async def get_campaign_by_id(session: AsyncSession, campaign_id: int) -> Campaign | None:
    """Retrieves a campaign by its ID, eagerly loading its templates."""
    result = await session.execute(
        select(Campaign).options(selectinload(Campaign.templates)).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()

async def get_campaign_by_name(session: AsyncSession, name: str) -> Campaign | None:
    """Retrieves a campaign by its exact name."""
    result = await session.execute(
        select(Campaign).where(Campaign.name == name)
    )
    return result.scalar_one_or_none()

# #FIXED: Transition to Single-Trip Atomic Deletion
# Refactored `delete_campaign` to use bulk SQL deletion `delete(Campaign).where(...)`.
# Eliminates loading the entire campaign ORM model into Python RAM before deletion.
# Also excised regulatory status guards — the repository is a silent vault and executes 
# unconditionally. The service layer already guards the state boundary.
async def delete_campaign(session: AsyncSession, campaign_id: int) -> tuple[bool, str]:
    """Deletes a campaign by its ID unconditionally. Returns (success, message)."""
    result = await session.execute(
        delete(Campaign).where(Campaign.id == campaign_id)
    )
    if result.rowcount > 0:
        await session.commit()
        return True, "Deleted."
    return False, "Campaign not found."

async def update_campaign_status(session: AsyncSession, campaign_id: int, new_status: str) -> None:
    """Updates the status of a specific campaign."""
    campaign = await get_campaign_by_id(session, campaign_id)
    if campaign:
        campaign.status = new_status
        await session.commit()

async def recover_running_campaigns(session: AsyncSession) -> None:
    """Finds all 'running' campaigns and sets them to 'paused' on bot startup."""
    result = await session.execute(
        select(Campaign).where(Campaign.status == "running")
    )
    campaigns = result.scalars().all()
    for campaign in campaigns:
        campaign.status = "paused"
    if campaigns:
        await session.commit()
