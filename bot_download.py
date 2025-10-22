import os
import re
import tempfile
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Токен из переменной окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN не установлен. Добавь его в Railway → Variables.")

# Настройки yt-dlp
BASE_OPTS = {
    "format": "best[ext=mp4]/best",
    "noplaylist": True,
    "quiet": True,
}

# Домены, которые бот обрабатывает
ALLOWED_HOSTS = (
    "tiktok.com",
    "instagram.com",
    "youtu.be",
    "youtube.com",
    "x.com",
    "twitter.com",
)

# Cookies для сервисов
COOKIES = {
    "instagram.com": "cookies_instagram.txt",
    "youtube.com": "cookies.txt",
    "youtu.be": "cookies.txt",
}

URL_REGEX = re.compile(r"https?://[^\s]+")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    urls = [u for u in re.findall(URL_REGEX, text) if any(h in u.lower() for h in ALLOWED_HOSTS)]
    if not urls:
        return

    for url in urls[:3]:  # максимум 3 ссылки
        with tempfile.TemporaryDirectory() as td:
            try:
                # Базовые опции
                ydl_opts = {**BASE_OPTS, "outtmpl": f"{td}/%(title)s.%(ext)s"}

                # Выбор cookies по домену
                cookie_file = None
                for domain, path in COOKIES.items():
                    if domain in url:
                        cookie_file = path
                        break

                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file

                # Обход Instagram API (важно!)
                "extractor_args"] = {"instagram": ["proxies=https://1.1.1.1:8080", "highlights=True"]}

                # --- Скачивание ---
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filepath = ydl.prepare_filename(info)

                # --- Если это альбом (несколько фото/видео) ---
                if info.get("entries"):
                    media_files = []
                    for entry in info["entries"]:
                        subfile = os.path.join(td, f"{entry.get('title','media')}.{entry.get('ext','jpg')}")
                        if os.path.exists(subfile):
                            media_files.append(subfile)
                    if not media_files:
                        files = os.listdir(td)
                        media_files = [os.path.join(td, f) for f in files]

                    if media_files:
                        for file in media_files[:5]:  # максимум 5 медиа
                            with open(file, "rb") as f:
                                if file.lower().endswith(".mp4"):
                                    await update.message.reply_video(
                                        video=InputFile(f),
                                        caption=f"🎬 Из: {url}\nКак вам такое, Мафтуна? 😏"
                                    )
                                else:
                                    await update.message.reply_photo(
                                        photo=InputFile(f),
                                        caption=f"📷 Из: {url}\nКак вам такое, Мафтуна? 😏"
                                    )
                        continue

                # --- Обычный одиночный пост ---
                if not os.path.exists(filepath):
                    files = os.listdir(td)
                    if files:
                        filepath = os.path.join(td, files[0])

                if not os.path.exists(filepath):
                    await update.message.reply_text(
                        f"⚠️ Instagram не дал файл по ссылке:\n{url}\n"
                        "Пост может быть временно недоступен."
                    )
                    continue

                with open(filepath, "rb") as f:
                    if filepath.lower().endswith(".mp4"):
                        await update.message.reply_video(
                            video=InputFile(f),
                            caption=f"🎬 Из: {url}\nКак вам такое, Мафтуна? 😏"
                        )
                    else:
                        await update.message.reply_photo(
                            photo=InputFile(f),
                            caption=f"📷 Из: {url}\nКак вам такое, Мафтуна? 😏"
                        )

            except Exception as e:
                await update.message.reply_text(f"⚠️ Ошибка при обработке {url}:\n{e}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle))
    print("✅ Бот запущен и ждёт ссылки...")
    app.run_polling()
    
