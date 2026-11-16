from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def safety_settings_keyboard(approval_mode: bool, daily_cap: int) -> InlineKeyboardMarkup:
    """Inline control panel for Outreach Safety & Limits."""
    approval_badge = "🟢 ON (Safe Mode)" if approval_mode else "⚪ OFF (Full Auto)"
    toggle_text = "Turn OFF Approval" if approval_mode else "Turn ON Approval"

    keyboard = [
        [
            InlineKeyboardButton(text=f"Approval: {approval_badge}", callback_data="noop")
        ],
        [
            InlineKeyboardButton(text=f"🔄 {toggle_text}", callback_data="toggle_approval_mode")
        ],
        [
            InlineKeyboardButton(text=f"🎯 Daily Cap: {daily_cap} DMs/session", callback_data="prompt_set_daily_cap")
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_safety_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
