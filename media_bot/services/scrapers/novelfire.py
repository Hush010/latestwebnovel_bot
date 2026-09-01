import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from .base import BaseScraper, ChapterItem, NovelMetadata

logger = logging.getLogger(__name__)


class NovelFireScraper(BaseScraper):
    """Scraper implementation for NovelFire (novelfire.net, novelfire.docs, novelfire.org)."""

    DOMAIN_NAMES = ["novelfire.net", "novelfire.docs", "novelfire.org"]

    async def get_metadata(self, novel_url: str) -> NovelMetadata:
        # Normalize base URL (remove trailing /chapters if present to get overview page)
        parsed = urlparse(novel_url)
        clean_path = re.sub(r"/chapters/?$", "", parsed.path).rstrip("/")
        base_url = f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        chapters_page_url = f"{base_url}/chapters"

        html = await self.fetch_html(base_url)
        soup = BeautifulSoup(html, "lxml")

        # Extract Title
        title_el = soup.find("h1") or soup.select_one(".novel-title")
        title = title_el.get_text(strip=True) if title_el else "Unknown Novel"

        # Extract Author
        author = "Unknown Author"
        author_el = soup.select_one("a[href*='/author/']") or soup.select_one(".author a")
        if author_el:
            author = author_el.get_text(strip=True)

        # Extract Cover Image
        cover_url = None
        img_el = soup.select_one(".novel-cover img, .poster img, .book-cover img, .cover img")
        if img_el:
            cover_url = img_el.get("src") or img_el.get("data-src")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(base_url, cover_url)

        # Extract Description
        desc_el = soup.select_one(".summary .content, .novel-description, #description, .description")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Fetch chapters list from /chapters with pagination
        chapters = []
        try:
            chapters_html = await self.fetch_html(chapters_page_url)
            ch_soup = BeautifulSoup(chapters_html, "lxml")

            # Detect maximum page number
            page_nums = []
            for p in ch_soup.select(".pagination a, .pages a, ul.pagination li a"):
                m = re.search(r"page=(\d+)", p.get("href", ""))
                if m:
                    page_nums.append(int(m.group(1)))
            max_page = max(page_nums) if page_nums else 1

            def _parse_page_chapters(page_soup: BeautifulSoup):
                page_items = []
                for a in page_soup.select("ul.chapter-list li a, .list-chapter li a, .chapter-list a"):
                    href = urljoin(base_url, a.get("href"))
                    raw_text = a.get_text(strip=True)
                    # Clean title: strip trailing 'X days ago', 'X months ago'
                    clean_title = re.sub(
                        r"\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s*ago",
                        "",
                        raw_text,
                        flags=re.I
                    ).strip()
                    # Clean title: strip prepended index digits if followed immediately by Chapter/Ch
                    clean_title = re.sub(
                        r"^\d+(?=(?:Chapter|Ch|Episode|Prologue|\b[A-Za-z]))",
                        "",
                        clean_title
                    ).strip()
                    page_items.append((href, clean_title or raw_text))
                return page_items

            # If only 1 page
            if max_page == 1:
                items = _parse_page_chapters(ch_soup)
                for idx, (href, ch_title) in enumerate(items, 1):
                    chapters.append(ChapterItem(index=idx, title=ch_title, url=href))
            else:
                # Concurrent fetch for all pages
                async with AsyncSession(impersonate="chrome120", verify=False, timeout=30) as session:
                    async def fetch_page(p_num: int):
                        if p_num == 1:
                            return _parse_page_chapters(ch_soup)
                        resp = await session.get(f"{chapters_page_url}?page={p_num}", headers=self.headers)
                        sp = BeautifulSoup(resp.text, "lxml")
                        return _parse_page_chapters(sp)

                    page_tasks = [fetch_page(p) for p in range(1, max_page + 1)]
                    pages_results = await asyncio.gather(*page_tasks, return_exceptions=True)

                    idx = 1
                    for res in pages_results:
                        if isinstance(res, list):
                            for href, ch_title in res:
                                chapters.append(ChapterItem(index=idx, title=ch_title, url=href))
                                idx += 1

        except Exception as e:
            logger.error(f"Error extracting NovelFire chapters: {e}", exc_info=True)

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

        content_el = (
            soup.select_one("#content")
            or soup.select_one(".content.clearfix")
            or soup.select_one("#chapter-content")
            or soup.select_one(".chapter-content")
            or soup.select_one(".content")
        )
        return self.sanitize_text(content_el)
