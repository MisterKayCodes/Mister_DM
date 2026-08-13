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
from services.campaign_service import CampaignService
from services.account_service import AccountService
from services.scheduler_service import SchedulerService
from utils.telegram_utils import safe_html
from bot.utils.ui_layouts import build_campaign_summary_text

router = Router()

def _build_campaigns_list_text(campaigns: list[dict]) -> str:
    """
    Builds the HTML display string for a list of campaigns.
    The Service returns raw dictionaries. The Mouth draws the HTML here.
    """
    if not campaigns:
        return "No campaigns found."
        
    text = "📋 Your Campaigns:\n\n"
    for camp in campaigns:
        text += f"<b>#{camp['id']} - {safe_html(camp['name'])}</b>\n"
        text += f"Account: {safe_html(camp['account_name'])}\n"
        text += f"Status: {safe_html(camp['status'])}\n"
        text += f"Created: {camp['created_at_str']}\n\n"
    return text

# ==========================================
# NAVIGATION
# ==========================================

# #FIXED: Firewall the Presentation Layer
# Added StateFilter("*") so users can escape an active FSM flow safely.
@router.message(F.text.in_({"🎯 Campaigns", "⬅️ Back to Campaigns"}), StateFilter("*"))
async def campaigns_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎯 Campaigns Menu\nManage your outreach campaigns.",
        reply_markup=campaigns_menu_keyboard()
    )

# ==========================================
# ADD CAMPAIGN WIZARD (FSM)
# ==========================================

@router.message(F.text == "➕ Add Campaign", StateFilter("*"))
async def add_campaign_start(message: Message, state: FSMContext):
    await message.answer("What is the name of this campaign? (e.g. August Forex Leads)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddCampaignStates.waiting_for_name)

@router.message(AddCampaignStates.waiting_for_name)
async def process_campaign_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Name cannot be empty. Please enter a valid name:")
        return
        
    await state.update_data(name=name)
    
    accounts = await AccountService.get_all_accounts()
        
    if not accounts:
        await message.answer("You have no accounts saved! Please create an Account first in the Accounts menu.", reply_markup=campaigns_menu_keyboard())
        await state.clear()
        return
        
    await message.answer("Which account will execute this campaign?", reply_markup=select_account_keyboard(accounts))
    await state.set_state(AddCampaignStates.waiting_for_account)

@router.message(AddCampaignStates.waiting_for_account)
async def process_campaign_account(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Cancel Creation":
        await state.clear()
        await message.answer("Campaign creation cancelled.", reply_markup=campaigns_menu_keyboard())
        return
        
    if not text.startswith("📧 "):
        await message.answer("Please use the keyboard buttons to select an account.")
        return
        
    account_name = text.replace("📧 ", "").strip()
    
    # #FIXED: Seal Logic Leakage (No Data Lookups in the Mouth)
    # Service call resolves the account — Mouth does not iterate lists.
    account = await AccountService.get_account_by_name(account_name)
    if not account:
        await message.answer("Account not found. Please try again.")
        return
        
    data = await state.get_data()
    campaign_name = data.get("name")
    
    success, msg = await CampaignService.add_campaign(campaign_name, account["id"])
        
    if success:
        await message.answer(
            f"✅ Campaign '{campaign_name}' created as [draft].\nAssigned to: {account['name']}",
            reply_markup=campaigns_menu_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ Failed: {msg}\nPlease choose a different name or cancel:",
            reply_markup=campaigns_menu_keyboard()
        )
        await state.clear()

# ==========================================
# CAMPAIGN LIST & MANAGEMENT
# ==========================================

# #FIXED: Separate Core and Presentation Data Formatting
# Service returns list[dict]. The Mouth renders HTML via _build_campaigns_list_text().
@router.message(F.text == "📋 List Campaigns", StateFilter("*"))
async def list_campaigns_handler(message: Message):
    campaigns = await CampaignService.get_all_campaigns()
    text = _build_campaigns_list_text(campaigns)
    await message.answer(text, reply_markup=campaigns_menu_keyboard() if not campaigns else campaigns_list_keyboard(campaigns), parse_mode="HTML")

# #FIXED: Seal Logic Leakage (No Data Lookups in the Mouth)
# Replaced in-memory generator loop with direct Service call.
@router.message(F.text.startswith("🎯 ") & ~F.text.in_({"🎯 Campaigns"}), StateFilter("*"))
async def manage_campaign_click(message: Message, state: FSMContext):
    campaign_name = message.text.replace("🎯 ", "").strip()

    campaign = await CampaignService.get_campaign_by_name(campaign_name)
    if not campaign:
        await message.answer("Campaign not found.")
        return

    # Store current campaign ID in FSM state so child handlers (templates, targets, controls) know context
    await state.update_data(current_campaign_id=campaign["id"])

    # #FIXED: Reclaim summary metadata rendering
    # Service returns a dict. Mouth renders it via build_campaign_summary_text().
    summary = await CampaignService.get_campaign_summary(campaign["id"])
    if not summary:
        await message.answer("Campaign not found.")
        return

    text = build_campaign_summary_text(summary)
    await message.answer(text, reply_markup=manage_campaign_keyboard(campaign["status"]), parse_mode="HTML")

# ==========================================
# SCHEDULER CONTROLS (Start / Pause / Stop)
# ==========================================

#FIXED: Remove hardcoded status leakage from the Mouth.
# WHAT WAS ADJUSTED: Removed hardcoded "running" string from manage_campaign_keyboard() argument.
# PREVENTED FAILURE: The Mouth was assuming the new status instead of reading the true DB state.
# SchedulerService now returns (success, msg, actual_status). The Mouth passes that status to the
# keyboard builder — it never guesses or caches what the status should be.
@router.message(F.text == "▶ Start Campaign", StateFilter("*"))
async def start_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("No campaign selected. Go back and select a campaign.")
        return
    
    success, msg, actual_status = await SchedulerService.start_campaign(campaign_id)
    
    if success:
        await message.answer(f"▶ {msg}", reply_markup=manage_campaign_keyboard(actual_status))
    else:
        await message.answer(f"❌ Cannot start: {msg}", reply_markup=manage_campaign_keyboard(actual_status))

#FIXED: Remove hardcoded status leakage from the Mouth.
# WHAT WAS ADJUSTED: Removed hardcoded "paused" string from manage_campaign_keyboard() argument.
# PREVENTED FAILURE: Same class of violation as start handler — status must be read from service payload.
@router.message(F.text == "⏸ Pause Campaign", StateFilter("*"))
async def pause_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("No campaign selected.")
        return
    
    success, msg, actual_status = await SchedulerService.pause_campaign(campaign_id)
    
    if success:
        await message.answer(f"⏸ {msg}", reply_markup=manage_campaign_keyboard(actual_status))
    else:
        await message.answer(f"❌ {msg}", reply_markup=manage_campaign_keyboard(actual_status))

#FIXED: Remove hardcoded status leakage from the Mouth.
# WHAT WAS ADJUSTED: Removed hardcoded "stopped" string from manage_campaign_keyboard() argument.
# PREVENTED FAILURE: Same class of violation — keyboard status driven entirely by DB truth, not assumptions.
@router.message(F.text == "🛑 Stop Campaign", StateFilter("*"))
async def stop_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("No campaign selected.")
        return
    
    success, msg, actual_status = await SchedulerService.stop_campaign(campaign_id)
    
    if success:
        await message.answer(f"🛑 {msg}", reply_markup=manage_campaign_keyboard(actual_status))
    else:
        await message.answer(f"❌ {msg}", reply_markup=manage_campaign_keyboard(actual_status))

# ==========================================
# DELETE CAMPAIGN
# ==========================================

@router.message(F.text.startswith("🗑 Delete Camp "), StateFilter("*"))
async def delete_campaign_prompt(message: Message):
    try:
        campaign_id = int(message.text.replace("🗑 Delete Camp ", "").strip())
    except ValueError:
        await message.answer("Invalid campaign ID format.")
        return

    # #FIXED: Migrate the delete status guard down into the Service layer.
    # The Mouth receives the verdict — it does not evaluate status logic.
    can_delete, status = await CampaignService.verify_campaign_deletable(campaign_id)
        
    if not can_delete:
        if status == "not_found":
            await message.answer("Campaign not found.")
        else:
            await message.answer(f"Cannot delete a campaign with status '{status}'. Only drafts can be deleted.")
        return
        
    campaign = await CampaignService.get_campaign_by_id(campaign_id)
    if campaign:
        await message.answer(
            f"Are you sure you want to delete campaign <b>{safe_html(campaign['name'])}</b>? This cannot be undone.",
            reply_markup=confirm_campaign_delete_keyboard(campaign_id),
            parse_mode="HTML"
        )

# #FIXED: Atomic Single-Signal Return for Actions
# delete_campaign returns the fresh list[dict] directly — no secondary fetch needed.
@router.message(F.text.startswith("✅ Yes, Delete Camp "), StateFilter("*"))
async def confirm_campaign_delete_handler(message: Message):
    try:
        campaign_id = int(message.text.replace("✅ Yes, Delete Camp ", "").strip())
    except ValueError:
        await message.answer("Invalid campaign ID format.")
        return

    deleted, msg, fresh_campaigns = await CampaignService.delete_campaign(campaign_id)
        
    if deleted:
        await message.answer("✅ Deleted.")
    else:
        await message.answer(f"❌ Failed to delete campaign: {msg}")
        
    text = _build_campaigns_list_text(fresh_campaigns)
    await message.answer(text, reply_markup=campaigns_menu_keyboard() if not fresh_campaigns else campaigns_list_keyboard(fresh_campaigns), parse_mode="HTML")
