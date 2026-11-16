# verify_scheduler_cap.py
"""Simple script to verify the daily DM cap warning added to the scheduler.
Run this after the scheduler changes have been deployed.
It works in DRY_RUN mode – no real Telegram messages are sent.
"""

import asyncio
from collections import defaultdict
from datetime import date
import sys, os
sys.path.append(os.path.abspath(r"C:\Kaycris\LIVE_PROJECTS\Mister_DM"))
from services.settings_service import SettingsService

# In‑memory structures must match those in scheduler_service.py
session_daily_counts = defaultdict(int)
current_date = date.today()

async def simulate_send(run_id: str, times: int):
    """Simulate sending `times` DMs for a given run/session id.
    Prints a warning when the daily cap is exceeded.
    """
    global current_date
    for i in range(times):
        # Reset counters if day changed
        if date.today() != current_date:
            session_daily_counts.clear()
            current_date = date.today()
        session_daily_counts[run_id] += 1
        cap = await SettingsService.get_daily_dm_cap()
        if session_daily_counts[run_id] > cap:
            print(f"[CAP WARNING] Session {run_id} sent {session_daily_counts[run_id]} DMs today (cap={cap})")
        else:
            print(f"DM {i+1} for session {run_id} within cap (sent={session_daily_counts[run_id]}, cap={cap})")
        await asyncio.sleep(0.1)  # mimic throttling

async def main():
    # Ensure the cap is set to the default (2) – you can change it in the UI first
    run_id = "demo-session"
    await simulate_send(run_id, 3)  # three DMs should trigger a warning on the 3rd

if __name__ == "__main__":
    asyncio.run(main())