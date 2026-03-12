from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

MAIN_MENU_KEYBOARD = [
    [
        InlineKeyboardButton("📥 YouTube",     callback_data="menu_youtube"),
        InlineKeyboardButton("📸 Instagram",   callback_data="menu_instagram"),
    ],
    [
        InlineKeyboardButton("⚡ Сжать видео", callback_data="menu_compress"),
        InlineKeyboardButton("ℹ️ Помощь",     callback_data="menu_help"),
    ],
]

WELCOME_TEXT = """
🎬 *Добро пожаловать в CreatorBot!*

Твой помощник для работы с видео-контентом.
Скачивай и сжимай видео в пару кликов! ⚡

━━━━━━━━━━━━━━━━━━━━━
📥 *Что умею прямо сейчас:*
• Скачать видео с YouTube (до 1080p) 🎬
• Скачать видео / Reel с Instagram 📸
• Извлечь аудио из YouTube в MP3 🎵
• Сжать видео без потери качества ⚡
━━━━━━━━━━━━━━━━━━━━━

👇 Выбери нужное действие:
"""

HELP_TEXT = """
ℹ️ *Помощь — CreatorBot*

📥 *YouTube:*
• Отправь ссылку вида `https://youtu.be/...`
• Выбери качество: 1080p / 720p / 480p / MP3
• Лимит: до 50 МБ (ограничение Telegram)

📸 *Instagram:*
• Отправь ссылку на Reel или публичный пост
• ⚠️ Только публичные аккаунты!

⚡ *Сжатие видео:*
• До 50 МБ — пришли файл напрямую
• Больше 50 МБ — через Google Drive ссылку

❌ *Команды:*
• /start — главное меню
• /cancel — отменить текущую загрузку

❓ Если что-то не работает — попробуй другую ссылку.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start — отправляет главное меню."""
    keyboard = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку."""
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="menu_back")]
    ])
    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат в главное меню."""
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
    # Всегда отправляем новое сообщение (работает для любых типов сообщений)
    await query.message.reply_text(
        WELCOME_TEXT,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def menu_soon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Заглушка для скоро доступных функций."""
    query = update.callback_query
    await query.answer("🔜 Эта функция скоро будет доступна!", show_alert=True)


def get_start_handlers():
    """Возвращает список обработчиков для главного меню."""
    return [
        CommandHandler("start", start),
        CallbackQueryHandler(menu_help, pattern="^menu_help$"),
        CallbackQueryHandler(menu_back, pattern="^menu_back$"),
    ]
