import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from services.account_service import AccountService
from services.target_service import TargetService
import os

API_ID = os.getenv("TELETHON_API_ID", "12345")
API_HASH = os.getenv("TELETHON_API_HASH", "dummy_hash")

class ReplyListenerService:
    """
    Manages persistent background connections to Telegram for tracking target replies.
    """
    
    # Registry: account_id -> {"client": TelegramClient, "task": asyncio.Task}
    active_listeners: dict[int, dict] = {}

    @staticmethod
    async def start_all_listeners():
        """Called on bot startup. Boot up listeners for all accounts."""
        accounts = await AccountService.get_all_accounts()
        print(f"[LISTENER ENGINE] Booting listeners for {len(accounts)} accounts...")
        for account in accounts:
            await ReplyListenerService.start_listener(account)

    @staticmethod
    async def start_listener(account: dict):
        """Spawns a new listener for a specific account."""
        account_id = account["id"]
        
        if account_id in ReplyListenerService.active_listeners:
            print(f"[LISTENER ENGINE] Listener for account {account_id} already running.")
            return

        session_string = account["session_string"]
        if not session_string:
            print(f"[LISTENER ENGINE] Account {account_id} missing session string.")
            return

        # Start the background task
        task = asyncio.create_task(ReplyListenerService._listener_loop(account_id, session_string))
        
        # We don't have the client instance yet (it's inside the loop), 
        # but we store the task so we can cancel it later.
        ReplyListenerService.active_listeners[account_id] = {"task": task, "client": None}
        print(f"[LISTENER ENGINE] Task spawned for account {account_id}.")

    @staticmethod
    async def stop_listener(account_id: int):
        """Cancels a running listener cleanly."""
        listener = ReplyListenerService.active_listeners.pop(account_id, None)
        if not listener:
            return
            
        task = listener.get("task")
        client = listener.get("client")
        
        if task:
            task.cancel()
            
        if client and client.is_connected():
            await client.disconnect()
            
        print(f"[LISTENER ENGINE] Listener for account {account_id} terminated.")

    @staticmethod
    async def _listener_loop(account_id: int, session_string: str):
        """
        The persistent auto-reconnecting listener loop.
        """
        client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
        
        # Store the client back in the registry so stop_listener can disconnect it
        if account_id in ReplyListenerService.active_listeners:
            ReplyListenerService.active_listeners[account_id]["client"] = client

        # Factory function to inject account_id into the event handler
        async def _handle_new_message(event):
            # We only care about incoming private messages
            if not event.is_private or event.out:
                return
                
            sender_id = event.sender_id
            if not sender_id:
                return

            # #FIXED: Broaden reply detection across all account campaigns.
            # WHY: If a target was messaged in Campaign 1 and Campaign 2, a single SQL bulk update 
            # safely marks them as 'replied' everywhere, bypassing Python loops and detached ORM errors.
            updated_count = await TargetService.mark_targets_as_replied(
                telegram_user_id=sender_id,
                account_id=account_id
            )
            
            if updated_count > 0:
                print(f"[LISTENER ENGINE] Account {account_id} received reply from User {sender_id}. Marked {updated_count} targets as replied.")

        # Register handler
        client.add_event_handler(_handle_new_message, events.NewMessage(incoming=True))

        while True:
            try:
                print(f"[LISTENER ENGINE] Account {account_id} connecting...")
                await client.connect()
                if not await client.is_user_authorized():
                    print(f"[LISTENER ENGINE] Account {account_id} session invalid! Stopping.")
                    break # Cannot recover from bad auth
                    
                print(f"[LISTENER ENGINE] Account {account_id} connected. Listening for replies...")
                await client.run_until_disconnected()
                
            except asyncio.CancelledError:
                print(f"[LISTENER ENGINE] Account {account_id} task cancelled by system.")
                break
            except Exception as e:
                print(f"[LISTENER ENGINE] Account {account_id} listener crashed: {e}. Reconnecting in 30s...")
                await asyncio.sleep(30)
            finally:
                if client.is_connected():
                    await client.disconnect()
