import logging
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from .base import BaseScraper, ChapterItem, NovelMetadata

logger = logging.getLogger(__name__)


class GenericScraper(BaseScraper):
    """Smart universal fallback scraper for generic novel websites."""

    DOMAIN_NAMES = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        # Generic scraper handles any valid http/https URL
        return url.startswith("http://") or url.startswith("https://")

    async def get_metadata(self, novel_url: str) -> NovelMetadata:
        html = await self.fetch_html(novel_url)
        soup = BeautifulSoup(html, "lxml")

        # Title heuristic
        title_el = soup.find("h1") or soup.select_one("meta[property='og:title']")
        title = ""
        if title_el:
            title = title_el.get("content") if title_el.name == "meta" else title_el.get_text(strip=True)
        if not title:
            title = soup.title.get_text(strip=True) if soup.title else "Unknown Novel"

        # Author heuristic
        author = "Unknown Author"
        author_match = soup.find(text=re.compile(r"Author:?", re.I))
        if author_match and author_match.parent:
            author = author_match.parent.get_text(strip=True).replace("Author:", "").strip()

        # Cover Image heuristic
        cover_url = None
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            cover_url = og_image["content"]
        else:
            img = soup.select_one(".cover img, .poster img, .book-cover img, .novel-cover img")
            if img:
                cover_url = img.get("src") or img.get("data-src")

        if cover_url and not cover_url.startswith("http"):
            cover_url = urljoin(novel_url, cover_url)

        # Description heuristic
        desc_el = soup.select_one("meta[name='description']") or soup.select_one(".description, .summary, #description")
        description = ""
        if desc_el:
            description = desc_el.get("content") if desc_el.name == "meta" else desc_el.get_text(strip=True)

        # Chapter extraction heuristic: find links containing "chapter" or within TOC lists
        chapters = []
        seen_urls = set()
        candidates = soup.find_all("a", href=True)
        
        idx = 1
        for a in candidates:
            href = a.get("href")
            text = a.get_text(strip=True)
            full_url = urljoin(novel_url, href)

            if full_url in seen_urls:
                continue

            # Check if link text or href looks like a chapter link
            is_chapter_text = bool(re.search(r"chapter|ch\.\s*\d+|episode|prologue|\b\d+\b", text, re.I))
            is_chapter_href = bool(re.search(r"/chapter[-_]?\d+|/ch[-_]?\d+", full_url, re.I))

            if is_chapter_text or is_chapter_href:
                if len(text) > 2 and not re.search(r"next|prev|home|index|login|register|bookmark", text, re.I):
                    seen_urls.add(full_url)
                    chapters.append(ChapterItem(index=idx, title=text, url=full_url))
                    idx += 1

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

        # Heuristic search for main reading content container
        candidates = [
            soup.select_one("#chapter-content"),
            soup.select_one(".chapter-content"),
            soup.select_one("#content"),
            soup.select_one(".content"),
            soup.select_one(".reading-content"),
            soup.select_one("article"),
            soup.select_one(".entry-content"),
            soup.select_one(".text"),
            soup.select_one("main"),
        ]

        content_el = next((el for el in candidates if el is not None), None)
        if not content_el:
            content_el = soup.body

        return self.sanitize_text(content_el)
