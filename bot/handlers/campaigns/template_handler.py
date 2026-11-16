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
from services.campaigns import TemplateService, CampaignService
from utils.telegram_utils import safe_html
from bot.utils.ui_layouts import build_campaign_summary_text, build_templates_list_text

router = Router()


# #FIXED: Firewall the Presentation Layer — StateFilter("*") on back_to_campaign_handler.
# WHAT WAS ADJUSTED: Added StateFilter("*") so the Back button can tear down active FSM loops.
# PREVENTED FAILURE: Without this, pressing "⬅️ Back to Campaign" mid-wizard (e.g. while
# typing a template body) would feed the button text into the FSM as template content.
@router.message(F.text == "⬅️ Back to Campaign", StateFilter("*"))
async def back_to_campaign_handler(message: Message, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return

    # #FIXED: Eliminated repeated "Managing Campaign:" UI string block.
    # WHAT WAS ADJUSTED: Replaced the inline HTML string construction with a call to
    # `CampaignService.get_campaign_summary` and `build_campaign_summary_text`.
    # PREVENTED FAILURE: The same string was being built identically in campaign_handler.py,
    # template_handler.py, and target_handler.py. Any future formatting change (new field,
    # emoji update) would require hunting down every copy. One source of truth prevents drift.
    summary = await CampaignService.get_campaign_summary(campaign_id)
    if not summary:
        await message.answer("Campaign not found. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return

    text = build_campaign_summary_text(summary)
    await message.answer(text, reply_markup=manage_campaign_keyboard(), parse_mode="HTML")


@router.message(F.text == "➕ Add Template", StateFilter(None))
async def add_template_start(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return

    await message.answer(
        "📝 <b>ADD TEMPLATE(S)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Send a single message template, OR\n"
        "• Send multiple variations separated by <code>---</code> or <code>===</code>, OR\n"
        "• Upload a <b>.txt</b> file containing variations separated by <code>---</code>.\n\n"
        "<i>Variables available:</i> <code>{username}</code>, <code>{first_name}</code>\n"
        "Send '❌ Cancel' to return.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.set_state(AddTemplateStates.waiting_for_content)


def _split_template_variants(raw_text: str) -> list[str]:
    """Splits raw text by --- or === delimiters and strips whitespace."""
    import re
    # Split on lines with 3 or more dashes or equals signs
    parts = re.split(r'(?:\r?\n|^)\s*(?:-{3,}|={3,})\s*(?:\r?\n|$)', raw_text)
    return [p.strip() for p in parts if p.strip()]


@router.message(AddTemplateStates.waiting_for_content)
async def process_template_content(message: Message, state: FSMContext):
    # Support Cancel check
    if message.text and message.text.strip() == "❌ Cancel":
        await state.set_state(None)
        data = await state.get_data()
        campaign_id = data.get("current_campaign_id")
        summary = await CampaignService.get_campaign_summary(campaign_id)
        if summary:
            text = build_campaign_summary_text(summary)
            await message.answer(text, reply_markup=manage_campaign_keyboard(), parse_mode="HTML")
        else:
            await message.answer("Lost context.", reply_markup=campaigns_menu_keyboard())
        return

    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await state.set_state(None)
        await message.answer("Lost campaign context.", reply_markup=campaigns_menu_keyboard())
        return

    raw_text = ""
    # Case 1: Uploaded .txt document
    if message.document:
        doc = message.document
        if not (doc.file_name and doc.file_name.lower().endswith(".txt")):
            await message.answer("❌ Please upload a plain .txt file, or send the templates as a text message.")
            return

        bot = message.bot
        file_io = await bot.download(doc.file_id)
        raw_text = file_io.read().decode("utf-8", errors="ignore")
    # Case 2: Direct text message
    elif message.text:
        raw_text = message.text.strip()
    else:
        await message.answer("❌ Please send a text message or a .txt file.")
        return

    variants = _split_template_variants(raw_text)
    if not variants:
        await message.answer("❌ No valid template content found. Please send non-empty text:")
        return

    # Add single or bulk
    if len(variants) == 1:
        success, msg = await TemplateService.add_template(campaign_id, variants[0])
        count = 1 if success else 0
    else:
        success, msg, count = await TemplateService.add_templates_bulk(campaign_id, variants)

    if success:
        if count > 1:
            await message.answer(f"✅ <b>{count} Template Variants saved!</b>\nThe dispatcher will cycle through them round-robin.", reply_markup=manage_campaign_keyboard(), parse_mode="HTML")
        else:
            await message.answer("✅ Template saved!", reply_markup=manage_campaign_keyboard())
    else:
        await message.answer(f"❌ Failed: {msg}", reply_markup=manage_campaign_keyboard())

    await state.set_state(None)


# #FIXED: Firewall the Presentation Layer — StateFilter("*") on view_templates_handler.
# WHAT WAS ADJUSTED: Added StateFilter("*").
# PREVENTED FAILURE: Without this, "📋 View Templates" pressed mid-FSM would be captured
# as raw text input, silently discarded, and leave the user stranded in the FSM.
@router.message(F.text == "📋 View Templates", StateFilter("*"))
async def view_templates_handler(message: Message, state: FSMContext):
    await state.set_state(None)
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Returning to campaigns.", reply_markup=campaigns_menu_keyboard())
        return

    # #FIXED: Atomic Courier Retrieval — Mouth parses the returned array to build HTML.
    # WHAT WAS ADJUSTED: Service returns the raw template objects. The Mouth calls
    # `build_templates_list_text()` locally to render them into HTML.
    # PREVENTED FAILURE: If the Service pre-built the HTML, it would be coupled to Telegram's
    # presentation format, making it impossible to reuse for logs, exports, or other channels.
    templates = await TemplateService.get_templates_by_campaign(campaign_id)

    if not templates:
        await message.answer("No templates found for this campaign.", reply_markup=manage_campaign_keyboard())
        return

    text = build_templates_list_text(templates)
    await message.answer(text, reply_markup=templates_list_keyboard(templates), parse_mode="HTML")


@router.message(F.text.startswith("🗑 Delete Tpl "), StateFilter(None))
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


# #FIXED: Remove Multi-Call Handler Linking — atomic delete returns fresh template list.
# WHAT WAS ADJUSTED: `TemplateService.delete_template` now returns `(bool, str, list[Template])`.
# The handler no longer calls `await view_templates_handler(message, state)` to refresh.
# PREVENTED FAILURE: Calling a handler from another handler chains execution in ways that
# are hard to trace, test, and debug. It also creates a second DB round-trip where one is enough.
@router.message(F.text.startswith("✅ Yes, Delete Tpl "), StateFilter(None))
async def confirm_template_delete_handler(message: Message, state: FSMContext):
    try:
        template_id = int(message.text.replace("✅ Yes, Delete Tpl ", "").strip())
    except ValueError:
        await message.answer("Invalid template ID format.")
        return

    deleted, msg, fresh_templates = await TemplateService.delete_template(template_id)

    if deleted:
        await message.answer("✅ Deleted.")
    else:
        await message.answer(f"❌ Failed to delete template: {msg}")

    # #FIXED: Conclude Truncated Paths
    # WHAT WAS ADJUSTED: Call the local decoupled text layout engine to output the fresh, current template dataset.
    # PREVENTED FAILURE: Missing text rendering on successful atomic deletion flow.
    if fresh_templates:
        text = build_templates_list_text(fresh_templates)
        await message.answer(text, reply_markup=templates_list_keyboard(fresh_templates), parse_mode="HTML")
    else:
        await message.answer("No templates remaining.", reply_markup=manage_campaign_keyboard())


@router.message(F.text == "❌ Cancel", StateFilter(None))
async def cancel_template_delete(message: Message, state: FSMContext):
    # #FIXED: Removed handler-to-handler call. Inline the view logic directly.
    templates = []
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if campaign_id:
        templates = await TemplateService.get_templates_by_campaign(campaign_id)

    if templates:
        text = build_templates_list_text(templates)
        await message.answer(text, reply_markup=templates_list_keyboard(templates), parse_mode="HTML")
    else:
        await message.answer("No templates found for this campaign.", reply_markup=manage_campaign_keyboard())
