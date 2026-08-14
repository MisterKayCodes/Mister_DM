# LAYER: Mouth — UI coordination only. No business logic.
import os
import logging
from contextlib import contextmanager

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from services.export_service import ExportService

router = Router()
logger = logging.getLogger(__name__)

from bot.constants.messages import (
    MSG_GENERATING,
    MSG_DONE_TARGET,
    MSG_DONE_CAMPAIGN,
    MSG_FAILED_UPLOAD,
    MSG_NO_CAMPAIGN,
)


def _cleanup(filepath: str):
    """Remove temp export file after sending."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError as e:
        logger.warning(f"Could not delete temp file {filepath}: {e}")


@router.callback_query(F.data.startswith("export_target_"), StateFilter("*"))
async def handle_export_target(callback: CallbackQuery):
    # Ack callback immediately to prevent Telegram timeout
    await callback.answer()
    target_id = int(callback.data.split("_")[2])
    
    status_msg = await callback.message.answer(MSG_GENERATING)
    
    try:
        success, result = await ExportService.export_target(target_id)
        if not success:
            await status_msg.edit_text(f"❌ Failed to export: {result}")
            return
            
        filepath = result
        try:
            doc = FSInputFile(filepath, filename=os.path.basename(filepath))
            await callback.message.answer_document(doc, caption=MSG_DONE_TARGET)
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Failed to send target export document: {e}")
            await status_msg.edit_text(MSG_FAILED_UPLOAD)
        finally:
            _cleanup(filepath)
            
    except Exception as e:
        logger.error(f"ExportService.export_target crashed: {e}")
        await status_msg.edit_text("❌ An unexpected error occurred.")


@router.message(F.text == "📥 Export Campaign", StateFilter("*"))
async def handle_export_campaign(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    
    # Guard against missing FSM context
    if not campaign_id:
        await message.answer(MSG_NO_CAMPAIGN)
        return
        
    status_msg = await message.answer(MSG_GENERATING)
    
    try:
        success, result = await ExportService.export_campaign(campaign_id)
        if not success:
            await status_msg.edit_text(f"❌ Failed to export: {result}")
            return
            
        filepath = result
        try:
            doc = FSInputFile(filepath, filename=os.path.basename(filepath))
            await message.answer_document(doc, caption=MSG_DONE_CAMPAIGN)
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Failed to send campaign export document: {e}")
            await status_msg.edit_text(MSG_FAILED_UPLOAD)
        finally:
            _cleanup(filepath)
            
    except Exception as e:
        logger.error(f"ExportService.export_campaign crashed: {e}")
        await status_msg.edit_text("❌ An unexpected error occurred.")
