# LAYER: Service (Nerves) — Owns session, controls business rules (ID fallback), returns dicts.
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from data.database import AsyncSessionLocal
from data.repositories import blacklist_repo

logger = logging.getLogger(__name__)

class BlacklistService:
    @staticmethod
    async def blacklist_target(username: str | None, telegram_user_id: int | None, reason: str = "MANUAL") -> tuple[bool, str]:
        if not username and not telegram_user_id:
            return False, "Must provide username or telegram ID."
            
        async with AsyncSessionLocal() as session:
            try:
                # Avoid duplicates
                if await blacklist_repo.is_blacklisted(session, telegram_user_id, username):
                    return False, "Target is already blacklisted."
                    
                await blacklist_repo.add_to_blacklist(session, telegram_user_id, username, reason)
                await session.commit()
                return True, "Added to blacklist."
            except IntegrityError:
                await session.rollback()
                return False, "Target is already blacklisted."
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to blacklist target: {e}")
                return False, "Database error."

    @staticmethod
    async def unblacklist_target(username: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session:
            try:
                count = await blacklist_repo.remove_from_blacklist_by_username(session, username)
                if count == 0:
                    return False, "Target not found in blacklist."
                await session.commit()
                return True, "Removed from blacklist."
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to unblacklist target: {e}")
                return False, "Database error."

    @staticmethod
    async def check_target_allowed(username: str | None, telegram_user_id: int | None) -> bool:
        """Returns True if the target is NOT blacklisted (allowed). Returns False if blacklisted."""
        if not username and not telegram_user_id:
            return True
            
        async with AsyncSessionLocal() as session:
            try:
                is_banned = await blacklist_repo.is_blacklisted(session, telegram_user_id, username)
                return not is_banned
            except Exception as e:
                logger.error(f"Failed to check blacklist for {username}/{telegram_user_id}: {e}")
                # Fail-open if DB crashes? Or fail-closed? Safer to fail-closed (return False),
                # but it could pause the whole bot for a glitch. We'll fail-open for now.
                return True

    @staticmethod
    async def get_all_blacklisted() -> list[dict]:
        async with AsyncSessionLocal() as session:
            entries = await blacklist_repo.get_all_blacklisted(session)
            return [
                {
                    "id": e.id,
                    "telegram_user_id": e.telegram_user_id,
                    "username": e.username,
                    "reason": e.reason,
                    "created_at_str": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else "Unknown"
                }
                for e in entries
            ]
