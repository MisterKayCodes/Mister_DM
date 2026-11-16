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
            InlineKeyboardButton(text="📊 Telemetry & Risk Log", callback_data="safety:telemetry")
        ],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_safety_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def telemetry_dashboard_keyboard(has_alerts: bool = False) -> InlineKeyboardMarkup:
    """Telemetry Dashboard Navigation Keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="telem:refresh"),
            InlineKeyboardButton(text="🔍 Filter by Session", callback_data="telem:filter:session")
        ]
    ]
    if has_alerts:
        keyboard.append([
            InlineKeyboardButton(text="⚠️ View Risk Patterns", callback_data="telem:view:alerts")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Back to Safety", callback_data="settings:safety")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def session_picker_keyboard(sessions: list) -> InlineKeyboardMarkup:
    """Session selector keyboard (callback data safely <= 64 bytes)."""
    keyboard = []
    # sessions can be list of dicts with 'session_name' or list of strings
    for s in sessions:
        name = s["session_name"] if isinstance(s, dict) else str(s)
        # Keep callback data short and compact
        cb = f"telem:sess:{name}"[:64]
        keyboard.append([
            InlineKeyboardButton(text=f"👤 {name}", callback_data=cb)
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Back to Telemetry", callback_data="telem:refresh")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
