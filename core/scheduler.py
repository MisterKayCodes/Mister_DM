import asyncio
import random
import logging
from config import DRY_RUN, DEV_DELAY_MIN, DEV_DELAY_MAX
from data.database import AsyncSessionLocal
from data.repositories import account_repo
from services.campaign_service import CampaignService
from services.target_service import TargetService
from services.telethon_client import send_outreach_message
from services.message_service import MessageService

logger = logging.getLogger(__name__)


class Scheduler:
    """
    The Brain layer orchestrator for running campaigns.
    Manages long-running tasks, single-transaction loops, and cancellation.
    """
    _active_campaigns = {}

    @classmethod
    async def start_campaign(cls, campaign_id: int):
        if campaign_id in cls._active_campaigns:
            logger.warning(f"Campaign {campaign_id} is already running.")
            return

        # Ensure campaign exists and get account
        async with AsyncSessionLocal() as session:
            campaign = await CampaignService.get_campaign_by_id(campaign_id, session)
            if not campaign:
                logger.error(f"Cannot start campaign {campaign_id}: Not found.")
                return

        # Create asyncio task
        task = asyncio.create_task(cls._campaign_loop(campaign_id))
        cls._active_campaigns[campaign_id] = task
        logger.info(f"Started scheduler loop for campaign {campaign_id}.")

    @classmethod
    async def stop_campaign(cls, campaign_id: int):
        task = cls._active_campaigns.pop(campaign_id, None)
        if task:
            task.cancel()
            logger.info(f"Stopped scheduler loop for campaign {campaign_id}.")

    @classmethod
    async def stop_all(cls):
        """Cleanly cancels all running campaigns. Called on bot shutdown."""
        campaign_ids = list(cls._active_campaigns.keys())
        for cid in campaign_ids:
            await cls.stop_campaign(cid)

    @classmethod
    async def _campaign_loop(cls, campaign_id: int):
        try:
            while True:
                # SINGLE TRANSACTION BOUNDARY FOR THIS ITERATION
                async with AsyncSessionLocal() as session:
                    try:
                        # 1. Fetch fresh campaign data
                        campaign = await CampaignService.get_campaign_by_id(campaign_id, session)
                        
                        if not campaign:
                            logger.error(f"Campaign {campaign_id} not found. Stopping.")
                            break
                            
                        if campaign["status"] != "running":
                            logger.info(f"Campaign {campaign_id} status is {campaign['status']}. Stopping loop.")
                            break

                        account = campaign["account"]
                        if not account or account["status"] != "active":
                            logger.warning(f"Account for campaign {campaign_id} is inactive. Stopping.")
                            await CampaignService.update_campaign_status(campaign_id, "paused", session)
                            await session.commit()
                            break

                        # 2. Get next target
                        target = await TargetService.get_next_pending_target(campaign_id, session)
                        if not target:
                            logger.info(f"Campaign {campaign_id} has no more pending targets. Stopping.")
                            await CampaignService.update_campaign_status(campaign_id, "completed", session)
                            await session.commit()
                            break

                        # 3. Pick random template
                        templates = campaign["templates"]
                        if not templates:
                            logger.warning(f"Campaign {campaign_id} has no templates. Stopping.")
                            await CampaignService.update_campaign_status(campaign_id, "paused", session)
                            await session.commit()
                            break
                            
                        template = random.choice(templates)
                        message_text = template["message"]

                        # Commit read/update ops before we block on sending
                        await session.commit()

                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Database error in campaign {campaign_id} loop: {e}")
                        await asyncio.sleep(10) # Wait before retry
                        continue
                        
                # 3.5 Check Blacklist (outside the target loop session to avoid long held locks)
                from services.blacklist_service import BlacklistService
                is_allowed = await BlacklistService.check_target_allowed(target["username"], target.get("telegram_user_id"))
                if not is_allowed:
                    logger.info(f"Target @{target['username']} is blacklisted. Skipping.")
                    async with AsyncSessionLocal() as session:
                        await TargetService.update_target_status(target["id"], "skipped", None, session)
                        await session.commit()
                    continue

                # 3.6 Check daily send limit before attempting to send
                async with AsyncSessionLocal() as session:
                    await account_repo.reset_daily_counter_if_needed(session, account["id"])
                    remaining = await account_repo.get_remaining_quota(session, account["id"])
                    await session.commit()

                if remaining <= 0:
                    logger.warning(f"Account {account['id']} hit daily limit. Pausing campaign {campaign_id}.")
                    async with AsyncSessionLocal() as session:
                        await CampaignService.update_campaign_status(campaign_id, "paused", session)
                        await session.commit()
                    break

                # 4. SEND MESSAGE (Outside the DB transaction to prevent holding locks over network)
                logger.info(f"Campaign {campaign_id} sending to @{target['username']}...")
                
                success = False
                telegram_user_id = None
                
                if DRY_RUN:
                    logger.info(f"[DRY RUN] Sent '{message_text[:15]}...' to @{target['username']}")
                    success = True
                    telegram_user_id = random.randint(100000, 999999)  # Mock ID
                else:
                    success, telegram_user_id = await send_outreach_message(account["session_string"], target["username"], message_text)

                # 5. LOG RESULT (New transaction)
                async with AsyncSessionLocal() as session:
                    try:
                        new_status = "sent" if success else "failed"
                        await TargetService.update_target_status(target["id"], new_status, telegram_user_id, session)
                        
                        if success:
                            # Log the outbound message
                            # In DRY_RUN, telegram_message_id is mocked
                            await MessageService.log_message(
                                account_id=account["id"],
                                target_id=target["id"],
                                direction="OUTBOUND",
                                message_type="TEXT",
                                text=message_text,
                                telegram_message_id=random.randint(1000, 9999) if DRY_RUN else None,
                                session=session
                            )
                            # Increment the account's daily send counter
                            await account_repo.increment_daily_counter(session, account["id"])
                            
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Failed to log target result for {target['id']}: {e}")

                # 6. SLEEP
                delay_secs = random.randint(DEV_DELAY_MIN, DEV_DELAY_MAX)
                logger.info(f"Campaign {campaign_id} sleeping for {delay_secs} seconds...")
                await asyncio.sleep(delay_secs)

        except asyncio.CancelledError:
            logger.info(f"Scheduler loop for campaign {campaign_id} cancelled.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in campaign {campaign_id} loop: {e}", exc_info=True)
        finally:
            # Always ensure it removes itself from the registry when dying
            cls._active_campaigns.pop(campaign_id, None)
