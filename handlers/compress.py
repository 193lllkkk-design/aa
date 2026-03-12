import asyncio
import os
import re
import subprocess
import logging
import glob
import shutil
import uuid

import requests
import gdown

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from utils.helpers import get_file_size_mb, cleanup, is_valid_url
from config import DOWNLOAD_DIR, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

# Состояния разговора
WAITING_VIDEO = 0  # Ждём файл или GDrive ссылку

BACK_BUTTON = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⚡ Сжать ещё", callback_data="menu_compress"),
        InlineKeyboardButton("🏠 В меню",    callback_data="menu_back"),
    ]
])

# ─────────────────────────────────────────────
# ffmpeg discovery
# ─────────────────────────────────────────────

def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    user = os.path.expanduser("~")
    search_roots = [
        os.path.join(user, "AppData", "Local", "Microsoft", "WinGet", "Packages"),
        os.path.join(user, "AppData", "Local", "Microsoft", "WinGet", "Links"),
        r"C:\Program Files\ffmpeg",
        r"C:\Program Files (x86)\ffmpeg",
        r"C:\ffmpeg\bin",
        r"C:\ffmpeg",
        r"C:\ProgramData\ffmpeg\bin",
    ]
    for root in search_roots:
        if not os.path.exists(root):
            continue
        matches = glob.glob(os.path.join(root, "**", "ffmpeg.exe"), recursive=True)
        if matches:
            return matches[0]
    return None

def is_ffmpeg_available() -> bool:
    return find_ffmpeg() is not None


# ─────────────────────────────────────────────
# Core compression
# ─────────────────────────────────────────────

def compress_video(input_path: str, output_path: str) -> dict:
    """Сжимает видео через ffmpeg. Возвращает статистику."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg не найден")

    cmd = [
        ffmpeg, "-i", input_path,
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg ошибка:\n{result.stderr[-400:]}")

    orig_mb = get_file_size_mb(input_path)
    comp_mb = get_file_size_mb(output_path)
    ratio   = (1 - comp_mb / orig_mb) * 100 if orig_mb > 0 else 0
    return {"orig_mb": orig_mb, "comp_mb": comp_mb, "ratio": ratio}


# ─────────────────────────────────────────────
# Google Drive download
# ─────────────────────────────────────────────

def is_gdrive_url(url: str) -> bool:
    return "drive.google.com" in url or "docs.google.com" in url

def extract_gdrive_id(url: str) -> str | None:
    """Извлекает file ID из любого формата GDrive ссылки."""
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def download_from_gdrive(url: str, output_path: str) -> None:
    """Скачивает файл с Google Drive в output_path."""
    file_id = extract_gdrive_id(url)
    if file_id:
        gdown.download(id=file_id, output=output_path, quiet=False, fuzzy=True)
    else:
        gdown.download(url=url, output=output_path, quiet=False, fuzzy=True)
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Не удалось скачать файл. Убедись, что ссылка публичная.")


# ─────────────────────────────────────────────
# Upload result (if too big for Telegram)
# ─────────────────────────────────────────────

def upload_to_gofile(file_path: str) -> str:
    """Загружает файл на gofile.io (API v2) и возвращает ссылку."""
    # Получаем лучший сервер
    srv_resp = requests.get("https://api.gofile.io/servers", timeout=10).json()
    server = srv_resp["data"]["servers"][0]["name"]
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"https://{server}.gofile.io/contents/uploadfile",
            files={"file": (os.path.basename(file_path), f)},
            timeout=600,
        ).json()
    if resp.get("status") != "ok":
        raise RuntimeError(f"Ошибка загрузки на gofile.io: {resp}")
    return resp["data"]["downloadPage"]


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

async def compress_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Точка входа — объясняем оба режима."""
    query = update.callback_query
    reply = query.message.reply_text if query else update.message.reply_text
    if query:
        await query.answer()

    if not is_ffmpeg_available():
        await reply(
            "⚠️ *ffmpeg не установлен*\n\n"
            "Установи через winget:\n`winget install --id Gyan.FFmpeg`\n"
            "Затем перезапусти бота.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await reply(
        "⚡ *Сжатие видео*\n\n"
        "📦 *До 50 МБ* — просто пришли видео-файл прямо сюда\n"
        "📁 *Свыше 50 МБ* — загрузи на Google Drive, сделай публичным и пришли ссылку\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔗 Как сделать GDrive ссылку публичной:\n"
        "1. Правой кнопкой на файл → _Поделиться_\n"
        "2. Выбрать _«Все у кого есть ссылка»_\n"
        "3. Скопировать ссылку и прислать сюда\n\n"
        "_Введи /cancel для отмены_",
        parse_mode="Markdown",
    )
    return WAITING_VIDEO


async def compress_receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем видео-файл напрямую или GDrive ссылку в виде текста."""
    msg = update.message

    # ── Прямой файл ──
    video = msg.video or msg.document
    if not video:
        await msg.reply_text(
            "⚠️ Пришли видео-файл (MP4, MOV, AVI, MKV)\n"
            "или ссылку на Google Drive для больших файлов.\n\n"
            "Введи /cancel для отмены."
        )
        return WAITING_VIDEO

    # Проверка расширения для документов
    if msg.document:
        fname = msg.document.file_name or ""
        if not any(fname.lower().endswith(e) for e in [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
            await msg.reply_text(
                "⚠️ Неподдерживаемый формат.\n"
                "Поддерживается: MP4, MOV, AVI, MKV, WEBM\n\n"
                "Введи /cancel для отмены."
            )
            return WAITING_VIDEO

    file_size = (video.file_size or 0) / (1024 * 1024)

    # Слишком большой для прямой загрузки
    if file_size > MAX_FILE_SIZE_MB:
        await msg.reply_text(
            f"⚠️ Файл {file_size:.0f} МБ — слишком большой для прямой загрузки.\n\n"
            "📁 Загрузи его на Google Drive, сделай публичным и пришли ссылку сюда."
        )
        return WAITING_VIDEO

    return await _compress_tg_file(msg, context, video)


async def compress_receive_gdrive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отдельный обработчик для GDrive-ссылок в состоянии WAITING_VIDEO."""
    url = update.message.text.strip()
    if not is_gdrive_url(url):
        await update.message.reply_text(
            "⚠️ Это не Google Drive ссылка.\n\n"
            "Пришли файл напрямую (до 50 МБ) или ссылку вида:\n"
            "`https://drive.google.com/file/d/.../view`",
            parse_mode="Markdown",
        )
        return WAITING_VIDEO
    return await _handle_gdrive(update.message, context, url)


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

async def _compress_tg_file(msg, context, video) -> int:
    """Скачивает файл из Telegram, сжимает и отправляет."""
    status = await msg.reply_text("⏳ *Скачиваю файл...*", parse_mode="Markdown")
    uid = uuid.uuid4().hex[:8]
    inp  = os.path.join(DOWNLOAD_DIR, f"comp_in_{uid}.mp4")
    outp = os.path.join(DOWNLOAD_DIR, f"comp_out_{uid}.mp4")

    try:
        tg_file = await context.bot.get_file(video.file_id)
        await tg_file.download_to_drive(inp)
        await status.edit_text("⚡ *Сжимаю видео...*\n\nПодожди немного!", parse_mode="Markdown")
        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, compress_video, inp, outp)
        await _send_compressed(msg, status, outp, stats)
    except Exception as e:
        logger.error(f"Ошибка сжатия (TG): {e}", exc_info=True)
        await _send_error(status, msg, str(e))
    finally:
        cleanup(inp, outp)

    return ConversationHandler.END


async def _handle_gdrive(msg, context, url: str) -> int:
    """Скачивает с Google Drive, сжимает и возвращает результат."""
    status = await msg.reply_text(
        "⏳ *Скачиваю с Google Drive...*\n\nЭто может занять несколько минут для больших файлов.",
        parse_mode="Markdown",
    )
    uid  = uuid.uuid4().hex[:8]
    inp  = os.path.join(DOWNLOAD_DIR, f"gdrive_in_{uid}.mp4")
    outp = os.path.join(DOWNLOAD_DIR, f"gdrive_out_{uid}.mp4")

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, download_from_gdrive, url, inp)

        if not os.path.exists(inp):
            raise RuntimeError("Файл не скачался. Проверь, что ссылка публичная.")

        inp_size = get_file_size_mb(inp)
        await status.edit_text(
            f"⚡ *Сжимаю видео...*\n\n"
            f"📦 Размер оригинала: {inp_size:.1f} МБ\n"
            f"Подожди — это займёт время!",
            parse_mode="Markdown",
        )

        stats = await loop.run_in_executor(None, compress_video, inp, outp)
        await _send_compressed(msg, status, outp, stats)

    except Exception as e:
        logger.error(f"Ошибка GDrive сжатия: {e}", exc_info=True)
        await _send_error(status, msg, str(e))
    finally:
        # Удаляем ВСЕ временные файлы с диска бота
        cleanup(inp, outp)

    return ConversationHandler.END


async def _send_compressed(msg, status_msg, outp: str, stats: dict) -> None:
    """Отправляет сжатое видео — напрямую или через gofile.io."""
    comp_mb = stats["comp_mb"]
    caption = (
        f"✅ *Готово! Видео сжато*\n\n"
        f"📦 До: {stats['orig_mb']:.1f} МБ\n"
        f"📦 После: {comp_mb:.1f} МБ\n"
        f"📉 Сжатие: {stats['ratio']:.0f}%\n\n"
        f"_Powered by CreatorBot 🤖_"
    )

    if comp_mb <= MAX_FILE_SIZE_MB:
        # Файл влезает в Telegram — отправляем напрямую
        await status_msg.delete()
        with open(outp, "rb") as f:
            await msg.reply_video(
                video=f,
                caption=caption,
                parse_mode="Markdown",
                supports_streaming=True,
                reply_markup=BACK_BUTTON,
            )
    else:
        # Слишком большой — заливаем на gofile.io
        await status_msg.edit_text(
            "📤 *Видео сжато! Загружаю на облако...*",
            parse_mode="Markdown",
        )
        loop = asyncio.get_running_loop()
        download_url = await loop.run_in_executor(None, upload_to_gofile, outp)
        await status_msg.delete()
        await msg.reply_text(
            caption + f"\n\n🔗 [Скачать сжатое видео]({download_url})\n"
            "_Ссылка действительна 10 дней_",
            parse_mode="Markdown",
            reply_markup=BACK_BUTTON,
            disable_web_page_preview=True,
        )


async def _send_error(status_msg, msg, error: str) -> None:
    short_err = error[:250]
    try:
        await status_msg.edit_text(f"❌ Ошибка:\n`{short_err}`", parse_mode="Markdown")
    except Exception:
        await msg.reply_text(f"❌ Ошибка:\n`{short_err}`", parse_mode="Markdown")


async def compress_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Сжатие отменено.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
# Handler registration
# ─────────────────────────────────────────────

def get_compress_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(compress_start, pattern="^menu_compress$"),
            CommandHandler("compress", compress_start),
        ],
        states={
            WAITING_VIDEO: [
                # GDrive ссылка
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    compress_receive_gdrive_url,
                ),
                # Прямой файл
                MessageHandler(
                    filters.VIDEO | filters.Document.ALL,
                    compress_receive_video,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", compress_cancel)],
        allow_reentry=True,
    )
