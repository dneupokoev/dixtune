# -*- coding: utf-8 -*-
# downloader.py
dv_file_version = '261011.01'
"""Логика скачивания аудио с YouTube через yt-dlp."""

import subprocess
import logging
from pathlib import Path
from datetime import date
from typing import Optional

from app.config import MUSIC_DIR, ARCHIVE_FILE, DIXTUNE_PROXY, DIXTUNE_COOKIES, DIXTUNE_POT_PROVIDER_URL
from app.utils import ensure_directory
from app.database import SessionLocal
from app import crud

logger = logging.getLogger("DixTune")


def download_channel(
    url: str,
    folder_name: str,
    min_date: Optional[date] = None,
    channel_id: Optional[int] = None
) -> bool:
    """Скачать аудио с YouTube-канала через yt-dlp.

    Args:
        url: URL канала или плейлиста YouTube.
        folder_name: Имя папки, в которую складывать файлы.
        min_date: Минимальная дата публикации видео (не качать старше).
        channel_id: ID канала для записи в журнал.

    Returns:
        True, если скачивание прошло успешно, иначе False.
    """
    channel_dir = MUSIC_DIR / folder_name
    ensure_directory(channel_dir)
    stderr_lines: list[str] = []

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

    # Cookies для авторизации на YouTube
    if DIXTUNE_COOKIES and Path(DIXTUNE_COOKIES).exists():
        cmd.extend(["--cookies", DIXTUNE_COOKIES])

    # Оптимизация перебора: останавливаться на уже скачанных видео
    cmd.extend(["--break-on-existing"])
    cmd.extend(["--break-per-input"])

    # Временный флаг для отладки логирования
    cmd.extend(["--verbose"])

    # Обход n challenge и signature: только tv client + удалённые компоненты + PO Token
    cmd.extend(["--extractor-args", f"youtube:player_client=tv;youtubepot-bgutilhttp:base_url={DIXTUNE_POT_PROVIDER_URL}"])
    cmd.extend(["--extractor-retries", "10"])
    cmd.extend(["--retries", "10"])
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

        # Построчное чтение stdout и stderr в реальном времени.
        # Логируем важные строки для отладки пропусков и скачиваний.
        import threading

        def log_stream(stream, prefix):
            for line in stream:
                line = line.strip()
                if prefix == "yt-dlp-err":
                    stderr_lines.append(line)
                if any(keyword in line for keyword in [
                    "[download]", "Destination:", "ERROR", "WARNING", "100%",
                    "Downloading item", "upload date", "has already been recorded",
                    "Skipping", "not in range"
                ]):
                    logger.info(f"{prefix}: {line}")

        stdout_thread = threading.Thread(target=log_stream, args=(process.stdout, "yt-dlp"))
        stderr_thread = threading.Thread(target=log_stream, args=(process.stderr, "yt-dlp-err"))

        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join()
        stderr_thread.join()
        process.wait()

        if process.returncode != 0:
            logger.error(f"yt-dlp завершился с кодом {process.returncode}")
            error_msg = f"yt-dlp завершился с кодом {process.returncode}"
            if stderr_lines:
                error_msg += "\n" + "\n".join(stderr_lines[-10:])
            db = SessionLocal()
            try:
                crud.create_sync_log(db, channel_id, "error", error_msg)
            finally:
                db.close()
            return False

        # Подсчёт файлов в папке канала (для отчёта)
        file_count = len(list(channel_dir.glob("*.mp3")))
        logger.info(f"Успешно обработан канал: {url}. Файлов в папке: {file_count}")
        db = SessionLocal()
        try:
            crud.create_sync_log(db, channel_id, "success", f"Скачано файлов: {file_count}")
        finally:
            db.close()
        return True

    except FileNotFoundError:
        logger.error("yt-dlp или ffmpeg не найдены в системе")
        db = SessionLocal()
        try:
            crud.create_sync_log(db, channel_id, "error", "yt-dlp или ffmpeg не найдены в системе")
        finally:
            db.close()
        return False
    except Exception as e:
        logger.error(f"Неизвестная ошибка при скачивании {url}: {str(e)}")
        db = SessionLocal()
        try:
            crud.create_sync_log(db, channel_id, "error", f"Неизвестная ошибка: {str(e)}")
        finally:
            db.close()
        return False
