import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
import httpx
import config
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from api.server import app

async def test_phase5_webhook():
    print("=== Testing Phase 5: Inbound Reply Webhook & Simulator Push ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    async with AsyncSessionLocal() as session:
        # Create campaign and target
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase5_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        username = "webhook_test_lead"
        await target_repo.add_targets_bulk(session, campaign_id, [username])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, username)
        assert target is not None, "Target must exist"
        
        # Set target status to 'sent' so webhook can match it
        target.status = "sent"
        target.telegram_user_id = 987654321
        await session.commit()
        target_id = target.id
        print(f"2. Prepared target '@{username}' with status='sent' (Telegram User ID: 987654321).")

    # 2. Test Inbound Reply Webhook Endpoint (POST /api/v1/webhook/reply)
    print("\n3. Testing POST /api/v1/webhook/reply...")
    payload = {
        "session_name": "dm_warrior_1",
        "from_username": username,
        "from_user_id": 987654321,
        "message_text": "Hey bro! Loved your trading signals post. How much is the VIP bot?",
        "timestamp": "2026-09-09T12:00:00Z"
    }

    # Call Webhook via Async ASGI Test Client
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/webhook/reply", json=payload)
        print("Webhook Status Code:", response.status_code)
        print("Webhook Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        print("--> Webhook Endpoint PASSED!")

    # 3. Sleep 1s to allow background Groq Triage task to complete
    print("\n4. Waiting 1s for non-blocking Groq Triage background task...")
    await asyncio.sleep(1)

    async with AsyncSessionLocal() as session:
        t = await target_repo.get_target_by_id(session, target_id)
        print("--> DB Status after webhook:", t.status)
        print("--> DB Triage Status after webhook:", t.triage_status)
        assert t.status == "replied"
        assert t.triage_status in ["TRANSACTIONAL", "RELATIONAL", "DEAD"]
        print("--> Background Triage & Target Status Update PASSED!")

    print("\n=== ALL PHASE 5 WEBHOOK TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase5_webhook())
