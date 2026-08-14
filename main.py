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
from services.campaign_service import CampaignService
from services.reply_listener_service import ReplyListenerService
from core.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await CampaignService.recover_running_campaigns()
    await ReplyListenerService.start_all_listeners()
    logger.info("✅ Bot is running!")

async def on_shutdown(bot: Bot):
    logger.info("Shutting down...")
    # Cancel all active campaign loops
    await Scheduler.stop_all()
    # Cancel all reply listener tasks
    for account_id in list(ReplyListenerService.active_listeners.keys()):
        await ReplyListenerService.stop_listener(account_id)
    await bot.session.close()
    logger.info("👋 Goodbye!")

async def main():
    logger.info("🚀 Starting up, please wait...")
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(account_router)
    dp.include_router(campaign_router)
    dp.include_router(template_router)
    dp.include_router(target_handler)
    dp.include_router(replies_handler)
    dp.include_router(pain_point_handler)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
