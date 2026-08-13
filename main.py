import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from data.database import init_db
from bot.handlers import account_router, campaign_router, template_router, target_router
from services.campaign_service import CampaignService

async def on_startup(bot: Bot):
    """Executes at the very start of polling."""
    # Clear pending updates so the bot doesn't reply to old messages
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Run startup recovery for Ghost Campaign states
    await CampaignService.recover_running_campaigns()
    print("✅ Startup Recovery: Running campaigns reverted to paused.")
    
    # This will now print AFTER all framework info logs are finished
    print("✅ Bot is running!")

async def on_shutdown(bot: Bot):
    """Executes when the bot is stopped."""
    print("\n👋 Shutting down bot session...")
    await bot.session.close()
    print("👋 Goodbye!")

async def main():
    # Keep the logging configuration
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting up, please wait...")
    
    # Initialize database
    await init_db()
    
    # Setup bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(account_router)
    dp.include_router(campaign_router)
    dp.include_router(template_router)
    dp.include_router(target_router)
    
    # Register native startup and shutdown lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # start_polling will fire logs FIRST, then trigger on_startup
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
