import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Создайте файл .env и укажите BOT_TOKEN=ваш_токен")

# Временная папка для загрузок
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Максимальный размер файла для отправки в Telegram (50 MB)
MAX_FILE_SIZE_MB = 50
