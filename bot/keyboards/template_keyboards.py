from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def manage_campaign_keyboard(status: str = "draft") -> ReplyKeyboardMarkup:
    """Status-aware keyboard for managing a specific campaign."""
    keyboard = [
        [
            KeyboardButton(text="➕ Add Template"),
            KeyboardButton(text="📋 View Templates")
        ],
        [
            KeyboardButton(text="👥 Add Targets"),
            KeyboardButton(text="👀 View Targets")
        ],
    ]
    
    # Scheduler controls — shown based on campaign status
    if status == "running":
        keyboard.append([
            KeyboardButton(text="⏸ Pause Campaign"),
            KeyboardButton(text="🛑 Stop Campaign")
        ])
    elif status in ("draft", "paused", "stopped"):
        keyboard.append([
            KeyboardButton(text="▶ Start Campaign")
        ])
    # completed: no start/pause/stop shown
    
    keyboard.append([
        KeyboardButton(text="🗑 Clear Targets"),
        KeyboardButton(text="🗑 Delete Campaign")
    ])
    keyboard.append([
        KeyboardButton(text="⬅️ Back to Campaigns")
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
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
