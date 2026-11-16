from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """The simplified 4-pillar main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Find People"),
                KeyboardButton(text="📤 Ready to Send")
            ],
            [
                KeyboardButton(text="💬 Inbox"),
                KeyboardButton(text="⚙️ Settings")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def settings_menu_keyboard() -> ReplyKeyboardMarkup:
    """The Settings & Tools sub-menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛡️ Outreach Safety"),
                KeyboardButton(text="📱 Fleet & Sessions")
            ],
            [
                KeyboardButton(text="📊 Stats"),
                KeyboardButton(text="🚫 Blacklist")
            ],
            [
                KeyboardButton(text="⚡ API Usage"),
                KeyboardButton(text="⬅️ Back to Main")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def accounts_menu_keyboard() -> ReplyKeyboardMarkup:
    """The Fleet & Sessions status menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Refresh Fleet Status")
            ],
            [
                KeyboardButton(text="⬅️ Back to Main")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# For dynamic lists with delete buttons, you have two options:

# Option 1: Use ReplyKeyboard with delete buttons as separate rows
def accounts_list_keyboard(accounts: list) -> ReplyKeyboardMarkup:
    """Accounts list with delete options using ReplyKeyboard."""
    keyboard = []
    
    # Add each account with a delete button in the same row
    # #FIXED: Swapped object dot-notation for dictionary key bracket lookups to prevent AttributeError crashes.
    for acc in accounts:
        keyboard.append([
            KeyboardButton(text=f"📧 {acc['name']}"),
            KeyboardButton(text=f"🗑 Delete Acc {acc['id']}")
        ])
        

    # Add navigation options
    keyboard.append([
        KeyboardButton(text="⬅️ Back to Accounts"),
        KeyboardButton(text="🏠 Main Menu")
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# Option 2: Use a simpler approach with numbered accounts
def accounts_list_simple_keyboard(accounts: list) -> ReplyKeyboardMarkup:
    """Simpler accounts list showing names only."""
    keyboard = []
    
    # Show accounts in rows of 2
    row = []
    for i, acc in enumerate(accounts):
        row.append(KeyboardButton(text=f"📧 {acc['name']}"))
        if len(row) == 2:  # 2 columns
            keyboard.append(row)
            row = []
    if row:  # Add remaining
        keyboard.append(row)
    
    # Add management options
    keyboard.append([
        KeyboardButton(text="➕ Add New"),
        KeyboardButton(text="🗑 Delete Account")
    ])
    keyboard.append([
        KeyboardButton(text="⬅️ Back to Accounts"),
        KeyboardButton(text="🏠 Main Menu")
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# For confirmation, ReplyKeyboard works differently
# You'll need to use a state-based approach instead
def confirm_delete_keyboard(account_id: int) -> ReplyKeyboardMarkup:
    """Confirmation using ReplyKeyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=f"✅ Yes, Delete Acc {account_id}"),
                KeyboardButton(text="❌ Cancel")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True  # Disappears after one use
    )