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
