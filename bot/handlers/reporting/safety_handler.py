import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.keyboards.safety_keyboards import safety_settings_keyboard
from bot.states.safety_states import SafetyStates
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = Router()

def _build_safety_panel_text(summary: dict) -> str:
    approval_str = "🟢 <b>ACTIVE (Human Review)</b>\n  <i>Every cold DM requires a 1-tap confirmation before sending.</i>" if summary["approval_mode"] else "⚪ <b>DISABLED (Autonomous)</b>\n  <i>DMs dispatch directly without operator confirmation.</i>"
    
    cap = summary["daily_dm_cap"]
    cap_note = "<i>(Safe default — eliminates Telegram spam freezes)</i>" if cap <= 2 else "<i>(⚠️ Above default — higher volume, monitor session health)</i>"

    return (
        "╔══════════════════════════════╗\n"
        "║   🛡️ <b>OUTREACH SAFETY & LIMITS</b>   ║\n"
        "╚══════════════════════════════╝\n\n"
        f"⚡ <b>Approval War Room:</b>\n{approval_str}\n\n"
        f"🎯 <b>Daily Session Quota:</b> <code>{cap} DMs / session / day</code>\n  {cap_note}\n\n"
        f"⏱️ <b>Anti-Spam Cooldown Gap:</b> <code>{summary['cooldown_hours']} Hours between dispatches</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Use the controls below to toggle approval mode or adjust the daily session cap:</i>"
    )

@router.message(F.text.in_({"🛡️ Outreach Safety", "Outreach Safety"}), StateFilter("*"))
async def show_safety_panel(message: Message, state: FSMContext):
    await state.clear()
    summary = await SettingsService.get_safety_summary()
    text = _build_safety_panel_text(summary)
    kb = safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "toggle_approval_mode")
async def cb_toggle_approval(callback: CallbackQuery):
    await SettingsService.toggle_approval_mode()
    summary = await SettingsService.get_safety_summary()
    text = _build_safety_panel_text(summary)
    kb = safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    mode_str = "Enabled" if summary["approval_mode"] else "Disabled"
    await callback.answer(f"Approval Mode {mode_str}!")

@router.callback_query(F.data == "refresh_safety_settings")
async def cb_refresh_safety(callback: CallbackQuery):
    summary = await SettingsService.get_safety_summary()
    text = _build_safety_panel_text(summary)
    kb = safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Settings refreshed.")

@router.callback_query(F.data == "prompt_set_daily_cap")
async def cb_prompt_daily_cap(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SafetyStates.waiting_for_daily_cap)
    await callback.message.answer(
        "🎯 <b>Set Daily DM Cap Per Session</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Send the maximum number of cold DMs each session can dispatch per day:\n"
        "• Recommended safe default: <code>2</code>\n"
        "• Send <code>❌ Cancel</code> to cancel.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SafetyStates.waiting_for_daily_cap)
async def process_daily_cap_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text in ("❌ Cancel", "cancel", "/cancel"):
        await state.clear()
        summary = await SettingsService.get_safety_summary()
        await message.answer("Cancelled. Settings unchanged.", reply_markup=safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"]))
        return

    try:
        val = int(text)
    except ValueError:
        await message.answer("❌ Invalid number. Please send an integer (e.g. 2, 3, 5):")
        return

    success, warning = await SettingsService.set_daily_dm_cap(val)
    if not success:
        await message.answer(f"❌ {warning}. Please try again:")
        return

    await state.clear()
    summary = await SettingsService.get_safety_summary()
    resp_text = f"✅ <b>Daily DM Cap updated to {val} DMs / session / day!</b>\n"
    if warning:
        resp_text += f"\n{warning}\n"
    resp_text += "\n" + _build_safety_panel_text(summary)

    kb = safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"])
    await message.answer(resp_text, reply_markup=kb, parse_mode="HTML")
