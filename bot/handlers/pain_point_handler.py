from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.states.pain_tag_states import PainPointStates
from bot.keyboards.pain_points_keyboards import pain_dashboard_keyboard, back_to_pain_dash_keyboard
from services.pain_tag_service import PainTagService
from services.target_service import TargetService
from bot.helpers.profile_renderer import render_target_profile
from bot.keyboards.target_keyboards import target_profile_keyboard

router = Router()


# ─── HELPERS ───────────────────────────────────────────────────────────────────

async def _render_pain_dashboard(message_or_edit, edit: bool = False):
    """
    Shared dashboard renderer. Avoids duplicating dashboard build logic.
    """
    tags = await PainTagService.get_all_pain_tags_with_counts()
    text = "🏷 <b>Pain Points Dashboard</b>\n\nTap a pain point to see who mentioned it:"

    kb = pain_dashboard_keyboard(tags)

    if edit:
        await message_or_edit.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_edit.answer(text, reply_markup=kb, parse_mode="HTML")


# ─── DASHBOARD ─────────────────────────────────────────────────────────────────

@router.message(F.text == "🏷 Pain Points", StateFilter("*"))
async def view_pain_dashboard(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _render_pain_dashboard(message, edit=False)
    except Exception:
        await message.answer("❌ Failed to load Pain Points. Please try again.")


@router.callback_query(F.data == "back_to_pain_dash")
async def back_to_pain_dashboard(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await _render_pain_dashboard(callback.message, edit=True)
    except Exception:
        await callback.answer("❌ Failed to refresh dashboard.", show_alert=True)
    await callback.answer()


# ─── PAIN POINT DETAIL ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("viewpain_"))
async def view_pain_point_details(callback: CallbackQuery, state: FSMContext):
    pain_tag_id = int(callback.data.split("_")[1])

    try:
        tags = await PainTagService.get_all_pain_tags_with_counts()
        tag_name = next((t["display_name"] for t in tags if t["id"] == pain_tag_id), "Unknown")
        targets = await PainTagService.get_targets_for_pain_tag(pain_tag_id)
    except Exception:
        await callback.answer("❌ Failed to load pain point details.", show_alert=True)
        return

    mentions = "\n".join([f"• @{t['username']}" for t in targets]) if targets else "No one yet."

    text = (
        f"🏷 <b>Pain Point:</b> {tag_name}\n\n"
        f"<b>Mentioned By:</b>\n{mentions}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_pain_dash_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ─── QUICK TAG ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "quick_tag_user")
async def quick_tag_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Who do you want to tag? Enter their Telegram @username\n\n"
        "Type /cancel to abort.",
    )
    await state.set_state(PainPointStates.waiting_for_username_to_tag)
    await callback.answer()


@router.message(F.text == "/cancel", PainPointStates.waiting_for_username_to_tag)
async def cancel_quick_tag(message: Message, state: FSMContext):
    await state.clear()
    try:
        await _render_pain_dashboard(message, edit=False)
    except Exception:
        await message.answer("Cancelled.")


@router.message(PainPointStates.waiting_for_username_to_tag)
async def process_quick_tag_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")

    if not username or " " in username:
        await message.answer("❌ Invalid username. Please enter a single @username (no spaces).")
        return

    try:
        # Fetch full target with pain tags in one call
        target = await TargetService.get_target_by_username(username, load_pain_tags=True)
    except Exception:
        await message.answer("❌ Database error. Please try again.")
        await state.clear()
        return

    if not target:
        await message.answer(
            f"❌ '@{username}' was not found in the database.\n"
            "Make sure they've been imported into a campaign first."
        )
        await state.clear()
        return

    await state.clear()

    await message.answer(
        render_target_profile(target),
        reply_markup=target_profile_keyboard(target["id"]),
        parse_mode="HTML"
    )
