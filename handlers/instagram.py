import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
import logging

from utils.helpers import is_valid_url, is_instagram_url, is_youtube_url, get_file_size_mb, cleanup
from utils.downloader import download_instagram, download_youtube
from config import MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

# Состояние разговора
WAITING_IG_URL = 0

BACK_BUTTON = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📸 Скачать ещё с Instagram", callback_data="menu_instagram"),
        InlineKeyboardButton("🏠 В меню", callback_data="menu_back"),
    ]
])


async def ig_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашиваем ссылку Instagram."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📸 *Скачать с Instagram*\n\n"
            "Отправь мне ссылку на Reel или публичный пост Instagram.\n\n"
            "_🔓 Только публичные аккаунты_\n"
            "_Пример: https://www.instagram.com/reel/..._",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "📸 *Скачать с Instagram*\n\n"
            "Отправь мне ссылку на Reel или публичный пост Instagram.\n\n"
            "_🔓 Только публичные аккаунты_\n"
            "_Пример: https://www.instagram.com/reel/..._",
            parse_mode="Markdown",
        )
    return WAITING_IG_URL


async def ig_receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем URL, скачиваем и отправляем видео."""
    url = update.message.text.strip()

    if not is_valid_url(url) or not is_instagram_url(url):
        await update.message.reply_text(
            "⚠️ Это не Instagram-ссылка.\n\n"
            "Отправь ссылку вида:\n"
            "• `https://www.instagram.com/reel/...`\n"
            "• `https://www.instagram.com/p/...`\n\n"
            "Для других платформ отправь /start и выбери нужное действие.",
            parse_mode="Markdown",
        )
        return WAITING_IG_URL

    msg = await update.message.reply_text(
        "⏳ *Скачиваю видео с Instagram...*\n\nЭто может занять несколько секунд ⚡",
        parse_mode="Markdown",
    )

    file_path = None
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(
            None, download_instagram, url
        )

        file_size = get_file_size_mb(file_path)
        if file_size > MAX_FILE_SIZE_MB:
            await msg.edit_text(
                f"⚠️ Видео слишком большое ({file_size:.1f} МБ).\n"
                f"Telegram позволяет отправлять файлы до {MAX_FILE_SIZE_MB} МБ."
            )
            cleanup(file_path)
            return ConversationHandler.END

        await msg.delete()

        with open(file_path, "rb") as f:
            await update.message.reply_video(
                video=f,
                caption="📸 Готово! Видео с Instagram\n\n_Powered by CreatorBot 🤖_",
                parse_mode="Markdown",
                supports_streaming=True,
                reply_markup=BACK_BUTTON,
            )

    except Exception as e:
        logger.error(f"Ошибка Instagram скачивания: {e}", exc_info=True)
        err = str(e).lower()

        if "private" in err or "login required" in err or "authentication" in err:
            error_msg = (
                "🔒 *Аккаунт приватный*\n\n"
                "Этот аккаунт закрыт — скачивание с приватных аккаунтов невозможно.\n"
                "Используй только публичные ссылки."
            )
        elif "not found" in err or "404" in err:
            error_msg = "🚫 Пост не найден. Возможно, он был удалён или ссылка неверна."
        elif "unavailable" in err:
            error_msg = "🚫 Это видео недоступно для скачивания."
        else:
            error_msg = f"❌ Ошибка при скачивании:\n`{str(e)[:200]}`"

        try:
            await msg.edit_text(error_msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(error_msg, parse_mode="Markdown")
    finally:
        cleanup(file_path)

    return ConversationHandler.END


async def ig_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена через /cancel."""
    await update.message.reply_text("❌ Загрузка Instagram отменена.")
    return ConversationHandler.END


def get_instagram_handler() -> ConversationHandler:
    """Возвращает готовый ConversationHandler для Instagram-загрузки."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ig_start, pattern="^menu_instagram$"),
            CommandHandler("instagram", ig_start),
        ],
        states={
            WAITING_IG_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ig_receive_url),
            ],
        },
        fallbacks=[CommandHandler("cancel", ig_cancel)],
        allow_reentry=True,
    )
