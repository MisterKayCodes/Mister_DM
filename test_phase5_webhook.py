import asyncio
import httpx
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from api.server import app

async def test_phase5_webhook():
    print("=== Testing Phase 5: Reply Webhook & Background Triage ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    test_username = "webhook_test_lead"
    test_user_id = 998877

    async with AsyncSessionLocal() as session:
        # Create campaign and insert target with status='sent'
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase5_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        await target_repo.add_targets_bulk(session, campaign_id, [test_username])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, test_username)
        assert target is not None, "Target must exist"
        
        # Set status to 'sent'
        target.status = "sent"
        target.telegram_user_id = test_user_id
        await session.commit()
        print(f"2. Inserted target '{test_username}' with status='sent'.")

    # 3. Simulate Inbound Webhook POST request using httpx ASGI transport
    print("\n3. Sending POST /api/v1/webhook/reply request...")
    payload = {
        "session_name": "Felix_War_Session",
        "from_username": test_username,
        "from_user_id": test_user_id,
        "message_text": "Hey I want to buy your trading signal software tool!"
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/webhook/reply", json=payload)
        print("Webhook Status Code:", response.status_code)
        print("Webhook Response JSON:", response.json())

        assert response.status_code == 200, "Webhook should return HTTP 200"
        data = response.json()
        assert data["status"] == "success"
        assert data["triage_triggered"] is True
        print("--> Webhook response PASSED!")

    # 4. Wait 1 second for background triage task to complete
    print("\n4. Waiting 1.5s for background Groq triage task...")
    await asyncio.sleep(1.5)

    # 5. Verify Database updates
    async with AsyncSessionLocal() as session:
        updated_target = await target_repo.get_target_by_id(session, target.id)
        print("Updated Target Status:", updated_target.status)
        print("Updated Target Triage Status:", updated_target.triage_status)

        assert updated_target.status == "replied", "Status should transition to 'replied'"
        assert updated_target.triage_status == "TRANSACTIONAL", "Triage status should be 'TRANSACTIONAL'"
        assert updated_target.replied_at is not None, "Replied_at timestamp should be set"
        print("--> Database Target Status & Triage Verdict PASSED!")

    print("\n=== ALL PHASE 5 WEBHOOK TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase5_webhook())
