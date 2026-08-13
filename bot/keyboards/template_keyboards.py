from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def manage_campaign_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for managing a specific campaign."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Add Template"),
                KeyboardButton(text="📋 View Templates")
            ],
            [
                KeyboardButton(text="👥 Add Targets"),
                KeyboardButton(text="📋 View Targets")
            ],
            [
                KeyboardButton(text="🗑 Delete Campaign"),
                KeyboardButton(text="⬅️ Back to Campaigns")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def templates_list_keyboard(templates: list) -> ReplyKeyboardMarkup:
    """Templates list with delete options."""
    keyboard = []
    
    # Add each template with a delete button
    # Since templates can be long, we just show "Tpl #ID" on the left 
    # and the delete button on the right
    for tpl in templates:
        keyboard.append([
            KeyboardButton(text=f"📄 Tpl {tpl.id}"),
            KeyboardButton(text=f"🗑 Delete Tpl {tpl.id}")
        ])
    
    # Add navigation options
    keyboard.append([
        KeyboardButton(text="⬅️ Back to Campaign"),
        KeyboardButton(text="🏠 Main Menu")
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def confirm_template_delete_keyboard(template_id: int) -> ReplyKeyboardMarkup:
    """Confirmation for deleting a template."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=f"✅ Yes, Delete Tpl {template_id}"),
                KeyboardButton(text="❌ Cancel")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
