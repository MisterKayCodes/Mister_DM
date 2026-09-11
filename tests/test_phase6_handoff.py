import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
import time
import httpx
import config
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from services.handoff_service import HandoffService
from api.server import app
from utils.dto_builders import target_to_dto

async def test_phase6_handoff():
    print("=== Testing Phase 6: Auto-Handoff System (Mister AI Integration) ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    username = f"handoff_test_{int(time.time())}"

    async with AsyncSessionLocal() as session:
        # Create campaign and target
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase6_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        await target_repo.add_targets_bulk(session, campaign_id, [username])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, username)
        assert target is not None, "Target must exist"
        
        # Populate target intel
        await target_repo.update_profile(
            session=session,
            target_id=target.id,
            profile_notes="Crypto trader, looking for long-term AI partner",
            profile_confidence=3,
            source_group="@BinanceSignals"
        )
        await target_repo.update_triage(
            session=session,
            target_id=target.id,
            triage_status="RELATIONAL",
            raw_chat="User: Hey tell me about your bot\nBot: Sure!"
        )
        await session.commit()
        target_id = target.id
        print(f"2. Inserted RELATIONAL target '{username}' (ID: {target_id}).")

    # 2. Test Handoff Initiation (Human Approval Required -> 'pending')
    print("\n3. Testing HandoffService.initiate_handoff() (Defaults to 'pending')...")
    status = await HandoffService.initiate_handoff(target_id)
    print("Handoff Status Result:", status)
    assert status == "pending"

    async with AsyncSessionLocal() as session:
        t = await target_repo.get_target_by_id(session, target_id)
        await session.refresh(t)
        assert t.handoff_status == "pending"
        print("--> DB Handoff Status verified:", t.handoff_status)

    # 3. Test REST API Handoff Approve Endpoint (Human Approval -> 'sent' + Network Call outside DB lock)
    print("\n4. Testing REST POST /api/v1/leads/{id}/handoff/approve...")
    headers = {"X-API-Key": config.DM_API_KEY}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/leads/{target_id}/handoff/approve", headers=headers)
        print("Approve Response Status Code:", response.status_code)
        print("Approve Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        print("--> REST Handoff Approve Endpoint PASSED!")

    async with AsyncSessionLocal() as session:
        t_approved = await target_repo.get_target_by_id(session, target_id)
        await session.refresh(t_approved)
        assert t_approved.handoff_status == "sent"
        assert t_approved.handoff_attempts >= 1
        print("--> DB Handoff Status after approval verified:", t_approved.handoff_status)

    # 4. Test Retry Failed Handoffs Service
    print("\n5. Testing HandoffService.retry_failed_handoffs()...")
    async with AsyncSessionLocal() as session:
        # Temporarily mark as handoff_failed
        t_fail = await target_repo.get_target_by_id(session, target_id)
        t_fail.handoff_status = "handoff_failed"
        await session.commit()

    successes = await HandoffService.retry_failed_handoffs()
    print("Retried Successes Count:", successes)
    assert successes >= 1

    async with AsyncSessionLocal() as session:
        t_recovered = await target_repo.get_target_by_id(session, target_id)
        await session.refresh(t_recovered)
        assert t_recovered.handoff_status == "sent"
        print("--> Retry Failed Handoffs Recovery PASSED!")

    print("\n=== ALL PHASE 6 HANDOFF TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase6_handoff())
