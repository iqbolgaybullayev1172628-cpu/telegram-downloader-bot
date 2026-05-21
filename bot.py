"""
Telegram Bot — Instagram va YouTube'dan video/audio yuklab oluvchi bot
"""
import os
import logging
import asyncio
from pathlib import Path

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- Sozlamalar ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # @BotFather'dan olingan token
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Telegram bot uchun maksimal fayl hajmi: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Foydalanuvchining havolasini vaqtinchalik saqlash
user_urls: dict[int, str] = {}


# ---------------- Yordamchi funksiyalar ----------------
def is_valid_url(url: str) -> bool:
    """URL Instagram yoki YouTube'ga tegishli ekanligini tekshirish."""
    url = url.lower()
    return any(
        domain in url
        for domain in ("instagram.com", "youtube.com", "youtu.be", "youtube-nocookie.com")
    )


def clean_user_files(user_id: int) -> None:
    """Foydalanuvchining vaqtincha fayllarini tozalash."""
    for f in DOWNLOAD_DIR.glob(f"{user_id}_*"):
        try:
            f.unlink()
        except OSError:
            pass


async def run_ytdlp(ydl_opts: dict, url: str) -> str:
    """yt-dlp ni alohida threadda ishga tushirish (asinxron blokirovkani oldini olish)."""
    loop = asyncio.get_event_loop()

    def _download() -> str:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Agar audio postprocessor ishlatilsa, kengaytma .mp3 ga o'zgaradi
            if ydl_opts.get("postprocessors"):
                for pp in ydl_opts["postprocessors"]:
                    if pp.get("key") == "FFmpegExtractAudio":
                        filename = str(Path(filename).with_suffix(".mp3"))
                        break
            return filename

    return await loop.run_in_executor(None, _download)


async def download_video(url: str, user_id: int) -> str:
    """Video yuklab olish (50MB chegarasiga moslashtirilgan)."""
    output_template = str(DOWNLOAD_DIR / f"{user_id}_%(id)s.%(ext)s")
    ydl_opts = {
        # 50MB dan kichik eng yaxshi sifat, agar topilmasa 720p yoki past
        "format": "best[filesize<50M]/best[height<=720]/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    return await run_ytdlp(ydl_opts, url)


async def download_audio(url: str, user_id: int) -> str:
    """Audio (MP3) yuklab olish."""
    output_template = str(DOWNLOAD_DIR / f"{user_id}_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    return await run_ytdlp(ydl_opts, url)


# ---------------- Handler funksiyalar ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "👋 Salom! Men Instagram va YouTube'dan video va audio yuklab beruvchi botman.\n\n"
        "📥 *Foydalanish:*\n"
        "1️⃣ Menga Instagram yoki YouTube havolasini yuboring\n"
        "2️⃣ Video yoki Audio (MP3) variantini tanlang\n"
        "3️⃣ Faylni qabul qiling ✅\n\n"
        "⚠️ *Eslatma:* Telegram bot orqali yuborilishi mumkin bo'lgan fayl hajmi *50 MB* gacha.\n\n"
        "Yordam uchun: /help"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ Iltimos, Instagram yoki YouTube havolasini yuboring.\n"
            "Masalan: https://youtu.be/... yoki https://instagram.com/..."
        )
        return

    user_urls[user_id] = url

    keyboard = [
        [
            InlineKeyboardButton("🎬 Video", callback_data="video"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio"),
        ],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📥 Yuklab olish formatini tanlang:",
        reply_markup=reply_markup,
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

        # Fayl mavjudligini va hajmini tekshirish
        if not file_path or not os.path.exists(file_path):
            # Ba'zan kengaytma o'zgaradi — papkadan qidiramiz
            candidates = list(DOWNLOAD_DIR.glob(f"{user_id}_*"))
            if candidates:
                file_path = str(candidates[0])
            else:
                raise FileNotFoundError("Yuklab olingan fayl topilmadi.")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            await status_msg.edit_text(
                f"❌ Fayl hajmi {file_size / 1024 / 1024:.1f} MB — "
                f"Telegram bot orqali yuborib bo'lmaydi (limit 50 MB)."
            )
            return

        await status_msg.edit_text("📤 Yuborilmoqda...")

        with open(file_path, "rb") as f:
            if choice == "video":
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    caption="✅ Mana sizning videongiz!",
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                )
            else:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    caption="✅ Mana sizning audioyingiz!",
                    read_timeout=120,
                    write_timeout=120,
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


# ---------------- Asosiy ----------------
def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "❌ BOT_TOKEN environment variable o'rnatilmagan!\n"
            "Iltimos, .env faylida yoki tizim o'zgaruvchilarida BOT_TOKEN ni o'rnating."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    logger.info("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
