import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, LOG_LEVEL
from handlers import register_all_handlers

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def start_health_server(port: int):
    """Run a minimal health check HTTP server for Render/Railway/cloud platforms."""
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="Webnovel ePub Bot is running 🚀", status=200)

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check HTTP server started on port {port}")
    return runner


async def setup_bot_commands(bot: Bot):
    """Set default Telegram bot menu commands."""
    commands = [
        BotCommand(command="start", description="🚀 Launch Bot & Main Menu"),
        BotCommand(command="novel", description="📚 Scrape webnovel and generate ePub"),
        BotCommand(command="help", description="📖 User guide & supported sites"),
        BotCommand(command="cancel", description="🚫 Cancel current action"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Main application lifecycle."""
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error(
            "CRITICAL: BOT_TOKEN is not set in .env! "
            "Please create a .env file with your Telegram bot token: BOT_TOKEN=123456:ABC-DEF..."
        )
        sys.exit(1)

    logger.info("Initializing Webnovel ePub Telegram Bot...")

    # Start health check server if PORT is provided by hosting environment (Render/Railway)
    port_env = os.getenv("PORT")
    http_runner = None
    if port_env:
        try:
            http_runner = await start_health_server(int(port_env))
        except Exception as e:
            logger.warning(f"Could not start HTTP health server on port {port_env}: {e}")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register handlers
    register_all_handlers(dp)

    # Register commands menu in Telegram
    try:
        await setup_bot_commands(bot)
        logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    logger.info("Bot started successfully. Listening for updates...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        if http_runner:
            await http_runner.cleanup()
        logger.info("Bot polling stopped and session closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot terminated by user.")
