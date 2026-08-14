# LAYER: Service — session injection, DTOs, business rules, no UI
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from data.database import AsyncSessionLocal
from services.message_service import MessageService
from services.target_service import TargetService
from services.campaign_service import CampaignService
from utils.file_generator import generate_target_export, generate_campaign_export

logger = logging.getLogger(__name__)

class ExportService:
    """Nerves layer for exporting conversation files."""

    @staticmethod
    async def export_target(target_id: int, session: AsyncSession = None) -> tuple[bool, str]:
        """
        Exports a single target's conversation history to a file.
        Returns (True, filepath) or (False, error_msg).
        """
        async def _execute(sess: AsyncSession):
            # 1. Fetch Target
            target = await TargetService.get_target_by_id(target_id, sess)
            if not target:
                return False, "Target not found."
                
            # 2. Fetch Messages
            messages = await MessageService.get_messages_for_target(target_id, sess)
            if not messages:
                return False, "No messages found for this target."
                
            # 3. Generate File
            filepath = generate_target_export(target["username"], messages)
            return True, filepath

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)

    @staticmethod
    async def export_campaign(campaign_id: int, session: AsyncSession = None) -> tuple[bool, str]:
        """
        Exports all conversations for a campaign to a file, grouped by target.
        Returns (True, filepath) or (False, error_msg).
        """
        async def _execute(sess: AsyncSession):
            # 1. Fetch Campaign
            campaign = await CampaignService.get_campaign_by_id(campaign_id, sess)
            if not campaign:
                return False, "Campaign not found."
                
            # 2. Fetch Messages
            messages = await MessageService.get_messages_for_campaign(campaign_id, sess)
            if not messages:
                return False, "No messages found for this campaign."
                
            # 3. Fetch all targets in campaign to resolve usernames
            # We fetch all targets to map target_id -> username efficiently
            targets = await TargetService.get_targets_for_campaign(campaign_id, sess)
            target_map = {t["id"]: t["username"] for t in targets}
            
            # 4. Group messages by username
            grouped = {}
            for msg in messages:
                username = target_map.get(msg["target_id"], f"Unknown_{msg['target_id']}")
                if username not in grouped:
                    grouped[username] = []
                grouped[username].append(msg)
                
            # 5. Generate File
            filepath = generate_campaign_export(campaign["name"], grouped)
            return True, filepath

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)
