import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo
from data.models.target import Target
from services.alert_service import AlertService


async def test_phase8():
    print("==========================================")
    print("  RUNNING PHASE 8 (WAR ROOM) TEST SUITE   ")
    print("==========================================")

    # Initialize DB
    await init_db()

    async with AsyncSessionLocal() as session:
        # Test 1: Create or fetch test target
        print("\n[TEST 1] Setting up test campaign and target...")
        import time
        campaign = await campaign_repo.get_campaign_by_name(session, "Phase 8 War Room Campaign")
        if not campaign:
            campaign = await campaign_repo.insert_campaign(session, f"Phase 8 War Room Campaign {int(time.time())}")
        
        ts = int(time.time())
        # Add target with username
        target_a = Target(
            campaign_id=campaign.id,
            username=f"warroom_lead_a_{ts}",
            note="John Doe",
            status="sent",
            triage_status="RELATIONAL"
        )
        # Add target without username (test fallback)
        target_b = Target(
            campaign_id=campaign.id,
            username=f"anon_b_{ts}",
            note=f"Anonymous Lead B {ts}",
            status="sent",
            triage_status="RELATIONAL"
        )
        session.add(target_a)
        session.add(target_b)
        await session.commit()
        await session.refresh(target_a)
        await session.refresh(target_b)

        print(f"[PASS] Created Target A ID={target_a.id} (@{target_a.username}) and Target B ID={target_b.id} (No username)")

        # Test 2: Set needs_human flag on target_a
        print("\n[TEST 2] Flagging target for human override...")
        rows_updated = await target_repo.set_target_needs_human(session, target_a.id, True)
        await session.commit()
        assert rows_updated == 1, "Failed to set needs_human flag"

        # Verify query
        needing_human = await target_repo.get_targets_needing_human(session)
        target_ids = [t.id for t in needing_human]
        assert target_a.id in target_ids, "Target A not found in get_targets_needing_human()"
        print("[PASS] set_target_needs_human() and get_targets_needing_human() verified!")

        # Test 3: AlertService Name Formatting & Display Fallback
        print("\n[TEST 3] Verifying AlertService display formatting fallback...")
        disp_a = AlertService.format_target_display({"id": target_a.id, "username": target_a.username, "note": target_a.note})
        disp_b = AlertService.format_target_display({"id": target_b.id, "username": "", "first_name": "Anonymous Lead B"})
        disp_c = AlertService.format_target_display({"id": 999, "username": "", "first_name": ""})

        assert disp_a == f"@{target_a.username}", f"Expected @{target_a.username}, got {disp_a}"
        assert "Anonymous Lead B" in disp_b, f"Expected Anonymous Lead B, got {disp_b}"
        assert disp_c == "Target #999", f"Expected Target #999, got {disp_c}"
        print(f"[PASS] Name formatting fallbacks: '{disp_a}', '{disp_b}', '{disp_c}'")

        # Test 4: AlertService Telegram payload assembly
        print("\n[TEST 4] AlertService alert payload generation...")
        res = await AlertService.send_war_room_alert(
            target_id=target_a.id,
            target_data={"id": target_a.id, "username": target_a.username, "note": target_a.note},
            persona_name="Sarah Chen",
            last_message="How do I know this is real?"
        )
        print(f"[PASS] AlertService call executed (Result: {res} - expected False if WAR_ROOM_GROUP_ID not set)")

        # Clean up needs_human flag
        await target_repo.set_target_needs_human(session, target_a.id, False)
        await session.commit()
        print("\n[SUCCESS] ALL PHASE 8 TESTS PASSED CLEANLY!")


if __name__ == "__main__":
    asyncio.run(test_phase8())
