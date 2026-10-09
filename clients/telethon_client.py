import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UserPrivacyRestrictedError, FloodWaitError
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("TELETHON_API_ID", "12345")
API_HASH = os.getenv("TELETHON_API_HASH", "dummy_hash")

async def verify_session(session_string: str) -> tuple[bool, str]:
    """
    Validates a Telethon session string by connecting and calling get_me().
    Returns (True, "Valid") or (False, "Error reason").
    """
    if not session_string:
        return False, "Empty session string provided."

    try:
        client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
        await client.connect()
        me = await client.get_me()
        if not me:
            return False, "AuthKeyUnregistered (or session revoked/banned)."
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid session format or connection error: {str(e) or type(e).__name__}"
    finally:
        if 'client' in locals() and client.is_connected():
            await client.disconnect()

async def send_outreach_message(session_string: str, username: str, message_text: str, dry_run: bool = True) -> tuple[bool, int | None]:
    """
    Sends a message using Telethon. 
    Returns (True, user_id) on success, (False, None) on failure.
    """
    if dry_run:
        print(f"[DRY RUN] Would send to {username}: {message_text[:30]}...")
        return True, 123456789  # Fake ID for dry run

    if not session_string:
        print(f"[TELETHON] Error: Empty session_string provided for {username}.")
        return False, None

    try:
        client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[TELETHON] Session is not authorized.")
            return False, None
            
        sent_msg = await client.send_message(username, message_text)
        print(f"[TELETHON] Successfully sent message to {username}.")
        
        # Extract the permanent user ID from the peer object
        user_id = getattr(sent_msg.peer_id, 'user_id', None)
        return True, user_id
        
    except UserPrivacyRestrictedError:
        print(f"[TELETHON] Privacy settings prevent sending to {username}.")
        return False, None
    except FloodWaitError as e:
        print(f"[TELETHON] Flood wait error: must wait {e.seconds} seconds.")
        return False, None
    except ValueError as e:
        print(f"[TELETHON] Value error for {username}: {e}")
        return False, None
    except Exception as e:
        print(f"[TELETHON] Unexpected error sending to {username}: {e}")
        return False, None
    finally:
        if 'client' in locals() and client.is_connected():
            await client.disconnect()
