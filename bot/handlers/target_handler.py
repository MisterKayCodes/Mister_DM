import io
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from bot.states.target_states import AddTargetStates
from bot.keyboards.target_keyboards import import_method_keyboard, confirm_clear_keyboard
from bot.keyboards.template_keyboards import manage_campaign_keyboard
from data.repositories.target_repo import (
    add_targets_bulk,
    get_targets_by_campaign,
    get_target_count,
    clear_targets
)
from data.repositories.campaign_repo import get_campaign_by_id
from data.database import AsyncSessionLocal
from bot.keyboards.campaign_keyboards import campaigns_menu_keyboard

router = Router()

# ──────────────────────────────────────────────
# GUARD: Draft-Only Check
# ──────────────────────────────────────────────

async def _get_draft_campaign(message: Message, state: FSMContext):
    """
    Central guard for all target modification handlers.
    Fetches the current campaign and enforces the draft-only rule.

    We do this in one place instead of copy-pasting the status check into every handler.
    The rule: only draft campaigns can be modified. If the scheduler is already
    running (status = running/paused), adding or clearing targets would mutate
    the dataset mid-flight, which introduces race conditions where the scheduler
    could skip or double-send targets.
    """
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Go back to the campaign list.", reply_markup=campaigns_menu_keyboard())
        return None

    async with AsyncSessionLocal() as session:
        campaign = await get_campaign_by_id(session, campaign_id)

    if not campaign:
        await message.answer("Campaign not found.")
        return None

    if campaign.status != "draft":
        await message.answer(
            f"❌ Cannot modify targets. Campaign is **{campaign.status}**.\n"
            "Only draft campaigns can be modified.",
            reply_markup=manage_campaign_keyboard(),
            parse_mode="Markdown"
        )
        return None

    return campaign


# ──────────────────────────────────────────────
# ADD TARGETS
# ──────────────────────────────────────────────

@router.message(F.text == "👥 Add Targets", StateFilter(None))
async def add_targets_menu(message: Message, state: FSMContext):
    campaign = await _get_draft_campaign(message, state)
    if not campaign:
        return

    await message.answer(
        "How do you want to add targets?",
        reply_markup=import_method_keyboard()
    )


@router.message(F.text == "📝 Paste Usernames", StateFilter(None))
async def paste_usernames_start(message: Message, state: FSMContext):
    campaign = await _get_draft_campaign(message, state)
    if not campaign:
        return

    await message.answer(
        "Send me the list of Telegram usernames.\n"
        "You can separate them with spaces, commas, or newlines. "
        "The @ symbol is optional.\n\n"
        "Example:\n@john_doe, cryptobro\nforex_king\n\n"
        "Send ❌ Cancel to go back.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddTargetStates.waiting_for_text_paste)


@router.message(AddTargetStates.waiting_for_text_paste)
async def process_text_paste(message: Message, state: FSMContext):
    if message.text.strip().startswith("❌"):
        await state.set_state(None)
        await message.answer("Cancelled.", reply_markup=manage_campaign_keyboard())
        return

    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")

    await message.answer("⏳ Processing...")

    async with AsyncSessionLocal() as session:
        stats = await add_targets_bulk(session, campaign_id, message.text)

    await state.set_state(None)
    await message.answer(
        f"✅ **Import Complete**\n\n"
        f"• Added: {stats['added']}\n"
        f"• Skipped (Duplicates): {stats['duplicates']}\n"
        f"• Invalid Format: {stats['invalid']}",
        reply_markup=manage_campaign_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "📁 Upload TXT File", StateFilter(None))
async def upload_file_start(message: Message, state: FSMContext):
    campaign = await _get_draft_campaign(message, state)
    if not campaign:
        return

    await message.answer(
        "Upload a .txt file containing usernames (one per line).\n\n"
        "Send ❌ Cancel to go back.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddTargetStates.waiting_for_file_upload)


@router.message(AddTargetStates.waiting_for_file_upload)
async def process_file_upload(message: Message, state: FSMContext):
    if message.text and message.text.strip().startswith("❌"):
        await state.set_state(None)
        await message.answer("Cancelled.", reply_markup=manage_campaign_keyboard())
        return

    if not message.document:
        await message.answer("Please upload a .txt file, or send ❌ Cancel to go back.")
        return

    if not message.document.file_name.endswith(".txt"):
        await message.answer("Only .txt files are supported. Please try again or send ❌ Cancel.")
        return

    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")

    await message.answer("⏳ Processing file...")

    # Download the file content into memory as bytes, then decode to string.
    # We never write the file to disk — there's no need, and disk writes add
    # latency, permission issues, and cleanup complexity.
    file = await message.bot.get_file(message.document.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    raw_text = file_bytes.read().decode("utf-8", errors="ignore")

    async with AsyncSessionLocal() as session:
        stats = await add_targets_bulk(session, campaign_id, raw_text)

    await state.set_state(None)
    await message.answer(
        f"✅ **Import Complete**\n\n"
        f"• Added: {stats['added']}\n"
        f"• Skipped (Duplicates): {stats['duplicates']}\n"
        f"• Invalid Format: {stats['invalid']}",
        reply_markup=manage_campaign_keyboard(),
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
# VIEW TARGETS
# ──────────────────────────────────────────────

@router.message(F.text == "👀 View Targets", StateFilter(None))
async def view_targets_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context.", reply_markup=campaigns_menu_keyboard())
        return

    async with AsyncSessionLocal() as session:
        targets = await get_targets_by_campaign(session, campaign_id)

    if not targets:
        await message.answer("No targets imported yet.", reply_markup=manage_campaign_keyboard())
        return

    total = len(targets)

    # We deliberately cap the inline preview at 20 entries.
    # Telegram messages have a hard 4096-character limit — a large list would crash silently.
    # Pagination UI is over-engineering for an MVP: it adds FSM states, keyboard logic,
    # and complexity with zero business value at this stage.
    # The correct MVP solution is an export file — it's more useful anyway
    # because the user can open it in Excel, search it, and share it.
    preview = targets[:20]
    preview_lines = [f"{i+1}. {t.username} ({t.status})" for i, t in enumerate(preview)]
    text = f"📋 Targets ({total} total):\n\n" + "\n".join(preview_lines)

    if total > 20:
        text += f"\n\n_...and {total - 20} more. See attached file for full list._"

    await message.answer(text, reply_markup=manage_campaign_keyboard(), parse_mode="Markdown")

    if total > 20:
        # Build the full list as a text file and send it directly in the chat.
        # No disk writes needed — we build it in memory using io.BytesIO.
        full_lines = [f"{t.username} ({t.status})" for t in targets]
        file_content = "\n".join(full_lines).encode("utf-8")
        await message.answer_document(
            document=BufferedInputFile(file_content, filename="targets_export.txt"),
            caption=f"Full list: {total} targets"
        )


# ──────────────────────────────────────────────
# CLEAR TARGETS
# ──────────────────────────────────────────────

@router.message(F.text == "🗑 Clear Targets", StateFilter(None))
async def clear_targets_prompt(message: Message, state: FSMContext):
    campaign = await _get_draft_campaign(message, state)
    if not campaign:
        return

    async with AsyncSessionLocal() as session:
        count = await get_target_count(session, campaign.id)

    await message.answer(
        f"⚠️ Are you sure you want to delete all **{count}** targets from this campaign?\n"
        "This cannot be undone.",
        reply_markup=confirm_clear_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "✅ Yes, Clear Targets", StateFilter(None))
async def confirm_clear_targets(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context.", reply_markup=campaigns_menu_keyboard())
        return

    async with AsyncSessionLocal() as session:
        deleted_count = await clear_targets(session, campaign_id)

    await message.answer(
        f"✅ Cleared {deleted_count} targets.",
        reply_markup=manage_campaign_keyboard()
    )
