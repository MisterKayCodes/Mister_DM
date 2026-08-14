# LAYER: Mouth — UI coordination only. No business logic, no DB access.
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards.blacklist_keyboards import blacklist_menu_keyboard
from bot.keyboards.account_keyboards import main_menu_keyboard
from services.blacklist_service import BlacklistService
from utils.telegram_utils import safe_html

router = Router()
logger = logging.getLogger(__name__)


class BlacklistStates(StatesGroup):
    waiting_for_username_to_add = State()
    waiting_for_username_to_remove = State()


def _build_blacklist_text(entries: list[dict]) -> str:
    """Renders blacklist entries as HTML. Pure formatting — no logic."""
    if not entries:
        return "🚫 Blacklist is empty."
    text = "🚫 <b>Blacklisted Users</b>\n\n"
    for e in entries:
        handle = f"@{safe_html(e['username'])}" if e["username"] else f"ID: {e['telegram_user_id']}"
        reason = safe_html(e["reason"] or "No reason given")
        text += f"• {handle} — {reason}\n  <i>Added: {e['created_at_str']}</i>\n\n"
    return text


# ==========================================
# NAVIGATION
# ==========================================

@router.message(F.text == "🚫 Blacklist", StateFilter("*"))
async def blacklist_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Blacklist Menu\nManage users who must never be contacted.", reply_markup=blacklist_menu_keyboard())


# ==========================================
# VIEW
# ==========================================

@router.message(F.text == "📋 View Blacklist", StateFilter("*"))
async def view_blacklist_handler(message: Message):
    try:
        entries = await BlacklistService.get_all_blacklisted()
    except Exception as e:
        logger.error(f"Failed to load blacklist: {e}")
        await message.answer("❌ Could not load blacklist. Please try again.")
        return

    text = _build_blacklist_text(entries)
    await message.answer(text, reply_markup=blacklist_menu_keyboard(), parse_mode="HTML")


# ==========================================
# ADD
# ==========================================

@router.message(F.text == "➕ Add to Blacklist", StateFilter("*"))
async def add_blacklist_start(message: Message, state: FSMContext):
    await message.answer("Enter the username to blacklist (without @):")
    await state.set_state(BlacklistStates.waiting_for_username_to_add)


@router.message(BlacklistStates.waiting_for_username_to_add)
async def process_blacklist_add(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    if not username:
        await message.answer("Username cannot be empty. Try again:")
        return

    try:
        success, msg = await BlacklistService.blacklist_target(username=username, telegram_user_id=None, reason="MANUAL")
    except Exception as e:
        logger.error(f"Failed to blacklist @{username}: {e}")
        await message.answer("❌ Could not blacklist user. Please try again.")
        await state.clear()
        return

    status = "✅" if success else "❌"
    await message.answer(f"{status} {msg}", reply_markup=blacklist_menu_keyboard())
    await state.clear()


# ==========================================
# REMOVE
# ==========================================

@router.message(F.text == "❌ Remove from Blacklist", StateFilter("*"))
async def remove_blacklist_start(message: Message, state: FSMContext):
    await message.answer("Enter the username to remove from the blacklist (without @):")
    await state.set_state(BlacklistStates.waiting_for_username_to_remove)


@router.message(BlacklistStates.waiting_for_username_to_remove)
async def process_blacklist_remove(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    if not username:
        await message.answer("Username cannot be empty. Try again:")
        return

    try:
        success, msg = await BlacklistService.unblacklist_target(username)
    except Exception as e:
        logger.error(f"Failed to remove @{username} from blacklist: {e}")
        await message.answer("❌ Could not remove user. Please try again.")
        await state.clear()
        return

    status = "✅" if success else "❌"
    await message.answer(f"{status} {msg}", reply_markup=blacklist_menu_keyboard())
    await state.clear()


# ==========================================
# ONE-CLICK BLACKLIST FROM TARGET PROFILE
# ==========================================

@router.message(F.text.startswith("🚫 Blacklist @"), StateFilter("*"))
async def blacklist_from_target_profile(message: Message, state: FSMContext):
    """Triggered from target profile — pre-fills username from button text."""
    username = message.text.replace("🚫 Blacklist @", "").strip()
    if not username:
        await message.answer("Could not determine username.")
        return

    try:
        success, msg = await BlacklistService.blacklist_target(username=username, telegram_user_id=None, reason="MANUAL")
    except Exception as e:
        logger.error(f"Failed to blacklist @{username} from profile: {e}")
        await message.answer("❌ Could not blacklist user.")
        return

    status = "✅" if success else "❌"
    await message.answer(f"{status} {msg}", reply_markup=blacklist_menu_keyboard())
    await state.clear()
