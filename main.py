import sys
import asyncio
import logging

# Windows konsolida Unicode/Emoji belgilarini to'g'ri ko'rsatish
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand

from config import BOT_TOKEN
from handlers import router

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s : %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Telegram menyusidagi buyruqlarni sozlash."""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="help", description="📖 Yordam va qo'llanma"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Botni ishga tushirishning asosiy funksiyasi."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "❌ XATOLIK: BOT_TOKEN aniqlanmadi!\n"
            "Iltimos, .env faylini oching va @BotFather dan olingan tokenni kiriting:\n"
            "BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ\n"
            + "=" * 60
        )
        sys.exit(1)

    # Bot va Dispatcher yaratish (300 soniya timeout bilan)
    session = AiohttpSession(timeout=300)
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Handler routerlarini ulash
    dp.include_router(router)

    # Bot ishga tushayotganda menyu buyruqlarini o'rnatish
    await set_bot_commands(bot)

    # Eski kutilayotgan yangilanishlarni (pending updates) o'chirish
    await bot.delete_webhook(drop_pending_updates=True)

    bot_user = await bot.get_me()
    logger.info(f"✅ Bot muvaffaqiyatli ishga tushdi: @{bot_user.username} ({bot_user.full_name})")

    try:
        # Polling rejimida yangilanishlarni qabul qilish
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
