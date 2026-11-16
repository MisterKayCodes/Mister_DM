import json
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from data.database import AsyncSessionLocal
from data.repositories import (
    draft_repo,
    target_repo,
    relationship_chats_repo,
    relationship_messages_repo,
    intents_repo
)
from clients.simulator_client import simulator_client
from utils.telegram_utils import safe_html

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data.startswith("approve_draft:"))
async def handle_approve_draft(callback: CallbackQuery):
    admin_name = callback.from_user.username or callback.from_user.first_name or "Operator"
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid draft ID.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        # 1. Atomic claim check to prevent multi-admin race conditions
        claimed = await draft_repo.atomic_claim_draft(session, draft_id, admin_name=admin_name)
        if not claimed:
            draft = await draft_repo.get_draft_by_id(session, draft_id)
            status_label = draft.status if draft else "already processed"
            await callback.answer(f"⚠️ This draft was {status_label} by another operator!", show_alert=True)
            return

        draft = await draft_repo.get_draft_by_id(session, draft_id)
        if not draft:
            await callback.answer("❌ Draft not found.", show_alert=True)
            return

        target = await target_repo.get_target_by_id(session, draft.target_id)
        if not target:
            await callback.answer("❌ Target not found.", show_alert=True)
            return

        session_name = draft.session_name or target.assigned_session or "default_session"

        # 2. Fire pending chapter media if attached
        if draft.pending_media_json:
            try:
                media_list = json.loads(draft.pending_media_json)
                for item in media_list:
                    file_id = item.get("telegram_file_id")
                    m_type = item.get("media_type", "photo")
                    if file_id:
                        await simulator_client.send_media(
                            session_name=session_name,
                            target_username=target.username,
                            telegram_file_id=file_id,
                            media_type=m_type,
                            telegram_user_id=getattr(target, "telegram_user_id", None)
                        )
            except Exception as media_exc:
                logger.error(f"[APPROVAL_HANDLER] Failed to send pending media for draft {draft_id}: {media_exc}")

        # 3. Fire text DM via Simulator
        send_success = False
        try:
            res = await simulator_client.send_dm(
                session_name=session_name,
                target_username=target.username,
                message_text=draft.draft_text,
                telegram_user_id=getattr(target, "telegram_user_id", None)
            )
            send_success = res.get("status") == "success" or res.get("ok", False)
        except Exception as send_exc:
            logger.error(f"[APPROVAL_HANDLER] DM send failed for draft {draft_id}: {send_exc}")

        # 4. Update DB state on success
        if draft.pending_arc_chapter:
            target.arc_chapter = draft.pending_arc_chapter

        asst_msg = await relationship_messages_repo.add_message(
            session=session,
            chat_id=draft.chat_id,
            role="assistant",
            content=draft.draft_text
        )
        if draft.intent_text:
            await intents_repo.log_intent(
                session=session,
                message_id=asst_msg.id,
                intent_text=draft.intent_text,
                confidence_score=draft.confidence_score,
                needs_human=False
            )

        await draft_repo.mark_draft_completed(session, draft_id, "approved", admin_name=admin_name)
        await session.commit()

        # 5. Edit War Room card UI
        target_display = f"@{target.username}" if target.username else f"Target #{target.id}"
        updated_card_text = (
            f"✅ <b>DRAFT APPROVED & SENT</b>\n\n"
            f"<b>Target:</b> {safe_html(target_display)}\n"
            f"<b>Approved By:</b> @{safe_html(admin_name)}\n\n"
            f"💬 <b>Sent Reply:</b>\n"
            f"<code>{safe_html(draft.draft_text)}</code>"
        )
        if callback.message:
            await callback.message.edit_text(updated_card_text, parse_mode="HTML")
        await callback.answer("✅ Draft approved & sent successfully!")


@router.callback_query(F.data.startswith("reject_draft:"))
async def handle_reject_draft(callback: CallbackQuery):
    admin_name = callback.from_user.username or callback.from_user.first_name or "Operator"
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid draft ID.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        claimed = await draft_repo.atomic_claim_draft(session, draft_id, admin_name=admin_name)
        if not claimed:
            draft = await draft_repo.get_draft_by_id(session, draft_id)
            status_label = draft.status if draft else "already processed"
            await callback.answer(f"⚠️ This draft was {status_label} by another operator!", show_alert=True)
            return

        draft = await draft_repo.get_draft_by_id(session, draft_id)
        target_display = "Target"
        if draft:
            target = await target_repo.get_target_by_id(session, draft.target_id)
            if target and target.username:
                target_display = f"@{target.username}"

        await draft_repo.mark_draft_completed(session, draft_id, "rejected", admin_name=admin_name)
        await session.commit()

        updated_card_text = (
            f"❌ <b>DRAFT REJECTED</b>\n\n"
            f"<b>Target:</b> {safe_html(target_display)}\n"
            f"<b>Rejected By:</b> @{safe_html(admin_name)}\n\n"
            f"💬 <b>Discarded Draft:</b>\n"
            f"<code>{safe_html(draft.draft_text if draft else '')}</code>"
        )
        if callback.message:
            await callback.message.edit_text(updated_card_text, parse_mode="HTML")
        await callback.answer("❌ Draft rejected and discarded.")
