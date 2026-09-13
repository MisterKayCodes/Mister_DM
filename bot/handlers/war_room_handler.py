import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext

from bot.states.war_room_states import WarRoomStates
from bot.keyboards.account_keyboards import main_menu_keyboard
from data.database import AsyncSessionLocal
from data.repositories import target_repo, relationship_messages_repo, personas_repo, campaign_repo
from clients.simulator_client import simulator_client
from utils.telegram_utils import safe_html

logger = logging.getLogger(__name__)
router = Router()


def war_room_dashboard_keyboard(targets_needing_human: list) -> InlineKeyboardMarkup:
    """Generates inline buttons for each target needing human override."""
    buttons = []
    for t in targets_needing_human[:10]:  # Limit to top 10
        display = f"@{t.username}" if t.username else f"Target #{t.id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🚨 Override {safe_html(display)}",
                callback_data=f"wr_select_{t.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔄 Refresh War Room", callback_data="wr_refresh")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def target_override_actions_keyboard(target_id: int) -> InlineKeyboardMarkup:
    """Action options for a specific target needing override."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Manual Reply", callback_data=f"wr_manual_{target_id}"),
            InlineKeyboardButton(text="🤖 Resume AI", callback_data=f"wr_resume_{target_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Back to War Room", callback_data="wr_refresh")
        ]
    ])


@router.message(F.text == "⚔️ War Room", StateFilter("*"))
async def show_war_room_dashboard(message: Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        needing_human = await target_repo.get_targets_needing_human(session)
        relational_targets = await target_repo.get_targets_by_triage(session, "RELATIONAL")

    text = (
        "⚔️ <b>WAR ROOM COMMAND CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 <b>Needs Human Backup:</b> {len(needing_human)}\n"
        f"🟢 <b>Active Relational Chats:</b> {len(relational_targets)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if needing_human:
        text += "\nSelect a lead below to inspect conversation & proxy-send a manual reply:"
        kb = war_room_dashboard_keyboard(needing_human)
    else:
        text += "\n✅ <i>All AI conversations running smoothly. No leads currently flagged for human intervention!</i>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Status", callback_data="wr_refresh")]
        ])

    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "wr_refresh")
async def refresh_war_room(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        needing_human = await target_repo.get_targets_needing_human(session)
        relational_targets = await target_repo.get_targets_by_triage(session, "RELATIONAL")

    text = (
        "⚔️ <b>WAR ROOM COMMAND CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 <b>Needs Human Backup:</b> {len(needing_human)}\n"
        f"🟢 <b>Active Relational Chats:</b> {len(relational_targets)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if needing_human:
        text += "\nSelect a lead below to inspect conversation & proxy-send a manual reply:"
        kb = war_room_dashboard_keyboard(needing_human)
    else:
        text += "\n✅ <i>All AI conversations running smoothly. No leads currently flagged for human intervention!</i>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Status", callback_data="wr_refresh")]
        ])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(CommandStart(deep_link=True))
async def handle_war_room_deep_link(message: Message, command: CommandObject, state: FSMContext):
    """Deep link handler for t.me/Bot?start=override_<target_id>"""
    await state.clear()
    args = command.args or ""
    if not args.startswith("override_"):
        # Not a war room deep link, fall through or ignore
        return

    try:
        target_id = int(args.replace("override_", ""))
    except ValueError:
        await message.answer("❌ Invalid deep link parameter.")
        return

    await _render_target_override_view(message_or_cb=message, target_id=target_id)


@router.callback_query(F.data.startswith("wr_select_"))
async def handle_target_select_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    target_id = int(callback.data.replace("wr_select_", ""))
    await _render_target_override_view(message_or_cb=callback, target_id=target_id)
    await callback.answer()


async def _render_target_override_view(message_or_cb, target_id: int):
    """Helper to render target details and recent conversation history."""
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, target_id)
        if not target:
            text = "❌ Target not found in database."
            if isinstance(message_or_cb, CallbackQuery):
                await message_or_cb.message.edit_text(text)
            else:
                await message_or_cb.answer(text)
            return

        # Fetch recent messages from relationship_chats
        from data.repositories import relationship_chats_repo
        chat = await relationship_chats_repo.get_chat_by_target(session, target_id)
        recent_history = []
        if chat:
            msgs = await relationship_messages_repo.get_recent_messages(session, chat.id, limit=5)
            recent_history = msgs

        # Get persona name
        persona_name = "Sarah"
        if target.assigned_persona_id:
            persona = await personas_repo.get_persona(session, target.assigned_persona_id)
            if persona:
                persona_name = persona.name

    display_name = f"@{target.username}" if target.username else f"Lead #{target.id}"
    
    script_text = "📜 <b>Recent Conversation History:</b>\n"
    if recent_history:
        for m in recent_history:
            sender = "👤 Lead" if m.role == "user" else f"🤖 {safe_html(persona_name)}"
            script_text += f"• <b>{sender}:</b> {safe_html(m.content)}\n"
    else:
        script_text += "<i>No prior message history recorded yet.</i>\n"

    body = (
        f"🚨 <b>WAR ROOM OVERRIDE FOR {safe_html(display_name)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Persona:</b> {safe_html(persona_name)}\n"
        f"<b>Status:</b> Needs Human Intervention\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{script_text}\n"
        "What would you like to do?"
    )

    kb = target_override_actions_keyboard(target_id)
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(body, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_cb.answer(body, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("wr_manual_"))
async def start_manual_reply_fsm(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.replace("wr_manual_", ""))
    await state.update_data(override_target_id=target_id)
    await state.set_state(WarRoomStates.waiting_for_override_text)

    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, target_id)
        display = f"@{target.username}" if (target and target.username) else f"Target #{target_id}"

    await callback.message.edit_text(
        f"✍️ <b>PROXY MANUAL REPLY FOR {display}</b>\n\n"
        "Type the exact text message you want Sarah/Marcus to send to this lead.\n"
        "<i>Mister DM will fire it directly through the burner Telegram account!</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="wr_refresh")]
        ])
    )
    await callback.answer()


@router.message(WarRoomStates.waiting_for_override_text, ~F.text)
async def process_manual_reply_non_text(message: Message):
    """Guards against stickers, photos, voice notes sent by admin during override."""
    await message.answer(
        "⚠️ <b>Plain text required.</b>\n"
        "Mister DM can only proxy-send text messages right now. Please type your reply as plain text:",
        parse_mode="HTML"
    )


@router.message(WarRoomStates.waiting_for_override_text)
async def process_manual_reply_text(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("override_target_id")
    reply_text = message.text.strip()

    if not reply_text:
        await message.answer("❌ Message cannot be empty. Please type your reply:")
        return

    await state.clear()

    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, target_id)
        if not target:
            await message.answer("❌ Target not found.", reply_markup=main_menu_keyboard())
            return

        # Lookup campaign to get assigned session name
        campaign = await campaign_repo.get_campaign_by_id(session, target.campaign_id)
        session_name = campaign.session_name if campaign else "Sarah_Ref"

        # 1. Fire DM via Mister Simulator
        try:
            res = await simulator_client.send_dm(
                session_name=session_name,
                target_username=target.username,
                message_text=reply_text,
                telegram_user_id=target.telegram_user_id
            )
            success = res.get("status") == "success" or res.get("ok", False)
        except Exception as exc:
            logger.error(f"[WAR_ROOM] Failed to send proxy DM via Simulator: {exc}")
            success = False

        if success:
            # 2. Clear needs_human flag
            await target_repo.set_target_needs_human(session, target_id, False)

            # 3. Log outbound message in relationship_messages
            from data.repositories import relationship_chats_repo
            chat = await relationship_chats_repo.get_chat_by_target(session, target_id)
            if chat:
                await relationship_messages_repo.add_message(
                    session=session,
                    chat_id=chat.id,
                    role="assistant",
                    content=reply_text
                )
            await session.commit()

            display = f"@{target.username}" if target.username else f"Target #{target_id}"
            await message.answer(
                f"✅ <b>Message Sent Successfully!</b>\n"
                f"Proxy sent to <b>{display}</b> via session <code>{session_name}</code>.\n"
                f"Human override cleared — conversation returned to AI.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
        else:
            await message.answer(
                "❌ <b>Failed to send message via Simulator.</b>\n"
                "Please verify Mister Simulator API is active.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )


@router.callback_query(F.data.startswith("wr_resume_"))
async def handle_resume_ai(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.replace("wr_resume_", ""))
    async with AsyncSessionLocal() as session:
        await target_repo.set_target_needs_human(session, target_id, False)
        await session.commit()

    await callback.message.edit_text(
        "🤖 <b>AI Resumed!</b>\n"
        "Human override flag cleared. Mister DM will handle the next response automatically.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to War Room", callback_data="wr_refresh")]
        ])
    )
    await callback.answer()
