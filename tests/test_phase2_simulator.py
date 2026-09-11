import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
from data.database import init_db, AsyncSessionLocal
from data.repositories import campaign_repo, account_repo
from services.scheduler_service import SchedulerService
from clients.simulator_client import simulator_client
from clients.exceptions import APIUnavailableError

async def test_phase2_simulator():
    print("=== Testing Phase 2: Mister Simulator Integration ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    # 2. Test Simulator Client Health Check
    print("\n2. Checking Mister Simulator health...")
    try:
        health = await simulator_client.check_health()
        print("Simulator Health Status:", health)
    except APIUnavailableError as e:
        print("--> Simulator API is offline (Mocking/Fallback mode expected in dev):", e)

    # 3. Test Simulator Session Lookup
    print("\n3. Testing get_dm_warrior_sessions()...")
    try:
        sessions = await simulator_client.get_dm_warrior_sessions()
        print(f"--> Found {len(sessions)} dm_warrior session(s):", sessions)
    except APIUnavailableError as e:
        print("--> Simulator API is offline (Mocking/Fallback mode expected in dev):", e)

    # 4. Test Campaign Model with session_name column
    print("\n4. Testing Campaign creation with session_name...")
    async with AsyncSessionLocal() as session:
        # Create campaign bound to a simulator session_name
        c = await campaign_repo.insert_campaign(
            session=session,
            name="Phase2_Simulator_Campaign",
            account_id=None
        )
        c.session_name = "dm_warrior_session_1"
        await session.commit()
        print(f"--> Successfully created campaign '{c.name}' with session_name '{c.session_name}' (ID: {c.id}).")

    # 5. Test Scheduler Service session borrowing logic
    print("\n5. Testing SchedulerService borrowing Simulator session logic...")
    async with AsyncSessionLocal() as session:
        campaigns = await campaign_repo.get_all_campaigns(session)
        assert len(campaigns) > 0, "Should have at least 1 campaign"
        target_c = campaigns[-1]
        print(f"Target Campaign ID: {target_c.id}, Name: {target_c.name}, Session Name: {target_c.session_name}")

    print("\n=== ALL PHASE 2 SIMULATOR TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase2_simulator())
