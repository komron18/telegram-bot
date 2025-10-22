import os
import re
import tempfile
from io import BytesIO
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from PIL import Image

# === Токен ===
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Add it in Railway -> Variables.")

# === Настройки yt-dlp ===
BASE_OPTS = {"format": "best[ext=mp4]/best", "noplaylist": True, "quiet": True}
COOKIES = {
    "youtube.com": "cookies.txt",
    "youtu.be": "cookies.txt",
    "instagram.com": "cookies (1).txt",
}
URL_REGEX = re.compile(r"https?://[^\s]+")
ALLOWED_HOSTS = ("tiktok.com", "instagram.com", "youtu.be", "youtube.com", "x.com", "twitter.com")

# === Функция для создания коллажа ===
def create_collage(images):
    imgs = [Image.open(p).convert("RGB") for p in images]
    count = len(imgs)
    if count == 1:
        return imgs[0]

    grid_size = (2, (count + 1) // 2)
    width, height = imgs[0].size
    collage = Image.new("RGB", (width * grid_size[0], height * grid_size[1]), color=(255, 255, 255))

    for idx, img in enumerate(imgs):
        x = (idx % 2) * width
        y = (idx // 2) * height
        collage.paste(img, (x, y))

    return collage

# === Основная функция обработки ссылок ===
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    urls = [u for u in re.findall(URL_REGEX, text) if any(h in u for h in ALLOWED_HOSTS)]
    if not urls:
        return

    for url in urls[:3]:
        with tempfile.TemporaryDirectory() as td:
            try:
                # Настройка yt-dlp
                ydl_opts = {**BASE_OPTS, "outtmpl": f"{td}/%(title)s.%(ext)s"}
                cookie_file = None
                for domain, path in COOKIES.items():
                    if domain in url and os.path.exists(path):
                        cookie_file = path
                        break
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file

                # Скачивание
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filepath = ydl.prepare_filename(info)

                    # Если файл не найден — ищем вручную
                    if not os.path.exists(filepath):
                        files = os.listdir(td)
                        if files:
                            filepath = os.path.join(td, files[0])

                # Отправка медиа
                caption = f"🎬 Из: {url}\nКак вам такое, Мафтуна? 😏"
                with open(filepath, "rb") as f:
                    if filepath.lower().endswith(".mp4"):
                        await update.message.reply_video(video=InputFile(f), caption=caption)
                    else:
                        await update.message.reply_photo(photo=InputFile(f), caption=caption)

            except Exception as e:
                await update.message.reply_text(f"⚠️ Ошибка при обработке {url}:\n{e}")

# === Обработка фото, присланных вручную ===
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = update.message.photo
    temp_files = []
    for i, photo in enumerate(photos):
        file = await context.bot.get_file(photo.file_id)
        temp_path = f"/tmp/photo_{i}.jpg"
        await file.download_to_drive(temp_path)
        temp_files.append(temp_path)

    if len(temp_files) == 1:
        with open(temp_files[0], "rb") as f:
            await update.message.reply_photo(photo=InputFile(f), caption="📷 Как вам такое, Мафтуна? 😏")
    else:
        collage = create_collage(temp_files)
        bio = BytesIO()
        collage.save(bio, format="JPEG")
        bio.seek(0)
        await update.message.reply_photo(photo=InputFile(bio, filename="collage.jpg"),
                                         caption="🖼 Коллаж готов! Как вам такое, Мафтуна? 😏")

# === Запуск ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_links))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    print("✅ Бот запущен и ждёт ссылки и фото...")
    app.run_polling()
