# -*- coding: utf-8 -*-
# downloader.py
dv_file_version = '261010.01'
"""Логика скачивания аудио с YouTube через yt-dlp."""

import subprocess
import logging
from pathlib import Path
from datetime import date
from typing import Optional

from app.config import MUSIC_DIR, ARCHIVE_FILE, LOG_PATH, DIXTUNE_PROXY, DIXTUNE_COOKIES
from app.utils import ensure_directory

logger = logging.getLogger("DixTune")


def download_channel(
    url: str,
    folder_name: str,
    min_date: Optional[date] = None
) -> bool:
    """Скачать аудио с YouTube-канала через yt-dlp."""
    channel_dir = MUSIC_DIR / folder_name
    ensure_directory(channel_dir)

    # Формируем команду yt-dlp
    # --audio-quality 128K можно изменить через переменную окружения (опционально)
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "128K",
        "--sponsorblock-remove", "default",
        "--download-archive", str(ARCHIVE_FILE),
        "--no-overwrites",
        "--ignore-errors",
        "-o", str(channel_dir / "%(upload_date>%Y%m%d)s_%(title)s.%(ext)s"),
        url
    ]

    if min_date:
        # Преобразуем дату в формат YYYYMMDD для yt-dlp
        date_str = min_date.strftime("%Y%m%d")
        cmd.extend(["--dateafter", date_str])

    # Добавляем настройки для обхода блокировок
    if DIXTUNE_PROXY:
        cmd.extend(["--proxy", DIXTUNE_PROXY])
    if DIXTUNE_COOKIES:
        cmd.extend(["--cookies", DIXTUNE_COOKIES])
    cmd.extend(["--extractor-args", "youtube:player_client=tv,mweb"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 час на скачивание
        )

        if result.returncode != 0:
            logger.error(f"Ошибка yt-dlp для {url}: {result.stderr}")
            return False

        logger.info(f"Успешно обработан канал: {url}")
        return True

    except FileNotFoundError:
        logger.error("yt-dlp или ffmpeg не найдены в системе")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут при скачивании {url}")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при скачивании {url}: {str(e)}")
        return False
