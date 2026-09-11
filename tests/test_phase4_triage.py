import sys
import os
sys.path.append(os.path.abspath("."))

import asyncio
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from services.triage_service import TriageService
from core.triage_engine import load_prompt, save_prompt, list_prompt_history, restore_prompt

async def test_phase4_triage():
    print("=== Testing Phase 4: Triage Engine & Groq Classification ===")
    
    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    async with AsyncSessionLocal() as session:
        # Create campaign and target
        campaigns = await campaign_repo.get_all_campaigns(session)
        if not campaigns:
            campaign = await campaign_repo.insert_campaign(session, "Phase4_Test_Campaign", account_id=1)
            await session.commit()
            campaign_id = campaign.id
        else:
            campaign_id = campaigns[0].id

        target_name = "triage_test_target"
        await target_repo.add_targets_bulk(session, campaign_id, [target_name])
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, target_name)
        assert target is not None, "Target must exist"
        
        # Populate target intel profile notes
        await target_repo.update_profile(
            session=session,
            target_id=target.id,
            profile_notes="Crypto trader interested in automated tools",
            profile_confidence=2,
            source_group="@BinanceSignals"
        )
        await session.commit()
        target_id = target.id

    # 2. Test TRANSACTIONAL Classification
    print("\n2. Testing TRANSACTIONAL classification...")
    chat_transactional = "User: How much does your signal bot cost?\nBot: Hey! It's $50/month. Would you like to buy?"
    status_t = await TriageService.classify_lead(target_id, chat_transactional)
    print("Verdict:", status_t)
    assert status_t == "TRANSACTIONAL"

    async with AsyncSessionLocal() as session:
        t = await target_repo.get_target_by_id(session, target_id)
        assert t.triage_status == "TRANSACTIONAL"
        print("--> DB Triage Status verified:", t.triage_status)

    # 3. Test RELATIONAL Classification
    print("\n3. Testing RELATIONAL classification...")
    chat_relational = "User: Hey bro! Thanks for reaching out. How's your trading week going?\nBot: Hey man! Pretty good, hit some nice trades today."
    status_r = await TriageService.classify_lead(target_id, chat_relational)
    print("Verdict:", status_r)
    assert status_r == "RELATIONAL"

    async with AsyncSessionLocal() as session:
        t = await target_repo.get_target_by_id(session, target_id)
        assert t.triage_status == "RELATIONAL"
        print("--> DB Triage Status verified:", t.triage_status)

    # 4. Test Prompt Versioning & History Rollback
    print("\n4. Testing Prompt Versioning & Auto-Archiving...")
    current_prompt = load_prompt()
    version_id = save_prompt(current_prompt)
    print(f"Saved New Version: {version_id}")

    history = list_prompt_history()
    print(f"Prompt History Items Count: {len(history)}")
    assert len(history) >= 1

    restored_filename = history[0]["filename"]
    print(f"Restoring archived prompt ({restored_filename})...")
    restored = restore_prompt(restored_filename)
    print(f"Restored Version: {restored['version']}")
    assert restored["version"] == version_id
    print("--> Prompt Rollback PASSED!")

    print("\n=== ALL PHASE 4 TRIAGE TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase4_triage())
