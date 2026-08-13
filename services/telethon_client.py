import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UserPrivacyRestrictedError, FloodWaitError
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("TELETHON_API_ID", "12345")
API_HASH = os.getenv("TELETHON_API_HASH", "dummy_hash")

async def send_outreach_message(session_string: str, username: str, message_text: str, dry_run: bool = True) -> bool:
    """
    Sends a message using Telethon. 
    Returns True on success, False on failure.
    """
    if dry_run:
        print(f"[DRY RUN] Would send to {username}: {message_text[:30]}...")
        return True

    if not session_string:
        print(f"[TELETHON] Error: Empty session_string provided for {username}.")
        return False

    client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[TELETHON] Session is not authorized.")
            return False
            
        await client.send_message(username, message_text)
        print(f"[TELETHON] Successfully sent message to {username}.")
        return True
    except UserPrivacyRestrictedError:
        print(f"[TELETHON] Privacy settings prevent sending to {username}.")
        return False
    except FloodWaitError as e:
        print(f"[TELETHON] Flood wait error: must wait {e.seconds} seconds.")
        # We don't sleep here; we just mark as failed and let the scheduler move on or stop.
        return False
    except ValueError as e:
        print(f"[TELETHON] Value error for {username}: {e}")
        return False
    except Exception as e:
        print(f"[TELETHON] Unexpected error sending to {username}: {e}")
        return False
    finally:
        await client.disconnect()
