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
        "📚 **What this bot does:**\n"
        "Scrapes full webnovels or custom chapter ranges and compiles clean, beautifully formatted `.epub` books with covers and navigable Table of Contents.\n\n"
        "🌐 **Supported Sites:**\n"
        "• NovelPhoenix (`novelphoenix.com`)\n"
        "• NovelFire (`novelfire.net`)\n"
        "• NovelBin (`novelbin.com`)\n"
        "• FreeWebNovel (`freewebnovel.com`)\n"
        "• Ranobes (`ranobes.top`)\n"
        "• Universal fallback for other webnovel sources.\n\n"
        "Click **📥 Download Webnovel** below or type `/novel` to get started!"
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
        "📖 **User Guide & How to Use**\n\n"
        "📚 **Commands:**\n"
        "• `/novel` — Start the interactive novel downloader wizard.\n"
        "• `/start` — Open the main menu.\n"
        "• `/cancel` — Cancel current operation.\n\n"
        "⚡ **Step-by-Step Flow:**\n"
        "1. Click **📥 Download Webnovel** or send `/novel`.\n"
        "2. Paste the URL of the novel's main overview or TOC page.\n"
        "3. Choose **Download Full Novel** or **Select Chapter Range** (e.g. `1-100`).\n"
        "4. The bot downloads each chapter with polite delays and compiles a clean `.epub` ebook.\n"
        "5. Receive your `.epub` document directly in Telegram!"
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
