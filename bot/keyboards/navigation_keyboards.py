from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def back_inline(back_label: str = "⬅️ Back", back_data: str = "nav_back") -> InlineKeyboardMarkup:
    """
    A single inline Back button shown during FSM flows where the ReplyKeyboard is removed.

    # We use inline buttons here instead of relying on the ReplyKeyboard because
    # FSM flows (paste usernames, upload file) call ReplyKeyboardRemove() to give
    # the user a clean input area. Without an escape route, the user is trapped:
    # they cannot cancel unless they know to type "❌ Cancel" — which is invisible.
    # Inline buttons stay pinned to the message, always visible, zero extra FSM states needed.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_label, callback_data=back_data)]
    ])


def back_and_home_inline() -> InlineKeyboardMarkup:
    """
    Two inline buttons: Back one step + Home (Main Menu).
    Used when removing the ReplyKeyboard during multi-step FSM flows.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="nav_back"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="nav_home")
        ]
    ])
