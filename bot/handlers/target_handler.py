# bot\handlers\target_handler.py
import io
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, BufferedInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from bot.states.target_states import AddTargetStates
from bot.keyboards.target_keyboards import import_method_keyboard, confirm_clear_keyboard
from bot.keyboards.template_keyboards import manage_campaign_keyboard
from bot.keyboards.navigation_keyboards import back_and_home_inline

# #FIXED: Removed inline import of main_menu_keyboard from inside nav_home_callback.
# WHAT WOULD HAVE HAPPENED: Inline imports inside callback handlers delay module loading
# to runtime, making import errors invisible until the button is tapped. Moving the import
# to the top of the file ensures failures are caught at startup, not mid-session.
from bot.keyboards.account_keyboards import main_menu_keyboard

from bot.keyboards.campaign_keyboards import campaigns_menu_keyboard
from services.target_service import TargetService
from services.campaign_service import CampaignService
from utils.telegram_utils import safe_html

router = Router()

# ──────────────────────────────────────────────
# GUARD: Draft-Only Check
# ──────────────────────────────────────────────

async def _get_draft_campaign(message: Message, state: FSMContext):
    """
    Central guard for all target modification handlers.
    Asks the Nerves (CampaignService) for a modifiability verdict.
    The Mouth receives a boolean and a status string — it never reads campaign.status itself.
    """
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context. Go back to the campaign list.", reply_markup=campaigns_menu_keyboard())
        return None

    # #FIXED: Decoupled status guard logic from the Mouth layer.
    # WHAT WAS ADJUSTED: Replaced `campaign.status != "draft"` evaluated inside the handler
    # with a call to `CampaignService.verify_campaign_modifiable`.
    # PREVENTED FAILURE: Business workflow rules (what counts as "modifiable") no longer live
    # in the presentation layer. If the rule changes (e.g. "paused" campaigns become editable),
    # only the Service needs to change — not every handler that guards targets.
    can_modify, status, campaign = await CampaignService.verify_campaign_modifiable(campaign_id)

    if not can_modify:
        if status == "not_found":
            await message.answer("Campaign not found.")
        else:
            await message.answer(
                f"❌ Cannot modify targets. Campaign is <b>{safe_html(status)}</b>.\n"
                "Only draft campaigns can be modified.",
                reply_markup=manage_campaign_keyboard(),
                parse_mode="HTML"
            )
        return None

    return campaign


# ──────────────────────────────────────────────
# INLINE NAV CALLBACKS (Back / Home)
# ──────────────────────────────────────────────

@router.callback_query(F.data == "nav_back")
async def nav_back_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handles the inline ⬅️ Back button shown during FSM flows where the ReplyKeyboard
    is removed. Cancels the current state and returns the user to the Manage Campaign screen.

    # We use callback_query instead of a reply message handler because the "Back" button
    # is an InlineKeyboardButton — it sends a callback, not a text message. This means
    # it works even when the user has already typed something in the input box.
    """
    await state.set_state(None)
    await callback.message.answer("Cancelled.", reply_markup=manage_campaign_keyboard())
    await callback.answer()


@router.callback_query(F.data == "nav_home")
async def nav_home_callback(callback: CallbackQuery, state: FSMContext):
    """Handles the inline 🏠 Main Menu button. Clears state and returns to the main menu."""
    await state.clear()
    await callback.message.answer("🏠 Main Menu", reply_markup=main_menu_keyboard())
    await callback.answer()


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

    # We remove the ReplyKeyboard here to give the user a clean input area.
    # We attach inline Back/Home buttons so the user is never left stranded
    # without an escape route. Without these, the user would have to know to
    # type "❌ Cancel" — which is invisible once the keyboard disappears.
    await message.answer(
        "Send me the list of Telegram usernames.\n"
        "You can separate them with spaces, commas, or newlines. "
        "The @ symbol is optional.\n\n"
        "Example:\n@john_doe, cryptobro\nforex_king",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Use the buttons below if you change your mind:",
        reply_markup=back_and_home_inline()
    )
    await state.set_state(AddTargetStates.waiting_for_text_paste)


@router.message(AddTargetStates.waiting_for_text_paste)
async def process_text_paste(message: Message, state: FSMContext):
    if message.text and message.text.strip().startswith("❌"):
        await state.set_state(None)
        await message.answer("Cancelled.", reply_markup=manage_campaign_keyboard())
        return

    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")

    await message.answer("⏳ Processing...")

    result = await TargetService.add_targets_bulk(campaign_id, message.text)

    await state.set_state(None)

    if not result.get("success", False):
        await message.answer(
            f"❌ Import failed: {result.get('message', 'Unknown error')}",
            reply_markup=manage_campaign_keyboard()
        )
        return

    stats = result["data"]
    await message.answer(
        f"✅ <b>Import Complete</b>\n\n"
        f"• Added: {stats['added']}\n"
        f"• Skipped (Duplicates): {stats['duplicates']}\n"
        f"• Invalid Format: {stats['invalid']}",
        reply_markup=manage_campaign_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📁 Upload TXT File", StateFilter(None))
async def upload_file_start(message: Message, state: FSMContext):
    campaign = await _get_draft_campaign(message, state)
    if not campaign:
        return

    await message.answer(
        "Upload a .txt file containing usernames (one per line).",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Use the buttons below if you change your mind:",
        reply_markup=back_and_home_inline()
    )
    await state.set_state(AddTargetStates.waiting_for_file_upload)


@router.message(AddTargetStates.waiting_for_file_upload)
async def process_file_upload(message: Message, state: FSMContext):
    if message.text and message.text.strip().startswith("❌"):
        await state.set_state(None)
        await message.answer("Cancelled.", reply_markup=manage_campaign_keyboard())
        return

    if not message.document:
        await message.answer("Please upload a .txt file, or tap ⬅️ Back below.")
        return

    if not message.document.file_name.endswith(".txt"):
        await message.answer("Only .txt files are supported. Please try again or tap ⬅️ Back.")
        return

    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")

    await message.answer("⏳ Processing file...")

    # Download the file content into memory as bytes.
    # We never write the file to disk — there's no need, and disk writes add
    # latency, permission issues, and cleanup complexity.
    file = await message.bot.get_file(message.document.file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    # #FIXED: Prevent event loop freezes
    # WHAT WAS ADJUSTED: Moved the `.read().decode()` logic into the Service layer's 
    # `process_file_bytes` method, which executes it asynchronously in a background thread.
    # PREVENTED FAILURE: Completely halts asynchronous execution loops for all concurrent 
    # users when large files are loaded directly in the main thread.
    result = await TargetService.process_file_bytes(campaign_id, file_bytes)

    await state.set_state(None)

    if not result.get("success", False):
        await message.answer(
            f"❌ Import failed: {result.get('message', 'Unknown error')}",
            reply_markup=manage_campaign_keyboard()
        )
        return

    stats = result["data"]
    await message.answer(
        f"✅ <b>Import Complete</b>\n\n"
        f"• Added: {stats['added']}\n"
        f"• Skipped (Duplicates): {stats['duplicates']}\n"
        f"• Invalid Format: {stats['invalid']}",
        reply_markup=manage_campaign_keyboard(),
        parse_mode="HTML"
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

    # #FIXED: Purge Model Destructuring
    # WHAT WAS ADJUSTED: Requested a list of dicts from the Service layer instead of raw DB models.
    # PREVENTED FAILURE: The Mouth no longer unboxes ORM objects or reads properties like `.username`.
    # It just loops over standard python dicts for safety and format agility.
    targets = await TargetService.get_targets_by_campaign(campaign_id)

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

    # #FIXED: Removed parse_mode="Markdown" and switched to plain text for this message.
    # WHAT WOULD HAVE HAPPENED: Usernames like "john_doe" contain underscores.
    # Telegram's MarkdownV1 parser treats underscores as italic markers.
    # It crashes with: "Can't find end of the entity starting at byte offset X"
    # because "john_doe" opens an italic span that never closes.
    # Plain text is safe for lists of usernames. HTML is used only where we need bold/italic.
    preview_lines = [f"{i+1}. {t['username']} ({t['status']})" for i, t in enumerate(preview)]
    text = f"📋 Targets ({total} total):\n\n" + "\n".join(preview_lines)

    if total > 20:
        text += f"\n\n...and {total - 20} more. See attached file for full list."

    await message.answer(text, reply_markup=manage_campaign_keyboard())

    if total > 20:
        # Build the full list as a text file and send it directly in the chat.
        # No disk writes needed — we build it in memory using BufferedInputFile.
        full_lines = [f"{t['username']} ({t['status']})" for t in targets]
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

    count = await TargetService.get_target_count(campaign.id)

    await message.answer(
        f"⚠️ Are you sure you want to delete all <b>{count}</b> targets from this campaign?\n"
        "This cannot be undone.",
        reply_markup=confirm_clear_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ Yes, Clear Targets", StateFilter(None))
async def confirm_clear_targets(message: Message, state: FSMContext):
    data = await state.get_data()
    campaign_id = data.get("current_campaign_id")
    if not campaign_id:
        await message.answer("Lost context.", reply_markup=campaigns_menu_keyboard())
        return

    deleted_count = await TargetService.clear_targets(campaign_id)

    await message.answer(
        f"✅ Cleared {deleted_count} targets.",
        reply_markup=manage_campaign_keyboard()
    )