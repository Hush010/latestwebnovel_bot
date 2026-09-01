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
        "👋 **Welcome to Media & Webnovel Bot!**\n\n"
        "Here is what I can do for you:\n"
        "🎵 **Music Downloader:** Search and download MP3 tracks with metadata tags.\n"
        "📚 **Novel Scraper & ePub Generator:** Extract full webnovels or custom chapter ranges and compile clean, formatted ePub books with covers & table of contents.\n\n"
        "Choose an option below or type a command:"
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
        "📖 **Bot Commands & Usage Guide**\n\n"
        "🎵 **Music Module:**\n"
        "• `/song <name or keywords>` — Search YouTube and choose a track to download as high-quality MP3 with ID3 tags.\n"
        "• Or click **🎵 Search Song** in the main menu.\n\n"
        "📚 **Webnovel Module:**\n"
        "• `/novel` — Start the interactive wizard to scrape a novel and generate an `.epub` file.\n"
        "• Supports **NovelBin**, **FreeWebNovel**, **Ranobes**, **NovelFire**, and many other webnovel sites.\n"
        "• Option to download the complete novel or select specific chapter ranges (e.g. `1-100`).\n\n"
        "⚙️ **Utility:**\n"
        "• `/cancel` — Cancel any ongoing operation or input prompt."
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
