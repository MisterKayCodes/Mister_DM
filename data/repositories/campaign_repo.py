from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.orm import selectinload
from data.models.campaign import Campaign

# Repo is dumb: no commits, no rollbacks, no business logic.

async def insert_campaign(session: AsyncSession, name: str, account_id: int) -> Campaign:
    """Inserts a new campaign. Caller must commit."""
    campaign = Campaign(name=name, account_id=account_id, status="draft")
    session.add(campaign)
    await session.flush()  # Get ID without committing
    return campaign

async def get_all_campaigns(session: AsyncSession) -> list[Campaign]:
    """Retrieves all campaigns with their associated account."""
    result = await session.execute(
        select(Campaign).options(selectinload(Campaign.account))
    )
    return list(result.scalars().all())

async def get_campaign_by_id(session: AsyncSession, campaign_id: int, load_templates: bool = False) -> Campaign | None:
    """Retrieves a campaign by ID. Optionally loads templates (expensive, default off)."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    if load_templates:
        stmt = stmt.options(selectinload(Campaign.templates))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_campaign_by_name(session: AsyncSession, name: str) -> Campaign | None:
    result = await session.execute(select(Campaign).where(Campaign.name == name))
    return result.scalar_one_or_none()

async def get_campaigns_by_account(session: AsyncSession, account_id: int) -> list[Campaign]:
    """Fetches all campaigns belonging to a specific account."""
    result = await session.execute(
        select(Campaign).where(Campaign.account_id == account_id)
    )
    return list(result.scalars().all())

async def delete_campaign(session: AsyncSession, campaign_id: int) -> int:
    """Deletes a campaign. Returns the number of rows deleted. Caller must commit."""
    result = await session.execute(
        delete(Campaign).where(Campaign.id == campaign_id)
    )
    return result.rowcount

async def update_campaign_status(session: AsyncSession, campaign_id: int, new_status: str) -> int:
    """Updates a campaign's status. Caller must commit. Returns rows affected."""
    result = await session.execute(
        update(Campaign).where(Campaign.id == campaign_id).values(status=new_status)
    )
    return result.rowcount

async def recover_running_campaigns(session: AsyncSession) -> int:
    """Finds all 'running' campaigns and sets them to 'paused'. Caller must commit."""
    result = await session.execute(
        update(Campaign).where(Campaign.status == "running").values(status="paused")
    )
    return result.rowcount
