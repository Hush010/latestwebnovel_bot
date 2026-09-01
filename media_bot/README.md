# 🤖 Telegram Media & Webnovel Downloader Bot

An asynchronous, production-ready Telegram Bot built with `aiogram 3.x`, `yt-dlp`, `ffmpeg`, `curl_cffi`, and `EbookLib`.

## ✨ Core Features

### 🎵 1. Music Downloader
- Search YouTube / audio sources via `/song <keywords>` or interactive button menu.
- Interactive inline keyboard displaying top 5 search results with duration.
- High-quality audio extraction strictly converted to `.mp3` using `ffmpeg`.
- ID3 metadata auto-tagging (Song Title & Artist) via `mutagen`.
- Immediate cleanup of temporary local files upon delivery.

### 📚 2. Webnovel Scraper & ePub Generator (FSM Wizard)
- Interactive conversational state machine (`NovelDownloadStates`).
- Step-by-step wizard:
  1. Paste novel URL (NovelBin, FreeWebNovel, Ranobes, NovelFire, and generic webnovel sources).
  2. Automatic TOC parsing, title/author extraction, and cover image detection.
  3. Inline choice: **Download Full Novel** ($1 - N$) or **Select Custom Chapter Range** (e.g. `1-100`).
  4. Polite scraping engine with randomized delays ($1.5s - 3.5s$) to prevent rate limits.
  5. Live throttled progress bar updates in Telegram.
  6. Compiles styled, clean `.epub` ebook with cover, chapters, and navigable Table of Contents (NCX/Nav).
  7. Delivers `.epub` document to chat and cleans up local storage immediately.

---

## 🚀 Quick Local Setup

### 1. Configure Bot Token
Copy `.env.example` to `.env` and insert your token from [@BotFather](https://t.me/BotFather):
```bash
cp .env.example .env
```
Edit `.env`:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 2. Run the Bot
```bash
# Using the preconfigured virtual environment
media_bot/.venv/bin/python media_bot/bot.py
```

---

## 🌐 24/7 Cloud Hosting
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for step-by-step instructions on hosting the bot 24/7 on Oracle Cloud (Free Forever), Hetzner, Railway, Render, or Docker VPS.
