import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from data.database import init_db
from bot.handlers.account_handler import router as account_router
from bot.handlers.campaign_handler import router as campaign_router
from bot.handlers.template_handler import router as template_router
from bot.handlers.target_handler import router as target_handler
from bot.handlers.replies_handler import router as replies_handler
from bot.handlers.pain_point_handler import router as pain_point_handler
from bot.handlers.export_handler import router as export_handler
from bot.handlers.stats_handler import router as stats_handler
from bot.handlers.blacklist_handler import router as blacklist_handler
from bot.handlers.war_room_handler import router as war_room_handler
from bot.handlers.approval_handler import router as approval_router
from services.campaign_service import CampaignService
from services.account_service import AccountService
from services.scheduler_service import SchedulerService
from api.server import start_api_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await CampaignService.recover_running_campaigns()
    # Reset daily counters for any account that hasn't been reset today
    await AccountService.reset_all_daily_counters_if_needed()
    
    # Start FastAPI REST server background task
    asyncio.create_task(start_api_server())
    logger.info("🌐 FastAPI REST Server running on port 8013")
    logger.info("✅ Bot is running!")

async def on_shutdown(bot: Bot):
    logger.info("Shutting down...")
    # Cancel all active campaign loops cleanly
    await SchedulerService.stop_all()
    await bot.session.close()
    logger.info("👋 Goodbye!")

async def main():
    logger.info("🚀 Starting up, please wait...")
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(war_room_handler)
    dp.include_router(approval_router)
    dp.include_router(account_router)
    dp.include_router(campaign_router)
    dp.include_router(template_router)
    dp.include_router(target_handler)
    dp.include_router(replies_handler)
    dp.include_router(pain_point_handler)
    dp.include_router(export_handler)
    dp.include_router(stats_handler)
    dp.include_router(blacklist_handler)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
