# 🚀 24/7 Cloud Deployment Guide

This guide explains how to host your Telegram Media & Webnovel Bot in the cloud so it runs 24/7 without needing your personal PC to stay powered on.

---

## 🌟 Recommended Cloud Hosting Options

| Provider | Cost | Best For | Why Choose It |
| :--- | :--- | :--- | :--- |
| **Oracle Cloud (Always Free)** | **100% FREE** forever | Long-term 24/7 bot hosting | Up to 4 ARM OCPUs & 24 GB RAM for \$0/month forever. |
| **Hetzner Cloud** | **~€3.50/mo** | High performance & reliability | Best price-to-performance VPS in Europe/US. |
| **DigitalOcean / Linode** | **\$4 - \$6/mo** | Simple setup & documentation | Standard Linux VPS with 1-click snapshots. |
| **Railway.app / Render** | **Free tier / Pay-per-use** | Fast Docker deployment | Deploy directly from GitHub repository without managing a Linux server. |

---

## Method 1: Deploy on a Linux VPS with Docker (Recommended)

This is the cleanest and most reliable method.

### Step 1: Connect to your VPS
```bash
ssh root@your_server_ip
```

### Step 2: Install Docker and Git (Ubuntu/Debian)
```bash
apt update && apt install -y docker.io docker-compose-v2 git
```

### Step 3: Copy or Clone your Bot files
```bash
git clone <your-repo-link> /opt/media_bot
cd /opt/media_bot
```

### Step 4: Configure your Environment
Create `.env` and paste your Telegram Bot Token:
```bash
cp .env.example .env
nano .env
```
Set:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
LOG_LEVEL=INFO
```
Save with `Ctrl + O`, then `Enter`, then exit with `Ctrl + X`.

### Step 5: Start the Bot
```bash
docker compose up -d --build
```

### Useful Management Commands:
- **View Live Logs:** `docker compose logs -f`
- **Restart Bot:** `docker compose restart`
- **Stop Bot:** `docker compose down`

---

## Method 2: Deploy on Linux VPS with Systemd

If you prefer running directly in Python without Docker:

### Step 1: Install Python & FFmpeg
```bash
apt update && apt install -y python3 python3-venv python3-pip ffmpeg
```

### Step 2: Setup Bot in `/opt/media_bot`
```bash
mkdir -p /opt/media_bot
cd /opt/media_bot
# Copy project files here
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env  # Add your BOT_TOKEN
```

### Step 3: Enable and Start Systemd Service
```bash
cp media_bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now media_bot
```

### Useful Commands:
- **Check Status:** `systemctl status media_bot`
- **View Logs:** `journalctl -u media_bot -f`
- **Restart:** `systemctl restart media_bot`

---

## Method 3: Deploy on Railway / Render (PaaS)

1. Push this folder to a GitHub repository.
2. Go to [Railway.app](https://railway.app) or [Render.com](https://render.com).
3. Create a new project connected to your GitHub repository.
4. Set the environment variable `BOT_TOKEN` in the Railway/Render dashboard.
5. Railway/Render will automatically detect the `Dockerfile` and start the bot.
