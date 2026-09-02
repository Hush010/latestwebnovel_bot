import asyncio
import logging
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

# Headers to mimic a real browser
BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Browser impersonation profiles to rotate
IMPERSONATION_PROFILES = [
    "chrome120", "chrome116", "chrome110", "chrome107", "chrome104",
    "edge99", "edge101",
    "safari17_0", "safari16_3", "safari15_5",
    "firefox117", "firefox110", "firefox102"
]


@dataclass
class ChapterItem:
    """Represents a chapter entry."""
    index: int
    title: str
    url: str
    content_html: Optional[str] = None


@dataclass
class NovelMetadata:
    """Metadata for a scraped webnovel."""
    title: str
    author: str
    cover_url: Optional[str]
    description: str
    chapters: List[ChapterItem] = field(default_factory=list)
    source_url: str = ""

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class BaseScraper(ABC):
    """Abstract base class for webnovel scrapers with TLS fingerprint impersonation."""

    DOMAIN_NAMES: List[str] = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this scraper supports the given URL."""
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in cls.DOMAIN_NAMES)

    async def fetch_html(self, url: str) -> str:
        """
        Fetch URL content using curl_cffi with authentic TLS browser impersonation.
        Rotates modern browser fingerprints and headers to bypass Cloudflare and WAF protections.
        """
        # Shuffle profiles to randomize order
        profiles = IMPERSONATION_PROFILES.copy()
        random.shuffle(profiles)
        last_err = None

        for imp in profiles:
            try:
                async with AsyncSession(impersonate=imp, verify=False, timeout=25) as session:
                    # Set browser-like headers
                    session.headers.update(BROWSER_HEADERS)
                    response = await session.get(url)
                    if response.status_code in (200, 201):
                        return response.text
                    elif response.status_code in (403, 503):
                        last_err = ConnectionError(f"Failed to fetch {url} (Status: {response.status_code})")
                        # Wait before trying next profile to avoid rate limiting
                        await asyncio.sleep(random.uniform(2, 5))
                        continue
                    else:
                        raise ConnectionError(f"Failed to fetch {url} (Status: {response.status_code})")
            except Exception as e:
                last_err = e
                # Wait before next attempt
                await asyncio.sleep(random.uniform(2, 5))
                continue

        raise last_err or ConnectionError(f"Failed to fetch {url}")

    @abstractmethod
    async def get_metadata(self, novel_url: str) -> NovelMetadata:
        """Scrape novel title, author, cover, and list of chapters."""
        pass

    @abstractmethod
    async def get_chapter_content(self, chapter_url: str) -> str:
        """Scrape and sanitize HTML text for a single chapter."""
        pass

    async def scrape_chapters(
        self,
        chapters: List[ChapterItem],
        start_idx: int,
        end_idx: int,
        progress_callback=None
    ) -> List[ChapterItem]:
        """
        Scrape a range of chapters (1-indexed) with randomized polite delays to prevent bans.
        """
        selected_chapters = chapters[start_idx - 1 : end_idx]
        total = len(selected_chapters)
        results = []

        for i, ch in enumerate(selected_chapters, 1):
            try:
                # Randomized delay: 1.5 to 3.5 seconds
                delay = random.uniform(1.5, 3.5)
                await asyncio.sleep(delay)

                html_content = await self.get_chapter_content(ch.url)
                ch.content_html = html_content
                results.append(ch)

                if progress_callback:
                    await progress_callback(current=i, total=total, current_title=ch.title)

            except Exception as e:
                logger.error(f"Error scraping chapter {ch.title} ({ch.url}): {e}")
                # Fallback content if chapter fails
                ch.content_html = f"<p><em>[Chapter content could not be retrieved: {e}]</em></p>"
                results.append(ch)

        return results

    def sanitize_text(self, soup_element) -> str:
        """Clean HTML elements, remove ads, scripts, watermarks."""
        if not soup_element:
            return ""

        # Remove garbage tags
        for tag in soup_element(["script", "style", "iframe", "ins", "button", "noscript", "svg", "form"]):
            tag.decompose()

        # Remove common ad and watermark classes
        for tag in soup_element.find_all(attrs={"class": re.compile(r"ad|banner|watermark|social|comment|share|donate", re.I)}):
            tag.decompose()

        # Clean paragraphs
        paragraphs = []
        for p in soup_element.find_all(["p", "div", "h2", "h3", "h4"]):
            text = p.get_text(strip=True)
            if text and not re.search(r"(read novel online free|visit .* for more chapters|translated by|patreon|discord)", text, re.I):
                paragraphs.append(f"<p>{text}</p>")

        if not paragraphs:
            # Fallback to direct text if no p tags
            lines = [line.strip() for line in soup_element.get_text().split("\n") if line.strip()]
            paragraphs = [f"<p>{line}</p>" for line in lines]

        return "\n".join(paragraphs)