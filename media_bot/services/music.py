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
    """Multi-source audio search and extraction engine (YouTube + SoundCloud fallback)."""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string to be safe for filenames."""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    @staticmethod
    def _clean_track_title(title: str) -> str:
        """Strip brackets, official audio tags, etc."""
        cleaned = re.sub(r'\[.*?\]|\(.*?\)|official audio|official video|lyrics|hq|audio|video', '', title, flags=re.I)
        return re.sub(r'\s+', ' ', cleaned).strip()

    @classmethod
    async def search_tracks(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search YouTube / SoundCloud for tracks matching query."""
        search_target = query if (query.startswith("http://") or query.startswith("https://")) else f"ytsearch{limit}:{query}"

        def _search():
            ydl_opts = {
                "format": "ba/b/bestaudio/best",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "ios", "mweb"]
                    }
                },
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }
            results = []
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_target, download=False)
                    if info:
                        entries = info.get("entries", [])
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
                                "source": "youtube"
                            })
            except Exception as e:
                logger.warning(f"YouTube search failed for '{query}': {e}")

            # If YouTube search returned nothing, fallback to SoundCloud search
            if not results and not (query.startswith("http://") or query.startswith("https://")):
                try:
                    sc_opts = {
                        "format": "bestaudio/best",
                        "noplaylist": True,
                        "quiet": True,
                        "no_warnings": True,
                        "extract_flat": True,
                    }
                    with yt_dlp.YoutubeDL(sc_opts) as sc_ydl:
                        sc_info = sc_ydl.extract_info(f"scsearch{limit}:{query}", download=False)
                        if sc_info:
                            for entry in sc_info.get("entries", []):
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
                                    "uploader": entry.get("uploader") or entry.get("user", {}).get("username", "Unknown Artist"),
                                    "url": entry.get("url") or entry.get("webpage_url"),
                                    "duration_string": duration_str,
                                    "duration": duration_sec,
                                    "source": "soundcloud"
                                })
                except Exception as sc_err:
                    logger.warning(f"SoundCloud fallback search failed: {sc_err}")

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
        Download track audio, convert to .mp3 via ffmpeg, and attach ID3 tags.
        Includes automatic fallback to SoundCloud if YouTube blocks datacenter IP.
        """
        download_id = uuid.uuid4().hex[:8]
        out_template = str(TEMP_DIR / f"song_{download_id}_%(title)s.%(ext)s")

        def _download_attempt(target_url: str, is_yt: bool = True):
            ydl_opts = {
                "format": "ba/b/bestaudio/best",
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
            if is_yt:
                ydl_opts["extractor_args"] = {
                    "youtube": {
                        "player_client": ["android", "ios", "mweb"]
                    }
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                title = expected_title or (info.get("title") if info else "Unknown Track")
                artist = expected_artist or (info.get("uploader") if info else "Unknown Artist")
                duration = info.get("duration", 0) if info else 0

                # Locate generated mp3 file
                target_file = None
                for file_path in TEMP_DIR.glob(f"song_{download_id}_*.mp3"):
                    target_file = file_path
                    break

                if not target_file or not target_file.exists():
                    raise FileNotFoundError("Audio extraction failed: output mp3 not found.")

                # Attach ID3 tags
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

        def _execute_with_fallback():
            # Attempt 1: Direct URL download
            try:
                return _download_attempt(track_url, is_yt=("youtube.com" in track_url or "youtu.be" in track_url))
            except Exception as primary_err:
                logger.warning(f"Primary audio download failed for {track_url}: {primary_err}. Attempting SoundCloud fallback...")

            # Attempt 2: Cleaned search query fallback to SoundCloud
            clean_title = cls._clean_track_title(expected_title or "")
            clean_artist = cls._clean_track_title(expected_artist or "")
            search_query = f"{clean_title} {clean_artist}".strip() or expected_title or ""
            
            if search_query:
                try:
                    fallback_target = f"scsearch1:{search_query}"
                    return _download_attempt(fallback_target, is_yt=False)
                except Exception as sc_err:
                    logger.error(f"SoundCloud fallback also failed for '{search_query}': {sc_err}")

            return None

        try:
            return await asyncio.to_thread(_execute_with_fallback)
        except Exception as e:
            logger.error(f"Failed to execute audio download for {track_url}: {e}", exc_info=True)
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
