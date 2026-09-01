import logging
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base import BaseScraper, ChapterItem, NovelMetadata

logger = logging.getLogger(__name__)


class NovelFireScraper(BaseScraper):
    """Scraper implementation for NovelFire (novelfire.net, novelfire.docs)."""

    DOMAIN_NAMES = ["novelfire.net", "novelfire.docs", "novelfire.org"]

    async def get_metadata(self, novel_url: str) -> NovelMetadata:
        html = await self.fetch_html(novel_url)
        soup = BeautifulSoup(html, "lxml")

        # Extract Title
        title_el = soup.select_one("h1.novel-title") or soup.select_one(".novel-info h1") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Novel"

        # Extract Author
        author = "Unknown Author"
        author_el = soup.select_one(".author a") or soup.select_one("a[href*='/author/']")
        if author_el:
            author = author_el.get_text(strip=True)

        # Extract Cover Image
        cover_url = None
        img_el = soup.select_one(".novel-cover img") or soup.select_one(".poster img")
        if img_el:
            cover_url = img_el.get("src") or img_el.get("data-src")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(novel_url, cover_url)

        # Extract Description
        desc_el = soup.select_one(".summary .content") or soup.select_one(".novel-description") or soup.select_one("#description")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Extract Chapters
        chapters = []
        for idx, a in enumerate(soup.select(".chapter-list a, .chapters a, #chapter-list a"), 1):
            ch_url = urljoin(novel_url, a.get("href"))
            ch_title = a.get("title") or a.get_text(strip=True) or f"Chapter {idx}"
            chapters.append(ChapterItem(index=idx, title=ch_title, url=ch_url))

        return NovelMetadata(
            title=title,
            author=author,
            cover_url=cover_url,
            description=description,
            chapters=chapters,
            source_url=novel_url
        )

    async def get_chapter_content(self, chapter_url: str) -> str:
        html = await self.fetch_html(chapter_url)
        soup = BeautifulSoup(html, "lxml")

        content_el = soup.select_one("#chapter-content") or soup.select_one(".chapter-content") or soup.select_one(".content-area")
        return self.sanitize_text(content_el)
