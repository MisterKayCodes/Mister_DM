# LAYER: Mouth — UI rendering only. No DB access, no business logic, no session management.
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from services.stats_service import StatsService

router = Router()
logger = logging.getLogger(__name__)


def _render_campaign_stats(stats: dict, campaign_name: str) -> str:
    """Renders campaign stats DTO to a clean HTML string. Pure formatting — no logic."""
    t = stats["targets"]
    m = stats["messages"]

    # Show sent + replied in the summary line for quick scanning
    lines = [
        f"📊 <b>{campaign_name} — Stats</b>\n",
        f"<b>Targets</b>",
        f"  Total:    {t['total']}",
        f"  Pending:  {t['pending']}",
        f"  Sent:     {t['sent']}",
        f"  Replied:  {t['replied']}",
        f"  Failed:   {t['failed']}",
        f"",
        f"<b>Messages Logged</b>",
        f"  Outbound: {m['outbound']}",
        f"  Inbound:  {m['inbound']}",
        f"",
        f"<b>Performance</b>",
        f"  Reply Rate:   {stats['reply_rate']}%  <i>(replied / sent)</i>",
        f"  Failure Rate: {stats['failure_rate']}%  <i>(failed / attempted)</i>",
        f"",
        f"<b>Last Activity:</b> {stats['last_activity']}",
    ]
    return "\n".join(lines)


def _render_global_stats(stats: dict) -> str:
    """Renders global stats DTO to a clean HTML string. Pure formatting — no logic."""
    c = stats["campaigns"]
    t = stats["targets"]

    lines = [
        f"📊 <b>Global Stats</b>\n",
        f"<b>Campaigns</b>",
        f"  Total:     {c['total']}",
        f"  Running:   {c['running']}",
        f"  Paused:    {c['paused']}",
        f"  Draft:     {c['draft']}",
        f"  Completed: {c['completed']}",
        f"  Stopped:   {c['stopped']}",
        f"",
        f"<b>Targets (all campaigns)</b>",
        f"  Total:    {t['total']}",
        f"  Sent:     {t['sent']}",
        f"  Replied:  {t['replied']}",
        f"  Failed:   {t['failed']}",
        f"",
        f"<b>Messages Logged:</b> {stats['total_messages']}",
        f"",
        f"<b>Performance</b>",
        f"  Reply Rate:   {stats['reply_rate']}%  <i>(replied / sent)</i>",
        f"  Failure Rate: {stats['failure_rate']}%  <i>(failed / attempted)</i>",
    ]
    return "\n".join(lines)


# --- Handlers ---

@router.message(Command("stats"), StateFilter("*"))
@router.message(F.text == "📊 Stats", StateFilter("*"))
async def global_stats_handler(message: Message, state: FSMContext):
    """Shows system-wide stats from the main menu or /stats command."""
    await state.clear()
    try:
        stats = await StatsService.get_global_stats()
        text = _render_global_stats(stats)
    except Exception as e:
        logger.error(f"Failed to fetch global stats: {e}")
        text = "❌ Could not load stats. Please try again."

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📊 View Stats", StateFilter("*"))
async def campaign_stats_handler(message: Message, state: FSMContext):
    """Shows per-campaign stats from the campaign management screen."""
    data = await state.get_data()
    campaign_id   = data.get("current_campaign_id")
    campaign_name = data.get("current_campaign_name", f"Campaign {campaign_id}")

    if not campaign_id:
        await message.answer("⚠️ No campaign selected. Open a campaign first.")
        return

    try:
        stats = await StatsService.get_campaign_stats(campaign_id)
        text = _render_campaign_stats(stats, campaign_name)
    except Exception as e:
        logger.error(f"Failed to fetch campaign stats for {campaign_id}: {e}")
        text = "❌ Could not load stats. Please try again."

    await message.answer(text, parse_mode="HTML")
