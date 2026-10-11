# -*- coding: utf-8 -*-
# downloader.py
dv_file_version = '261011.01'
"""Логика скачивания аудио с YouTube через yt-dlp."""

import subprocess
import logging
from pathlib import Path
from datetime import date
from typing import Optional

from app.config import MUSIC_DIR, ARCHIVE_FILE, DIXTUNE_PROXY
from app.utils import ensure_directory

logger = logging.getLogger("DixTune")


def download_channel(
    url: str,
    folder_name: str,
    min_date: Optional[date] = None
) -> bool:
    """Скачать аудио с YouTube-канала через yt-dlp.

    Args:
        url: URL канала или плейлиста YouTube.
        folder_name: Имя папки, в которую складывать файлы.
        min_date: Минимальная дата публикации видео (не качать старше).

    Returns:
        True, если скачивание прошло успешно, иначе False.
    """
    channel_dir = MUSIC_DIR / folder_name
    ensure_directory(channel_dir)

    # Нормализация URL: если это канал (@name), добавляем /videos для правильного порядка
    if "youtube.com/@" in url and not url.endswith("/videos"):
        url = url.rstrip("/") + "/videos"

    # Формируем команду yt-dlp
    cmd = [
        "yt-dlp",
        "-x",                                    # Извлечь аудио
        "--audio-format", "mp3",                 # Формат MP3
        "--audio-quality", "128K",               # Битрейт 128 kbps
        "--sponsorblock-remove", "default",      # Вырезать спонсорские вставки
        "--download-archive", str(ARCHIVE_FILE), # Архив скачанных видео
        "--no-overwrites",                       # Не перезаписывать существующие
        "--ignore-errors",                       # Продолжать при ошибках
        "-o", str(channel_dir / "%(upload_date>%Y%m%d)s_%(title)s.%(ext)s"),
        url
    ]

    # Фильтр по дате: не качать видео старше min_date
    if min_date:
        date_str = min_date.strftime("%Y%m%d")
        cmd.extend(["--dateafter", date_str])
        # Останавливаться, как только встретится видео старше min_date.
        # Экономит время, если видео идут в порядке от новых к старым.
        cmd.extend(["--break-on-reject"])

    # Ленивая обработка плейлиста: не получать весь список сразу
    cmd.extend(["--lazy-playlist"])

    # Обход блокировок: прокси (ByeDPI)
    if DIXTUNE_PROXY:
        cmd.extend(["--proxy", DIXTUNE_PROXY])

    # Оптимизация перебора: останавливаться на уже скачанных видео
    cmd.extend(["--break-on-existing"])
    cmd.extend(["--break-per-input"])

    # Обход n challenge и signature: только tv client + удалённые компоненты
    cmd.extend(["--extractor-args", "youtube:player_client=tv"])
    cmd.extend(["--extractor-retries", "5"])
    cmd.extend(["--remote-components", "ejs:github"])

    # Логируем команду перед запуском (без секретов)
    safe_cmd = [
        arg for arg in cmd
        if not any(secret and secret in arg for secret in [DIXTUNE_PROXY])
    ]
    logger.info(f"Запуск yt-dlp: {' '.join(safe_cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Построчное чтение вывода в реальном времени.
        # Логируем только важные строки, чтобы не засорять лог.
        for line in process.stdout:
            line = line.strip()
            if any(keyword in line for keyword in [
                "[download]", "Destination:", "ERROR", "WARNING", "100%"
            ]):
                logger.info(f"yt-dlp: {line}")

        stderr_output = process.stderr.read()
        process.wait()

        if process.returncode != 0:
            logger.error(f"yt-dlp завершился с кодом {process.returncode}")
            if stderr_output:
                logger.error(f"yt-dlp stderr: {stderr_output}")
            return False

        # Подсчёт файлов в папке канала (для отчёта)
        file_count = len(list(channel_dir.glob("*.mp3")))
        logger.info(f"Успешно обработан канал: {url}. Файлов в папке: {file_count}")
        return True

    except FileNotFoundError:
        logger.error("yt-dlp или ffmpeg не найдены в системе")
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при скачивании {url}: {str(e)}")
        return False
