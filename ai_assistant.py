import logging
import asyncio
from typing import Dict, List, Any
import aiohttp
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Foydalanuvchilar suhbat tarixi xotirasi (user_id -> xabarlar ro'yxati)
_user_histories: Dict[int, List[Dict[str, Any]]] = {}

# Modellarni navbat bilan sinab ko'rish ro'yxati (tezkor va barqaror)
MODELS_TO_TRY = [
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]

SYSTEM_PROMPT = (
    "Siz 'texnoxbot' nomli Telegram botining aqlli, xushmuomala va samimiy AI suhbatdoshisiz. "
    "Foydalanuvchi bilan o'zbek tilida (yoki foydalanuvchi murojaat qilgan tilda) samimiy, madaniyatli va lo'nda suhbat qurasiz. "
    "Telegram xabarlariga mos, tushunarli, chiroyli paragraflar va me'yordagi emojilardan foydalaning. "
    "Agar foydalanuvchi Instagramdan video yuklash yoki dumaloq video (kruglyash) yasash haqida so'rasa, "
    "botimiz bu vazifalarni bajara olishini (Instagram link yuborish yoki video fayl yuborish kifoyaligini) tushuntiring."
)


def reset_chat(user_id: int):
    """Foydalanuvchining suhbat tarixini tozalaydi."""
    if user_id in _user_histories:
        _user_histories[user_id] = []


async def _call_gemini_api(model: str, contents: List[Dict[str, Any]]) -> str:
    """Gemini REST API ga so'rov yuborish."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        }
    }

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
                return "Kechirasiz, javob olishda muammo bo'ldi. Iltimos, qaytadan yozib ko'ring."
            else:
                err_body = await response.text()
                logger.warning(f"Gemini API xatolik ({response.status}) model {model}: {err_body[:200]}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"Gemini error {response.status}"
                )


async def ask_ai(user_id: int, user_message: str) -> str:
    """
    Foydalanuvchi xabarini qabul qilib, suhbat tarixini hisobga olgan holda
    Gemini AI dan javob qaytaradi.
    """
    if not GEMINI_API_KEY:
        return "⚠️ AI xizmati sozlanmagan. Iltimos, administrator bilan bog'laning."

    # Foydalanuvchi tarixini olish yoki yangisini yaratish
    history = _user_histories.setdefault(user_id, [])

    # Joriy so'rov uchun contents tuzish
    contents = list(history)
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    response_text = None

    for model in MODELS_TO_TRY:
        try:
            response_text = await _call_gemini_api(model, contents)
            if response_text:
                break
        except Exception as e:
            logger.warning(f"Model {model} bilan sinov muvaffaqiyatsiz bo'ldi: {e}")
            await asyncio.sleep(0.5)
            continue

    if not response_text:
        return "😔 Kechirasiz, serverda vaqtinchalik yuklama yuqori bo'lgani sababli javob bera olmadim. Iltimos, birozdan so'ng qayta yozing."

    # Muvaffaqiyatli javobni tarixga saqlash
    history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    history.append({
        "role": "model",
        "parts": [{"text": response_text}]
    })

    # Xotira hajmini cheklash (oxirgi 8 ta xabar)
    if len(history) > 8:
        _user_histories[user_id] = history[-8:]

    return response_text
