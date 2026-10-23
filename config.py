import os
from pathlib import Path
from dotenv import load_dotenv

# Loyiha ildiz katalogi
BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklash
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Gemini AI API kaliti
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Yuklab olinadigan vaqtinchalik fayllar katalogi
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Instagram cookies fayli (agar mavjud bo'lsa)
COOKIES_FILE = BASE_DIR / "cookies.txt"

# Telegram bot orqali yuborish mumkin bo'lgan maksimal fayl hajmi (50 MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
