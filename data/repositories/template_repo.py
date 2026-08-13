from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.template import Template

async def add_template(session: AsyncSession, campaign_id: int, content: str) -> tuple[bool, str]:
    """Adds a new template to a campaign."""
    new_template = Template(
        campaign_id=campaign_id,
        content=content
    )
    session.add(new_template)
    try:
        await session.commit()
        return True, "Template added successfully."
    except Exception as e:
        await session.rollback()
        return False, f"Error adding template: {e}"

async def get_templates_by_campaign(session: AsyncSession, campaign_id: int) -> list[Template]:
    """Retrieves all templates for a specific campaign."""
    result = await session.execute(select(Template).where(Template.campaign_id == campaign_id))
    return list(result.scalars().all())

async def get_template_by_id(session: AsyncSession, template_id: int) -> Template | None:
    """Retrieves a template by its ID."""
    result = await session.execute(select(Template).where(Template.id == template_id))
    return result.scalar_one_or_none()

async def delete_template(session: AsyncSession, template_id: int) -> tuple[bool, str]:
    """Deletes a template by its ID. Returns (success, message)."""
    template = await get_template_by_id(session, template_id)
    if not template:
        return False, "Template not found."
        
    await session.delete(template)
    await session.commit()
    return True, "Template deleted."
