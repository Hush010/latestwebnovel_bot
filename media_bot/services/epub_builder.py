import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import List, Optional
import aiohttp
from ebooklib import epub
from urllib.parse import urlparse

from config import TEMP_DIR
from .scrapers.base import ChapterItem, NovelMetadata

logger = logging.getLogger(__name__)

BOOK_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: "Georgia", "Merriweather", "Times New Roman", serif;
    line-height: 1.6;
    margin: 5%;
    padding: 0;
    color: #1a1a1a;
    background-color: #fdfdfd;
}
h1, h2, h3 {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    text-align: center;
    color: #2c3e50;
    margin-bottom: 1.5em;
}
p {
    text-indent: 1.5em;
    margin-bottom: 0.8em;
    text-align: justify;
}
.chapter-header {
    text-align: center;
    border-bottom: 1px solid #ddd;
    padding-bottom: 1em;
    margin-bottom: 2em;
}
"""


class EpubBuilder:
    """Compiles scraped chapters into a standard, clean .epub file."""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
        return clean[:60] if len(clean) > 60 else clean

    @classmethod
    async def _fetch_cover_image(cls, url: str) -> Optional[bytes]:
        """Fetch cover image bytes asynchronously."""
        if not url or not url.startswith("http"):
            return None
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            logger.warning(f"Failed to download cover image from {url}: {e}")
        return None

    @classmethod
    async def build_epub(
        cls,
        metadata: NovelMetadata,
        chapters: List[ChapterItem],
        range_suffix: str = ""
    ) -> Optional[str]:
        """
        Build an .epub file from chapters.
        Returns the absolute path to the generated .epub file.
        """
        def _compile(cover_bytes=None):
            book = epub.EpubBook()
            book_id = f"urn:uuid:{uuid.uuid4()}"
            book.set_identifier(book_id)
            book.set_title(metadata.title)
            book.set_language("en")
            book.add_author(metadata.author or "Unknown Author")

            # Set cover image if available
            if cover_bytes:
                # Determine file extension from cover URL or default to .jpg
                ext = ".jpg"
                if metadata.cover_url:
                    try:
                        parsed = urlparse(metadata.cover_url)
                        path = parsed.path
                        if '.' in path:
                            ext = path[path.rfind('.'):]
                            if not ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
                                ext = '.jpg'
                    except Exception:
                        pass
                book.set_cover(f"cover{ext}", cover_bytes)

            # Add CSS
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=BOOK_CSS.encode("utf-8")
            )
            book.add_item(nav_css)

            # Chapters & TOC
            epub_chapters = []
            toc_entries = []

            for ch in chapters:
                ch_filename = f"chapter_{ch.index:04d}.xhtml"
                epub_ch = epub.EpubHtml(
                    title=ch.title,
                    file_name=ch_filename,
                    lang="en"
                )
                
                # Format chapter HTML
                body_content = ch.content_html or "<p><em>[No Content]</em></p>"
                html_document = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{ch.title}</title>
    <link rel="stylesheet" href="style/nav.css" type="text/css" />
</head>
<body>
    <div class="chapter-header">
        <h2>{ch.title}</h2>
    </div>
    <div class="chapter-body">
        {body_content}
    </div>
</body>
</html>"""
                epub_ch.set_content(html_document.encode("utf-8"))
                epub_ch.add_item(nav_css)
                book.add_item(epub_ch)
                epub_chapters.append(epub_ch)
                toc_entries.append(epub_ch)

            # Table of Contents
            book.toc = tuple(toc_entries)

            # Navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Spine
            book.spine = ["nav"] + epub_chapters

            # Output filename
            sanitized_title = cls._sanitize_filename(metadata.title)
            suffix = f"_{range_suffix}" if range_suffix else ""
            unique_token = uuid.uuid4().hex[:6]
            output_filename = f"{sanitized_title}{suffix}_{unique_token}.epub"
            output_path = TEMP_DIR / output_filename

            epub.write_epub(str(output_path), book, {})
            return str(output_path)

        try:
            # Download cover image if available
            cover_bytes = await cls._fetch_cover_image(metadata.cover_url)
            
            # Execute CPU-bound ePub creation in thread
            epub_file_path = await asyncio.to_thread(_compile, cover_bytes)

            return epub_file_path

        except Exception as e:
            logger.error(f"Failed to build ePub for {metadata.title}: {e}", exc_info=True)
            return None

    @staticmethod
    def cleanup_file(file_path: str):
        """Safely delete the generated .epub file."""
        try:
            p = Path(file_path)
            if p.exists():
                p.unlink()
                logger.info(f"Cleaned up local ePub file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete {file_path}: {e}")
