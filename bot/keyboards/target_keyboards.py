from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def import_method_keyboard() -> ReplyKeyboardMarkup:
    """Offers the two import methods for targets."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Paste Usernames"),
                KeyboardButton(text="📁 Upload TXT File")
            ],
            [KeyboardButton(text="❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def confirm_clear_keyboard() -> ReplyKeyboardMarkup:
    """Confirmation before wiping all targets from a campaign."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Yes, Clear Targets"),
                KeyboardButton(text="❌ Cancel")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def target_profile_keyboard(target_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for the Target Profile view."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 Add Pain Tag", callback_data=f"add_pain_{target_id}")],
        [InlineKeyboardButton(text="📝 Edit Note", callback_data=f"edit_note_{target_id}")],
        [InlineKeyboardButton(text="📥 Export Chat", callback_data=f"export_target_{target_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Replies", callback_data="view_replies")]
    ])

def note_cancel_keyboard(target_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for canceling note edit."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data=f"profile_{target_id}")]
    ])

