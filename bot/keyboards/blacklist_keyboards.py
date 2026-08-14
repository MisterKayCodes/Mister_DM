# LAYER: Mouth (Keyboards) — Keyboard builders only. No logic, no DB access.
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def blacklist_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main blacklist menu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 View Blacklist"), KeyboardButton(text="➕ Add to Blacklist")],
            [KeyboardButton(text="❌ Remove from Blacklist")],
            [KeyboardButton(text="⬅️ Back to Main")]
        ],
        resize_keyboard=True
    )
