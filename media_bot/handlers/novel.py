import asyncio
import logging
import re
import time
from typing import Dict, Any, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import NovelDownloadStates
from keyboards import get_novel_options_keyboard, get_cancel_keyboard, get_main_menu_keyboard
from services.scrapers import get_scraper_for_url, ChapterItem, NovelMetadata
from services.epub_builder import EpubBuilder

logger = logging.getLogger(__name__)
router = Router(name="novel")


@router.message(Command("novel"))
async def cmd_novel(message: Message, state: FSMContext):
    """Start interactive novel scraping wizard."""
    await state.clear()
    await message.answer(
        "📚 **Webnovel Downloader & ePub Generator**\n\n"
        "Please paste the URL of the novel's main page or table of contents.\n\n"
        "_(Supports NovelBin, FreeWebNovel, Ranobes, NovelFire, and many others)_",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(NovelDownloadStates.waiting_for_url)


@router.callback_query(F.data == "btn_novel_download")
async def callback_novel_start(callback: CallbackQuery, state: FSMContext):
    """Start novel wizard from main menu button."""
    await state.clear()
    await callback.message.answer(
        "📚 **Webnovel Downloader & ePub Generator**\n\n"
        "Please paste the URL of the novel's main page or table of contents:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(NovelDownloadStates.waiting_for_url)
    await callback.answer()


@router.message(NovelDownloadStates.waiting_for_url)
async def process_novel_url(message: Message, state: FSMContext):
    """Verify novel URL, parse metadata and chapter count."""
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer(
            "⚠️ Please enter a valid URL starting with `http://` or `https://`:",
            reply_markup=get_cancel_keyboard()
        )
        return

    status_msg = await message.answer(
        "🔍 *Analyzing novel and fetching chapter list...*\n"
        "This may take a few seconds depending on the site.",
        parse_mode="Markdown"
    )

    scraper = get_scraper_for_url(url)

    try:
        metadata: NovelMetadata = await scraper.get_metadata(url)
    except Exception as e:
        logger.error(f"Error fetching novel metadata from {url}: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Could not analyze novel from the provided URL.\n\n"
            f"*Error:* `{str(e)[:150]}`\n\n"
            "Please make sure the link is accessible and try again.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    if not metadata.chapters:
        await status_msg.edit_text(
            f"⚠️ Could not find any chapters on the page for **{metadata.title}**.\n\n"
            "Please ensure you pasted the novel's table of contents or main overview page.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Save metadata to FSMContext data dictionary
    await state.update_data(
        novel_url=url,
        title=metadata.title,
        author=metadata.author,
        cover_url=metadata.cover_url,
        description=metadata.description,
        total_chapters=metadata.total_chapters,
        chapters=[{"index": c.index, "title": c.title, "url": c.url} for c in metadata.chapters]
    )

    info_text = (
        f"📖 **Title:** {metadata.title}\n"
        f"✍️ **Author:** {metadata.author}\n"
        f"📊 **Found:** `{metadata.total_chapters:,}` chapters\n\n"
        "How would you like to download this novel?"
    )

    # If cover image is available, send photo with caption
    if metadata.cover_url:
        try:
            await status_msg.delete()
            await message.answer_photo(
                photo=metadata.cover_url,
                caption=info_text,
                reply_markup=get_novel_options_keyboard(metadata.total_chapters),
                parse_mode="Markdown"
            )
            await state.set_state(NovelDownloadStates.waiting_for_choice)
            return
        except Exception as img_err:
            logger.debug(f"Failed sending cover image directly: {img_err}")

    # Fallback to text message
    await status_msg.edit_text(
        info_text,
        reply_markup=get_novel_options_keyboard(metadata.total_chapters),
        parse_mode="Markdown"
    )
    await state.set_state(NovelDownloadStates.waiting_for_choice)


@router.callback_query(NovelDownloadStates.waiting_for_choice, F.data == "novel_opt:full")
async def process_full_novel(callback: CallbackQuery, state: FSMContext):
    """User selected Full Novel download."""
    data = await state.get_data()
    total = data.get("total_chapters", 0)
    await callback.answer()
    await start_scraping_workflow(
        event=callback,
        state=state,
        start_ch=1,
        end_ch=total
    )


@router.callback_query(NovelDownloadStates.waiting_for_choice, F.data == "novel_opt:range")
async def process_range_prompt(callback: CallbackQuery, state: FSMContext):
    """User selected Custom Chapter Range."""
    data = await state.get_data()
    total = data.get("total_chapters", 0)
    
    await callback.message.answer(
        f"🔢 Enter the chapter range you want (from `1` to `{total}`).\n\n"
        "Example formats:\n"
        "• `1-50`\n"
        "• `100-250`\n"
        "• `1` (single chapter)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(NovelDownloadStates.waiting_for_range)
    await callback.answer()


@router.callback_query(F.data == "novel_opt:cancel")
async def process_novel_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel novel download."""
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🚫 Novel download cancelled.", reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.message(NovelDownloadStates.waiting_for_range)
async def process_range_input(message: Message, state: FSMContext):
    """Validate and process custom chapter range."""
    text = message.text.strip()
    data = await state.get_data()
    total = data.get("total_chapters", 0)

    # Parse range: "1-100" or "50"
    match = re.match(r"^(\d+)(?:\s*-\s*(\d+))?$", text)
    if not match:
        await message.answer(
            f"⚠️ Invalid format. Please enter a valid range like `1-100` (max `{total}`):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return

    start_ch = int(match.group(1))
    end_ch = int(match.group(2)) if match.group(2) else start_ch

    # Validate 1 <= start <= end <= total
    if start_ch < 1 or end_ch > total or start_ch > end_ch:
        await message.answer(
            f"⚠️ Invalid range! Chapters must be between `1` and `{total}` with start ≤ end.\n"
            f"You entered: `{start_ch}-{end_ch}`. Please try again:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return

    await start_scraping_workflow(
        event=message,
        state=state,
        start_ch=start_ch,
        end_ch=end_ch
    )


async def start_scraping_workflow(
    event: Message | CallbackQuery,
    state: FSMContext,
    start_ch: int,
    end_ch: int
):
    """Execute chapter scraping with polite delays, compile .epub, and send file."""
    await state.set_state(NovelDownloadStates.scraping_in_progress)

    data = await state.get_data()
    novel_url = data.get("novel_url", "")
    title = data.get("title", "Novel")
    author = data.get("author", "Unknown Author")
    cover_url = data.get("cover_url")
    description = data.get("description", "")
    raw_chapters = data.get("chapters", [])

    total_to_download = end_ch - start_ch + 1

    progress_msg = None
    if isinstance(event, CallbackQuery):
        progress_msg = await event.message.answer(
            f"🚀 **Starting download for:** *{title}*\n"
            f"📚 Chapters: `{start_ch}` to `{end_ch}` (`{total_to_download}` total)\n\n"
            "⏳ Scraping chapter 1 of {total_to_download}...",
            parse_mode="Markdown"
        )
    else:
        progress_msg = await event.answer(
            f"🚀 **Starting download for:** *{title}*\n"
            f"📚 Chapters: `{start_ch}` to `{end_ch}` (`{total_to_download}` total)\n\n"
            f"⏳ Scraping chapter 1 of {total_to_download}...",
            parse_mode="Markdown"
        )

    scraper = get_scraper_for_url(novel_url)
    chapter_objects = [
        ChapterItem(index=c["index"], title=c["title"], url=c["url"])
        for c in raw_chapters
    ]

    last_update_time = time.time()

    async def update_progress(current: int, total: int, current_title: str):
        nonlocal last_update_time
        # Throttle progress edits to avoid Telegram rate limits (at least 3.5s interval or on finish)
        now = time.time()
        if now - last_update_time > 3.5 or current == total:
            last_update_time = now
            pct = int((current / total) * 100)
            bar_len = 10
            filled = int((current / total) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            try:
                await progress_msg.edit_text(
                    f"🚀 **Scraping {title}**\n\n"
                    f"[{bar}] {pct}%\n"
                    f"📄 Chapter `{current}/{total}`: _{current_title[:35]}_\n\n"
                    "⏱ Applying polite delays to avoid rate limits...",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # Scrape selected range of chapters
    scraped_chapters = await scraper.scrape_chapters(
        chapters=chapter_objects,
        start_idx=start_ch,
        end_idx=end_ch,
        progress_callback=update_progress
    )

    try:
        await progress_msg.edit_text(
            "📦 **Compiling ePub document...**\n"
            "Building Table of Contents and styling chapter text...",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    metadata = NovelMetadata(
        title=title,
        author=author,
        cover_url=cover_url,
        description=description,
        chapters=scraped_chapters,
        source_url=novel_url
    )

    range_label = f"Ch{start_ch}-{end_ch}"
    epub_path = await EpubBuilder.build_epub(metadata, scraped_chapters, range_suffix=range_label)

    if not epub_path:
        await progress_msg.edit_text(
            f"❌ Failed to generate .epub file for **{title}**.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Send document
    try:
        doc = FSInputFile(
            path=epub_path,
            filename=f"{EpubBuilder._sanitize_filename(title)}_{range_label}.epub"
        )
        caption = (
            f"📚 **{title}**\n"
            f"✍️ Author: {author}\n"
            f"📑 Chapters: {start_ch} - {end_ch} ({total_to_download} chapters)\n\n"
            "✨ _Generated with Media & Novel Bot_"
        )
        
        target_chat_msg = event.message if isinstance(event, CallbackQuery) else event
        await target_chat_msg.answer_document(
            document=doc,
            caption=caption,
            parse_mode="Markdown"
        )
        # Delete progress message
        await progress_msg.delete()

    except Exception as e:
        logger.error(f"Error sending ePub document: {e}", exc_info=True)
        await progress_msg.edit_text(
            f"❌ Error delivering ePub file: {e}",
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        # Immediately delete the local .epub file and clear state
        EpubBuilder.cleanup_file(epub_path)
        await state.clear()
