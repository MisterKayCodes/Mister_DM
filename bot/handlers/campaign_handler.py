from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from bot.states.campaign_states import AddCampaignStates
from bot.keyboards.campaign_keyboards import (
    campaigns_menu_keyboard,
    select_account_keyboard,
    campaigns_list_keyboard,
    confirm_campaign_delete_keyboard
)
from data.repositories.campaign_repo import add_campaign, get_all_campaigns, delete_campaign, get_campaign_by_id
from data.repositories.account_repo import get_all_accounts
from data.database import AsyncSessionLocal

router = Router()

@router.message(F.text.in_({"🎯 Campaigns", "⬅️ Back to Campaigns"}))
async def campaigns_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎯 Campaigns Menu\nManage your outreach campaigns.",
        reply_markup=campaigns_menu_keyboard()
    )

@router.message(F.text == "➕ Add Campaign")
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
    
    # Load accounts for selection
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
        
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
    
    # Find the account ID
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
        
    account = next((a for a in accounts if a.name == account_name), None)
    if not account:
        await message.answer("Account not found. Please try again.")
        return
        
    data = await state.get_data()
    campaign_name = data.get("name")
    
    async with AsyncSessionLocal() as session:
        success, msg = await add_campaign(session, campaign_name, account.id)
        
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

@router.message(F.text == "📋 List Campaigns")
async def list_campaigns_handler(message: Message):
    async with AsyncSessionLocal() as session:
        campaigns = await get_all_campaigns(session)
    
    if not campaigns:
        text = "No campaigns found."
        await message.answer(text, reply_markup=campaigns_menu_keyboard())
        return

    text = "📋 Your Campaigns:\n\n"
    for camp in campaigns:
        date_str = camp.created_at.strftime('%Y-%m-%d') if camp.created_at else "Unknown"
        acc_name = camp.account.name if camp.account else "Unknown"
        text += f"**#{camp.id} - {camp.name}**\n"
        text += f"Account: {acc_name}\n"
        text += f"Status: {camp.status}\n"
        text += f"Created: {date_str}\n\n"
    
    await message.answer(text, reply_markup=campaigns_list_keyboard(campaigns), parse_mode="Markdown")

@router.message(F.text.startswith("🗑 Delete Camp "))
async def delete_campaign_prompt(message: Message):
    try:
        campaign_id = int(message.text.replace("🗑 Delete Camp ", "").strip())
    except ValueError:
        await message.answer("Invalid campaign ID format.")
        return

    async with AsyncSessionLocal() as session:
        campaign = await get_campaign_by_id(session, campaign_id)
        
    if not campaign:
        await message.answer("Campaign not found.")
        return
        
    if campaign.status != "draft":
        await message.answer(f"Cannot delete a campaign with status '{campaign.status}'. Only drafts can be deleted.")
        return
        
    await message.answer(
        f"Are you sure you want to delete campaign **{campaign.name}**? This cannot be undone.",
        reply_markup=confirm_campaign_delete_keyboard(campaign_id),
        parse_mode="Markdown"
    )

@router.message(F.text.startswith("✅ Yes, Delete Camp "))
async def confirm_campaign_delete_handler(message: Message):
    try:
        campaign_id = int(message.text.replace("✅ Yes, Delete Camp ", "").strip())
    except ValueError:
        await message.answer("Invalid campaign ID format.")
        return

    async with AsyncSessionLocal() as session:
        deleted, msg = await delete_campaign(session, campaign_id)
        
    if deleted:
        await message.answer("✅ Deleted.")
    else:
        await message.answer(f"❌ Failed to delete campaign: {msg}")
        
    # Refresh list
    await list_campaigns_handler(message)

@router.message(F.text.startswith("🎯 "))
async def ignore_campaign_click(message: Message):
    await message.answer("Use the delete button next to the name to manage this campaign, or use the menu.")
