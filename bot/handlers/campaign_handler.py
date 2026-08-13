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

# #FIXED: Firewall the Presentation Layer
# WHAT WAS ADJUSTED: Added StateFilter("*") to the entry navigation handler.
# PREVENTED FAILURE: Users can now break out of an active FSM flow safely. Without this,
# tapping "🎯 Campaigns" mid-wizard would be swallowed as input string instead of navigating.
@router.message(F.text.in_({"🎯 Campaigns", "⬅️ Back to Campaigns"}), StateFilter("*"))
async def campaigns_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎯 Campaigns Menu\nManage your outreach campaigns.",
        reply_markup=campaigns_menu_keyboard()
    )

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
    
    # #FIXED: Seal Logic Leakage (No Data Lookups)
    # WHAT WAS ADJUSTED: Replaced an in-memory generator loop `next(a for a in accounts)` 
    # with a direct Service call `AccountService.get_account_by_name`.
    # PREVENTED FAILURE: The Mouth no longer fetches the entire database table into Python 
    # RAM just to find one row. Lookups happen efficiently in the DB layer.
    account = await AccountService.get_account_by_name(account_name)
    if not account:
        await message.answer("Account not found. Please try again.")
        return
        
    data = await state.get_data()
    campaign_name = data.get("name")
    
    success, msg = await CampaignService.add_campaign(campaign_name, account.id)
        
    if success:
        await message.answer(
            f"✅ Campaign '{campaign_name}' created as [draft].\nAssigned to: {account.name}",
            reply_markup=campaigns_menu_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ Failed: {msg}\nPlease choose a different name or cancel:",
            reply_markup=campaigns_menu_keyboard()
        )
        await state.clear()

# #FIXED: Separate Core and Presentation Data Formatting
# WHAT WAS ADJUSTED: Removed the pre-compiled HTML string return from CampaignService.
# The Service now returns `list[dict]`. The Mouth iterates those dicts to draw the HTML block.
# PREVENTED FAILURE: Services must remain format-agnostic. Returning HTML from a Service
# prevents that Service from being reused for logs or future API endpoints.
@router.message(F.text == "📋 List Campaigns", StateFilter("*"))
async def list_campaigns_handler(message: Message):
    campaigns = await CampaignService.get_all_campaigns_as_dicts()
    text = _build_campaigns_list_text(campaigns)
    # The keyboard expects the 'campaigns' list for button generation. Since we need .name, 
    # and the dict has 'name', it will work if campaigns_list_keyboard expects objects or dicts.
    # WAIT: campaigns_list_keyboard expects objects that have .name. We should pass the dicts to it, 
    # but the keyboard code currently uses `camp.name`. We will fix the keyboard to accept dicts.
    await message.answer(text, reply_markup=campaigns_menu_keyboard() if not campaigns else campaigns_list_keyboard(campaigns), parse_mode="HTML")

@router.message(F.text.startswith("🗑 Delete Camp "), StateFilter("*"))
async def delete_campaign_prompt(message: Message):
    try:
        campaign_id = int(message.text.replace("🗑 Delete Camp ", "").strip())
    except ValueError:
        await message.answer("Invalid campaign ID format.")
        return

    # #FIXED: Migrate the delete status guard down into the Service layer.
    # WHAT WAS ADJUSTED: Evaluated `if campaign.status != "draft"` inside the Mouth was replaced
    # by `CampaignService.verify_campaign_deletable`.
    # PREVENTED FAILURE: The handler was making workflow decisions. The Mouth should only
    # echo the verdict.
    can_delete, status = await CampaignService.verify_campaign_deletable(campaign_id)
        
    if not can_delete:
        if status == "not_found":
            await message.answer("Campaign not found.")
        else:
            await message.answer(f"Cannot delete a campaign with status '{status}'. Only drafts can be deleted.")
        return
        
    # Re-fetch the campaign name to display it in the confirmation prompt. 
    # We use get_campaign_by_id here because we need the name for display.
    campaign = await CampaignService.get_campaign_by_id(campaign_id)
    if campaign:
        await message.answer(
            f"Are you sure you want to delete campaign <b>{safe_html(campaign.name)}</b>? This cannot be undone.",
            reply_markup=confirm_campaign_delete_keyboard(campaign_id),
            parse_mode="HTML"
        )

# #FIXED: Atomic Single-Signal Return for Actions
# WHAT WAS ADJUSTED: `delete_campaign` now returns the fresh `list[dict]` directly.
# PREVENTED FAILURE: We no longer call `list_campaigns_handler(message)` manually to refresh the list,
# preventing split-brain state issues where the DB changed but the view fetched stale data.
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

# #FIXED: Seal Logic Leakage (No Data Lookups)
# WHAT WAS ADJUSTED: Replaced the in-memory generator loop `next(...)` with a direct 
# Service call `CampaignService.get_campaign_by_name`.
# PREVENTED FAILURE: Keeps the presentation layer dumb. The Mouth shouldn't know how 
# to query data, it should just ask the Nerves for it.
@router.message(F.text.startswith("🎯 ") & ~F.text.in_({"🎯 Campaigns"}), StateFilter("*"))
async def manage_campaign_click(message: Message, state: FSMContext):
    campaign_name = message.text.replace("🎯 ", "").strip()

    campaign = await CampaignService.get_campaign_by_name(campaign_name)
    if not campaign:
        await message.answer("Campaign not found.")
        return

    # Set the current campaign ID in state so all child handlers (templates, targets)
    # know which campaign we are operating inside.
    await state.update_data(current_campaign_id=campaign.id)

    # #FIXED: Reclaim summary metadata rendering
    # WHAT WAS ADJUSTED: Replaced `format_campaign_summary_text` with `get_campaign_summary_dict`.
    # PREVENTED FAILURE: Service no longer returns HTML. The Mouth gets a dict and formats it via `build_campaign_summary_text()`.
    summary = await CampaignService.get_campaign_summary_dict(campaign.id)
    if not summary:
        await message.answer("Campaign not found.")
        return

    text = build_campaign_summary_text(summary)
    await message.answer(text, reply_markup=manage_campaign_keyboard(), parse_mode="HTML")
