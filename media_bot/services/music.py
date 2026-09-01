import os
import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB

from config import TEMP_DIR

logger = logging.getLogger(__name__)


class MusicService:
    """Service for searching, downloading, and converting audio tracks using yt-dlp & ffmpeg."""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string to be safe for filenames."""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    @classmethod
    async def search_tracks(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search YouTube for tracks matching query."""
        search_target = query if (query.startswith("http://") or query.startswith("https://")) else f"ytsearch{limit}:{query}"

        def _search():
            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_target, download=False)
                if not info:
                    return []
                entries = info.get("entries", [])
                results = []
                for entry in entries:
                    if not entry:
                        continue
                    duration_sec = entry.get("duration")
                    duration_str = ""
                    if duration_sec is not None:
                        mins, secs = divmod(int(duration_sec), 60)
                        duration_str = f"{mins}:{secs:02d}"
                    
                    results.append({
                        "id": entry.get("id"),
                        "title": entry.get("title", "Unknown Title"),
                        "uploader": entry.get("uploader") or entry.get("channel", "Unknown Artist"),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "duration_string": duration_str,
                        "duration": duration_sec,
                    })
                return results

        try:
            return await asyncio.to_thread(_search)
        except Exception as e:
            logger.error(f"Error searching tracks for '{query}': {e}", exc_info=True)
            return []

    @classmethod
    async def download_track(
        cls,
        track_url: str,
        expected_title: Optional[str] = None,
        expected_artist: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Download track audio, convert strictly to .mp3 via ffmpeg, and attach ID3 tags.
        Returns dict with file_path, title, artist, duration, or None on error.
        """
        download_id = uuid.uuid4().hex[:8]
        out_template = str(TEMP_DIR / f"song_{download_id}_%(title)s.%(ext)s")

        def _download():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(track_url, download=True)
                title = expected_title or info.get("title", "Unknown Track")
                artist = expected_artist or info.get("uploader") or info.get("channel", "Unknown Artist")
                duration = info.get("duration", 0)

                # Locate the generated mp3 file
                target_file = None
                for file_path in TEMP_DIR.glob(f"song_{download_id}_*.mp3"):
                    target_file = file_path
                    break

                if not target_file or not target_file.exists():
                    raise FileNotFoundError("Audio extraction failed: output mp3 not found.")

                # Ensure ID3 metadata tags are attached
                try:
                    try:
                        audio = EasyID3(str(target_file))
                    except Exception:
                        audio = MP3(str(target_file))
                        audio.add_tags()
                        audio = EasyID3(str(target_file))

                    audio["title"] = title
                    audio["artist"] = artist
                    audio.save()
                except Exception as meta_err:
                    logger.warning(f"Could not write ID3 tags for {target_file}: {meta_err}")

                return {
                    "file_path": str(target_file),
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                }

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(f"Error downloading track {track_url}: {e}", exc_info=True)
            return None

    @staticmethod
    def cleanup_file(file_path: str):
        """Safely delete a temporary file if it exists."""
        try:
            p = Path(file_path)
            if p.exists():
                p.unlink()
                logger.info(f"Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete {file_path}: {e}")
