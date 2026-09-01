from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict, Any


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard with quick actions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎵 Search Song", callback_data="btn_music_search"),
                InlineKeyboardButton(text="📥 Download Novel", callback_data="btn_novel_download")
            ],
            [
                InlineKeyboardButton(text="ℹ️ Help & Commands", callback_data="btn_help")
            ]
        ]
    )
    return keyboard


def get_music_results_keyboard(results: List[Dict[str, Any]], search_cache_key: str) -> InlineKeyboardMarkup:
    """Build inline keyboard for music search results."""
    buttons = []
    for idx, item in enumerate(results):
        title = item.get("title", "Unknown")
        duration = item.get("duration_string", "")
        duration_label = f" ({duration})" if duration else ""
        # Truncate title for button display
        display_text = f"{idx + 1}. {title[:38]}{duration_label}"
        buttons.append([
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"dl_song:{search_cache_key}:{idx}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_music")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_novel_options_keyboard(total_chapters: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for full novel vs chapter range."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📚 Download Full Novel (1 - {total_chapters})",
                    callback_data="novel_opt:full"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Select Chapter Range",
                    callback_data="novel_opt:range"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="novel_opt:cancel"
                )
            ]
        ]
    )
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button for any ongoing FSM step."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="fsm_cancel")]
        ]
    )
