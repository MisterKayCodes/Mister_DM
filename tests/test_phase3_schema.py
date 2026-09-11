import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from utils.dto_builders import target_to_dto

async def test_phase3_schema():
    print("=== Testing Phase 3: Target Schema & Lead Intelligence Upgrades ===")
    
    # 1. Initialize DB (Triggers auto-migration ALTER TABLE checks)
    await init_db()
    print("1. Database initialized with auto-migrations.")

    async with AsyncSessionLocal() as session:
        # Get or create test campaign
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase3_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        # Insert target
        username = "intel_test_target"
        await target_repo.add_targets_bulk(session, campaign_id, [username])
        await session.commit()

        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, username)
        assert target is not None, "Target should exist"
        target_id = target.id
        print(f"2. Created test target '{username}' (ID: {target_id}).")

        # 2. Test update_profile repo method
        print("\n3. Testing target_repo.update_profile()...")
        await target_repo.update_profile(
            session=session,
            target_id=target_id,
            profile_notes="Crypto trader, looking for signal automation tools",
            profile_confidence=2,
            source_group="@BinanceSignals"
        )
        await session.commit()

        # 3. Test update_triage repo method
        print("\n4. Testing target_repo.update_triage()...")
        await target_repo.update_triage(
            session=session,
            target_id=target_id,
            triage_status="RELATIONAL",
            raw_chat="User: Hey tell me about your bot\nBot: Sure, we automate DMs!"
        )
        await session.commit()

        # 4. Verify target DTO shape
        print("\n5. Testing target_to_dto()...")
        updated_target = await target_repo.get_target_by_id(session, target_id)
        dto = target_to_dto(updated_target)
        
        print("--> Target DTO Output:")
        for k, v in dto.items():
            print(f"    {k}: {v}")

        assert dto["triage_status"] == "RELATIONAL"
        assert dto["profile_confidence"] == 2
        assert dto["source_group"] == "@BinanceSignals"
        assert dto["profile_notes"] == "Crypto trader, looking for signal automation tools"
        print("\n--> All Schema DTO Fields Verified Successfully!")

    print("\n=== ALL PHASE 3 SCHEMA TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase3_schema())
