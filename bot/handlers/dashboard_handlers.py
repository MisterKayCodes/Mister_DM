import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode

from services.groq_tracker import groq_tracker
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_({"⚡ API Usage", "/api_usage", "API Usage", "/usage"}))
async def show_api_usage(message: Message):
    """Renders 1-screen Groq API & Token Radar dashboard."""
    stats = groq_tracker.get_stats()
    model_name = getattr(config, "GROQ_ROLEPLAY_MODEL", None) or getattr(config, "GROQ_TRIAGE_MODEL", "llama-3.3-70b-versatile")
    
    text = (
        "╔══════════════════════╗\n"
        "║   ⚡ <b>GROQ API & TOKEN RADAR</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"🤖 <b>Active Model:</b> <code>{model_name}</code>\n"
        f"📡 <b>Radar Status:</b> <code>{stats['status_badge']}</code>\n"
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "📡 <b>Live Groq Quota Meter</b>\n"
        f"📦 <b>Tokens (TPM):</b> <code>{stats['tokens_remaining']:,}</code> / <code>{stats['tokens_limit']:,}</code>\n"
        f"📞 <b>Requests (RPM):</b> <code>{stats['requests_remaining']:,}</code> / <code>{stats['requests_limit']:,}</code>\n"
        f"⏳ <b>Request Rollover:</b> <code>{stats['reset_requests']}</code>\n"
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Session Metrics (Since Startup)</b>\n"
        f"📞 <b>Total LLM Calls:</b> <code>{stats['call_count']}</code>\n"
        f"📥 <b>Prompt Tokens:</b> <code>{stats['prompt_tokens']:,}</code>\n"
        f"📤 <b>Response Tokens:</b> <code>{stats['completion_tokens']:,}</code>\n"
        f"🔢 <b>Session Total:</b> <code>{stats['total_tokens']:,}</code>\n"
    )

    await message.answer(text, parse_mode=ParseMode.HTML)
