import logging
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from .base import BaseScraper, ChapterItem, NovelMetadata

logger = logging.getLogger(__name__)


class NovelBinScraper(BaseScraper):
    """Scraper implementation for NovelBin (novelbin.com, novelbin.me, novelbin.net)."""

    DOMAIN_NAMES = ["novelbin.com", "novelbin.me", "novelbin.net", "novelbin.org"]

    async def get_metadata(self, novel_url: str) -> NovelMetadata:
        html = await self.fetch_html(novel_url)
        soup = BeautifulSoup(html, "lxml")

        # Extract Title
        title_el = soup.select_one("h3.title") or soup.select_one(".novel-title") or soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Novel"

        # Extract Author
        author = "Unknown Author"
        for li in soup.select(".info li, .novel-info li"):
            text = li.get_text()
            if "Author" in text:
                author_el = li.find("a")
                if author_el:
                    author = author_el.get_text(strip=True)
                else:
                    author = text.replace("Author:", "").strip()
                break

        # Extract Cover Image
        cover_url = None
        img_el = soup.select_one(".book img") or soup.select_one(".novel-cover img")
        if img_el:
            cover_url = img_el.get("data-src") or img_el.get("src")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(novel_url, cover_url)

        # Extract Description
        desc_el = soup.select_one(".desc-text") or soup.select_one("#tab-description") or soup.select_one(".novel-detail-item")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Extract Chapter list - check direct list or novel ID for ajax
        chapters = []
        novel_id_el = soup.select_one("#rating[data-novel-id]") or soup.select_one("[data-novel-id]")
        novel_id = novel_id_el.get("data-novel-id") if novel_id_el else None

        if novel_id:
            ajax_url = urljoin(novel_url, f"/ajax/chapter-archive?novelId={novel_id}")
            try:
                ajax_html = await self.fetch_html(ajax_url)
                ajax_soup = BeautifulSoup(ajax_html, "lxml")
                for idx, a in enumerate(ajax_soup.select("li a"), 1):
                    ch_url = urljoin(novel_url, a.get("href"))
                    ch_title = a.get("title") or a.get_text(strip=True) or f"Chapter {idx}"
                    chapters.append(ChapterItem(index=idx, title=ch_title, url=ch_url))
            except Exception as e:
                logger.warning(f"Failed to fetch NovelBin ajax chapter list: {e}")

        # Fallback to direct page list if ajax was empty
        if not chapters:
            for idx, a in enumerate(soup.select(".list-chapter a, #list-chapter a"), 1):
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

        content_el = soup.select_one("#chr-content") or soup.select_one("#chapter-content") or soup.select_one(".chapter-content")
        return self.sanitize_text(content_el)
