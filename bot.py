"""
Telegram Bot — Instagram va YouTube'dan video/audio yuklab oluvchi bot
Cookie qo'llab-quvvatlash bilan
"""
import os
import logging
import asyncio
from pathlib import Path

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
COOKIES_DIR = Path("cookies")
COOKIES_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024

user_urls: dict[int, str] = {}


def setup_cookies() -> None:
    yt_cookies = os.getenv("YOUTUBE_COOKIES")
    if yt_cookies and yt_cookies.strip():
        (COOKIES_DIR / "youtube.txt").write_text(yt_cookies)
        logger.info("✅ YouTube cookies yuklandi")
    else:
        logger.warning("⚠️ YOUTUBE_COOKIES yo'q — YouTube bloklanishi mumkin")

    ig_cookies = os.getenv("INSTAGRAM_COOKIES")
    if ig_cookies and ig_cookies.strip():
        (COOKIES_DIR / "instagram.txt").write_text(ig_cookies)
        logger.info("✅ Instagram cookies yuklandi")
    else:
        logger.warning("⚠️ INSTAGRAM_COOKIES yo'q — Instagram bloklanishi mumkin")


def get_cookie_file(url: str) -> str | None:
    u = url.lower()
    if "instagram.com" in u:
        p = COOKIES_DIR / "instagram.txt"
        return str(p) if p.exists() else None
    if "youtube.com" in u or "youtu.be" in u:
        p = COOKIES_DIR / "youtube.txt"
        return str(p) if p.exists() else None
    return None


def is_valid_url(url: str) -> bool:
    u = url.lower()
    return any(d in u for d in ("instagram.com", "youtube.com", "youtu.be"))


def clean_user_files(user_id: int) -> None:
    for f in DOWNLOAD_DIR.glob(f"{user_id}_*"):
        try:
            f.unlink()
        except OSError:
            pass


async def run_ytdlp(ydl_opts: dict, url: str) -> str:
    loop = asyncio.get_event_loop()

    def _download() -> str:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if ydl_opts.get("postprocessors"):
                for pp in ydl_opts["postprocessors"]:
                    if pp.get("key") == "FFmpegExtractAudio":
                        filename = str(Path(filename).with_suffix(".mp3"))
                        break
            return filename

    return await loop.run_in_executor(None, _download)


async def download_video(url: str, user_id: int) -> str:
    output_template = str(DOWNLOAD_DIR / f"{user_id}_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "best[height<=720]/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios"],
            }
        },
    }
    cf = get_cookie_file(url)
    if cf:
        ydl_opts["cookiefile"] = cf
    return await run_ytdlp(ydl_opts, url)


async def download_audio(url: str, user_id: int) -> str:
    output_template = str(DOWNLOAD_DIR / f"{user_id}_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios"],
            }
        },
    }
    cf = get_cookie_file(url)
    if cf:
        ydl_opts["cookiefile"] = cf
    return await run_ytdlp(ydl_opts, url)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "👋 Salom! Men Instagram va YouTube'dan video va audio yuklab beruvchi botman.\n\n"
        "📥 *Foydalanish:*\n"
        "1️⃣ Menga Instagram yoki YouTube havolasini yuboring\n"
        "2️⃣ Video yoki Audio (MP3) variantini tanlang\n"
        "3️⃣ Faylni qabul qiling ✅\n\n"
        "⚠️ *Eslatma:* Fayl hajmi *50 MB* gacha bo'lishi kerak."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if not is_valid_url(url):
        await update.message.reply_text("❌ Iltimos, Instagram yoki YouTube havolasini yuboring.")
        return

    user_urls[user_id] = url
    keyboard = [
        [
            InlineKeyboardButton("🎬 Video", callback_data="video"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio"),
        ],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "📥 Yuklab olish formatini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "cancel":
        user_urls.pop(user_id, None)
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    if user_id not in user_urls:
        await query.edit_message_text("❌ Havola topilmadi. Yangi havola yuboring.")
        return

    url = user_urls[user_id]
    status_msg = await query.edit_message_text("⏳ Yuklab olinmoqda... Iltimos kuting.")

    file_path = None
    try:
        if choice == "video":
            file_path = await download_video(url, user_id)
        elif choice == "audio":
            file_path = await download_audio(url, user_id)
        else:
            return

        if not file_path or not os.path.exists(file_path):
            candidates = list(DOWNLOAD_DIR.glob(f"{user_id}_*"))
            if candidates:
                file_path = str(candidates[0])
            else:
                raise FileNotFoundError("Yuklab olingan fayl topilmadi.")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            await status_msg.edit_text(
                f"❌ Fayl hajmi {file_size / 1024 / 1024:.1f} MB — limit 50 MB."
            )
            return

        await status_msg.edit_text("📤 Yuborilmoqda...")
        with open(file_path, "rb") as f:
            if choice == "video":
                await context.bot.send_video(
                    chat_id=query.message.chat_id, video=f,
                    caption="✅ Mana sizning videongiz!",
                    supports_streaming=True,
                    read_timeout=120, write_timeout=120,
                )
            else:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id, audio=f,
                    caption="✅ Mana sizning audioyingiz!",
                    read_timeout=120, write_timeout=120,
                )
        await status_msg.delete()

    except Exception as e:
        logger.exception("Yuklab olishda xatolik:")
        error_text = str(e)[:300]
        try:
            await status_msg.edit_text(
                f"❌ Xatolik yuz berdi:\n`{error_text}`\n\nQayta urinib ko'ring.",
                parse_mode="Markdown",
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ Xatolik: {error_text}",
            )
    finally:
        clean_user_files(user_id)
        user_urls.pop(user_id, None)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN environment variable o'rnatilmagan!")
    setup_cookies()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    logger.info("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
