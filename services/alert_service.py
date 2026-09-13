import random
import logging
import httpx
import config
from utils.telegram_utils import safe_html

logger = logging.getLogger(__name__)

# Rotating fun / conversational alert templates
ALERT_TEMPLATES = [
    "🚨 <b>Boss, {persona_name} needs backup!</b>\nCurrently talking to <b>{target_display}</b> and the lead asked a tough question:\n\n<i>\"{last_message}\"</i>\n\nWhat should we tell them?",
    "⚡ <b>War Room Alert!</b>\n{persona_name} hit a road block with <b>{target_display}</b>.\n\n<b>Lead said:</b> <i>\"{last_message}\"</i>\n\nTake over or guide the response!",
    "⚠️ <b>Attention Boss!</b>\n{persona_name} just paused the conversation with <b>{target_display}</b>.\n\n<b>Last Message:</b> <i>\"{last_message}\"</i>\n\nNeed your input on how to handle this.",
    "👀 <b>Oga, {persona_name} don stick for {target_display} o!</b>\n\n<b>Target said:</b> <i>\"{last_message}\"</i>\n\nMake you help out before the lead cold!"
]


class AlertService:
    """
    Service for pushing War Room alerts to Telegram Group / Admin DM
    when an AI conversation needs human override.
    """

    @staticmethod
    def format_target_display(target_data: dict) -> str:
        """
        Graceful name formatting fallback:
        If username exists, returns '@username'.
        Otherwise falls back to first_name or 'Lead #ID'.
        """
        username = target_data.get("username")
        first_name = target_data.get("first_name") or target_data.get("note")
        target_id = target_data.get("id")

        if username and username.strip():
            clean = username.lstrip("@")
            return f"@{clean}"
        elif first_name and first_name.strip():
            return f"{first_name.strip()} (No @username)"
        else:
            return f"Target #{target_id}"

    @staticmethod
    async def send_war_room_alert(
        target_id: int,
        target_data: dict,
        persona_name: str = "Sarah",
        last_message: str = ""
    ) -> bool:
        """
        Dispatches an inline keyboard alert to the configured WAR_ROOM_GROUP_ID.
        Uses Telegram Bot API directly via HTTPX.
        """
        target_group = config.WAR_ROOM_GROUP_ID
        if not target_group:
            logger.warning("[ALERT_SERVICE] WAR_ROOM_GROUP_ID is not configured. Alert skipped.")
            return False

        target_display = AlertService.format_target_display(target_data)
        
        # Pick a random template to keep notifications fresh
        template = random.choice(ALERT_TEMPLATES)
        text = template.format(
            persona_name=safe_html(persona_name),
            target_display=safe_html(target_display),
            last_message=safe_html(last_message or "No message content")
        )

        # Deep link URL to jump directly into private DM with bot
        deep_link = f"https://t.me/{config.BOT_USERNAME}?start=override_{target_id}"

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✍️ Jump in to Reply", "url": deep_link}
                ]
            ]
        }

        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": target_group,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                data = response.json()
                if data.get("ok"):
                    logger.info(f"[ALERT_SERVICE] Successfully dispatched alert for target {target_id} to chat {target_group}")
                    return True
                else:
                    logger.error(f"[ALERT_SERVICE] Telegram API error sending alert: {data}")
                    return False
        except Exception as e:
            logger.error(f"[ALERT_SERVICE] Failed to send alert: {e}", exc_info=True)
            return False

    @staticmethod
    async def send_admin_alert(text: str) -> bool:
        """
        Dispatches a raw notification text to the configured WAR_ROOM_GROUP_ID.
        Used for system pings, sleep notifications, and admin alerts.
        """
        target_group = config.WAR_ROOM_GROUP_ID
        if not target_group or not config.BOT_TOKEN:
            logger.warning("[ALERT_SERVICE] WAR_ROOM_GROUP_ID or BOT_TOKEN not configured. Admin alert skipped.")
            return False

        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": target_group,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                data = response.json()
                if data.get("ok"):
                    logger.info(f"[ALERT_SERVICE] Successfully dispatched admin alert to chat {target_group}")
                    return True
                else:
                    logger.error(f"[ALERT_SERVICE] Telegram API error sending admin alert: {data}")
                    return False
        except Exception as e:
            logger.error(f"[ALERT_SERVICE] Failed to send admin alert: {e}", exc_info=True)
            return False

