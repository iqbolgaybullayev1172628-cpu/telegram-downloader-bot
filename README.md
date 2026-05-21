# 📥 Telegram Video Yuklovchi Bot

Instagram va YouTube'dan video hamda audio (MP3) yuklab beruvchi Telegram bot.

## ✨ Imkoniyatlar

- 🎬 YouTube va Instagram'dan **video** yuklab olish
- 🎵 Video'dan **MP3 audio** ajratib olish (192 kbps)
- 🔘 Inline tugmalar orqali qulay tanlov
- 🇺🇿 O'zbek tilida interfeys
- ⚡ Asinxron — bir necha foydalanuvchini bir vaqtda xizmat qila oladi

## 📋 Talablar

- **Python 3.10+**
- **ffmpeg** (audio konvertatsiya uchun majburiy)
- Telegram bot tokeni (@BotFather'dan)

## 🚀 O'rnatish

### 1. Telegram bot tokenini olish

1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Botga nom va username bering
4. Sizga beriladigan **tokenni** saqlab qo'ying (masalan: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

### 2. Loyihani yuklab olish

```bash
# Loyiha papkasiga o'ting
cd telegram_downloader_bot
```

### 3. ffmpeg o'rnatish

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
[ffmpeg.org](https://ffmpeg.org/download.html) saytidan yuklab oling va PATH ga qo'shing.

### 4. Python kutubxonalarini o'rnatish

```bash
# Virtual environment yaratish (tavsiya etiladi)
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

### 5. Tokenni sozlash

`.env.example` faylini `.env` deb ko'chiring va tokeningizni kiriting:

```bash
cp .env.example .env
# .env faylini ochib BOT_TOKEN=... ga tokeningizni yozing
```

Yoki to'g'ridan-to'g'ri eksport qiling:

**Linux/macOS:**
```bash
export BOT_TOKEN="bu_yerga_tokeningiz"
```

**Windows (PowerShell):**
```powershell
$env:BOT_TOKEN="bu_yerga_tokeningiz"
```

### 6. Botni ishga tushirish

```bash
python bot.py
```

Agar `.env` faylidan token o'qishni xohlasangiz, `python-dotenv` o'rnating:

```bash
pip install python-dotenv
```

Va `bot.py` faylining boshiga qo'shing:

```python
from dotenv import load_dotenv
load_dotenv()
```

## 🎯 Foydalanish

1. Botga `/start` yuboring
2. Instagram yoki YouTube havolasini yuboring, masalan:
   - `https://youtu.be/dQw4w9WgXcQ`
   - `https://www.instagram.com/reel/...`
3. **🎬 Video** yoki **🎵 Audio (MP3)** tugmasini tanlang
4. Fayl tayyor bo'lganda yuboriladi ✅

## ⚠️ Muhim eslatmalar

- **50 MB limit**: Telegram oddiy botlar uchun fayl hajmi chegarasi 50 MB. Undan kattaroq fayllarni yuborish uchun [Local Bot API Server](https://github.com/tdlib/telegram-bot-api) ni mahalliy ishga tushirish kerak (u 2 GB gacha qo'llab-quvvatlaydi).
- **Instagram private postlar**: Faqat ochiq (public) postlardan yuklab olish mumkin. Yopiq akkauntlar uchun cookie kerak bo'ladi.
- **YouTube Shorts**: To'liq qo'llab-quvvatlanadi.
- **Pleylistlar**: Faqat birinchi videoni yuklaydi (`noplaylist: True`).

## 🐳 Docker bilan ishga tushirish (ixtiyoriy)

Dockerfile yaratib oling:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
```

So'ng:

```bash
docker build -t telegram-downloader-bot .
docker run -e BOT_TOKEN="tokeningiz" telegram-downloader-bot
```

## 🛠 Muammolarni hal qilish

| Muammo | Yechim |
|--------|--------|
| `ffmpeg not found` | ffmpeg o'rnating (yuqoriga qarang) |
| `BOT_TOKEN not set` | `.env` faylida yoki `export BOT_TOKEN=...` orqali tokeningizni sozlang |
| `File too large` | Fayl 50 MB dan katta — past sifatli formatni tanlang yoki Local Bot API ishlating |
| Instagram private | Yopiq postlarni yuklab bo'lmaydi |
| YouTube xato beradi | `pip install -U yt-dlp` orqali yt-dlp ni yangilang |

## 📜 Litsenziya

Erkin foydalanish uchun. Faqat o'zingiz huquqiga ega bo'lgan yoki ruxsat berilgan kontentni yuklab oling.
