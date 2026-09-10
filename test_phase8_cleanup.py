import asyncio
import time
import httpx
from unittest.mock import AsyncMock, patch
import config
from data.database import init_db, AsyncSessionLocal
from data.repositories import target_repo, campaign_repo, blacklist_repo, template_repo, message_repo, account_repo
from services.scheduler_service import SchedulerService
from services.export_service import ExportService
from clients.simulator_client import simulator_client
from api.server import app

async def test_phase8_cleanup():
    print("=== Testing Phase 8: Scheduler Unification, Safety Nets & Template Analytics ===")
    
    # Mock simulator client for standalone unit testing environment
    simulator_client.get_dm_warrior_sessions = AsyncMock(return_value=[{"name": "dm_warrior_1"}])
    simulator_client.send_dm = AsyncMock(return_value={"status": "success", "telegram_user_id": 999888})

    # 1. Initialize DB
    await init_db()
    print("1. Database initialized.")

    headers = {"X-API-Key": config.DM_API_KEY}
    ts = int(time.time())
    blacklisted_username = f"p8_blacklisted_{ts}"
    quota_username = f"p8_quota_{ts}"
    valid_username = f"p8_valid_{ts}"
    sim_only_username = f"p8_sim_only_{ts}"
    cancel_username = f"p8_cancel_{ts}"

    # -----------------------------------------------------------------
    # TEST 1: Blacklist Safety Net Test
    # -----------------------------------------------------------------
    print("\n2. Testing Blacklist Safety Net...")
    async with AsyncSessionLocal() as session:
        campaign = await campaign_repo.insert_campaign(session, f"Phase8_Test_{ts}", account_id=1)
        campaign.session_name = "dm_warrior_1"
        await session.commit()
        campaign_id = campaign.id

        await template_repo.add_template(session, campaign_id, "Hello from Phase 8!")
        await session.commit()

        await target_repo.add_targets_bulk(session, campaign_id, [blacklisted_username])
        await blacklist_repo.add_to_blacklist(session, None, blacklisted_username, "Test reason")
        await session.commit()
        
        target = await target_repo.get_target_by_campaign_and_username(session, campaign_id, blacklisted_username)
        target_id = target.id

    ok, msg, status = await SchedulerService.start_campaign(campaign_id)
    assert ok, f"Failed to start campaign: {msg}"
    print(f"--> Campaign {campaign_id} started (Status: {status}). Sleeping 2s to allow loop iteration...")
    await asyncio.sleep(2)

    async with AsyncSessionLocal() as session:
        t_check = await target_repo.get_target_by_id(session, target_id)
        print(f"--> Target @{blacklisted_username} status after scheduler loop: {t_check.status}")
        assert t_check.status == "skipped", "Blacklisted target MUST be marked as 'skipped'"
        print("--> Blacklist Safety Net Test PASSED!")

    await SchedulerService.stop_campaign(campaign_id)

    # -----------------------------------------------------------------
    # TEST 2: Daily Quota Auto-Pause Test
    # -----------------------------------------------------------------
    print("\n3. Testing Daily Quota Auto-Pause...")
    async with AsyncSessionLocal() as session:
        acc = await account_repo.get_account_by_id(session, 1)
        if not acc:
            await account_repo.add_account(session, "Quota_Account", "session_str_mock", 1, 2, 1)
            acc = await account_repo.get_account_by_name(session, "Quota_Account")
        
        acc.daily_limit = 1
        acc.messages_sent_today = 1
        await session.commit()

        c_quota = await campaign_repo.insert_campaign(session, f"Quota_Campaign_{ts}", account_id=acc.id)
        await session.commit()
        c_quota_id = c_quota.id

        await template_repo.add_template(session, c_quota_id, "Quota test message")
        await target_repo.add_targets_bulk(session, c_quota_id, [quota_username])
        await session.commit()

    ok, msg, status = await SchedulerService.start_campaign(c_quota_id)
    await asyncio.sleep(2)

    async with AsyncSessionLocal() as session:
        c_check = await campaign_repo.get_campaign_by_id(session, c_quota_id)
        print(f"--> Campaign {c_quota_id} status after quota limit hit: {c_check.status}")
        assert c_check.status == "paused", "Campaign MUST auto-pause when account daily quota limit is hit"
        print("--> Daily Quota Auto-Pause Test PASSED!")

    async with AsyncSessionLocal() as session:
        acc = await account_repo.get_account_by_id(session, acc.id)
        if acc:
            acc.messages_sent_today = 0
            await session.commit()

    # -----------------------------------------------------------------
    # TEST 3: Outbound & Inbound Message Logging Gap Fix (Local Account)
    # -----------------------------------------------------------------
    print("\n4. Testing Outbound & Inbound Message Logging Gap Fix (Local Account)...")
    async with AsyncSessionLocal() as session:
        c_outbound = await campaign_repo.insert_campaign(session, f"Outbound_Campaign_{ts}", account_id=1)
        c_outbound.session_name = "dm_warrior_1"
        await session.commit()
        c_out_id = c_outbound.id

        await template_repo.add_template(session, c_out_id, "Outbound message test template")
        tmpls = await template_repo.get_templates_by_campaign(session, c_out_id)
        tmpl_id = tmpls[0].id

        await target_repo.add_targets_bulk(session, c_out_id, [valid_username])
        await session.commit()

        t_valid = await target_repo.get_target_by_campaign_and_username(session, c_out_id, valid_username)
        t_valid_id = t_valid.id

    from services import scheduler_service
    scheduler_service.DRY_RUN = True

    ok, msg, status = await SchedulerService.start_campaign(c_out_id)
    await asyncio.sleep(2)
    await SchedulerService.stop_campaign(c_out_id)

    async with AsyncSessionLocal() as session:
        msgs = await message_repo.get_messages_for_target(session, t_valid_id)
        assert len(msgs) >= 1, "Outbound message MUST be logged in messages table"
        out_msg = msgs[0]
        print(f"--> Logged Outbound Message ID: {out_msg.id}, Template ID: {out_msg.template_id}, Direction: {out_msg.direction}")
        assert out_msg.direction == "OUTBOUND"
        assert out_msg.template_id == tmpl_id
        print("--> Outbound Message Logging PASSED!")

    # -----------------------------------------------------------------
    # TEST 4: Pure Simulator Campaign (account_id = None) Logging & QA Pass
    # -----------------------------------------------------------------
    print("\n5. Testing Pure Simulator-Only Campaign (account_id = None)...")
    async with AsyncSessionLocal() as session:
        c_sim = await campaign_repo.insert_campaign(session, f"Pure_Simulator_Campaign_{ts}", account_id=None)
        c_sim.session_name = "dm_warrior_1"
        await session.commit()
        c_sim_id = c_sim.id

        await template_repo.add_template(session, c_sim_id, "Simulator pure test template")
        tmpls_sim = await template_repo.get_templates_by_campaign(session, c_sim_id)
        tmpl_sim_id = tmpls_sim[0].id

        await target_repo.add_targets_bulk(session, c_sim_id, [sim_only_username])
        await session.commit()

        t_sim = await target_repo.get_target_by_campaign_and_username(session, c_sim_id, sim_only_username)
        t_sim_id = t_sim.id

    ok, msg, status = await SchedulerService.start_campaign(c_sim_id)
    await asyncio.sleep(2)
    await SchedulerService.stop_campaign(c_sim_id)

    async with AsyncSessionLocal() as session:
        sim_msgs = await message_repo.get_messages_for_target(session, t_sim_id)
        assert len(sim_msgs) >= 1, "Simulator-only outbound message MUST be logged successfully"
        sim_out = sim_msgs[0]
        print(f"--> Simulator Outbound Message ID: {sim_out.id}, Account ID: {sim_out.account_id}, Direction: {sim_out.direction}")
        assert sim_out.account_id is None, "Pure Simulator campaign MUST log account_id as None (not hardcoded 1)"
        print("--> Pure Simulator Outbound Logging PASSED!")

    # Inbound webhook for Simulator-only lead
    webhook_sim_payload = {
        "session_name": "dm_warrior_1",
        "from_username": sim_only_username,
        "from_user_id": 888777,
        "message_text": "Hey from pure simulator lead!"
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/webhook/reply", json=webhook_sim_payload)
        assert res.status_code == 200

    async with AsyncSessionLocal() as session:
        sim_msgs_all = await message_repo.get_messages_for_target(session, t_sim_id)
        assert len(sim_msgs_all) >= 2
        sim_in = sim_msgs_all[-1]
        print(f"--> Simulator Inbound Message ID: {sim_in.id}, Account ID: {sim_in.account_id}, Direction: {sim_in.direction}")
        assert sim_in.account_id is None, "Pure Simulator inbound reply MUST log account_id as None"
        print("--> Pure Simulator Inbound Logging PASSED!")

    # -----------------------------------------------------------------
    # TEST 5: Export Service Verification
    # -----------------------------------------------------------------
    print("\n6. Testing ExportService.export_target()...")
    async with AsyncSessionLocal() as session:
        ok_exp, export_text = await ExportService.export_target(t_valid_id, session=session)
        assert ok_exp is True
        assert "No messages found" not in str(export_text)
        print("--> Export Service Verification PASSED!")

    # -----------------------------------------------------------------
    # TEST 6: Template Reply Rate Analytics Endpoint
    # -----------------------------------------------------------------
    print("\n7. Testing GET /api/v1/stats/templates Endpoint...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/stats/templates", headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        matched = [item for item in data if item["template_id"] == tmpl_sim_id]
        assert len(matched) == 1
        stat = matched[0]
        print(f"--> Pure Simulator Template #{tmpl_sim_id} Stats: Sent={stat['total_sent']}, Replied={stat['total_replied']}, Rate={stat['reply_rate_percent']}%")
        assert stat["total_sent"] == 1
        assert stat["total_replied"] == 1
        assert stat["reply_rate_percent"] == 100.0
        print("--> Template Performance Analytics PASSED!")

    # -----------------------------------------------------------------
    # TEST 7: Explicit Task Cancellation on stop_all()
    # -----------------------------------------------------------------
    print("\n8. Testing SchedulerService.stop_all() Cancellation...")
    async with AsyncSessionLocal() as session:
        c_cancel = await campaign_repo.insert_campaign(session, f"Cancel_Campaign_{ts}", account_id=1)
        c_cancel.session_name = "dm_warrior_1"
        await session.commit()
        c_cancel_id = c_cancel.id

        await template_repo.add_template(session, c_cancel_id, "Cancellation test template")
        await target_repo.add_targets_bulk(session, c_cancel_id, [cancel_username, f"target_2_{ts}"])
        await session.commit()

    ok_start, _, _ = await SchedulerService.start_campaign(c_cancel_id)
    assert ok_start is True
    assert c_cancel_id in SchedulerService.active_campaigns
    
    await SchedulerService.stop_all()
    assert c_cancel_id not in SchedulerService.active_campaigns
    print("--> Explicit Task Cancellation PASSED!")

    print("\n=== ALL PHASE 8 CLEANUP & QA TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_phase8_cleanup())
