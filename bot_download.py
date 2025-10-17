import re
import tempfile
import os
from yt_dlp import YoutubeDL
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Токен читаем из переменной окружения (заполнишь на Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Add it in Render -> Environment.")

# yt-dlp: берём лучший готовый файл (обычно mp4); без плейлистов
YDL_OPTS = {"format": "best[ext=mp4]/best", "noplaylist": True}

# Находим ссылки в тексте, фильтруем нужные домены
URL_REGEX = re.compile(r"https?://[^\s]+")
ALLOWED_HOSTS = ("tiktok.com", "instagram.com", "youtu.be", "youtube.com", "x.com", "twitter.com")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text

    urls = []
    for u in re.findall(URL_REGEX, text):
        low = u.lower()
        if any(h in low for h in ALLOWED_HOSTS):
            urls.append(u)

    if not urls:
        return

    await update.message.reply_text("⏳ Скачиваю видео...")

    for url in urls[:3]:  # защита от спама — максимум 3 ссылки за раз
        with tempfile.TemporaryDirectory() as td:
            try:
                # Скачиваем во временную папку
                ydl_opts = {**YDL_OPTS, "outtmpl": f"{td}/%(id)s.%(ext)s"}
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filepath = ydl.prepare_filename(info)

                # Отправляем как видео; если не выйдет — как документ
                try:
                    with open(filepath, "rb") as f:
                        await update.message.reply_video(video=InputFile(f), caption=f"🎬 Из: {url}")
                except Exception:
                    with open(filepath, "rb") as f:
                        await update.message.reply_document(document=InputFile(f), caption=f"📄 Из: {url}")

            except Exception as e:
                await update.message.reply_text(f"⚠️ Не удалось обработать: {url}\n{e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle))
    print("✅ Бот запущен (polling).")
    app.run_polling()
