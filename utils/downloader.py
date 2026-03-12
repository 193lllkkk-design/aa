import os
import logging
import yt_dlp
from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

# Используем format_sort чтобы выбирать качество без ffmpeg
QUALITY_SORT = {
    "1080": ["res:1080", "ext:mp4", "vcodec:h264"],
    "720":  ["res:720",  "ext:mp4", "vcodec:h264"],
    "480":  ["res:480",  "ext:mp4", "vcodec:h264"],
    "360":  ["res:360",  "ext:mp4", "vcodec:h264"],
    "audio": None,
}


def download_youtube(url: str, quality: str = "720") -> str:
    """
    Скачивает видео (или аудио) с YouTube без ffmpeg.
    Использует format_sort для выбора качества без слияния потоков.
    """
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"yt_{unique_id}.%(ext)s")
    is_audio = quality == "audio"

    if is_audio:
        fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
        sort = []
    else:
        # best[ext=mp4] выбирает только готовые потоки (без слияния)
        fmt = "best[ext=mp4]/best[ext=webm]/best"
        sort = QUALITY_SORT.get(quality, ["res:720", "ext:mp4"])

    ydl_opts = {
        "format": fmt,
        "format_sort": sort,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        real_ext = info.get("ext", "mp4")
        file_path = os.path.join(DOWNLOAD_DIR, f"yt_{unique_id}.{real_ext}")

        if not os.path.exists(file_path):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(f"yt_{unique_id}"):
                    file_path = os.path.join(DOWNLOAD_DIR, f)
                    break

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден после скачивания: {file_path}")

    logger.info(f"✅ YouTube скачан: {file_path}")
    return file_path


def download_instagram(url: str) -> str:
    """
    Скачивает видео из Instagram (Reel, Post) без ffmpeg.
    """
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"ig_{unique_id}.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "format_sort": ["ext:mp4", "vcodec:h264"],
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        real_ext = info.get("ext", "mp4")
        file_path = os.path.join(DOWNLOAD_DIR, f"ig_{unique_id}.{real_ext}")

        if not os.path.exists(file_path):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(f"ig_{unique_id}"):
                    file_path = os.path.join(DOWNLOAD_DIR, f)
                    break

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Instagram файл не найден: {file_path}")

    logger.info(f"✅ Instagram скачан: {file_path}")
    return file_path
