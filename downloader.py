import os
import re
import uuid
import shutil
import logging
from typing import Dict, Any, List, Optional
import yt_dlp

from config import DOWNLOADS_DIR, COOKIES_FILE

logger = logging.getLogger(__name__)

# Instagram havolalarini aniqlash uchun regex
INSTAGRAM_URL_REGEX = re.compile(
    r'https?://(?:www\.)?(?:instagram\.com|instagr\.am)/[^\s<>"\'`]+',
    re.IGNORECASE
)


def extract_instagram_url(text: str) -> Optional[str]:
    """
    Matn ichidan Instagram havolasini ajratib oladi va tozaylaydi.
    """
    if not text:
        return None
    match = INSTAGRAM_URL_REGEX.search(text)
    if not match:
        return None
    url = match.group(0)
    # Oxiridagi keraksiz belgilarni olib tashlash
    url = url.rstrip('.,;!?)\'">]')
    return url


class InstagramDownloader:
    """
    Instagram'dan video va medialarni yt-dlp yordamida xavfsiz va
    asinxron rejimda yuklab olish sinfi.
    """

    def __init__(self, base_dir=DOWNLOADS_DIR, cookies_file=COOKIES_FILE):
        self.base_dir = base_dir
        self.cookies_file = cookies_file

    def download(self, url: str) -> Dict[str, Any]:
        """
        Berilgan Instagram havolasidan videoni yuklab oladi.
        Ushbu metod sinxron ishlaydi, shuning uchun aiogram handlerida
        asyncio.to_thread() orqali chaqirilishi kerak.
        """
        task_id = uuid.uuid4().hex
        task_dir = os.path.join(self.base_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)

        downloaded_files: List[str] = []

        def progress_hook(d):
            if d.get("status") == "finished":
                filename = d.get("filename")
                if filename and filename not in downloaded_files:
                    downloaded_files.append(filename)

        ydl_opts = {
            # Eng yaxshi sifatdagi MP4 formatini tanlash
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(task_dir, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': False,  # Karusel (bir nechta video/rasm) postlarni ham qo'llab-quvvatlash
            'progress_hooks': [progress_hook],
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
        }

        # Agar cookies.txt mavjud bo'lsa, uni qo'shamiz
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = str(self.cookies_file)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # Agar progress_hook orqali fayllar to'liq yozilmagan bo'lsa, jildni tekshiramiz
            if not downloaded_files and os.path.exists(task_dir):
                for fname in os.listdir(task_dir):
                    fpath = os.path.join(task_dir, fname)
                    if os.path.isfile(fpath):
                        downloaded_files.append(fpath)

            # Vaqtinchalik (.part, .ytdl) fayllarni chiqarib tashlaymiz
            valid_files = [
                f for f in downloaded_files
                if os.path.exists(f) and not f.endswith(('.part', '.ytdl', '.temp'))
            ]

            if not valid_files:
                self.cleanup(task_dir)
                return {
                    "success": False,
                    "error_type": "no_media",
                    "message": "Ushbu havoladan yuklab olish uchun hech qanday media topilmadi."
                }

            # Post haqidagi ma'lumotlar
            title = (info.get("title") or info.get("description") or "").strip()
            uploader = (info.get("uploader") or info.get("channel") or "").strip()
            duration = info.get("duration")
            width = info.get("width")
            height = info.get("height")

            return {
                "success": True,
                "task_dir": task_dir,
                "files": valid_files,
                "title": title,
                "uploader": uploader,
                "duration": int(duration) if duration and isinstance(duration, (int, float)) else None,
                "width": int(width) if width and isinstance(width, (int, float)) else None,
                "height": int(height) if height and isinstance(height, (int, float)) else None,
                "webpage_url": info.get("webpage_url", url),
            }

        except yt_dlp.utils.DownloadError as e:
            self.cleanup(task_dir)
            err_str = str(e).lower()
            logger.error(f"yt-dlp DownloadError: {e}")

            if "private" in err_str or "login" in err_str:
                msg = "❌ Bu video yopiq (private) profilga tegishli yoki ko'rish uchun Instagram akkountiga kirish talab etiladi."
                err_type = "private"
            elif "unavailable" in err_str or "not found" in err_str or "404" in err_str:
                msg = "❌ Video topilmadi yoki muallif tomonidan o'chirib yuborilgan."
                err_type = "not_found"
            else:
                msg = "❌ Videoni yuklab olishda xatolik yuz berdi. Havola to'g'riligini tekshiring yoki birozdan so'ng qayta urinib ko'ring."
                err_type = "download_error"

            return {
                "success": False,
                "error_type": err_type,
                "message": msg
            }

        except Exception as e:
            self.cleanup(task_dir)
            logger.exception("Yuklab olishda kutilmagan xatolik yuz berdi:")
            return {
                "success": False,
                "error_type": "unexpected",
                "message": f"❌ Kutilmagan xatolik yuz berdi: {str(e)}"
            }

    @staticmethod
    def cleanup(task_dir: str):
        """Vaqtinchalik yuklab olingan fayllar va jildni o'chiradi."""
        try:
            if task_dir and os.path.exists(task_dir):
                shutil.rmtree(task_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Jildni tozalashda xatolik ({task_dir}): {e}")
