import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.keyboards.safety_keyboards import (
    safety_settings_keyboard,
    telemetry_dashboard_keyboard,
    session_picker_keyboard
)
from bot.states.safety_states import SafetyStates
from services.settings_service import SettingsService
from services.reporting.telemetry_service import TelemetryService

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


def _format_telemetry_dashboard_text(telemetry_data: dict) -> str:
    summary = telemetry_data["summary"]
    recent_logs = telemetry_data["recent_logs"]
    alerts = telemetry_data.get("alerts", [])

    total = summary.get("total_sent", 0)
    healthy = summary.get("healthy_count", 0)
    healthy_rate = summary.get("healthy_rate", 100.0)
    flood_wait = summary.get("flood_wait_count", 0)
    peer_flood = summary.get("peer_flood_count", 0)
    banned = summary.get("banned_count", 0)
    active_sess = summary.get("active_sessions_count", 0)

    # Status Emoji mapper
    def outcome_emoji(outcome: str) -> str:
        o = (outcome or "").lower()
        if o == "sent":
            return "🟢"
        if o == "flood_wait":
            return "🟡"
        if o == "peer_flood":
            return "🟠"
        if o == "banned":
            return "🛑"
        return "🔴"

    # Format Recent Events
    event_lines = []
    if not recent_logs:
        event_lines.append("<i>No outreach activity recorded yet.</i>")
    else:
        for log in recent_logs[:5]:
            emoji = outcome_emoji(log.outcome)
            target = f"@{log.target_username}" if log.target_username else "target"
            gap_str = f"+{log.gap_minutes}m" if log.daily_index > 1 else "first"
            tmpl_str = f"T#{log.template_id}" if log.template_id else "direct"
            event_lines.append(
                f"{emoji} <code>{log.session_name}</code> → <b>{target}</b> "
                f"[#{log.daily_index} | {gap_str} | {tmpl_str}]"
            )

    recent_section = "\n".join(event_lines)

    # Format Alerts
    alerts_section = ""
    if alerts:
        alerts_section = "\n⚠️ <b>Risk Patterns Detected:</b>\n" + "\n".join([f"• {a}" for a in alerts]) + "\n"

    return (
        "╔══════════════════════════════╗\n"
        "║  📊 <b>OUTREACH TELEMETRY (24H)</b>  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"📤 <b>Total Dispatches:</b> <code>{total}</code>\n"
        f"🛡️ <b>Session Health:</b> <code>{healthy_rate}%</code> ({healthy} healthy)\n"
        f"⏳ <b>FloodWait:</b> <code>{flood_wait}</code> | 🚫 <b>PeerFlood:</b> <code>{peer_flood}</code> | 🛑 <b>Banned:</b> <code>{banned}</code>\n"
        f"🤖 <b>Active Sessions:</b> <code>{active_sess}</code>\n"
        f"{alerts_section}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏱️ <b>Recent Outreach Events:</b>\n"
        f"{recent_section}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Telemetry tracks real-time dispatch pacing, cooldowns, and risk signatures.</i>"
    )


@router.callback_query(F.data.in_({"safety:telemetry", "telem:refresh"}))
async def cb_show_telemetry(callback: CallbackQuery):
    telemetry_data = await TelemetryService.get_dashboard_summary()
    has_alerts = bool(telemetry_data.get("alerts"))
    text = _format_telemetry_dashboard_text(telemetry_data)
    kb = telemetry_dashboard_keyboard(has_alerts=has_alerts)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "settings:safety")
async def cb_back_to_safety(callback: CallbackQuery):
    summary = await SettingsService.get_safety_summary()
    text = _build_safety_panel_text(summary)
    kb = safety_settings_keyboard(summary["approval_mode"], summary["daily_dm_cap"])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "telem:filter:session")
async def cb_filter_session(callback: CallbackQuery):
    telemetry_data = await TelemetryService.get_dashboard_summary()
    sessions = telemetry_data.get("active_sessions", [])
    if not sessions:
        await callback.answer("No active sessions found in telemetry log.", show_alert=True)
        return

    kb = session_picker_keyboard(sessions)
    text = (
        "🔍 <b>Select Session to Inspect:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an active outreach session to view its recent history and risk profile:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("telem:sess:"))
async def cb_session_detail(callback: CallbackQuery):
    session_name = callback.data.split("telem:sess:")[-1]
    logs = await TelemetryService.get_session_history(session_name, limit=10)

    if not logs:
        text = f"👤 <b>Session:</b> <code>{session_name}</code>\n\n<i>No recent telemetry events found for this session.</i>"
    else:
        log_lines = []
        for l in logs:
            status_tag = f"[{l.outcome.upper()}]"
            target_str = f"@{l.target_username}" if l.target_username else "target"
            gap_str = f"+{l.gap_minutes}m gap" if l.daily_index > 1 else "first run"
            log_lines.append(
                f"• {status_tag} → <b>{target_str}</b>\n"
                f"   DM #{l.daily_index} today ({gap_str}) at {l.created_at.strftime('%H:%M:%S') if l.created_at else ''}"
            )
        text = (
            f"👤 <b>Session Telemetry:</b> <code>{session_name}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(log_lines)
        )

    kb = session_picker_keyboard([])  # Returns back to telemetry button
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "telem:view:alerts")
async def cb_view_alerts(callback: CallbackQuery):
    telemetry_data = await TelemetryService.get_dashboard_summary()
    alerts = telemetry_data.get("alerts", [])
    if not alerts:
        await callback.answer("No active risk alerts! System running cleanly.", show_alert=True)
        return

    alert_text = (
        "⚠️ <b>ACTIVE RISK PATTERNS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        + "\n\n".join(alerts) + "\n\n"
        "<i>Recommended action: Increase delay between DMs or keep approval mode active.</i>"
    )
    kb = telemetry_dashboard_keyboard(has_alerts=True)
    try:
        await callback.message.edit_text(alert_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(alert_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

