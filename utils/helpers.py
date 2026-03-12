import os
import re
import logging

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """Проверяет что строка похожа на URL."""
    pattern = re.compile(
        r'^(https?://)'
        r'([\w\-]+\.)+[\w\-]+'
        r'(/[^\s]*)?$',
        re.IGNORECASE,
    )
    return bool(pattern.match(url.strip()))


def is_youtube_url(url: str) -> bool:
    """Проверяет что URL — YouTube-ссылка."""
    return any(d in url for d in ['youtube.com', 'youtu.be', 'youtube-nocookie.com'])


def is_instagram_url(url: str) -> bool:
    """Проверяет что URL — Instagram-ссылка."""
    return 'instagram.com' in url


def get_file_size_mb(path: str) -> float:
    """Возвращает размер файла в МБ."""
    if os.path.exists(path):
        return os.path.getsize(path) / (1024 * 1024)
    return 0.0


def cleanup(*paths: str):
    """Удаляет временные файлы после отправки."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.info(f"🗑 Удалён временный файл: {path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {path}: {e}")


def trim_url(url: str) -> str:
    """Обрезает лишние параметры из ссылки (если есть)."""
    return url.strip().split('?')[0] if '?' in url else url.strip()
