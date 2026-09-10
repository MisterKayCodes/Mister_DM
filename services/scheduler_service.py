import asyncio
import random
import logging
from services.campaign_service import CampaignService
from services.target_service import TargetService
from services.template_service import TemplateService
from services.account_service import AccountService
from services.blacklist_service import BlacklistService
from services.message_service import MessageService
from services.telethon_client import send_outreach_message
from clients.simulator_client import simulator_client
from clients.exceptions import APIUnavailableError, APIResponseError
from data.database import AsyncSessionLocal
from data.repositories import account_repo

logger = logging.getLogger(__name__)

# Toggle for safety during dev
DRY_RUN = False
DEV_DELAY_MIN = 10
DEV_DELAY_MAX = 20

class SchedulerService:
    """
    Manages the background execution of campaigns.
    Delegates DMs to Mister Simulator API when session_name is available,
    with fallback to local account session_string.
    Enforces Blacklist checks, Daily Quotas, Outbound Message Logging, and explicit task cancellations.
    """
    
    # Task registry
    active_campaigns: dict[int, asyncio.Task] = {}

    @staticmethod
    async def start_campaign(campaign_id: int) -> tuple[bool, str, str]:
        """
        Validates and starts a campaign in the background.
        Returns (success, message, actual_new_status).
        """
        if campaign_id in SchedulerService.active_campaigns:
            campaign = await CampaignService.get_campaign_by_id(campaign_id)
            return False, "Campaign is already running.", campaign["status"] if campaign else "unknown"
            
        # 1. Validation
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "Campaign not found.", "unknown"
            
        if campaign["status"] == "completed":
            return False, "Campaign is already completed.", campaign["status"]

        # Check session availability (Simulator session or local account)
        account = None
        session_name = campaign.get("session_name")
        
        if not session_name:
            # Fallback to local account
            account_id = campaign.get("account_id")
            if account_id:
                account = await AccountService.get_account_by_id(account_id)
            
            # If no local account, attempt to borrow a dm_warrior session from Simulator
            if not account:
                dm_warriors = await simulator_client.get_dm_warrior_sessions()
                if dm_warriors:
                    session_name = dm_warriors[0].get("name") or dm_warriors[0].get("session_name")
                
            if not session_name and not account:
                return False, "No active Simulator session or local account assigned to campaign.", campaign["status"]
            
        summary = await CampaignService.get_campaign_summary(campaign_id)
        if summary["templates_count"] == 0:
            return False, "Add at least one template before starting.", campaign["status"]
            
        pending_target = await TargetService.get_next_pending_target(campaign_id)
        if not pending_target:
            return False, "No pending targets left.", campaign["status"]
            
        # 2. Update Status
        await CampaignService.update_campaign_status(campaign_id, "running")
        
        # 3. Start Background Task
        task = asyncio.create_task(SchedulerService._campaign_loop(campaign_id, session_name, account))
        SchedulerService.active_campaigns[campaign_id] = task
        
        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign started.", updated["status"] if updated else "running"

    @staticmethod
    async def _campaign_loop(campaign_id: int, session_name: str | None, account: dict | None):
        """
        The core engine loop. Delegating DM sends to Mister Simulator.
        """
        logger.info(f"[SCHEDULER] Started campaign {campaign_id} (Session: {session_name or 'Local Account'})")
        
        try:
            while True:
                campaign = await CampaignService.get_campaign_by_id(campaign_id)
                if not campaign or campaign["status"] != "running":
                    logger.info(f"[SCHEDULER] Campaign {campaign_id} no longer running. Exiting loop.")
                    break
                    
                target = await TargetService.get_next_pending_target(campaign_id)
                if not target:
                    logger.info(f"[SCHEDULER] Campaign {campaign_id} completed.")
                    await CampaignService.update_campaign_status(campaign_id, "completed")
                    break

                # -------------------------------------------------------------
                # 1. Blacklist Check
                # -------------------------------------------------------------
                is_allowed = await BlacklistService.check_target_allowed(
                    username=target["username"],
                    telegram_user_id=target.get("telegram_user_id")
                )
                if not is_allowed:
                    logger.info(f"[SCHEDULER] Target @{target['username']} is blacklisted. Skipping.")
                    await TargetService.update_target_status(
                        target_id=target["id"],
                        new_status="skipped",
                        telegram_user_id=None
                    )
                    continue

                # -------------------------------------------------------------
                # 2. Daily Quota Check (For local accounts)
                # -------------------------------------------------------------
                if account and account.get("id"):
                    acc_id = account["id"]
                    async with AsyncSessionLocal() as session:
                        await account_repo.reset_daily_counter_if_needed(session, acc_id)
                        remaining = await account_repo.get_remaining_quota(session, acc_id)
                        await session.commit()

                    if remaining <= 0:
                        logger.warning(f"[SCHEDULER] Account {acc_id} hit daily quota limit. Pausing campaign {campaign_id}.")
                        await CampaignService.update_campaign_status(campaign_id, "paused")
                        break

                templates = await TemplateService.get_templates_by_campaign(campaign_id)
                if not templates:
                    logger.info(f"[SCHEDULER] Campaign {campaign_id} has no templates. Stopping.")
                    await CampaignService.update_campaign_status(campaign_id, "paused")
                    break
                    
                template = random.choice(templates)
                message_text = template["content"]
                template_id = template["id"]
                
                logger.info(f"[SCHEDULER] Processing target @{target['username']} with Template #{template_id}...")
                
                success = False
                resolved_user_id = None
                
                # Delegation Path A: Mister Simulator API
                target_session = session_name or campaign.get("session_name")
                if target_session:
                    try:
                        res = await simulator_client.send_dm(
                            session_name=target_session,
                            target_username=target["username"],
                            message_text=message_text
                        )
                        success = res.get("status") == "success" or res.get("ok", False)
                        resolved_user_id = res.get("telegram_user_id") or res.get("user_id")
                    except APIUnavailableError as e:
                        logger.error(f"[SCHEDULER] Simulator API unavailable: {e}. Pausing campaign {campaign_id}.")
                        await CampaignService.update_campaign_status(campaign_id, "paused")
                        break
                    except APIResponseError as e:
                        logger.error(f"[SCHEDULER] Simulator API error: {e}")
                        success = False
                # Delegation Path B: Legacy Local Account Fallback
                elif account and account.get("session_string"):
                    success, resolved_user_id = await send_outreach_message(
                        session_string=account["session_string"],
                        username=target["username"],
                        message_text=message_text,
                        dry_run=DRY_RUN
                    )

                new_status = "sent" if success else "failed"
                await TargetService.update_target_status(
                    target_id=target["id"], 
                    new_status=new_status, 
                    telegram_user_id=resolved_user_id if success else None
                )

                # -------------------------------------------------------------
                # 3. Log Outbound Message (With Template ID Attribution!)
                # -------------------------------------------------------------
                if success:
                    acc_id = account.get("id") if account else campaign.get("account_id")
                    ok_log, log_res = await MessageService.log_message(
                        target_id=target["id"],
                        direction="OUTBOUND",
                        message_type="TEXT",
                        account_id=acc_id,
                        text=message_text,
                        telegram_message_id=resolved_user_id,
                        template_id=template_id
                    )
                    if not ok_log:
                        logger.error(f"[SCHEDULER] Failed to log outbound message for target {target['id']}: {log_res}")

                    if account and account.get("id"):
                        async with AsyncSessionLocal() as session:
                            await account_repo.increment_daily_counter(session, account["id"])
                            await session.commit()

                campaign_check = await CampaignService.get_campaign_by_id(campaign_id)
                if campaign_check and campaign_check["status"] != "running":
                    logger.info(f"[SCHEDULER] Campaign {campaign_id} soft-paused. Exiting before sleep.")
                    break
                
                delay_min = DEV_DELAY_MIN if DRY_RUN else (account["delay_min"] * 60 if account else 60)
                delay_max = DEV_DELAY_MAX if DRY_RUN else (account["delay_max"] * 60 if account else 180)
                sleep_time = random.randint(delay_min, delay_max)
                
                logger.info(f"[SCHEDULER] Sleeping for {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info(f"[SCHEDULER] Campaign {campaign_id} loop received Cancellation signal. Exiting cleanly.")
            raise
        except Exception as e:
            logger.error(f"[SCHEDULER] Fatal error in campaign {campaign_id}: {e}", exc_info=True)
            await CampaignService.update_campaign_status(campaign_id, "stopped")
        finally:
            SchedulerService.active_campaigns.pop(campaign_id, None)
            logger.info(f"[SCHEDULER] Campaign {campaign_id} loop terminated.")

    @staticmethod
    async def pause_campaign(campaign_id: int) -> tuple[bool, str, str]:
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "Campaign not found.", "unknown"
            
        if campaign["status"] != "running":
            return False, f"Campaign is currently {campaign['status']}, not running.", campaign["status"]
            
        await CampaignService.update_campaign_status(campaign_id, "paused")
        task = SchedulerService.active_campaigns.pop(campaign_id, None)
        if task:
            task.cancel()

        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign paused.", updated["status"] if updated else "paused"

    @staticmethod
    async def stop_campaign(campaign_id: int) -> tuple[bool, str, str]:
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "Campaign not found.", "unknown"
            
        await CampaignService.update_campaign_status(campaign_id, "stopped")
        task = SchedulerService.active_campaigns.pop(campaign_id, None)
        if task:
            task.cancel()

        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign stopped.", updated["status"] if updated else "stopped"

    @staticmethod
    async def stop_all():
        """Cleanly cancels all running campaign tasks on server shutdown."""
        campaign_ids = list(SchedulerService.active_campaigns.keys())
        for cid in campaign_ids:
            task = SchedulerService.active_campaigns.pop(cid, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("[SCHEDULER] All active campaigns cleanly stopped.")
