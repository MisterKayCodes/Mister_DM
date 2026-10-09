from data.database import AsyncSessionLocal
from data.repositories import account_repo

class AccountService:
    """
    Coordinates business logic and database sessions for Accounts.
    The Mouth (handlers) calls this service instead of touching the DB directly.
    """

    @staticmethod
    async def add_account(name: str, session_string: str, delay_min: int, delay_max: int, daily_limit: int = 40) -> tuple[bool, str]:
        # #FIXED: Session lifecycle moved to the Service layer (Nerves).
        # WHAT WOULD HAVE HAPPENED: Handlers opening their own sessions violates the
        # architectural rule that the bot (Mouth) should not manage database state.
        async with AsyncSessionLocal() as session:
            return await account_repo.add_account(session, name, session_string, delay_min, delay_max, daily_limit)

    # #FIXED: Convert State to Clean Payload Dictionaries
    # By mapping SQLAlchemy models into plain dictionaries before they leave the Service layer, 
    # we prevent the Mouth (handlers) from suffering DetachedInstanceError execution drops. 
    # It completely blocks schema logic leakage since handlers no longer hold active database rows.
    @staticmethod
    async def get_all_accounts() -> list[dict]:
        async with AsyncSessionLocal() as session:
            accounts = await account_repo.get_all_accounts(session)
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "session_string": a.session_string,
                    "delay_min": a.delay_min,
                    "delay_max": a.delay_max,
                    "daily_limit": a.daily_limit or 40,
                    "messages_sent_today": a.messages_sent_today or 0,
                    "status": "active" if a.is_active else "inactive"
                } for a in accounts
            ]

    @staticmethod
    async def ensure_simulator_account(session_name: str) -> dict | None:
        """
        Ensures a Simulator-managed session exists as an Account record in Mister_DM database.
        Returns serialized Account payload dict.
        """
        async with AsyncSessionLocal() as session:
            existing = await account_repo.get_account_by_name(session, session_name)
            if existing:
                return {
                    "id": existing.id,
                    "name": existing.name,
                    "session_string": existing.session_string,
                    "delay_min": existing.delay_min,
                    "delay_max": existing.delay_max,
                    "daily_limit": existing.daily_limit or 40,
                    "messages_sent_today": existing.messages_sent_today or 0,
                    "status": "active" if existing.is_active else "inactive"
                }

            # Automatically register Simulator session in local database
            success, msg = await account_repo.add_account(
                session=session,
                name=session_name,
                session_string="SIMULATOR_MANAGED",
                delay_min=1,
                delay_max=3,
                daily_limit=40
            )
            if success:
                await session.commit()
                created = await account_repo.get_account_by_name(session, session_name)
                if created:
                    return {
                        "id": created.id,
                        "name": created.name,
                        "session_string": created.session_string,
                        "delay_min": created.delay_min,
                        "delay_max": created.delay_max,
                        "daily_limit": created.daily_limit or 40,
                        "messages_sent_today": created.messages_sent_today or 0,
                        "status": "active" if created.is_active else "inactive"
                    }
            return None

    # #FIXED: Convert State to Clean Payload Dictionaries
    # By mapping SQLAlchemy models into plain dictionaries before they leave the Service layer, 
    # we prevent the Mouth (handlers) from suffering DetachedInstanceError execution drops. 
    # It completely blocks schema logic leakage since handlers no longer hold active database rows.
    @staticmethod
    async def get_account_by_id(account_id: int) -> dict | None:
        async with AsyncSessionLocal() as session:
            account = await account_repo.get_account_by_id(session, account_id)
            if not account:
                return None
            return {
                "id": account.id,
                "name": account.name,
                "session_string": account.session_string,
                "delay_min": account.delay_min,
                "delay_max": account.delay_max,
                "daily_limit": account.daily_limit or 40,
                "messages_sent_today": account.messages_sent_today or 0,
                "status": "active" if account.is_active else "inactive"
            }

    # #FIXED: Convert State to Clean Payload Dictionaries
    # By mapping SQLAlchemy models into plain dictionaries before they leave the Service layer, 
    # we prevent the Mouth (handlers) from suffering DetachedInstanceError execution drops. 
    # It completely blocks schema logic leakage since handlers no longer hold active database rows.
    @staticmethod
    async def get_account_by_name(name: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            account = await account_repo.get_account_by_name(session, name)
            if not account:
                return None
            return {
                "id": account.id,
                "name": account.name,
                "session_string": account.session_string,
                "delay_min": account.delay_min,
                "delay_max": account.delay_max,
                "daily_limit": account.daily_limit or 40,
                "messages_sent_today": account.messages_sent_today or 0,
                "status": "active" if account.is_active else "inactive"
            }

    # #FIXED: Convert State to Clean Payload Dictionaries
    # By mapping SQLAlchemy models into plain dictionaries before they leave the Service layer, 
    # we prevent the Mouth (handlers) from suffering DetachedInstanceError execution drops. 
    # It completely blocks schema logic leakage since handlers no longer hold active database rows.
    @staticmethod
    async def delete_account(account_id: int) -> tuple[bool, str, list[dict]]:
        async with AsyncSessionLocal() as session:
            success, msg = await account_repo.delete_account(session, account_id)
            accounts = await account_repo.get_all_accounts(session)
            fresh_accounts = [
                {
                    "id": a.id,
                    "name": a.name,
                    "session_string": a.session_string,
                    "delay_min": a.delay_min,
                    "delay_max": a.delay_max,
                    "daily_limit": a.daily_limit or 40,
                    "messages_sent_today": a.messages_sent_today or 0,
                    "status": "active" if a.is_active else "inactive"
                } for a in accounts
            ]
            return success, msg, fresh_accounts

    @staticmethod
    async def reset_all_daily_counters_if_needed() -> None:
        """Called at startup to reset any account whose last_reset_date is before today."""
        async with AsyncSessionLocal() as session:
            accounts = await account_repo.get_all_accounts(session)
            for account in accounts:
                await account_repo.reset_daily_counter_if_needed(session, account.id)
            await session.commit()
