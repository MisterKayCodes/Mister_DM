from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from bot.states.template_states import AddTemplateStates
from bot.keyboards.template_keyboards import (
    manage_campaign_keyboard,
    templates_list_keyboard,
    confirm_template_delete_keyboard
)
from bot.keyboards.campaign_keyboards import campaigns_menu_keyboard
from data.repositories.template_repo import add_template, get_templates_by_campaign, delete_template
from data.repositories.campaign_repo import get_campaign_by_id, get_all_campaigns
from data.database import AsyncSessionLocal

router = Router()

@router.message(F.text == "⬅️ Back to Campaign")
async def back_to_campaign_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return
        
    async with AsyncSessionLocal() as session:
        campaign = await get_campaign_by_id(session, campaign_id)
        
    if not campaign:
        await message.answer("Campaign not found. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return
        
    templates_count = len(campaign.templates) if campaign.templates else 0
    targets_count = 0  # Placeholder for Phase 4
    
    text = (
        f"Managing Campaign:\n**{campaign.name}**\n\n"
        f"Status: {campaign.status.capitalize()}\n\n"
        f"Templates: {templates_count}\n"
        f"Targets: {targets_count}\n"
        f"Replies: Coming Soon\n"
    )
    
    await message.answer(text, reply_markup=manage_campaign_keyboard(), parse_mode="Markdown")

@router.message(F.text == "➕ Add Template")
async def add_template_start(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return
        
    await message.answer(
        "Send me the message content for this template.\n(Variables like {first_name} coming soon)\n\n"
        "Send '❌ Cancel' to cancel.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddTemplateStates.waiting_for_content)

@router.message(AddTemplateStates.waiting_for_content)
async def process_template_content(message: Message, state: FSMContext):
    content = message.text.strip()
    if content == "❌ Cancel":
        await state.set_state(None) # clear state but keep data
        await back_to_campaign_handler(message, state)
        return
        
    if not content:
        await message.answer("Template cannot be empty. Please send the message text:")
        return
        
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    
    async with AsyncSessionLocal() as session:
        success, msg = await add_template(session, campaign_id, content)
        
    if success:
        await message.answer("✅ Template saved!", reply_markup=manage_campaign_keyboard())
    else:
        await message.answer(f"❌ Failed: {msg}", reply_markup=manage_campaign_keyboard())
        
    await state.set_state(None)

@router.message(F.text == "📋 View Templates")
async def view_templates_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return
        
    async with AsyncSessionLocal() as session:
        templates = await get_templates_by_campaign(session, campaign_id)
        
    if not templates:
        await message.answer("No templates found for this campaign.", reply_markup=manage_campaign_keyboard())
        return
        
    text = "📋 Templates for this Campaign:\n\n"
    for tpl in templates:
        text += f"**[Template #{tpl.id}]**\n{tpl.content}\n\n"
        
    await message.answer(text, reply_markup=templates_list_keyboard(templates), parse_mode="Markdown")

@router.message(F.text.startswith("🗑 Delete Tpl "))
async def delete_template_prompt(message: Message):
    try:
        template_id = int(message.text.replace("🗑 Delete Tpl ", "").strip())
    except ValueError:
        await message.answer("Invalid template ID format.")
        return
        
    await message.answer(
        f"Are you sure you want to delete Template #{template_id}? This cannot be undone.",
        reply_markup=confirm_template_delete_keyboard(template_id)
    )

@router.message(F.text.startswith("✅ Yes, Delete Tpl "))
async def confirm_template_delete_handler(message: Message, state: FSMContext):
    try:
        template_id = int(message.text.replace("✅ Yes, Delete Tpl ", "").strip())
    except ValueError:
        await message.answer("Invalid template ID format.")
        return
        
    async with AsyncSessionLocal() as session:
        deleted, msg = await delete_template(session, template_id)
        
    if deleted:
        await message.answer("✅ Deleted.")
    else:
        await message.answer(f"❌ Failed to delete template: {msg}")
        
    # Refresh list
    await view_templates_handler(message, state)

@router.message(F.text == "❌ Cancel", StateFilter(None))
async def cancel_template_delete(message: Message, state: FSMContext):
    # This will catch the cancel from the delete confirmation
    await view_templates_handler(message, state)
