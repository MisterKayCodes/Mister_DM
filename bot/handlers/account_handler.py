from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter  # Added for state restrictions
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

# ==========================================
# NAVIGATION & GLOBAL HANDLERS
# ==========================================

# #FIXED: Added StateFilter("*") to the navigation commands below.
# WHAT WOULD HAVE HAPPENED: If a user clicked "🏠 Main Menu" or "⬅️ Back to Accounts" 
# while inside a multi-step form wizard (like typing an account name), the bot 
# would completely ignore the navigation intent and process the button text as form input.
@router.message(F.text == "/start", StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Welcome to Mister DM.\nSelect an option below:",
        reply_markup=main_menu_keyboard()
    )

@router.message(F.text.in_({"⬅️ Back to Main", "🏠 Main Menu"}), StateFilter("*"))
async def main_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Main Menu:",
        reply_markup=main_menu_keyboard()
    )

@router.message(F.text.in_({"👥 Targets", "💬 Replies", "🏷 Pain Points", "📊 Stats", "⚙ Settings"}), StateFilter("*"))
async def coming_soon_handler(message: Message):
    await message.answer("Coming soon 🚧")

@router.message(F.text.in_({"📱 Accounts", "⬅️ Back to Accounts"}), StateFilter("*"))
async def accounts_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📱 Accounts Menu\nManage your Telegram outreach accounts.",
        reply_markup=accounts_menu_keyboard()
    )

# ==========================================
# ADD ACCOUNT WIZARD (FSM)
# ==========================================

@router.message(F.text.in_({"➕ Add Account", "➕ Add New"}), StateFilter(None))
async def add_account_start(message: Message, state: FSMContext):
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
        await state.clear()

# ==========================================
# ACCOUNT MANAGEMENT (LIST & DELETE)
# ==========================================

@router.message(F.text == "📋 List Accounts", StateFilter(None))
async def list_accounts_handler(message: Message):
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
    
    text = "📋 Your Accounts:" if accounts else "No accounts found."
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

# #FIXED: Changed filter from "🗑 Delete " to "🗑 Delete Acc " to prevent collision with Campaign delete buttons.
# WHAT WOULD HAVE HAPPENED: When a user clicked "🗑 Delete Camp 1", this handler would intercept it, 
# try to parse "Camp 1" as an integer, and crash with an "Invalid account ID format" error.
@router.message(F.text.startswith("🗑 Delete Acc "), StateFilter(None))
async def delete_account_prompt(message: Message):
    try:
        account_id = int(message.text.replace("🗑 Delete Acc ", "").strip())
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

# #FIXED: Merged the delete database operation and the accounts-refresh call into a single `async with` context block.
# WHAT WOULD HAVE HAPPENED: Opening and closing two independent sessions inside a fraction of a second 
# introduces connection pool thrashing and could result in transactional race conditions or SQLite database locks.
# #FIXED: Changed filter from "✅ Yes, Delete " to "✅ Yes, Delete Acc " to prevent collision with Campaign confirm buttons.
# WHAT WOULD HAVE HAPPENED: If a user clicked "✅ Yes, Delete Camp 1", this handler would intercept it,
# try to parse "Camp 1" as an integer, and crash with an "Invalid account ID format" error.
@router.message(F.text.startswith("✅ Yes, Delete Acc "), StateFilter(None))
async def confirm_delete_handler(message: Message):
    try:
        account_id = int(message.text.replace("✅ Yes, Delete Acc ", "").strip())
    except ValueError:
        await message.answer("Invalid account ID format.")
        return

    async with AsyncSessionLocal() as session:
        deleted, msg = await delete_account(session, account_id)
        
        if deleted:
            await message.answer("✅ Deleted.")
        else:
            await message.answer(f"❌ Failed to delete account: {msg}")
            
        accounts = await get_all_accounts(session)
        
    text = "📋 Your Accounts:" if accounts else "No accounts found."
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

# #FIXED: Changed text rule from absolute exact match F.text == "❌ Cancel" to a prefix match `.startswith()`.
# WHAT WOULD HAVE HAPPENED: If your dynamic confirmation markup sets up a dynamic cancel button 
# containing an entity tag (e.g., "❌ Cancel (ID: 5)"), clicking it would cause the bot to ignore 
# the click entirely, freezing the user out of canceling their execution.
@router.message(F.text.startswith("❌ Cancel"), StateFilter(None))
async def cancel_delete_handler(message: Message):
    async with AsyncSessionLocal() as session:
        accounts = await get_all_accounts(session)
        
    text = "📋 Your Accounts:" if accounts else "No accounts found."
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

# #FIXED: Added `StateFilter(None)` explicitly to this fallback interceptor.
# WHAT WOULD HAVE HAPPENED (The Campaign Problem): When selecting an account via an active campaign wizard 
# (e.g., picking "📧 Trading Outreach"), this filter would blindly hijack the string message payload 
# and prompt the user to use the delete buttons instead of letting the Campaign wizard ingest it.
@router.message(F.text.startswith("📧 "), StateFilter(None))
async def ignore_email_click(message: Message):
    await message.answer("Use the delete button next to the name to manage this account, or use the menu.")
