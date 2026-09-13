import asyncio
import os
import sys
import time

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from data.models.target import Target
from core.prompt_builder import build_personalized_opener_prompt


async def test_phase9():
    print("==========================================")
    print("  RUNNING PHASE 9 (PROFILER) TEST SUITE   ")
    print("==========================================")

    # Initialize DB
    await init_db()

    async with AsyncSessionLocal() as session:
        # Test 1: Setup test campaign and targets
        print("\n[TEST 1] Creating test campaign & targets for ingest...")
        ts = int(time.time())
        campaign = await campaign_repo.insert_campaign(session, f"Phase 9 Test Campaign {ts}")

        target1 = Target(
            campaign_id=campaign.id,
            username=f"active_trader_{ts}",
            note="Active User",
            status="pending"
        )
        target2 = Target(
            campaign_id=campaign.id,
            username=f"silent_lurker_{ts}",
            note="Silent User",
            status="pending"
        )
        session.add(target1)
        session.add(target2)
        await session.commit()
        await session.refresh(target1)
        await session.refresh(target2)

        assert target1.lead_type == "LURKER", f"Expected default lead_type LURKER, got {target1.lead_type}"
        print(f"[PASS] Targets created with default lead_type='LURKER'! Target IDs: {target1.id}, {target2.id}")

        # Test 2: Bulk Ingest DeepSeek Profiles
        print("\n[TEST 2] Ingesting DeepSeek JSON payload...")
        mock_profiles = [
            {
                "username": f"active_trader_{ts}",
                "lead_type": "ACTIVE",
                "profile_notes": "Crypto trader. Frustrated with high fees. High net worth.",
                "goal": "BUY_INDICATOR",
                "timezone": "Africa/Lagos"
            },
            {
                "username": f"silent_lurker_{ts}",
                "lead_type": "LURKER",
                "profile_notes": None,
                "goal": "JOIN_GROUP",
                "timezone": "Europe/London"
            }
        ]

        active_cnt, lurker_cnt = await target_repo.ingest_deepseek_profiles(
            session=session,
            campaign_id=campaign.id,
            profiles=mock_profiles
        )
        await session.commit()

        assert active_cnt == 1, f"Expected 1 active count, got {active_cnt}"
        assert lurker_cnt == 1, f"Expected 1 lurker count, got {lurker_cnt}"

        # Re-fetch targets to verify updated fields
        t1_updated = await target_repo.get_target_by_id(session, target1.id)
        t2_updated = await target_repo.get_target_by_id(session, target2.id)

        assert t1_updated.lead_type == "ACTIVE", f"Expected ACTIVE, got {t1_updated.lead_type}"
        assert "Crypto trader" in t1_updated.profile_notes
        assert t1_updated.profile_confidence == 5
        assert t1_updated.goal == "BUY_INDICATOR"
        assert t1_updated.timezone == "Africa/Lagos"

        assert t2_updated.lead_type == "LURKER"
        assert t2_updated.timezone == "Europe/London"
        print(f"[PASS] Profile ingestion verified: Matched {active_cnt} ACTIVE and {lurker_cnt} LURKER leads!")

        # Test 3: Personalized Opener Prompt Construction
        print("\n[TEST 3] Verifying build_personalized_opener_prompt()...")
        prompt = build_personalized_opener_prompt(
            persona_name="Sarah Chen",
            contact_name=t1_updated.username,
            profile_notes=t1_updated.profile_notes,
            template_examples=["Hey, quick question about trading.", "Saw your post earlier!"]
        )

        assert "Sarah Chen" in prompt
        assert t1_updated.username.upper() in prompt
        assert "Crypto trader" in prompt
        assert "Saw your post earlier!" in prompt
        print("[PASS] build_personalized_opener_prompt() correctly formats system instructions!")

        print("\n[SUCCESS] ALL PHASE 9 TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    asyncio.run(test_phase9())
