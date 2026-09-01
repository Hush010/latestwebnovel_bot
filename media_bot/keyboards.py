from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from typing import List, Dict, Any


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard with Webnovel Downloader and SpotDown WebApp."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Download Webnovel", callback_data="btn_novel_download")
            ],
            [
                InlineKeyboardButton(
                    text="🎵 SpotDown Music (Web App)",
                    web_app=WebAppInfo(url="https://spotdown.org/en2/track")
                )
            ],
            [
                InlineKeyboardButton(text="ℹ️ Help & Supported Sites", callback_data="btn_help")
            ]
        ]
    )
    return keyboard


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
