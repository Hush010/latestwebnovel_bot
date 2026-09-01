from typing import Type
from .base import BaseScraper, ChapterItem, NovelMetadata
from .novelbin import NovelBinScraper
from .freewebnovel import FreeWebNovelScraper
from .ranobes import RanobesScraper
from .novelfire import NovelFireScraper
from .generic import GenericScraper

SCRAPERS = [
    NovelBinScraper,
    FreeWebNovelScraper,
    RanobesScraper,
    NovelFireScraper,
]


def get_scraper_for_url(url: str) -> BaseScraper:
    """Return the dedicated scraper for the URL, or GenericScraper as fallback."""
    for scraper_cls in SCRAPERS:
        if scraper_cls.can_handle(url):
            return scraper_cls()
    return GenericScraper()


__all__ = [
    "BaseScraper",
    "ChapterItem",
    "NovelMetadata",
    "NovelBinScraper",
    "FreeWebNovelScraper",
    "RanobesScraper",
    "NovelFireScraper",
    "GenericScraper",
    "get_scraper_for_url",
]
