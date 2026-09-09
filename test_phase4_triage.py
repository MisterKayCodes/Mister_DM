import asyncio
import os
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from core.triage_engine import TriageEngine
from services.triage_service import TriageService
from utils.dto_builders import target_to_dto

async def test_phase4_triage():
    print("=== Testing Phase 4: Triage Engine & Groq Classification ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    async with AsyncSessionLocal() as session:
        # Fetch or create test campaign
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase4_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        # Insert test target
        username = "triage_test_target"
        await target_repo.add_targets_bulk(session, campaign_id, [username])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, username)
        assert target is not None, "Target must exist"
        
        # 2. Test Transactional Classification
        print("\n2. Testing TRANSACTIONAL classification...")
        chat_transactional = "User: How much does your trading signal software cost?\nBot: It's $50/month."
        verdict1 = await TriageService.classify_lead(target.id, chat_transactional)
        print("Verdict:", verdict1)
        assert verdict1 == "TRANSACTIONAL"

        # Verify DB updated
        t1 = await target_repo.get_target_by_id(session, target.id)
        await session.refresh(t1)
        assert t1.triage_status == "TRANSACTIONAL"
        print("--> DB Triage Status verified:", t1.triage_status)

        # 3. Test Relational Classification
        print("\n3. Testing RELATIONAL classification...")
        chat_relational = "User: Hey man nice to meet you, tell me more about your life!\nBot: Hey friend!"
        verdict2 = await TriageService.classify_lead(target.id, chat_relational)
        print("Verdict:", verdict2)
        assert verdict2 == "RELATIONAL"

        # Verify DB updated
        t2 = await target_repo.get_target_by_id(session, target.id)
        await session.refresh(t2)
        assert t2.triage_status == "RELATIONAL"
        print("--> DB Triage Status verified:", t2.triage_status)

    # 4. Test Prompt Versioning & Auto-Archiving
    print("\n4. Testing Prompt Versioning & Auto-Archiving...")
    original_prompt = TriageEngine.load_prompt()
    original_text = original_prompt["system_prompt"]

    # Save a new prompt
    new_prompt_text = original_text + "\n\nNote: Version 2 test prompt edit."
    saved_data = TriageEngine.save_prompt(new_prompt_text)
    print("Saved New Version:", saved_data["version"])

    # Check history
    history = TriageEngine.list_prompt_history()
    print("Prompt History Items Count:", len(history))
    assert len(history) > 0, "History should contain archived prompt"
    
    # Restore original prompt from history
    archived_file = history[0]["filename"]
    print(f"Restoring archived prompt ({archived_file})...")
    restored_data = TriageEngine.restore_prompt(archived_file)
    print("Restored Version:", restored_data["version"])
    assert TriageEngine.load_prompt()["system_prompt"] == original_text
    print("--> Prompt Rollback PASSED!")

    print("\n=== ALL PHASE 4 TRIAGE TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase4_triage())
