from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_keyboard

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    await state.clear()
    welcome_text = (
        "👋 **Welcome to Webnovel Downloader & ePub Generator Bot!**\n\n"
        "📚 **Webnovel Scraper & ePub Creator:**\n"
        "Scrape entire webnovels or custom chapter ranges and automatically compile clean, beautifully formatted `.epub` ebooks with cover art and navigable Table of Contents.\n\n"
        "🎵 **Music:**\n"
        "Use the **SpotDown Web App** button below for high-speed Spotify track downloads.\n\n"
        "Click an option below or send `/novel` to get started!"
    )
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("help"))
@router.callback_query(F.data == "btn_help")
async def cmd_help(event: Message | CallbackQuery):
    """Handle /help command or Help button."""
    help_text = (
        "📖 **User Guide & Supported Webnovel Sources**\n\n"
        "📚 **Commands:**\n"
        "• `/novel` — Launch the interactive scraper wizard.\n"
        "• `/start` — Open the main interactive menu.\n"
        "• `/cancel` — Cancel any active prompt.\n\n"
        "🌐 **Supported Providers:**\n"
        "• **NovelPhoenix** (`novelphoenix.com`)\n"
        "• **NovelFire** (`novelfire.net`)\n"
        "• **NovelBin** (`novelbin.com`, `novelbin.me`, `novelbin.net`)\n"
        "• **FreeWebNovel** (`freewebnovel.com`)\n"
        "• **Ranobes** (`ranobes.top`, `ranobes.net`)\n"
        "• **Universal Fallback** for other standard webnovel sites.\n\n"
        "⚡ **Features:**\n"
        "• Full novel or custom range selection (`1-50`, `100-200`).\n"
        "• Automated cover art download and TOC metadata embedding.\n"
        "• Clean typography styling without intrusive ads or site watermarks."
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(help_text, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(help_text, parse_mode="Markdown")


@router.message(Command("cancel"))
@router.callback_query(F.data == "fsm_cancel")
async def cmd_cancel(event: Message | CallbackQuery, state: FSMContext):
    """Cancel current FSM state."""
    current_state = await state.get_state()
    if current_state is None:
        text = "ℹ️ No active action to cancel."
    else:
        await state.clear()
        text = "🚫 Action cancelled. Returning to main menu."

    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=get_main_menu_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_main_menu_keyboard())
