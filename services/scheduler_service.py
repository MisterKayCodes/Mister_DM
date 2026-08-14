import asyncio
import random
from services.campaign_service import CampaignService
from services.target_service import TargetService
from services.template_service import TemplateService
from services.account_service import AccountService
from services.telethon_client import send_outreach_message

# Toggle for safety during dev
DRY_RUN = False
# Override delays for testing (10-20 seconds)
DEV_DELAY_MIN = 10
DEV_DELAY_MAX = 20

class SchedulerService:
    """
    Manages the background execution of campaigns.
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
            # #FIXED: Consistent 3-tuple return on all exit paths.
            # PREVENTED FAILURE: Handler unpacks (success, msg, actual_status). A 2-tuple here
            # causes a ValueError at runtime the moment any campaign is missing from the DB.
            return False, "Campaign not found.", "unknown"
            
        if campaign["status"] == "completed":
            return False, "Campaign is already completed.", campaign["status"]
            
        account_id = campaign["account_id"]
        account = await AccountService.get_account_by_id(account_id)
        if not account:
            return False, "Account missing.", campaign["status"]
            
        summary = await CampaignService.get_campaign_summary(campaign_id)
        if summary["templates_count"] == 0:
            return False, "Add at least one template before starting.", campaign["status"]
            
        pending_target = await TargetService.get_next_pending_target(campaign_id)
        if not pending_target:
            return False, "No pending targets left.", campaign["status"]
            
        # 2. Update Status
        await CampaignService.update_campaign_status(campaign_id, "running")
        
        # 3. Start Background Task
        task = asyncio.create_task(SchedulerService._campaign_loop(campaign_id, account))
        SchedulerService.active_campaigns[campaign_id] = task
        
        # Re-fetch true status from DB — never assume what we just wrote
        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign started.", updated["status"] if updated else "running"

    @staticmethod
    async def _campaign_loop(campaign_id: int, account: dict):
        """
        The core engine loop.
        """
        print(f"[SCHEDULER] Started campaign {campaign_id}")
        
        try:
            while True:
                # Re-fetch campaign to check if status was changed (e.g. paused)
                campaign = await CampaignService.get_campaign_by_id(campaign_id)
                if not campaign or campaign["status"] != "running":
                    print(f"[SCHEDULER] Campaign {campaign_id} no longer running. Exiting loop.")
                    break
                    
                target = await TargetService.get_next_pending_target(campaign_id)
                if not target:
                    print(f"[SCHEDULER] Campaign {campaign_id} completed.")
                    await CampaignService.update_campaign_status(campaign_id, "completed")
                    break
                    
                templates = await TemplateService.get_templates_by_campaign(campaign_id)
                if not templates:
                    print(f"[SCHEDULER] Campaign {campaign_id} has no templates. Stopping.")
                    await CampaignService.update_campaign_status(campaign_id, "paused")
                    break
                    
                template = random.choice(templates)
                message_text = template["content"]
                
                print(f"[SCHEDULER] Processing target {target['username']}...")
                
                # #FIXED: Handoff immutable target ID for reply tracking.
                # WHY: send_outreach_message now resolves the immutable telegram_user_id. We must 
                # save it during the 'sent' state transition so the background listener can match replies.
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
                
                # Check soft-pause before sleeping
                campaign_check = await CampaignService.get_campaign_by_id(campaign_id)
                if campaign_check and campaign_check["status"] != "running":
                    print(f"[SCHEDULER] Campaign {campaign_id} soft-paused. Exiting before sleep.")
                    break
                
                # Delay calculation (override during dev)
                delay_min = DEV_DELAY_MIN if DRY_RUN else account["delay_min"] * 60
                delay_max = DEV_DELAY_MAX if DRY_RUN else account["delay_max"] * 60
                sleep_time = random.randint(delay_min, delay_max)
                
                print(f"[SCHEDULER] Sleeping for {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
                
        except Exception as e:
            print(f"[SCHEDULER] Fatal error in campaign {campaign_id}: {e}")
            await CampaignService.update_campaign_status(campaign_id, "stopped")
        finally:
            SchedulerService.active_campaigns.pop(campaign_id, None)
            print(f"[SCHEDULER] Campaign {campaign_id} loop terminated.")

    @staticmethod
    async def pause_campaign(campaign_id: int) -> tuple[bool, str, str]:
        """
        Soft-pauses the campaign. Returns (success, message, actual_new_status).
        """
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "Campaign not found.", "unknown"
            
        if campaign["status"] != "running":
            return False, f"Campaign is currently {campaign['status']}, not running.", campaign["status"]
            
        await CampaignService.update_campaign_status(campaign_id, "paused")
        
        # Re-fetch true status from DB
        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign paused. It will stop after the current iteration finishes.", updated["status"] if updated else "paused"

    @staticmethod
    async def stop_campaign(campaign_id: int) -> tuple[bool, str, str]:
        """
        Soft-stops the campaign. Returns (success, message, actual_new_status).
        """
        campaign = await CampaignService.get_campaign_by_id(campaign_id)
        if not campaign:
            return False, "Campaign not found.", "unknown"
            
        await CampaignService.update_campaign_status(campaign_id, "stopped")
        
        # Re-fetch true status from DB
        updated = await CampaignService.get_campaign_by_id(campaign_id)
        return True, "Campaign stopped.", updated["status"] if updated else "stopped"
