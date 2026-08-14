from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def pain_selection_keyboard(tags: list[dict], target_id: int) -> InlineKeyboardMarkup:
    """Keyboard for selecting a pain tag to assign."""
    keyboard = []
    for tag in tags:
        keyboard.append([InlineKeyboardButton(text=f"{tag['display_name']}", callback_data=f"selectpain_{tag['id']}")])
        
    keyboard.append([InlineKeyboardButton(text="➕ Create New Pain Point", callback_data="create_new_pain")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Cancel", callback_data=f"profile_{target_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def pain_dashboard_keyboard(tags: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard for the main pain points dashboard."""
    keyboard = [[InlineKeyboardButton(text="🏷 Tag a User directly", callback_data="quick_tag_user")]]
    
    for tag in tags:
        keyboard.append([InlineKeyboardButton(text=f"{tag['display_name']} ({tag['count']})", callback_data=f"viewpain_{tag['id']}")])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_pain_dash_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Dashboard", callback_data="back_to_pain_dash")]
    ])
