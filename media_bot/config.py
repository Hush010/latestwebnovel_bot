import os
from pathlib import Path
from dotenv import load_dotenv

# Base project path
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "temp_downloads")).resolve()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Ensure temp directory exists
TEMP_DIR.mkdir(parents=True, exist_ok=True)
