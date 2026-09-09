import asyncio
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from utils.dto_builders import target_to_dto

async def test_phase3_schema():
    print("=== Testing Phase 3: Schema Upgrades & Lead Intelligence ===")
    
    # 1. Initialize database & run auto-migration checks
    print("\n1. Running init_db() auto-migrations...")
    await init_db()
    print("--> Database initialized & auto-migrations verified!")

    async with AsyncSessionLocal() as session:
        # Create a dummy campaign if none exists
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase3_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id
            
        # 2. Add target with Phase 3 Lead Intelligence
        test_username = "phase3_test_lead"
        print(f"\n2. Inserting target '{test_username}' with rich profile notes...")
        await target_repo.add_targets_bulk(session, campaign_id, [test_username])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, test_username)
        assert target is not None, "Target should exist after insertion"
        
        # Update profile
        await target_repo.update_profile(
            session=session,
            target_id=target.id,
            profile_notes="Forex trader, ~45, active in BTC groups",
            profile_confidence=3,
            source_group="@BinanceSignals"
        )
        # Update triage
        await target_repo.update_triage(
            session=session,
            target_id=target.id,
            triage_status="RELATIONAL",
            raw_chat="User: Hey tell me more about your bot\nBot: Sure!"
        )
        await session.commit()
        
        # 3. Retrieve and verify via Repository
        print("\n3. Querying target by triage status 'RELATIONAL'...")
        relational_leads = await target_repo.get_targets_by_triage(session, "RELATIONAL")
        assert len(relational_leads) > 0, "Should find at least 1 RELATIONAL lead"
        
        test_lead = relational_leads[0]
        dto = target_to_dto(test_lead)
        
        print("\nFetched Target DTO:")
        print("Username:", dto["username"])
        print("Triage Status:", dto["triage_status"])
        print("Profile Notes:", dto["profile_notes"])
        print("Profile Confidence:", dto["profile_confidence"])
        print("Source Group:", dto["source_group"])
        
        assert dto["triage_status"] == "RELATIONAL"
        assert dto["profile_notes"] == "Forex trader, ~45, active in BTC groups"
        assert dto["profile_confidence"] == 3
        assert dto["source_group"] == "@BinanceSignals"
        
        print("--> DTO validation PASSED!")

    print("\n=== ALL PHASE 3 SCHEMA TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase3_schema())
