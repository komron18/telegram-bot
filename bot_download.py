import re
import tempfile
import os
from yt_dlp import YoutubeDL
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# токен берётся из переменной окружения (Render -> Environment)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# общие настройки для yt-dlp
BASE_OPTS = {
    "format": "best[ext=mp4]/best",
    "noplaylist": True,
    "quiet": True,
}

# распознавание ссылок
URL_REGEX = re.compile(r"https?://[^\s]+")

# домены и соответствующие cookie-файлы
COOKIES = {
    "youtube.com": "cookies.txt",
    "youtu.be": "cookies.txt",
    "instagram.com": "cookies (1).txt",
}

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    urls = re.findall(URL_REGEX, text)

    if not urls:
        return

    await update.message.reply_text("⏳ Скачиваю видео...")

    for url in urls:
        with tempfile.TemporaryDirectory() as td:
            try:
                # определяем cookie-файл по домену
                cookie_file = None
                for domain, path in COOKIES.items():
                    if domain in url:
                        cookie_file = path
                        break

                ydl_opts = {
                    **BASE_OPTS,
                    "outtmpl": f"{td}/%(title)s.%(ext)s",
                }

                # если есть cookie для домена — добавляем
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)

                # пробуем отправить как видео
                with open(file_path, "rb") as f:
                    await update.message.reply_video(video=InputFile(f), caption=f"🎬 Из: {url}")

            except Exception as e:
                await update.message.reply_text(f"⚠️ Ошибка при обработке {url}:\n{e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle))
    print("✅ Бот запущен и ждёт ссылки...")
    app.run_polling()
