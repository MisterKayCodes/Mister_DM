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
    direction: Optional[str] = "INBOUND"

@router.post("/webhook/reply")
async def receive_reply(payload: ReplyWebhookPayload):
    """
    Inbound/Outbound webhook called by Mister Simulator when a dm_warrior session receives or sends a reply.
    """
    clean_username = payload.from_username.lstrip("@").strip()
    is_outbound = (payload.direction or "").upper() == "OUTBOUND"
    
    async with AsyncSessionLocal() as session:
        # 1. Find target by telegram_user_id first (most reliable), then username
        target = None
        
        if payload.from_user_id:
            stmt = (
                select(Target)
                .where(Target.telegram_user_id == payload.from_user_id)
                .where(Target.status.in_(["sent", "replied"]))
                .limit(1)
            )
            result = await session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            stmt = (
                select(Target)
                .where(Target.username == clean_username)
                .where(Target.status.in_(["sent", "replied"]))
                .limit(1)
            )
            result = await session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            logger.warning(f"[WEBHOOK] Webhook from @{clean_username} — no matching target found. Ignoring.")
            return {"status": "ignored", "reason": "No matching target found"}

        # 2. Update status and session lock
        target.status = "replied"
        if not target.replied_at:
            target.replied_at = func.now()
        if payload.from_user_id:
            target.telegram_user_id = payload.from_user_id
            
        if payload.session_name:
            target.assigned_session = payload.session_name
        
        # If outbound manual reply by operator, clear needs_human flag
        if is_outbound:
            target.needs_human = False

        await session.commit()
        
        target_id = target.id
        target_username = target.username

        # 3. Log message in database
        if is_outbound:
            from data.repositories import relationship_chats_repo, relationship_messages_repo
            chat = await relationship_chats_repo.get_chat_by_target(session, target_id)
            if chat:
                await relationship_messages_repo.add_message(
                    session=session,
                    chat_id=chat.id,
                    role="assistant",
                    content=payload.message_text
                )
                await session.commit()
            logger.info(f"[WEBHOOK] Outbound manual operator reply logged for @{target_username}")
            return {"status": "success", "target_id": target_id, "synced": "outbound"}

        # Inbound reply path
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

    # 4. Fire triage in background for inbound messages
    asyncio.create_task(TriageService.classify_lead(target_id, payload.message_text))

    return {
        "status": "success",
        "target_id": target_id,
        "username": target_username,
        "triage_triggered": True
    }
