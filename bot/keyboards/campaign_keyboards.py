from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from data.models.account import Account

def campaigns_menu_keyboard() -> ReplyKeyboardMarkup:
    """The campaigns menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Add Campaign"),
                KeyboardButton(text="📋 List Campaigns")
            ],
            [
                KeyboardButton(text="⬅️ Back to Main")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def select_account_keyboard(accounts: list[Account]) -> ReplyKeyboardMarkup:
    """Keyboard for selecting an account during campaign creation."""
    keyboard = []
    
    # Add each account as a button
    for acc in accounts:
        keyboard.append([KeyboardButton(text=f"📧 {acc.name}")])
        
    # Add cancel button
    keyboard.append([KeyboardButton(text="❌ Cancel Creation")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def campaigns_list_keyboard(campaigns: list) -> ReplyKeyboardMarkup:
    """Campaigns list with delete options."""
    keyboard = []
    
    # Add each campaign as a button to manage it
    for camp in campaigns:
        # Check if camp is a dict (new structure) or an object (old structure/fallback)
        name = camp["name"] if isinstance(camp, dict) else camp.name
        keyboard.append([
            KeyboardButton(text=f"🎯 {name}")
        ])
    
    # Add navigation options
    keyboard.append([
        KeyboardButton(text="⬅️ Back to Campaigns"),
        KeyboardButton(text="🏠 Main Menu")
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def confirm_campaign_delete_keyboard(campaign_id: int) -> ReplyKeyboardMarkup:
    """Confirmation for deleting a campaign."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=f"✅ Yes, Delete Camp {campaign_id}"),
                KeyboardButton(text="❌ Cancel")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
