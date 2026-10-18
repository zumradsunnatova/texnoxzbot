import os
import uuid
import html
import shutil
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.media_group import MediaGroupBuilder

from downloader import extract_instagram_url, InstagramDownloader
from video_converter import convert_to_video_note
from config import MAX_FILE_SIZE_BYTES, DOWNLOADS_DIR

logger = logging.getLogger(__name__)

router = Router(name="main_router")
downloader = InstagramDownloader()

# Telegram Bot API getFile orqali yuklab olish mumkin bo'lgan maksimal hajm (20 MB)
MAX_TELEGRAM_DOWNLOAD_BYTES = 20 * 1024 * 1024


def build_caption(title: str, uploader: str, bot_username: str = "") -> str:
    """Xavfsiz HTML formatdagi video sarlavhasini yasaydi."""
    parts = []
    if title:
        clean_title = html.escape(title[:300].strip())
        if len(title) > 300:
            clean_title += "..."
        parts.append(f"🎬 <b>{clean_title}</b>")

    if uploader:
        clean_uploader = html.escape(uploader.strip())
        parts.append(f"👤 <b>Muallif:</b> @{clean_uploader}")

    if bot_username:
        parts.append(f"🤖 @{bot_username}")

    return "\n\n".join(parts)


def get_post_keyboard(post_url: str) -> InlineKeyboardMarkup:
    """Instagram original posti uchun inline tugma yaratadi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Instagram'da ochish", url=post_url)
            ]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """
    /start buyrug'i uchun handler.
    """
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {html.escape(message.from_user.full_name)}!</b>\n\n"
        f"Men ko'p funksiyali video botman! 🚀\n\n"
        f"<b>Mening imkoniyatlarim:</b>\n"
        f"1️⃣ <b>Instagram yuklovchi:</b> Menga Instagram Reels yoki video havolasini yuboring — tayyor qilib yuklab beraman.\n"
        f"2️⃣ <b>Dumaloq video (Video Note / Kruglyash):</b> Menga istalgan oddiy video yuboring — uni Telegram dumaloq video xabari formatiga o'tkazib beraman! ⭕\n\n"
        f"💡 <i>Sinab ko'rish uchun hoziroq havola yoki video yuboring!</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    /help buyrug'i uchun handler.
    """
    help_text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "📥 <b>1. Instagram'dan video yuklash:</b>\n"
        "• Instagram'da videoning havolasidan nusxa oling (Copy link).\n"
        "• Havolani botga yuboring.\n"
        "• Bot videoni yuklab beradi.\n\n"
        "⭕ <b>2. Dumaloq video (kruglyash) yasash:</b>\n"
        "• O'zingizdagi istalgan to'rtburchak/oddiy videoni botga yuboring.\n"
        "• Bot uni avtomatik tarzda markazidan 1:1 kvadrat qilib qirqadi va Telegram dumaloq video xabariga aylantirib beradi.\n\n"
        "⚠️ <b>Eslatmalar:</b>\n"
        "• Dumaloq videolar davomiyligi Telegram talabi bo'yicha maksimal 60 soniya bo'ladi.\n"
        "• Botga yuboriladigan videoning hajmi 20 MB dan oshmasligi lozim."
    )
    await message.answer(help_text, parse_mode="HTML")


async def process_video_to_note(message: Message, bot: Bot, file_id: str, file_size: int, duration: int = None):
    """Oddiy videoni yuklab olib, dumaloq video xabariga o'tkazuvchi umumiy yordamchi funksiya."""
    if file_size and file_size > MAX_TELEGRAM_DOWNLOAD_BYTES:
        size_mb = file_size / (1024 * 1024)
        await message.reply(
            f"⚠️ <b>Kechirasiz, video hajmi juda katta ({size_mb:.1f} MB)!</b>\n\n"
            f"Telegram botlar orqali qayta ishlash uchun maksimal <b>20 MB</b> gacha bo'lgan videolarni qabul qilish mumkin.",
            parse_mode="HTML"
        )
        return

    status_msg = await message.reply("⏳ <b>Video qabul qilindi. Dumaloq video formatiga o'tkazilmoqda...</b>", parse_mode="HTML")

    task_id = uuid.uuid4().hex
    task_dir = os.path.join(DOWNLOADS_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    input_path = os.path.join(task_dir, "input_video.mp4")
    output_path = os.path.join(task_dir, "output_note.mp4")

    try:
        async with ChatActionSender.record_video_note(bot=bot, chat_id=message.chat.id):
            # Telegramdan videoni yuklab olish (timeout 300 soniya qilib belgilandi)
            file_info = await bot.get_file(file_id)
            await bot.download_file(
                file_path=file_info.file_path,
                destination=input_path,
                timeout=300,
                chunk_size=1024 * 512
            )

            # FFmpeg yordamida dumaloq formatga o'tkazish
            success = await asyncio.to_thread(convert_to_video_note, input_path, output_path, 60)

        if not success:
            await status_msg.edit_text("❌ Videoni dumaloq formatga o'tkazishda xatolik yuz berdi.", parse_mode="HTML")
            return

        out_duration = min(duration, 60) if duration else None

        # Dumaloq video (Video Note) ko'rinishida yuborish
        await bot.send_video_note(
            chat_id=message.chat.id,
            video_note=FSInputFile(output_path),
            duration=out_duration,
            length=384,
            reply_to_message_id=message.message_id
        )

        if duration and duration > 60:
            await message.reply(
                "ℹ️ <i>Telegram dumaloq video xabarlari maksimal 60 soniya bo'lishi mumkinligi sababli, videoning dastlabki 60 soniyasi olindi.</i>",
                parse_mode="HTML"
            )

        try:
            await status_msg.delete()
        except Exception:
            pass

    except asyncio.TimeoutError:
        logger.warning("Video yuklab olishda TimeoutError yuz berdi.")
        await status_msg.edit_text(
            "❌ <b>Yuklash vaqti tugadi (Timeout):</b> Internet tezligi pastligi sababli videoni serverdan yuklab olish cho'zilib ketdi. Iltimos, qayta urinib ko'ring.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception("Dumaloq video yaratishda xatolik:")
        err_msg = str(e).strip() or type(e).__name__
        await status_msg.edit_text(
            f"❌ Xatolik yuz berdi: {html.escape(err_msg)}",
            parse_mode="HTML"
        )
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)


@router.message(F.video)
async def handle_video(message: Message, bot: Bot):
    """Foydalanuvchi to'g'ridan-to'g'ri video yuborganida ishga tushadi."""
    video = message.video
    await process_video_to_note(
        message=message,
        bot=bot,
        file_id=video.file_id,
        file_size=video.file_size,
        duration=video.duration
    )


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    """Foydalanuvchi fayl (hujjat) ko'rinishida video yuborganida ishga tushadi."""
    doc = message.document
    mime = (doc.mime_type or "").lower()
    fname = (doc.file_name or "").lower()

    # Fayl video ekanligini tekshirish
    is_video = mime.startswith("video/") or fname.endswith(('.mp4', '.mov', '.mkv', '.avi', '.webm'))
    if is_video:
        await process_video_to_note(
            message=message,
            bot=bot,
            file_id=doc.file_id,
            file_size=doc.file_size
        )
    else:
        # Agar oddiy fayl (masalan pdf yoki rasm) bo'lsa
        await message.reply(
            "⚠️ <b>Iltimos, video fayl yoki Instagram havolasini yuboring!</b>",
            parse_mode="HTML"
        )


@router.message(F.text)
async def handle_instagram_link(message: Message, bot: Bot):
    """
    Foydalanuvchi yuborgan xabarni tekshiradi va Instagram havolasi bo'lsa videoni yuklaydi.
    """
    url = extract_instagram_url(message.text)

    # Agar xabarda Instagram havolasi bo'lmasa
    if not url:
        await message.reply(
            "⚠️ <b>Iltimos, to'g'ri Instagram havolasini yoki dumaloq formatga o'tkazish uchun video yuboring!</b>\n\n"
            "Masalan:\n<code>https://www.instagram.com/reel/...</code>",
            parse_mode="HTML"
        )
        return

    # Jarayon boshlanganini bildiruvchi xabar
    status_msg = await message.reply("⏳ <b>Video yuklanmoqda, iltimos kuting...</b>", parse_mode="HTML")

    task_dir = None
    try:
        # Telegramda 'video yuklanmoqda' indikatorini ko'rsatish
        async with ChatActionSender.upload_video(bot=bot, chat_id=message.chat.id):
            result = await asyncio.to_thread(downloader.download, url)

        # Agar yuklab olishda xatolik yuz bergan bo'lsa
        if not result["success"]:
            await status_msg.edit_text(result["message"], parse_mode="HTML")
            return

        task_dir = result.get("task_dir")
        files = result.get("files", [])
        bot_info = await bot.get_me()
        caption = build_caption(
            title=result.get("title", ""),
            uploader=result.get("uploader", ""),
            bot_username=bot_info.username or ""
        )
        reply_markup = get_post_keyboard(result.get("webpage_url", url))

        # Agar bitta fayl bo'lsa
        if len(files) == 1:
            file_path = files[0]
            file_size = os.path.getsize(file_path)

            if file_size > MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                await status_msg.edit_text(
                    f"⚠️ <b>Kechirasiz, video hajmi juda katta ({size_mb:.1f} MB)!</b>\n\n"
                    f"Telegram botlari orqali faqat 50 MB gacha bo'lgan fayllarni yuborish mumkin.",
                    parse_mode="HTML"
                )
                return

            ext = os.path.splitext(file_path)[1].lower()
            input_file = FSInputFile(file_path)

            if ext in ['.mp4', '.mov', '.mkv', '.webm']:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=input_file,
                    caption=caption,
                    duration=result.get("duration"),
                    width=result.get("width"),
                    height=result.get("height"),
                    supports_streaming=True,
                    reply_to_message_id=message.message_id,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=input_file,
                    caption=caption,
                    reply_to_message_id=message.message_id,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )

        # Agar karusel bo'lsa
        elif len(files) > 1:
            valid_media_files = [f for f in files if os.path.getsize(f) <= MAX_FILE_SIZE_BYTES]

            if not valid_media_files:
                await status_msg.edit_text(
                    "⚠️ Medialar hajmi Telegram cheklovidan (50 MB) oshib ketganligi sababli yuborib bo'lmadi.",
                    parse_mode="HTML"
                )
                return

            media_group = MediaGroupBuilder(caption=caption[:1024])
            for fpath in valid_media_files[:10]:
                ext = os.path.splitext(fpath)[1].lower()
                inp = FSInputFile(fpath)
                if ext in ['.mp4', '.mov', '.mkv', '.webm']:
                    media_group.add_video(media=inp)
                else:
                    media_group.add_photo(media=inp)

            try:
                await bot.send_media_group(
                    chat_id=message.chat.id,
                    media=media_group.build(),
                    reply_to_message_id=message.message_id
                )
            except Exception as e:
                logger.warning(f"MediaGroup yuborishda xatolik, alohida yuborilmoqda: {e}")
                for fpath in valid_media_files:
                    ext = os.path.splitext(fpath)[1].lower()
                    inp = FSInputFile(fpath)
                    if ext in ['.mp4', '.mov', '.mkv', '.webm']:
                        await bot.send_video(chat_id=message.chat.id, video=inp)
                    else:
                        await bot.send_photo(chat_id=message.chat.id, photo=inp)

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.exception("Xatolik yuz berdi:")
        await status_msg.edit_text(
            f"❌ Xatolik yuz berdi: {html.escape(str(e))}",
            parse_mode="HTML"
        )
    finally:
        if task_dir:
            downloader.cleanup(task_dir)
