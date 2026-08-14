# LAYER: Mouth — UI coordination only. No DB access, no business logic.
import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.states.campaign_states import AddCampaignStates
from bot.keyboards.campaign_keyboards import (
    campaigns_menu_keyboard,
    select_account_keyboard,
    campaigns_list_keyboard,
    confirm_campaign_delete_keyboard
)
from bot.keyboards.template_keyboards import manage_campaign_keyboard
from bot.constants.messages import (
    CAMP_ASK_NAME, CAMP_NAME_EMPTY, CAMP_ASK_ACCOUNT, CAMP_NO_ACCOUNTS,
    CAMP_CANCELLED, CAMP_USE_KEYBOARD, CAMP_ACCOUNT_GONE,
    CAMP_CREATE_OK, CAMP_CREATE_FAIL, CAMP_MENU_HEADER, CAMP_LIST_HEADER,
    CAMP_LIST_EMPTY, CAMP_NOT_FOUND, CAMP_LOAD_ERROR, CAMP_NO_SELECTION,
    CAMP_DELETE_INVALID, CAMP_DELETE_CONFIRM, CAMP_DELETE_BLOCKED,
    CAMP_DELETE_OK, CAMP_DELETE_FAIL
)
from services.campaign_service import CampaignService
from services.account_service import AccountService
from services.scheduler_service import SchedulerService
from utils.telegram_utils import safe_html
from bot.utils.ui_layouts import build_campaign_summary_text

router = Router()
logger = logging.getLogger(__name__)


# --- Validation helper: strips emoji prefix from keyboard button text ---
def _strip_prefix(text: str, prefix: str) -> str:
    """Removes a known emoji prefix from a keyboard button value."""
    return text.replace(prefix, "").strip()


def _build_campaigns_list_text(campaigns: list[dict]) -> str:
    """Renders campaign list DTO as HTML. Pure formatting — no logic."""
    if not campaigns:
        return CAMP_LIST_EMPTY
    text = CAMP_LIST_HEADER
    for camp in campaigns:
        text += f"<b>#{camp['id']} - {safe_html(camp['name'])}</b>\n"
        text += f"Account: {safe_html(camp['account_name'])}\n"
        text += f"Status: {safe_html(camp['status'])}\n"
        text += f"Created: {camp['created_at_str']}\n\n"
    return text


def _campaigns_list_reply(campaigns: list[dict]):
    """Returns the right keyboard for the campaigns list."""
    return campaigns_menu_keyboard() if not campaigns else campaigns_list_keyboard(campaigns)


# ==========================================
# NAVIGATION
# ==========================================

@router.message(F.text.in_({"🎯 Campaigns", "⬅️ Back to Campaigns"}), StateFilter("*"))
async def campaigns_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(CAMP_MENU_HEADER, reply_markup=campaigns_menu_keyboard())


# ==========================================
# ADD CAMPAIGN WIZARD (FSM)
# ==========================================

@router.message(F.text == "➕ Add Campaign", StateFilter("*"))
async def add_campaign_start(message: Message, state: FSMContext):
    await message.answer(CAMP_ASK_NAME, reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddCampaignStates.waiting_for_name)


@router.message(AddCampaignStates.waiting_for_name)
async def process_campaign_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer(CAMP_NAME_EMPTY)
        return

    await state.update_data(name=name)

    try:
        accounts = await AccountService.get_all_accounts()
    except Exception as e:
        logger.error(f"Failed to fetch accounts during campaign creation: {e}")
        await message.answer(CAMP_LOAD_ERROR, reply_markup=campaigns_menu_keyboard())
        await state.clear()
        return

    if not accounts:
        await message.answer(CAMP_NO_ACCOUNTS, reply_markup=campaigns_menu_keyboard())
        await state.clear()
        return

    await message.answer(CAMP_ASK_ACCOUNT, reply_markup=select_account_keyboard(accounts))
    await state.set_state(AddCampaignStates.waiting_for_account)


@router.message(AddCampaignStates.waiting_for_account)
async def process_campaign_account(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "❌ Cancel Creation":
        await state.clear()
        await message.answer(CAMP_CANCELLED, reply_markup=campaigns_menu_keyboard())
        return

    if not text.startswith("📧 "):
        await message.answer(CAMP_USE_KEYBOARD)
        return

    account_name = _strip_prefix(text, "📧 ")

    try:
        account = await AccountService.get_account_by_name(account_name)
    except Exception as e:
        logger.error(f"Failed to fetch account '{account_name}': {e}")
        await message.answer(CAMP_LOAD_ERROR, reply_markup=campaigns_menu_keyboard())
        await state.clear()
        return

    if not account:
        await message.answer(CAMP_ACCOUNT_GONE)
        return

    data = await state.get_data()
    campaign_name = data.get("name")

    try:
        success, msg = await CampaignService.add_campaign(campaign_name, account["id"])
    except Exception as e:
        logger.error(f"Failed to create campaign '{campaign_name}': {e}")
        await message.answer(CAMP_LOAD_ERROR, reply_markup=campaigns_menu_keyboard())
        await state.clear()
        return

    if success:
        await message.answer(
            CAMP_CREATE_OK.format(name=safe_html(campaign_name), account=safe_html(account["name"])),
            reply_markup=campaigns_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(CAMP_CREATE_FAIL.format(msg=msg), reply_markup=campaigns_menu_keyboard())

    await state.clear()


# ==========================================
# CAMPAIGN LIST & MANAGEMENT
# ==========================================

@router.message(F.text == "📋 List Campaigns", StateFilter("*"))
async def list_campaigns_handler(message: Message):
    try:
        campaigns = await CampaignService.get_all_campaigns()
    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}")
        await message.answer(CAMP_LOAD_ERROR, reply_markup=campaigns_menu_keyboard())
        return

    text = _build_campaigns_list_text(campaigns)
    await message.answer(text, reply_markup=_campaigns_list_reply(campaigns), parse_mode="HTML")


@router.message(F.text.startswith("🎯 ") & ~F.text.in_({"🎯 Campaigns"}), StateFilter("*"))
async def manage_campaign_click(message: Message, state: FSMContext):
    campaign_name = _strip_prefix(message.text, "🎯 ")

    try:
        campaign = await CampaignService.get_campaign_by_name(campaign_name)
    except Exception as e:
        logger.error(f"Failed to fetch campaign '{campaign_name}': {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    if not campaign:
        await message.answer(CAMP_NOT_FOUND)
        return

    # Store campaign ID and name — both needed by child handlers (stats, targets, controls)
    await state.update_data(current_campaign_id=campaign["id"], current_campaign_name=campaign["name"])

    try:
        summary = await CampaignService.get_campaign_summary(campaign["id"])
    except Exception as e:
        logger.error(f"Failed to fetch summary for campaign {campaign['id']}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    if not summary:
        await message.answer(CAMP_NOT_FOUND)
        return

    text = build_campaign_summary_text(summary)
    await message.answer(text, reply_markup=manage_campaign_keyboard(campaign["status"]), parse_mode="HTML")


# ==========================================
# SCHEDULER CONTROLS (Start / Pause / Stop)
# ==========================================

@router.message(F.text == "▶ Start Campaign", StateFilter("*"))
async def start_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer(CAMP_NO_SELECTION)
        return

    try:
        success, msg, actual_status = await SchedulerService.start_campaign(campaign_id)
    except Exception as e:
        logger.error(f"SchedulerService.start_campaign crashed for {campaign_id}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    prefix = "▶" if success else "❌ Cannot start:"
    await message.answer(f"{prefix} {msg}", reply_markup=manage_campaign_keyboard(actual_status))


@router.message(F.text == "⏸ Pause Campaign", StateFilter("*"))
async def pause_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer(CAMP_NO_SELECTION)
        return

    try:
        success, msg, actual_status = await SchedulerService.pause_campaign(campaign_id)
    except Exception as e:
        logger.error(f"SchedulerService.pause_campaign crashed for {campaign_id}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    prefix = "⏸" if success else "❌"
    await message.answer(f"{prefix} {msg}", reply_markup=manage_campaign_keyboard(actual_status))


@router.message(F.text == "🛑 Stop Campaign", StateFilter("*"))
async def stop_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer(CAMP_NO_SELECTION)
        return

    try:
        success, msg, actual_status = await SchedulerService.stop_campaign(campaign_id)
    except Exception as e:
        logger.error(f"SchedulerService.stop_campaign crashed for {campaign_id}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    prefix = "🛑" if success else "❌"
    await message.answer(f"{prefix} {msg}", reply_markup=manage_campaign_keyboard(actual_status))


# ==========================================
# DELETE CAMPAIGN
# ==========================================

@router.message(F.text.startswith("🗑 Delete Camp "), StateFilter("*"))
async def delete_campaign_prompt(message: Message):
    try:
        campaign_id = int(_strip_prefix(message.text, "🗑 Delete Camp "))
    except ValueError:
        await message.answer(CAMP_DELETE_INVALID)
        return

    try:
        can_delete, status = await CampaignService.verify_campaign_deletable(campaign_id)
    except Exception as e:
        logger.error(f"Failed to verify deletable for campaign {campaign_id}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    if not can_delete:
        if status == "not_found":
            await message.answer(CAMP_NOT_FOUND)
        else:
            await message.answer(
                CAMP_DELETE_BLOCKED.format(status=status),
                parse_mode="HTML"
            )
        return

    try:
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
    except Exception as e:
        logger.error(f"Failed to fetch campaign {campaign_id} for delete confirmation: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    if campaign:
        await message.answer(
            CAMP_DELETE_CONFIRM.format(name=safe_html(campaign["name"])),
            reply_markup=confirm_campaign_delete_keyboard(campaign_id),
            parse_mode="HTML"
        )


@router.message(F.text.startswith("✅ Yes, Delete Camp "), StateFilter("*"))
async def confirm_campaign_delete_handler(message: Message):
    try:
        campaign_id = int(_strip_prefix(message.text, "✅ Yes, Delete Camp "))
    except ValueError:
        await message.answer(CAMP_DELETE_INVALID)
        return

    try:
        deleted, msg, fresh_campaigns = await CampaignService.delete_campaign(campaign_id)
    except Exception as e:
        logger.error(f"Failed to delete campaign {campaign_id}: {e}")
        await message.answer(CAMP_LOAD_ERROR)
        return

    # Atomic: one message carries verdict + updated list
    if deleted:
        list_text = _build_campaigns_list_text(fresh_campaigns)
        await message.answer(
            f"{CAMP_DELETE_OK}\n\n{list_text}",
            reply_markup=_campaigns_list_reply(fresh_campaigns),
            parse_mode="HTML"
        )
    else:
        await message.answer(CAMP_DELETE_FAIL.format(msg=msg), reply_markup=campaigns_menu_keyboard())
