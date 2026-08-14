# LAYER: Core / Brain — Orchestration, Background Lifecycle. No UI code.
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import TELETHON_API_ID, TELETHON_API_HASH
from services.account_service import AccountService
from services.target_service import TargetService
from services.message_service import MessageService
from data.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class ReplyListener:
    """
    Manages persistent background connections to Telegram for tracking target replies.
    Orchestrates connection lifecycles across all active accounts.
    """
    
    # Registry: account_id -> {"client": TelegramClient, "task": asyncio.Task}
    active_listeners: dict[int, dict] = {}

    @classmethod
    async def start_all_listeners(cls):
        """Called on bot startup. Boot up listeners for all active accounts."""
        # Single session for startup account fetch
        accounts = await AccountService.get_all_accounts()
        
        # Filter accounts that have a valid session string
        valid_accounts = [acc for acc in accounts if acc.get("session_string")]
        logger.info(f"[LISTENER ENGINE] Booting listeners for {len(valid_accounts)} accounts...")
        
        for account in valid_accounts:
            await cls.start_listener(account)

    @classmethod
    async def start_listener(cls, account: dict):
        """Spawns a new listener for a specific account."""
        account_id = account["id"]
        
        if account_id in cls.active_listeners:
            logger.info(f"[LISTENER ENGINE] Listener for account {account_id} already running.")
            return

        session_string = account.get("session_string")
        if not session_string:
            logger.error(f"[LISTENER ENGINE] Account {account_id} missing session string. Cannot start.")
            return

        # Start the background task
        task = asyncio.create_task(cls._listener_loop(account_id, session_string))
        cls.active_listeners[account_id] = {"task": task, "client": None}
        logger.info(f"[LISTENER ENGINE] Task spawned for account {account_id}.")

    @classmethod
    async def stop_listener(cls, account_id: int):
        """Cancels a running listener cleanly."""
        listener = cls.active_listeners.pop(account_id, None)
        if not listener:
            return
            
        task = listener.get("task")
        client = listener.get("client")
        
        if task:
            task.cancel()
            
        if client and client.is_connected():
            await client.disconnect()
            
        logger.info(f"[LISTENER ENGINE] Listener for account {account_id} terminated.")

    @classmethod
    async def stop_all(cls):
        """Cancels all running listeners. Called on bot shutdown."""
        account_ids = list(cls.active_listeners.keys())
        for acc_id in account_ids:
            await cls.stop_listener(acc_id)
        logger.info("[LISTENER ENGINE] All listeners stopped.")

    @classmethod
    async def _listener_loop(cls, account_id: int, session_string: str):
        """
        The persistent auto-reconnecting listener loop.
        """
        client = TelegramClient(StringSession(session_string), int(TELETHON_API_ID), TELETHON_API_HASH)
        
        # Store the client back in the registry so stop_listener can disconnect it
        if account_id in cls.active_listeners:
            cls.active_listeners[account_id]["client"] = client

        # Factory function to inject account_id into the event handler
        async def _handle_new_message(event):
            # We only care about incoming private messages
            if not event.is_private or event.out:
                return
                
            sender_id = event.sender_id
            if not sender_id:
                return

            # Determine message type and text
            message_type = "TEXT"
            if getattr(event, 'photo', None):
                message_type = "PHOTO"
            elif getattr(event, 'voice', None):
                message_type = "VOICE"
            elif getattr(event, 'document', None):
                message_type = "DOCUMENT"
            elif getattr(event, 'sticker', None):
                message_type = "STICKER"
            elif getattr(event, 'media', None):
                message_type = "OTHER"
                
            text = event.text if event.text else None
            telegram_message_id = event.id

            # Execute logging and target updating in ONE session boundary
            async with AsyncSessionLocal() as session:
                try:
                    targets = await TargetService.get_targets_by_telegram_id_and_account(
                        telegram_user_id=sender_id,
                        account_id=account_id,
                        session=session
                    )
                    
                    if targets:
                        # Log message for all matching targets
                        for t in targets:
                            await MessageService.log_message(
                                account_id=account_id,
                                target_id=t["id"],
                                direction="INBOUND",
                                message_type=message_type,
                                text=text,
                                telegram_message_id=telegram_message_id,
                                session=session
                            )

                        # Mark targets as replied
                        updated_count = await TargetService.mark_targets_as_replied(
                            telegram_user_id=sender_id,
                            account_id=account_id,
                            session=session
                        )
                        
                        await session.commit()
                        logger.info(f"[LISTENER ENGINE] Account {account_id} logged reply from User {sender_id}. Marked {updated_count} targets as replied.")
                except Exception as e:
                    await session.rollback()
                    logger.error(f"[LISTENER ENGINE] Failed to process incoming message on account {account_id}: {e}")

        # Register handler
        client.add_event_handler(_handle_new_message, events.NewMessage(incoming=True))

        while True:
            try:
                logger.info(f"[LISTENER ENGINE] Account {account_id} connecting...")
                await client.connect()
                
                if not await client.is_user_authorized():
                    logger.error(f"[LISTENER ENGINE] Account {account_id} session invalid! Stopping.")
                    # In a full prod system, we might mark account as inactive here
                    break 
                    
                logger.info(f"[LISTENER ENGINE] Account {account_id} connected. Listening for replies...")
                await client.run_until_disconnected()
                
            except asyncio.CancelledError:
                logger.info(f"[LISTENER ENGINE] Account {account_id} task cancelled by system.")
                break
            except ConnectionError as e:
                logger.warning(f"[LISTENER ENGINE] Account {account_id} connection error: {e}. Reconnecting in 30s...")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"[LISTENER ENGINE] Account {account_id} listener crashed: {e}. Reconnecting in 60s...")
                await asyncio.sleep(60)
            finally:
                if client.is_connected():
                    await client.disconnect()
