# LAYER: Service — session injection, DTOs, business rules, no UI
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from data.database import AsyncSessionLocal
from data.repositories import message_repo, target_repo, campaign_repo

logger = logging.getLogger(__name__)

def _message_to_dto(msg) -> dict:
    """Single source of truth for the message DTO shape."""
    return {
        "id": msg.id,
        "telegram_message_id": msg.telegram_message_id,
        "account_id": msg.account_id,
        "campaign_id": msg.campaign_id,
        "target_id": msg.target_id,
        "direction": msg.direction,
        "message_type": msg.message_type,
        "text": msg.text,
        "template_id": getattr(msg, "template_id", None),
        "timestamp": msg.timestamp,
        "timestamp_str": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else "Unknown",
    }

class MessageService:
    """Nerve layer for Messages. Controls transactions, returns DTOs."""

    @staticmethod
    async def log_message(
        target_id: int,
        direction: str,
        message_type: str,
        account_id: int | None = None,
        text: str | None = None,
        telegram_message_id: int | None = None,
        template_id: int | None = None,
        session: AsyncSession = None
    ) -> tuple[bool, dict | str]:
        """Logs a message. Resolves campaign_id and account_id from target/campaign cleanly if available."""
        async def _execute(sess: AsyncSession):
            target = await target_repo.get_target_by_id(sess, target_id)
            if not target:
                return False, "Target not found"

            resolved_account_id = account_id
            if resolved_account_id is None and target.campaign_id:
                campaign = await campaign_repo.get_campaign_by_id(sess, target.campaign_id)
                if campaign and campaign.account_id:
                    resolved_account_id = campaign.account_id

            msg = await message_repo.insert_message(
                session=sess,
                account_id=resolved_account_id,
                target_id=target_id,
                direction=direction,
                message_type=message_type,
                text=text,
                telegram_message_id=telegram_message_id,
                campaign_id=target.campaign_id,
                template_id=template_id
            )
            return True, _message_to_dto(msg)

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                try:
                    result = await _execute(new_sess)
                    if result[0]:
                        await new_sess.commit()
                    return result
                except Exception as e:
                    await new_sess.rollback()
                    logger.error(f"Failed to log message: {e}")
                    return False, str(e)
        return await _execute(session)

    @staticmethod
    async def get_messages_for_target(target_id: int, session: AsyncSession = None) -> list[dict]:
        """Fetches all messages for a specific target."""
        async def _execute(sess: AsyncSession):
            messages = await message_repo.get_messages_for_target(sess, target_id)
            return [_message_to_dto(m) for m in messages]

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)
    
    @staticmethod
    async def get_messages_for_campaign(campaign_id: int, session: AsyncSession = None) -> list[dict]:
        """Fetches all messages for a specific campaign."""
        async def _execute(sess: AsyncSession):
            messages = await message_repo.get_messages_for_campaign(sess, campaign_id)
            return [_message_to_dto(m) for m in messages]

        if session is None:
            async with AsyncSessionLocal() as new_sess:
                return await _execute(new_sess)
        return await _execute(session)
