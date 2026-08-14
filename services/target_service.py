import io
import re
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from data.repositories import campaign_repo
from utils.string_utils import clean_username
import logging

logger = logging.getLogger(__name__)

class TargetService:
    """
    Coordinates business logic for Targets.
    Acts as the 'Nerves', insulating the Mouth from the Memory.
    Controls transactions, validates data, and returns unified DTOs.
    """

    @staticmethod
    async def add_targets_bulk(campaign_id: int, raw_text: str, session: AsyncSession = None) -> dict:
        """
        Validates campaign existence, parses raw text, cleans usernames,
        and delegates insertion to the repository.
        """
        async def _execute(sess: AsyncSession):
            # Validate campaign exists
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                raise ValueError("Campaign does not exist.")

            # Parse and clean usernames
            raw_list = re.split(r'[\s,]+', raw_text)
            valid_usernames = set()
            invalid = 0

            for raw in raw_list:
                if not raw:
                    continue
                username = clean_username(raw)
                if not username:
                    invalid += 1
                    continue
                valid_usernames.add(username)

            added = await target_repo.add_targets_bulk(sess, campaign_id, list(valid_usernames))
            duplicates = len(valid_usernames) - added

            logger.info(f"Imported targets for campaign {campaign_id}: {added} added, {duplicates} dups, {invalid} invalid.")
            
            return {
                "success": True,
                "data": {
                    "added": added,
                    "duplicates": duplicates,
                    "invalid": invalid
                }
            }

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    logger.error(f"Failed to add targets: {e}")
                    return {"success": False, "message": str(e)}
        return await _execute(session)

    @staticmethod
    async def process_file_bytes(campaign_id: int, file_bytes: io.BytesIO, session: AsyncSession = None) -> dict:
        """Decodes massive text files in a background thread."""
        def _decode():
            return file_bytes.read().decode("utf-8", errors="ignore")
            
        raw_text = await asyncio.to_thread(_decode)
        return await TargetService.add_targets_bulk(campaign_id, raw_text, session=session)

    @staticmethod
    async def get_targets_by_campaign(campaign_id: int, session: AsyncSession = None) -> list[dict]:
        async def _execute(sess: AsyncSession):
            targets = await target_repo.get_targets_by_campaign(sess, campaign_id)
            return [
                {
                    "id": t.id,
                    "campaign_id": t.campaign_id,
                    "username": t.username,
                    "status": t.status,
                    "created_at": t.created_at
                } for t in targets
            ]

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_target_count(campaign_id: int, session: AsyncSession = None) -> int:
        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await target_repo.get_target_count(new_sess, campaign_id)
        return await target_repo.get_target_count(session, campaign_id)

    @staticmethod
    async def clear_targets(campaign_id: int, session: AsyncSession = None) -> dict:
        async def _execute(sess: AsyncSession):
            campaign = await campaign_repo.get_campaign_by_id(sess, campaign_id)
            if not campaign:
                return {"success": False, "message": "Campaign not found."}
            if campaign.status == "running":
                return {"success": False, "message": "Cannot clear targets while campaign is running."}
                
            count = await target_repo.clear_targets(sess, campaign_id)
            return {"success": True, "data": {"deleted": count}}

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    if result["success"]:
                        await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    return {"success": False, "message": str(e)}
        return await _execute(session)

    @staticmethod
    async def get_next_pending_target(campaign_id: int, session: AsyncSession = None) -> dict | None:
        async def _execute(sess: AsyncSession):
            target = await target_repo.get_next_pending_target(sess, campaign_id)
            if not target:
                return None
            return {
                "id": target.id,
                "campaign_id": target.campaign_id,
                "username": target.username,
                "status": target.status
            }
            
        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def update_target_status(target_id: int, new_status: str, telegram_user_id: int | None = None, session: AsyncSession = None) -> dict:
        async def _execute(sess: AsyncSession):
            update_data = {"status": new_status}
            if new_status == "sent":
                from sqlalchemy import func
                update_data["sent_at"] = func.now()
                if telegram_user_id:
                    update_data["telegram_user_id"] = telegram_user_id
                    
            rows = await target_repo.update_target(sess, target_id, update_data)
            return {"success": rows > 0}

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    res = await _execute(new_sess)
                    await new_sess.commit()
                    return res
                except Exception as e:
                    await new_sess.rollback()
                    return {"success": False, "message": str(e)}
        return await _execute(session)

    @staticmethod
    async def mark_targets_as_replied(telegram_user_id: int, account_id: int, session: AsyncSession = None) -> dict:
        async def _execute(sess: AsyncSession):
            # Resolve campaigns for this account
            campaigns = await campaign_repo.get_campaigns_by_account(sess, account_id)
            if not campaigns:
                return {"success": True, "data": {"updated": 0}}
                
            campaign_ids = [c.id for c in campaigns]
            updated = await target_repo.mark_targets_as_replied(sess, telegram_user_id, campaign_ids)
            return {"success": True, "data": {"updated": updated}}

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    res = await _execute(new_sess)
                    await new_sess.commit()
                    return res
                except Exception as e:
                    await new_sess.rollback()
                    return {"success": False, "message": str(e)}
        return await _execute(session)

    @staticmethod
    async def get_target_by_id(target_id: int, load_pain_tags: bool = False, session: AsyncSession = None) -> dict | None:
        async def _execute(sess: AsyncSession):
            target = await target_repo.get_target_by_id(sess, target_id, load_pain_tags=load_pain_tags)
            if not target:
                return None
            dto = {
                "id": target.id,
                "username": target.username,
                "status": target.status,
                "note": target.note
            }
            if load_pain_tags:
                dto["pain_tags"] = [{"id": pt.id, "display_name": pt.display_name} for pt in target.pain_tags]
            return dto

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_target_by_username(username: str, load_pain_tags: bool = False, session: AsyncSession = None) -> dict | None:
        async def _execute(sess: AsyncSession):
            target = await target_repo.get_target_by_username(sess, username, load_pain_tags=load_pain_tags)
            if not target:
                return None
            dto = {
                "id": target.id,
                "username": target.username,
                "status": target.status,
                "note": target.note
            }
            if load_pain_tags:
                dto["pain_tags"] = [{"id": pt.id, "display_name": pt.display_name} for pt in target.pain_tags]
            return dto

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def get_replied_targets(session: AsyncSession = None) -> list[dict]:
        async def _execute(sess: AsyncSession):
            targets = await target_repo.get_replied_targets(sess)
            return [
                {
                    "id": t.id,
                    "username": t.username,
                    "status": t.status,
                    "note": t.note
                } for t in targets
            ]
            
        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def update_target_note(target_id: int, note: str, session: AsyncSession = None) -> dict:
        async def _execute(sess: AsyncSession):
            rows = await target_repo.update_target(sess, target_id, {"note": note})
            return {"success": rows > 0}

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    res = await _execute(new_sess)
                    await new_sess.commit()
                    return res
                except Exception as e:
                    await new_sess.rollback()
                    return {"success": False, "message": str(e)}
        return await _execute(session)
