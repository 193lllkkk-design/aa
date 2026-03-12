import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
import logging

from utils.helpers import is_valid_url, is_youtube_url, get_file_size_mb, cleanup
from utils.downloader import download_youtube
from config import MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

# Состояния разговора
WAITING_YT_URL, WAITING_YT_QUALITY = range(2)

# Callback data для кнопок качества
QUALITY_BUTTONS = [
    [
        InlineKeyboardButton("🎬 1080p", callback_data="yt_1080"),
        InlineKeyboardButton("📺 720p",  callback_data="yt_720"),
    ],
    [
        InlineKeyboardButton("📱 480p",  callback_data="yt_480"),
        InlineKeyboardButton("🔉 360p",  callback_data="yt_360"),
    ],
    [
        InlineKeyboardButton("🎵 Только аудио (MP3)", callback_data="yt_audio"),
    ],
    [
        InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
    ],
]

BACK_BUTTON = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📥 Скачать ещё с YouTube", callback_data="menu_youtube"),
        InlineKeyboardButton("🏠 В меню", callback_data="menu_back"),
    ]
])


async def yt_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Точка входа — запрашиваем ссылку YouTube."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📥 *Скачать с YouTube*\n\n"
            "Отправь мне ссылку на видео с YouTube.\n\n"
            "_Пример: https://youtu.be/dQw4w9WgXcQ_",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "📥 *Скачать с YouTube*\n\n"
            "Отправь мне ссылку на видео с YouTube.\n\n"
            "_Пример: https://youtu.be/dQw4w9WgXcQ_",
            parse_mode="Markdown",
        )
    return WAITING_YT_URL


async def yt_receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем URL и показываем выбор качества."""
    url = update.message.text.strip()

    if not is_valid_url(url) or not is_youtube_url(url):
        await update.message.reply_text(
            "⚠️ Это не YouTube-ссылка.\n\n"
            "Отправь ссылку вида:\n"
            "• `https://youtu.be/...`\n"
            "• `https://youtube.com/watch?v=...`\n\n"
            "Для других платформ отправь /start и выбери нужное действие.",
            parse_mode="Markdown",
        )
        return WAITING_YT_URL

    context.user_data["yt_url"] = url
    keyboard = InlineKeyboardMarkup(QUALITY_BUTTONS)
    await update.message.reply_text(
        "⚙️ *Выбери качество видео:*",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return WAITING_YT_QUALITY



async def yt_receive_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем качество, скачиваем и отправляем файл."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Загрузка отменена.")
        return ConversationHandler.END

    quality = query.data.replace("yt_", "")  # '1080', '720', 'audio' и т.д.
    url = context.user_data.get("yt_url")

    quality_labels = {
        "1080": "1080p",
        "720":  "720p",
        "480":  "480p",
        "360":  "360p",
        "audio": "MP3 аудио",
    }

    await query.edit_message_text(
        f"⏳ Скачиваю в качестве *{quality_labels.get(quality, quality)}*...\n\n"
        "Это может занять несколько секунд ⚡",
        parse_mode="Markdown",
    )

    file_path = None
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(
            None, download_youtube, url, quality
        )

        file_size = get_file_size_mb(file_path)
        if file_size > MAX_FILE_SIZE_MB:
            await query.message.reply_text(
                f"⚠️ Файл слишком большой ({file_size:.1f} МБ).\n"
                f"Telegram позволяет отправлять файлы до {MAX_FILE_SIZE_MB} МБ.\n\n"
                "Попробуй выбрать более низкое качество."
            )
            cleanup(file_path)
            return ConversationHandler.END

        with open(file_path, "rb") as f:
            if quality == "audio":
                await query.message.reply_audio(
                    audio=f,
                    caption="🎵 Готово! Аудио с YouTube\n\n_Powered by CreatorBot 🤖_",
                    parse_mode="Markdown",
                    reply_markup=BACK_BUTTON,
                )
            else:
                await query.message.reply_video(
                    video=f,
                    caption=f"🎬 Готово! Качество: {quality_labels.get(quality)}\n\n_Powered by CreatorBot 🤖_",
                    parse_mode="Markdown",
                    supports_streaming=True,
                    reply_markup=BACK_BUTTON,
                )

    except Exception as e:
        logger.error(f"Ошибка YouTube скачивания: {e}", exc_info=True)
        err = str(e).lower()
        if "private" in err or "login" in err:
            msg = "🔒 Это видео приватное или требует авторизации — скачать невозможно."
        elif "unavailable" in err or "not available" in err:
            msg = "🚫 Видео недоступно (удалено или ограничено по региону)."
        elif "copyright" in err:
            msg = "©️ Видео заблокировано из-за авторских прав."
        else:
            msg = f"❌ Ошибка при скачивании:\n`{str(e)[:200]}`"

        await query.message.reply_text(msg, parse_mode="Markdown")
    finally:
        cleanup(file_path)

    return ConversationHandler.END


async def yt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена через /cancel."""
    await update.message.reply_text("❌ Загрузка YouTube отменена.")
    return ConversationHandler.END


def get_youtube_handler() -> ConversationHandler:
    """Возвращает готовый ConversationHandler для YouTube-загрузки."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(yt_start, pattern="^menu_youtube$"),
            CommandHandler("youtube", yt_start),
        ],
        states={
            WAITING_YT_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, yt_receive_url),
            ],
            WAITING_YT_QUALITY: [
                CallbackQueryHandler(yt_receive_quality, pattern="^yt_"),
                CallbackQueryHandler(yt_receive_quality, pattern="^cancel$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", yt_cancel)],
        allow_reentry=True,
    )
