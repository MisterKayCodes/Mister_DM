from data.database import AsyncSessionLocal
from data.repositories import settings_repo

class SettingsService:
    """
    Coordinates business logic for system runtime settings:
    - approval_mode ('true' | 'false')
    - daily_dm_cap ('2', etc.)
    - cooldown_hours ('4', etc.)
    """

    @staticmethod
    async def is_approval_mode() -> bool:
        async with AsyncSessionLocal() as session:
            val = await settings_repo.get_setting(session, "approval_mode")
            return val.lower() in ("true", "1", "yes")

    @staticmethod
    async def toggle_approval_mode() -> bool:
        """Toggles approval mode between true and false. Returns new state."""
        current = await SettingsService.is_approval_mode()
        new_val = "false" if current else "true"
        async with AsyncSessionLocal() as session:
            await settings_repo.set_setting(session, "approval_mode", new_val, "Require human approval before sending DMs")
        return not current

    @staticmethod
    async def get_daily_dm_cap() -> int:
        async with AsyncSessionLocal() as session:
            val = await settings_repo.get_setting(session, "daily_dm_cap")
            try:
                return int(val)
            except (ValueError, TypeError):
                return 2

    @staticmethod
    async def set_daily_dm_cap(cap: int) -> tuple[bool, str]:
        """Sets the daily DM cap. Returns (success, warning_msg)."""
        if cap <= 0:
            return False, "Daily limit must be at least 1."
        
        warning = ""
        if cap > 2:
            warning = f"⚠️ Note: Setting daily cap to {cap} DMs per session exceeds the recommended default (2). It will run, but monitor for Telegram rate limits."
        
        async with AsyncSessionLocal() as session:
            await settings_repo.set_setting(session, "daily_dm_cap", str(cap), "Maximum cold DMs per session per day")
        return True, warning

    @staticmethod
    async def get_safety_summary() -> dict:
        async with AsyncSessionLocal() as session:
            raw = await settings_repo.get_all_settings(session)
            return {
                "approval_mode": raw.get("approval_mode", "true").lower() in ("true", "1", "yes"),
                "daily_dm_cap": int(raw.get("daily_dm_cap", 2)),
                "cooldown_hours": int(raw.get("cooldown_hours", 4))
            }
