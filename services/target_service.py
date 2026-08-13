from data.database import AsyncSessionLocal
from data.repositories import target_repo
import asyncio
import io


class TargetService:
    """
    Coordinates business logic and database sessions for Targets.
    """

    @staticmethod
    async def add_targets_bulk(campaign_id: int, raw_text: str) -> dict:
        async with AsyncSessionLocal() as session:
            return await target_repo.add_targets_bulk(session, campaign_id, raw_text)

    # #FIXED: Preserve Blocking Performance Protection
    # Retained the background execution routing strategy inside process_file_bytes
    # to prevent massive text allocation and decoding from freezing the event loop thread.
    @staticmethod
    async def process_file_bytes(campaign_id: int, file_bytes: io.BytesIO) -> dict:
        """
        Decodes the byte stream in a background thread so the main asyncio event loop
        isn't blocked when processing massive 15MB txt files with 100k lines.
        """
        def _decode():
            return file_bytes.read().decode("utf-8", errors="ignore")
            
        raw_text = await asyncio.to_thread(_decode)
        return await TargetService.add_targets_bulk(campaign_id, raw_text)

    # #FIXED: Encapsulate Data Transformations Within the Transaction Context
    # Consolidates and handles dictionary conversion internally inside the execution window block.
    # Returns an array of standard, decoupled Python dictionaries containing explicitly mapped properties.
    # Blocks DetachedInstanceError execution drops or backend schema leaks.
    @staticmethod
    async def get_targets_by_campaign(campaign_id: int) -> list[dict]:
        async with AsyncSessionLocal() as session:
            targets = await target_repo.get_targets_by_campaign(session, campaign_id)
            return [
                {
                    "id": t.id,
                    "campaign_id": t.campaign_id,
                    "username": t.username,
                    "status": t.status,
                    "created_at": t.created_at
                } for t in targets
            ]

    @staticmethod
    async def get_target_count(campaign_id: int) -> int:
        async with AsyncSessionLocal() as session:
            return await target_repo.get_target_count(session, campaign_id)

    @staticmethod
    async def clear_targets(campaign_id: int) -> int:
        async with AsyncSessionLocal() as session:
            return await target_repo.clear_targets(session, campaign_id)

    @staticmethod
    async def get_next_pending_target(campaign_id: int) -> dict | None:
        async with AsyncSessionLocal() as session:
            target = await target_repo.get_next_pending_target(session, campaign_id)
            if not target:
                return None
            return {
                "id": target.id,
                "campaign_id": target.campaign_id,
                "username": target.username,
                "status": target.status
            }

    @staticmethod
    async def update_target_status(target_id: int, new_status: str, telegram_user_id: int | None = None) -> None:
        async with AsyncSessionLocal() as session:
            await target_repo.update_target_status(session, target_id, new_status, telegram_user_id)

    @staticmethod
    async def mark_targets_as_replied(telegram_user_id: int, account_id: int) -> int:
        async with AsyncSessionLocal() as session:
            return await target_repo.mark_targets_as_replied(session, telegram_user_id, account_id)
