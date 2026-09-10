import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from data.models.target import Target
from sqlalchemy import select
from sqlalchemy.sql import func
from services.triage_service import TriageService
from services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])

class ReplyWebhookPayload(BaseModel):
    session_name: str
    from_username: str
    from_user_id: Optional[int] = None
    message_text: str
    timestamp: Optional[str] = None

@router.post("/webhook/reply")
async def receive_reply(payload: ReplyWebhookPayload):
    """
    Inbound webhook called by Mister Simulator when a dm_warrior session receives a reply.
    Updates target status to 'replied', logs INBOUND message, and fires Groq triage in background.
    """
    clean_username = payload.from_username.lstrip("@").strip()
    
    async with AsyncSessionLocal() as session:
        # 1. Find target by telegram_user_id first (most reliable), then username
        target = None
        
        if payload.from_user_id:
            stmt = (
                select(Target)
                .where(Target.telegram_user_id == payload.from_user_id)
                .where(Target.status == "sent")
                .limit(1)
            )
            result = await session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            stmt = (
                select(Target)
                .where(Target.username == clean_username)
                .where(Target.status == "sent")
                .limit(1)
            )
            result = await session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            logger.warning(f"[WEBHOOK] Inbound reply from @{clean_username} — no matching sent target found. Ignoring.")
            return {"status": "ignored", "reason": "No matching sent target found"}

        # 2. Update status to replied
        target.status = "replied"
        target.replied_at = func.now()
        if payload.from_user_id:
            target.telegram_user_id = payload.from_user_id
        
        await session.commit()
        
        target_id = target.id
        target_username = target.username
        logger.info(f"[WEBHOOK] @{target_username} (ID: {target_id}) marked as replied. Firing triage...")

        # 3. Log inbound reply message
        ok_log, log_res = await MessageService.log_message(
            target_id=target_id,
            direction="INBOUND",
            message_type="TEXT",
            text=payload.message_text,
            telegram_message_id=None,
            session=session
        )
        if not ok_log:
            logger.error(f"[WEBHOOK] Failed to log inbound reply message for @{target_username}: {log_res}")
        else:
            await session.commit()

    # 4. Fire triage in background (non-blocking)
    asyncio.create_task(TriageService.classify_lead(target_id, payload.message_text))

    return {
        "status": "success",
        "target_id": target_id,
        "username": target_username,
        "triage_triggered": True
    }
