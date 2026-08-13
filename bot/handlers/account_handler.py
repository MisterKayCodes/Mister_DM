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
from services.account_service import AccountService
from services.telethon_client import verify_session
from services.reply_listener_service import ReplyListenerService
from utils.string_utils import generate_safe_filename
from utils.telegram_utils import safe_html

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
    await message.answer("Please paste the Telethon StringSession for this account:")
    await state.set_state(AddAccountStates.waiting_for_session_string)

@router.message(AddAccountStates.waiting_for_session_string)
async def process_session_string(message: Message, state: FSMContext):
    session_string = message.text.strip()
    if not session_string:
        await message.answer("Session string cannot be empty. Please try again:")
        return
    await state.update_data(session_string=session_string)
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
    session_string = data.get("session_string")
    
    # Save the max delay in state in case we need to retry validation
    await state.update_data(delay_max=delay_max)
    
    await _validate_and_save_account(message, state, session_string, name, delay_min, delay_max)

@router.message(AddAccountStates.waiting_for_session_retry)
async def process_session_retry(message: Message, state: FSMContext):
    session_string = message.text.strip()
    if not session_string:
        await message.answer("Session string cannot be empty. Please try again:")
        return
        
    await state.update_data(session_string=session_string)
    data = await state.get_data()
    
    await _validate_and_save_account(
        message, state, 
        session_string, data.get("name"), data.get("delay_min"), data.get("delay_max")
    )

async def _validate_and_save_account(message: Message, state: FSMContext, session_string: str, name: str, delay_min: int, delay_max: int):
    """Helper to validate session and save account, handling the explicit retry state."""
    
    # 1. Validate Session
    status_msg = await message.answer("⏳ Validating session... Please wait.")
    
    is_valid, error_reason = await verify_session(session_string)
    
    if not is_valid:
        # This is 100% fine because it does NOT have a reply_markup!
        await status_msg.edit_text(
            f"❌ <b>Session validation failed</b>\n\n"
            f"Reason:\n<code>{error_reason}</code>\n\n"
            f"Please send another session string:",
            parse_mode="HTML"
        )
        await state.set_state(AddAccountStates.waiting_for_session_retry)
        return
        
    # 2. Save Account
    success, msg = await AccountService.add_account(name, session_string, delay_min, delay_max)
        
    if success:
        # #FIXED: Dynamically spawn background listener.
        # WHY: When a user creates an account, they shouldn't have to restart the bot to track replies.
        # We fetch the fresh account from DB to get the assigned ID, then boot its listener instantly.
        account = await AccountService.get_account_by_name(name)
        if account:
            await ReplyListenerService.start_listener(account)
            
        await status_msg.delete()
        await message.answer(
            f"✅ Session verified.\n✅ Account saved! ({name} | {delay_min}–{delay_max} mins)",
            reply_markup=accounts_menu_keyboard()
        )
        await state.clear()
    else:
        await status_msg.delete()
        await message.answer(
            f"❌ Failed to save to database: {msg}\nPlease choose a different name or go back:",
            reply_markup=accounts_menu_keyboard()
        )
        await state.clear()

# ==========================================
# ACCOUNT MANAGEMENT (LIST & DELETE)
# ==========================================

@router.message(F.text == "📋 List Accounts", StateFilter(None))
async def list_accounts_handler(message: Message):
    accounts = await AccountService.get_all_accounts()
    
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

    account = await AccountService.get_account_by_id(account_id)
        
    if not account:
        await message.answer("Account not found.")
        return
        
    await message.answer(
        f"Are you sure you want to delete <b>{safe_html(account['name'])}</b>? This cannot be undone.",
        reply_markup=confirm_delete_keyboard(account_id),
        parse_mode="HTML"
    )

# #FIXED: Merged the delete database operation and the accounts-refresh call into a single `async with` context block.
# WHAT WOULD HAVE HAPPENED: Opening and closing two independent sessions inside a fraction of a second 
# introduces connection pool thrashing and could result in transactional race conditions or SQLite database locks.
# #FIXED: Upgraded confirm_delete_handler to prevent multi-call coordination mutations inside the Mouth.
# WHAT WOULD HAVE HAPPENED: If the handler invoked `AccountService.delete_account` and then immediately 
# called `AccountService.get_all_accounts`, it creates a race condition where the UI layer (the Mouth) 
# is orchestrating state tracking. By returning `(success, msg, fresh_accounts_list)` atomically from 
# the Service (the Nerves), we guarantee the returned state perfectly matches the database transaction boundary.
@router.message(F.text.startswith("✅ Yes, Delete Acc "), StateFilter(None))
async def confirm_delete_handler(message: Message):
    try:
        account_id = int(message.text.replace("✅ Yes, Delete Acc ", "").strip())
    except ValueError:
        await message.answer("Invalid account ID format.")
        return

    deleted, msg, accounts = await AccountService.delete_account(account_id)
    
    if deleted:
        # #FIXED: Dynamically kill background listener.
        # WHY: To prevent memory leaks and zombie Telegram connections running for a deleted account.
        await ReplyListenerService.stop_listener(account_id)
        
        await message.answer(f"✅ Account deleted successfully.")
    else:
        await message.answer(f"❌ Failed to delete account: {msg}")
        
    text = "📋 Your Accounts:" if accounts else "No accounts found."
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

# #FIXED: Changed text rule from absolute exact match F.text == "❌ Cancel" to a prefix match `.startswith()`.
# WHAT WOULD HAVE HAPPENED: If your dynamic confirmation markup sets up a dynamic cancel button 
# containing an entity tag (e.g., "❌ Cancel (ID: 5)"), clicking it would cause the bot to ignore 
# the click entirely, freezing the user out of canceling their execution.
@router.message(F.text.startswith("❌ Cancel"), StateFilter(None))
async def cancel_delete_handler(message: Message):
    accounts = await AccountService.get_all_accounts()
        
    text = "📋 Your Accounts:" if accounts else "No accounts found."
    await message.answer(text, reply_markup=accounts_list_keyboard(accounts))

# #FIXED: Added `StateFilter(None)` explicitly to this fallback interceptor.
# WHAT WOULD HAVE HAPPENED (The Campaign Problem): When selecting an account via an active campaign wizard 
# (e.g., picking "📧 Trading Outreach"), this filter would blindly hijack the string message payload 
# and prompt the user to use the delete buttons instead of letting the Campaign wizard ingest it.
@router.message(F.text.startswith("📧 "), StateFilter(None))
async def ignore_email_click(message: Message):
    await message.answer("Use the delete button next to the name to manage this account, or use the menu.")
