"""
CreatorBot — Telegram Bot для видео-профессионалов
"""
import logging
import asyncio
from telegram.ext import Application

from config import BOT_TOKEN
from handlers.start import get_start_handlers
from handlers.youtube import get_youtube_handler
from handlers.instagram import get_instagram_handler
from handlers.compress import get_compress_handler

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота."""
    logger.info("🚀 Запуск CreatorBot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # 1. Регистрируем ConversationHandler-ы ПЕРВЫМИ (они имеют приоритет)
    app.add_handler(get_youtube_handler())
    app.add_handler(get_instagram_handler())
    app.add_handler(get_compress_handler())

    # 2. Регистрируем остальные обработчики (меню, /start)
    for handler in get_start_handlers():
        app.add_handler(handler)

    logger.info("✅ Все обработчики зарегистрированы.")
    logger.info("🤖 Бот запущен! Нажми Ctrl+C для остановки.")

    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
