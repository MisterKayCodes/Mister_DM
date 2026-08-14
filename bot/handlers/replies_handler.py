from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.states.replies_states import RepliesStates
from bot.keyboards.target_keyboards import target_profile_keyboard, note_cancel_keyboard
from bot.utils.profile_renderer import render_target_profile
from services.target_service import TargetService
from services.pain_tag_service import PainTagService
from bot.keyboards.pain_points_keyboards import pain_selection_keyboard

router = Router()


# ─── HELPERS ───────────────────────────────────────────────────────────────────

async def _show_target_profile(message_or_callback, target_id: int, edit: bool = False):
    """
    Shared helper: loads target profile and renders it.
    Avoids duplicating render logic across handlers.
    """
    target = await TargetService.get_target_by_id(target_id, load_pain_tags=True)
    if not target:
        text = "❌ Target not found."
        kb = None
    else:
        text = render_target_profile(target)
        kb = target_profile_keyboard(target_id)

    if edit:
        await message_or_callback.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")


# ─── REPLIES LIST ──────────────────────────────────────────────────────────────

@router.message(F.text == "💬 Replies", StateFilter("*"))
async def view_replies_list(message: Message, state: FSMContext):
    await state.clear()

    try:
        targets = await TargetService.get_replied_targets()
    except Exception:
        await message.answer("❌ Failed to load replies. Please try again.")
        return

    if not targets:
        await message.answer("No replies tracked yet. Start a campaign and wait for targets to respond!")
        return

    keyboard = [
        [InlineKeyboardButton(text=f"@{t['username']}", callback_data=f"profile_{t['id']}")]
        for t in targets[:50]  # Cap at 50 — pagination is a Phase 8+ concern
    ]

    await message.answer(
        f"💬 <b>Replied Targets ({len(targets)})</b>\n\nTap a target to open their profile:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "view_replies")
async def back_to_replies(callback: CallbackQuery, state: FSMContext):
    """Back button from profile: sends a fresh replies list."""
    await state.clear()

    try:
        targets = await TargetService.get_replied_targets()
    except Exception:
        await callback.answer("❌ Failed to load replies.", show_alert=True)
        return

    if not targets:
        await callback.message.edit_text("No replies tracked yet.")
        await callback.answer()
        return

    keyboard = [
        [InlineKeyboardButton(text=f"@{t['username']}", callback_data=f"profile_{t['id']}")]
        for t in targets[:50]
    ]

    await callback.message.edit_text(
        f"💬 <b>Replied Targets ({len(targets)})</b>\n\nTap a target to open their profile:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


# ─── PROFILE VIEW ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("profile_"))
async def view_target_profile(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[1])
    try:
        await _show_target_profile(callback.message, target_id, edit=True)
    except Exception:
        await callback.answer("❌ Failed to load profile.", show_alert=True)
    await callback.answer()


# ─── ADD PAIN TAG ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_pain_"))
async def start_add_pain_tag(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    await state.update_data(current_target_id=target_id)

    try:
        tags = await PainTagService.get_all_pain_tags_with_counts()
    except Exception:
        await callback.answer("❌ Failed to load pain tags.", show_alert=True)
        return

    await callback.message.edit_text(
        "Select a pain point to assign, or create a new one:",
        reply_markup=pain_selection_keyboard(tags, target_id)
    )
    await state.set_state(RepliesStates.waiting_for_pain_selection)
    await callback.answer()


@router.callback_query(RepliesStates.waiting_for_pain_selection, F.data.startswith("selectpain_"))
async def assign_existing_pain_tag(callback: CallbackQuery, state: FSMContext):
    pain_tag_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    target_id = data.get("current_target_id")

    if not target_id:
        await callback.answer("Lost context. Please go back.", show_alert=True)
        await state.clear()
        return

    try:
        result = await PainTagService.tag_target(target_id, pain_tag_id)
    except Exception:
        await callback.answer("❌ Failed to assign tag.", show_alert=True)
        return

    if result["success"]:
        await callback.answer("✅ Pain Tag assigned!")
    else:
        await callback.answer(f"⚠️ {result['message']}", show_alert=True)

    await state.clear()
    await _show_target_profile(callback.message, target_id, edit=True)


@router.callback_query(RepliesStates.waiting_for_pain_selection, F.data == "create_new_pain")
async def prompt_new_pain_tag(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("current_target_id")

    await callback.message.edit_text(
        "Enter the name of the new pain point (e.g., 'Manual Posting'):",
        reply_markup=note_cancel_keyboard(target_id)  # Reuse cancel keyboard
    )
    await state.set_state(RepliesStates.waiting_for_new_pain_name)
    await callback.answer()


@router.message(RepliesStates.waiting_for_new_pain_name)
async def process_new_pain_tag(message: Message, state: FSMContext):
    name = message.text.strip()

    if not name or len(name) < 2:
        await message.answer("❌ Name too short. Please enter at least 2 characters.")
        return

    if len(name) > 60:
        await message.answer("❌ Name too long. Max 60 characters.")
        return

    data = await state.get_data()
    target_id = data.get("current_target_id")

    if not target_id:
        await message.answer("Lost context. Please go back to Replies.")
        await state.clear()
        return

    try:
        tag_result = await PainTagService.create_pain_tag(name)
        if not tag_result["success"]:
            await message.answer(f"❌ {tag_result['message']}")
            await state.clear()
            return

        assign_result = await PainTagService.tag_target(target_id, tag_result["data"]["id"])
        if assign_result["success"]:
            await message.answer(f"✅ Created and assigned '{tag_result['data']['display_name']}'!")
        else:
            await message.answer(f"⚠️ {assign_result['message']}")

    except Exception:
        await message.answer("❌ Something went wrong. Please try again.")

    await state.clear()
    await _show_target_profile(message, target_id, edit=False)


# ─── EDIT NOTE ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_note_"))
async def start_edit_note(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    await state.update_data(current_target_id=target_id)

    await callback.message.edit_text(
        "Send me the new note for this target (overwrites the existing note):",
        reply_markup=note_cancel_keyboard(target_id)
    )
    await state.set_state(RepliesStates.waiting_for_note_text)
    await callback.answer()


@router.message(RepliesStates.waiting_for_note_text)
async def process_edit_note(message: Message, state: FSMContext):
    note = message.text.strip()
    data = await state.get_data()
    target_id = data.get("current_target_id")

    if not target_id:
        await message.answer("Lost context. Please go back to Replies.")
        await state.clear()
        return

    if len(note) > 500:
        await message.answer("❌ Note too long. Max 500 characters.")
        return

    try:
        await TargetService.update_target_note(target_id, note)
    except Exception:
        await message.answer("❌ Failed to save note. Please try again.")
        await state.clear()
        return

    await message.answer("✅ Note updated.")
    await state.clear()
    await _show_target_profile(message, target_id, edit=False)
