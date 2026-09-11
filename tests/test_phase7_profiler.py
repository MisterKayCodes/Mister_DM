import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
import time
import httpx
import config
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from api.server import app
from utils.dto_builders import target_to_dto

async def test_phase7_profiler():
    print("=== Testing Phase 7: Mister Profiler Intake Pipeline ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    headers = {"X-API-Key": config.DM_API_KEY}
    ts = int(time.time())
    group_name = f"@BinanceSignals_{ts}"
    user_single = f"profiler_single_{ts}"
    user_bulk1 = f"profiler_bulk1_{ts}"
    user_bulk2 = f"profiler_bulk2_{ts}"

    async with AsyncSessionLocal() as session:
        # Create a campaign matching group_name
        campaign = await campaign_repo.insert_campaign(session, f"Campaign_{group_name}", account_id=1)
        await session.commit()
        campaign_id = campaign.id
        print(f"2. Created campaign 'Campaign_{group_name}' (ID: {campaign_id}).")

    # 2. Test Single Intake with Source Group Auto-Match
    print("\n3. Testing Single Intake (POST /api/v1/leads/intake) with source_group auto-match...")
    payload_single = {
        "username": user_single,
        "source_group": group_name,
        "profile_notes": "Forex & Crypto trader, high net worth",
        "profile_confidence": 2
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leads/intake", json=payload_single, headers=headers)
        print("Single Intake Response Status Code:", response.status_code)
        print("Single Intake Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        print("--> Single Intake & Auto-Match PASSED!")

    # 3. Test Atomic Merge (Re-sending same lead with higher confidence and notes)
    print("\n4. Testing Atomic Merge Strategy (Re-sending same lead)...")
    payload_merge = {
        "username": user_single,
        "source_group": group_name,
        "profile_notes": "Forex & Crypto trader, high net worth, active in BTC groups",
        "profile_confidence": 3
    }

    async with AsyncSessionLocal() as session:
        # Set target status to 'sent' before merge to verify status is never reset
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, user_single)
        target.status = "sent"
        await session.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leads/intake", json=payload_merge, headers=headers)
        print("Merge Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json()["data"]["result"] == "merged"

    async with AsyncSessionLocal() as session:
        t_merged = await target_repo.get_target_by_campaign_and_username(session, campaign_id, user_single)
        await session.refresh(t_merged)
        assert t_merged.profile_confidence == 3
        assert t_merged.status == "sent", "Outreach status MUST NOT be overwritten during merge"
        print("--> Atomic Merge Strategy PASSED!")

    # 4. Test Bulk Batch Intake (POST /api/v1/leads/intake/bulk)
    print("\n5. Testing Bulk Batch Intake (POST /api/v1/leads/intake/bulk)...")
    payload_bulk = {
        "leads": [
            {
                "username": user_bulk1,
                "source_group": group_name,
                "profile_notes": "Bulk lead 1 note",
                "profile_confidence": 1
            },
            {
                "username": user_bulk2,
                "source_group": group_name,
                "profile_notes": "Bulk lead 2 note",
                "profile_confidence": 2
            },
            {
                "username": user_single,  # Duplicate to test merge inside bulk
                "source_group": group_name,
                "profile_notes": "Bulk duplicate merge test note",
                "profile_confidence": 3
            }
        ]
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leads/intake/bulk", json=payload_bulk, headers=headers)
        print("Bulk Intake Response Status Code:", response.status_code)
        print("Bulk Intake Response JSON:", response.json())
        assert response.status_code == 200
        summary = response.json()["summary"]
        assert summary["total"] == 3
        assert summary["created"] == 2
        assert summary["merged"] == 1
        assert summary["failed"] == 0
        print("--> Bulk Batch Intake PASSED!")

    print("\n=== ALL PHASE 7 PROFILER INTAKE TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase7_profiler())
