from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from bot.states.account_states import AddAccountStates
from bot.keyboards.account_keyboards import (
    main_menu_keyboard,
    accounts_menu_keyboard,
    accounts_list_keyboard,
    confirm_delete_keyboard
)
from data.repositories.account_repo import add_account, get_all_accounts, delete_account, get_account_by_id
from data.database import AsyncSessionLocal
import re

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Welcome to Mister DM.\nSelect an option below:",
        reply_markup=main_menu_keyboard()
    )

@router.message(F.text.in_({"⬅️ Back to Main", "🏠 Main Menu"}))
async def main_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Main Menu:",
        reply_markup=main_menu_keyboard()
    )

@router.message(F.text.in_({"🎯 Campaigns", "👥 Targets", "💬 Replies", "🏷 Pain Points", "📊 Stats", "⚙ Settings"}))
async def coming_soon_handler(message: Message):
    await message.answer("Coming soon 🚧")

@router.message(F.text.in_({"📱 Accounts", "⬅️ Back to Accounts"}))
async def accounts_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📱 Accounts Menu\nManage your Telegram outreach accounts.",
        reply_markup=accounts_menu_keyboard()
    )

@router.message(F.text.in_({"➕ Add Account", "➕ Add New"}))
async def add_account_start(message: Message, state: FSMContext):
    # Use ReplyKeyboardRemove to keep the chat clean while filling out the form
    await message.answer("What should we call this account? (e.g. Forex Outreach)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddAccountStates.waiting_for_name)

@router.message(AddAccountStates.waiting_for_name)
async def process_account_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Name cannot be empty. Please enter a valid name:")
        return
    await state.update_data(name=name)
    await message.answer("Minimum delay between messages (in minutes):")
    await state.set_state(AddAccountStates.waiting_for_delay_min)

@router.message(AddAccountStates.waiting_for_delay_min)
async def process_delay_min(message: Message, state: FSMContext):
    try:
        delay_min = int(message.text.strip())
        if delay_min <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a valid positive integer for minimum delay:")
        return
    
    await state.update_data(delay_min=delay_min)
    await message.answer("Maximum delay between messages (in minutes):")
    await state.set_state(AddAccountStates.waiting_for_delay_max)

@router.message(AddAccountStates.waiting_for_delay_max)
async def process_delay_max(message: Message, state: FSMContext):
    try:
        delay_max = int(message.text.strip())
    except ValueError:
        await message.answer("Please enter a valid integer for maximum delay:")
        return
    
    data = await state.get_data()
    delay_min = data.get("delay_min")
    
    if delay_max <= delay_min:
        await message.answer(f"Maximum delay must be greater than minimum delay ({delay_min}). Try again:")
        return
    
    name = data.get("name")
    
    # Auto-generate session path based on name
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    session_path = f"sessions/{safe_name}.session"
    
    async with AsyncSessionLocal() as session:
        success, msg = await add_account(session, name, session_path, delay_min, delay_max)
        
    if success:
        await message.answer(
            f"✅ Account saved! ({name} | {delay_min}–{delay_max} mins)\nSession path: {session_path}",
            reply_markup=accounts_menu_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ Failed: {msg}\nPlease choose a different name or go back:",
            reply_markup=accounts_menu_keyboard()
        )
        await state.clear() # Clear state if it fails so keyboard works again

@router.message(F.text == "📋 List Accounts")
async def list_accounts_handler(message: Message):
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
    
    if not accounts:
        text = "No accounts found."
    else:
        text = "📋 Your Accounts:"
    
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

@router.message(F.text.startswith("🗑 Delete ") & ~F.text.in_({"🗑 Delete Account"}))
async def delete_account_prompt(message: Message):
    # Extract ID from text like "🗑 Delete 1"
    try:
        account_id = int(message.text.replace("🗑 Delete ", "").strip())
    except ValueError:
        await message.answer("Invalid account ID format.")
        return

    async with AsyncSessionLocal() as session:
        account = await get_account_by_id(session, account_id)
        
    if not account:
        await message.answer("Account not found.")
        return
        
    await message.answer(
        f"Are you sure you want to delete **{account.name}**? This cannot be undone.",
        reply_markup=confirm_delete_keyboard(account_id),
        parse_mode="Markdown"
    )

@router.message(F.text.startswith("✅ Yes, Delete "))
async def confirm_delete_handler(message: Message):
    try:
        account_id = int(message.text.replace("✅ Yes, Delete ", "").strip())
    except ValueError:
        await message.answer("Invalid account ID format.")
        return

    async with AsyncSessionLocal() as session:
        deleted = await delete_account(session, account_id)
        
    if deleted:
        await message.answer("✅ Deleted.")
    else:
        await message.answer("❌ Failed to delete account.")
        
    # Refresh list
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
        
    if not accounts:
        text = "No accounts found."
    else:
        text = "📋 Your Accounts:"
        
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

@router.message(F.text == "❌ Cancel")
async def cancel_delete_handler(message: Message):
    # Instead of deleting, just refresh the list
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
        
    if not accounts:
        text = "No accounts found."
    else:
        text = "📋 Your Accounts:"
        
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

@router.message(F.text.startswith("📧 "))
async def ignore_email_click(message: Message):
    # This handles clicking on the account name "📧 Forex Outreach" directly
    await message.answer("Use the delete button next to the name to manage this account, or use the menu.")
