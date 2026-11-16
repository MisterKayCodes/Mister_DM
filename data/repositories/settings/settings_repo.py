from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data.models.settings.system_setting import SystemSetting

DEFAULTS = {
    "approval_mode": "true",
    "daily_dm_cap": "2",
    "cooldown_hours": "4"
}

async def get_setting(session: AsyncSession, key: str) -> str:
    """Retrieves a setting value, falling back to default if not yet in DB."""
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is not None:
        return setting.value
    return DEFAULTS.get(key, "")

async def set_setting(session: AsyncSession, key: str, value: str, description: str | None = None) -> SystemSetting:
    """Inserts or updates a setting key-value pair."""
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SystemSetting(key=key, value=str(value), description=description)
        session.add(setting)
    else:
        setting.value = str(value)
        if description:
            setting.description = description
    await session.commit()
    return setting

async def get_all_settings(session: AsyncSession) -> dict[str, str]:
    """Retrieves all settings as a key-value dictionary with defaults merged."""
    result = await session.execute(select(SystemSetting))
    settings = result.scalars().all()
    merged = dict(DEFAULTS)
    for s in settings:
        merged[s.key] = s.value
    return merged
