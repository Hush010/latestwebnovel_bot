import logging
import uuid
import time
from typing import Dict, Any, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import MusicStates
from keyboards import get_music_results_keyboard, get_cancel_keyboard, get_main_menu_keyboard
from services.music import MusicService

logger = logging.getLogger(__name__)
router = Router(name="music")

# In-memory search results cache with expiration
SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 900  # 15 minutes


def _clean_expired_cache():
    now = time.time()
    expired = [k for k, v in SEARCH_CACHE.items() if now - v["timestamp"] > CACHE_TTL]
    for k in expired:
        SEARCH_CACHE.pop(k, None)


async def execute_music_search(message: Message, query: str):
    """Search for music and show results with inline keyboard."""
    _clean_expired_cache()
    status_msg = await message.answer(f"🔍 Searching YouTube for: *{query}*...", parse_mode="Markdown")

    results = await MusicService.search_tracks(query, limit=5)
    if not results:
        await status_msg.edit_text(
            f"❌ No audio tracks found for *{query}*. Please try different search keywords.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return

    cache_key = uuid.uuid4().hex[:10]
    SEARCH_CACHE[cache_key] = {
        "timestamp": time.time(),
        "results": results
    }

    results_text = "🎵 **Select a song to download:**\n\n" + "\n".join(
        [f"**{i+1}.** {item['title']} `[{item['duration_string'] or 'N/A'}]`" for i, item in enumerate(results)]
    )

    await status_msg.edit_text(
        results_text,
        reply_markup=get_music_results_keyboard(results, cache_key),
        parse_mode="Markdown"
    )


@router.message(Command("song"))
async def cmd_song(message: Message, state: FSMContext):
    """Handle /song [query] command."""
    await state.clear()
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) > 1:
        query = command_parts[1].strip()
        await execute_music_search(message, query)
    else:
        await message.answer(
            "🎵 What song or artist would you like to search for?",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MusicStates.waiting_for_query)


@router.callback_query(F.data == "btn_music_search")
async def callback_music_search(query: CallbackQuery, state: FSMContext):
    """Handle Search Song button from main menu."""
    await state.clear()
    await query.message.answer(
        "🎵 Enter the song name or artist you want to search for:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(MusicStates.waiting_for_query)
    await query.answer()


@router.message(MusicStates.waiting_for_query)
async def process_music_query(message: Message, state: FSMContext):
    """Process search query from user."""
    query = message.text.strip()
    if not query:
        await message.answer("Please enter a valid song title or artist name:")
        return

    await state.clear()
    await execute_music_search(message, query)


@router.callback_query(F.data.startswith("dl_song:"))
async def callback_download_song(callback: CallbackQuery):
    """Handle download button click for a specific song."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid request.", show_alert=True)
        return

    cache_key, item_idx_str = parts[1], parts[2]
    item_idx = int(item_idx_str)

    cache_data = SEARCH_CACHE.get(cache_key)
    if not cache_data or item_idx >= len(cache_data["results"]):
        await callback.message.edit_text(
            "⚠️ Search results expired. Please perform a new search with `/song`.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    selected_track = cache_data["results"][item_idx]
    title = selected_track.get("title", "Track")
    track_url = selected_track.get("url")
    artist = selected_track.get("uploader", "Unknown Artist")

    await callback.message.edit_text(
        f"⏳ **Downloading & converting:**\n🎶 *{title}*\n\nPlease wait a moment...",
        parse_mode="Markdown"
    )
    await callback.answer()

    # Download & convert strictly to mp3
    dl_result = await MusicService.download_track(
        track_url=track_url,
        expected_title=title,
        expected_artist=artist
    )

    if not dl_result or not dl_result.get("file_path"):
        await callback.message.edit_text(
            f"❌ Failed to download audio for *{title}*. The source may be restricted or unavailable.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return

    file_path = dl_result["file_path"]
    try:
        audio_file = FSInputFile(
            path=file_path,
            filename=f"{MusicService._sanitize_filename(title)}.mp3"
        )
        duration = int(dl_result.get("duration") or 0)
        
        await callback.message.answer_audio(
            audio=audio_file,
            title=dl_result["title"],
            performer=dl_result["artist"],
            duration=duration,
            caption=f"🎵 **{dl_result['title']}**\n👤 {dl_result['artist']}",
            parse_mode="Markdown"
        )
        # Clean up the status prompt
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error sending audio file: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Error sending audio file: {e}",
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        # Immediately delete the local .mp3 from disk
        MusicService.cleanup_file(file_path)


@router.callback_query(F.data == "cancel_music")
async def callback_cancel_music(callback: CallbackQuery):
    """Cancel song search."""
    await callback.message.edit_text(
        "🚫 Song search cancelled.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
