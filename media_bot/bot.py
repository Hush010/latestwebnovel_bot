import asyncio
import logging
import sys
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


async def setup_bot_commands(bot: Bot):
    """Set default Telegram bot menu commands."""
    commands = [
        BotCommand(command="start", description="🚀 Launch Bot & Main Menu"),
        BotCommand(command="song", description="🎵 Search and download MP3 music"),
        BotCommand(command="novel", description="📚 Scrape webnovel and generate ePub"),
        BotCommand(command="help", description="📖 User guide & help"),
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

    logger.info("Initializing Media & Novel Telegram Bot...")

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
        logger.info("Bot polling stopped and session closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot terminated by user.")
