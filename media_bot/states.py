from aiogram.fsm.state import State, StatesGroup


class NovelDownloadStates(StatesGroup):
    """FSM states for interactive webnovel scraping and ePub generation."""
    waiting_for_url = State()
    waiting_for_choice = State()
    waiting_for_range = State()
    scraping_in_progress = State()


class MusicStates(StatesGroup):
    """FSM states for music search."""
    waiting_for_query = State()
