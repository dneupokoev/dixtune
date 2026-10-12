# -*- coding: utf-8 -*-
# downloader.py
dv_file_version = '261012.10'
"""Логика скачивания аудио с YouTube через yt-dlp."""

import subprocess
import logging
import re
import os
import signal
import threading
from pathlib import Path
from datetime import date
from typing import Optional
from mutagen.easyid3 import EasyID3

from app.config import MUSIC_DIR, ARCHIVE_FILE, DIXTUNE_PROXY, DIXTUNE_COOKIES, DIXTUNE_POT_PROVIDER_URL
from app.utils import ensure_directory
from app.database import SessionLocal
from app import crud
from app.state import current_process, stop_requested

logger = logging.getLogger("DixTune")
MAX_RETRY_DEPTH = 3


def stop_download() -> None:
    """Остановить текущий процесс скачивания yt-dlp.

    Отправляет SIGINT всей группе процессов, что позволяет yt-dlp
    завершить текущий файл и корректно выйти.
    """
    import app.state
    if app.state.current_process and app.state.current_process.poll() is None:
        try:
            pgid = os.getpgid(app.state.current_process.pid)
            os.killpg(pgid, signal.SIGINT)
            logger.info("Отправлен сигнал SIGINT группе процессов yt-dlp")
        except (ProcessLookupError, PermissionError) as e:
            logger.error(f"Не удалось остановить процесс yt-dlp: {e}")


def fix_date_tag(file_path: Path) -> None:
    """Исправить тег date в MP3 файле, установив формат YYYY-MM.

    Args:
        file_path: Путь к MP3 файлу.
    """
    try:
        audio = EasyID3(str(file_path))
        if 'date' in audio:
            date_value = audio['date'][0]
            # Преобразуем YYYYMMDD в YYYY-MM
            if len(date_value) >= 6:
                year = date_value[:4]
                month = date_value[4:6]
                new_date = f"{year}-{month}"
                if new_date != date_value:
                    audio['date'] = new_date
                    audio.save()
                    logger.info(f"Исправлен тег date в {file_path.name}: {date_value} -> {new_date}")
    except Exception as e:
        logger.error(f"Ошибка при исправлении тега date в {file_path.name}: {e}")


def clean_one_filename(file_path: Path) -> Path:
    """Очистить имя одного файла от повторяющихся подчёркиваний и лишних символов.

    Args:
        file_path: Путь к файлу.

    Returns:
        Новый путь к файлу после переименования.
    """
    original_name = file_path.name
    # Схлопываем повторяющиеся подчёркивания
    cleaned_name = re.sub(r'_+', '_', original_name)
    # Замена полноширинных и «умных» символов на подчёркивание
    cleaned_name = cleaned_name.replace('？', '_')  # полноширинный вопросительный знак (U+FF1F)
    cleaned_name = cleaned_name.replace('｜', '_')  # полноширинная вертикальная черта (U+FF5C)
    cleaned_name = cleaned_name.replace('：', '_')  # полноширинное двоеточие (U+FF1A)
    cleaned_name = cleaned_name.replace('＊', '_')  # полноширинная звёздочка (U+FF0A)
    cleaned_name = cleaned_name.replace('”', '_')   # правая двойная кавычка (U+201D)
    cleaned_name = cleaned_name.replace('“', '_')   # левая двойная кавычка (U+201C)
    cleaned_name = cleaned_name.replace('’', '_')   # правая одинарная кавычка (U+2019)
    cleaned_name = cleaned_name.replace('‘', '_')   # левая одинарная кавычка (U+2018)
    cleaned_name = cleaned_name.replace('／', '_')  # полноширинный слэш (U+FF0F)
    cleaned_name = cleaned_name.replace('＼', '_')  # полноширинный обратный слэш (U+FF3C)
    # Убираем подчёркивания в начале и конце имени
    cleaned_name = cleaned_name.strip('_')

    if cleaned_name == original_name:
        return file_path

    new_path = file_path.with_name(cleaned_name)
    
    # Защита от коллизии: если файл с таким именем уже есть —
    # добавляем числовой суффикс
    if new_path.exists() and new_path != file_path:
        base = new_path.stem
        suffix = new_path.suffix
        counter = 1
        while new_path.exists():
            new_path = file_path.with_name(f"{base}_{counter}{suffix}")
            counter += 1
        logger.warning(
            f"Коллизия имён: {original_name} -> {new_path.name} "
            f"(добавлен суффикс)"
        )
    
    try:
        file_path.rename(new_path)
        logger.info(f"Переименован файл: {original_name} -> {new_path.name}")
    except OSError as e:
        logger.error(f"Не удалось переименовать {original_name}: {e}")
        return file_path
    
    return new_path


def clean_filenames(channel_dir: Path) -> None:
    """Очистить имена всех .mp3 в директории (для fallback).

    Args:
        channel_dir: Директория с файлами канала.
    """
    for file_path in channel_dir.glob("*.mp3"):
        clean_one_filename(file_path)


def check_and_retry(
    channel_dir: Path,
    url: str,
    folder_name: str,
    min_date: Optional[date],
    channel_id: Optional[int],
    recursion_depth: int = 0,
) -> None:
    """Проверить наличие .webm без .mp3 и повторить скачивание.

    Args:
        channel_dir: Директория с файлами канала.
        url: URL канала или плейлиста YouTube.
        folder_name: Имя папки, в которую складывать файлы.
        min_date: Минимальная дата публикации видео.
        channel_id: ID канала для записи в журнал.
        recursion_depth: Текущая глубина рекурсии.
    """
    if recursion_depth >= MAX_RETRY_DEPTH:
        logger.warning(
            f"Достигнута максимальная глубина рекурсии "
            f"({MAX_RETRY_DEPTH}) для канала {url}. Прекращаю попытки."
        )
        return

    # Найти все .webm файлы, для которых нет соответствующего .mp3
    orphan_webm_files = []
    for webm_file in channel_dir.glob("*.webm"):
        mp3_file = webm_file.with_suffix(".mp3")
        if not mp3_file.exists():
            orphan_webm_files.append(webm_file)

    if not orphan_webm_files:
        return

    logger.warning(
        f"Найдено {len(orphan_webm_files)} файлов .webm без .mp3. "
        f"Глубина рекурсии: {recursion_depth + 1}/{MAX_RETRY_DEPTH}"
    )

    # Удалить ID из архива для этих файлов, чтобы yt-dlp снова их обработал
    # yt-dlp использует ID видео в архиве. Имя файла .webm содержит ID в формате:
    # <video_id>.<ext> или <title>.<video_id>.<ext>
    # Мы удаляем сам .webm файл, чтобы yt-dlp не считал его уже скачанным
    for webm_file in orphan_webm_files:
        try:
            webm_file.unlink()
            logger.info(f"Удалён orphan .webm файл: {webm_file.name}")
        except OSError as e:
            logger.error(f"Не удалось удалить {webm_file.name}: {e}")

    # Повторный запуск download_channel с увеличенной глубиной
    download_channel(url, folder_name, min_date, channel_id, _depth=recursion_depth + 1)


def download_channel(
    url: str,
    folder_name: str,
    min_date: Optional[date] = None,
    channel_id: Optional[int] = None,
    _depth: int = 0
) -> bool:
    """Скачать аудио с YouTube-канала через yt-dlp.

    Args:
        url: URL канала или плейлиста YouTube.
        folder_name: Имя папки, в которую складывать файлы.
        min_date: Минимальная дата публикации видео (не качать старше).
        channel_id: ID канала для записи в журнал.
        _depth: Текущая глубина рекурсии для защиты от бесконечного цикла.

    Returns:
        True, если скачивание прошло успешно, иначе False.
    """
    import app.state

    if _depth >= MAX_RETRY_DEPTH:
        logger.warning(
            f"Достигнута максимальная глубина рекурсии "
            f"({MAX_RETRY_DEPTH}) для {url}"
        )
        return False

    if app.state.stop_requested:
        logger.info("Скачивание пропущено: запрошена остановка")
        return False

    channel_dir = MUSIC_DIR / folder_name
    ensure_directory(channel_dir)
    stderr_lines: list[str] = []

    # Нормализация URL: если это канал (@name), добавляем /videos для правильного порядка
    if "youtube.com/@" in url and not url.endswith("/videos"):
        url = url.rstrip("/") + "/videos"

    # Снимок состояния папки ДО скачивания
    mp3_before = set(channel_dir.glob("*.mp3"))
    mp3_before_count = len(mp3_before)

    # Формируем команду yt-dlp
    cmd = [
        "yt-dlp",
        "-x",                                    # Извлечь аудио
        "--audio-format", "mp3",                 # Формат MP3
        "--audio-quality", "128K",               # Битрейт 128 kbps
        "--sponsorblock-remove", "default",      # Вырезать спонсорские вставки
        "--sponsorblock-api", "https://api.sponsor.ajay.app",
        "--download-archive", str(ARCHIVE_FILE), # Архив скачанных видео
        "--no-overwrites",                       # Не перезаписывать существующие
        "--ignore-errors",                       # Продолжать при ошибках
        "-o", str(channel_dir / "%(title)s.%(ext)s"),
        url
    ]

    # Фильтр по дате: не качать видео старше min_date
    if min_date:
        date_str = min_date.strftime("%Y%m%d")
        cmd.extend(["--dateafter", date_str])

    # Ленивая обработка плейлиста: не получать весь список сразу
    cmd.extend(["--lazy-playlist"])

    # Ограничение количества проверяемых видео
    cmd.extend(["--playlist-end", "10"])

    # Фильтр: исключить трансляции (is_live) и Shorts (duration < 60)
    cmd.extend(["--match-filter", "!is_live & duration > 60"])

    # Безопасные имена файлов для Windows
    cmd.extend(["--windows-filenames"])

    # Обход блокировок: прокси (ByeDPI)
    if DIXTUNE_PROXY:
        cmd.extend(["--proxy", DIXTUNE_PROXY])

    # Пауза между запросами для снижения нагрузки на ByeDPI
    cmd.extend(["--sleep-requests", "1"])

    # Cookies для авторизации на YouTube
    if DIXTUNE_COOKIES and Path(DIXTUNE_COOKIES).exists():
        cmd.extend(["--cookies", DIXTUNE_COOKIES])

    # Автоматическое заполнение тегов MP3 на основе метаданных YouTube
    cmd.extend(["--embed-metadata"])
    cmd.extend(["--parse-metadata", "uploader:%(album_artist)s"])
    cmd.extend(["--parse-metadata", "%(uploader)s:%(album)s"])
    cmd.extend(["--replace-in-metadata", "album", "^.*$", "YouTube"])
    cmd.extend(["--parse-metadata", "%(upload_date>%Y%m%d)s %(title)s:%(title)s"])
    cmd.extend(["--parse-metadata", "uploader:%(artist)s"])

    # Обход n challenge и signature: mweb client + удалённые компоненты + PO Token
    cmd.extend(["--extractor-args", "youtube:player_client=mweb"])
    cmd.extend(["--extractor-args", f"youtubepot-bgutilhttp:base_url={DIXTUNE_POT_PROVIDER_URL}"])
    cmd.extend(["--extractor-retries", "3"])
    cmd.extend(["--retries", "3"])
    cmd.extend(["--remote-components", "ejs:github"])

    # Постобработка каждого файла сразу после скачивания.
    # after_move — срабатывает после перемещения файла в целевую директорию.
    # Прерывание синхронизации больше не оставляет "сырые" файлы.
    cmd.extend([
        "--exec", "after_move:python -m app.postprocess %(filepath)q"
    ])

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
            text=True,
            start_new_session=True
        )
        app.state.current_process = process

        # Построчное чтение stdout и stderr в реальном времени.
        # Логируем важные строки для отладки пропусков и скачиваний.
        def log_stream(stream, prefix):
            for line in stream:
                line = line.strip()
                if prefix == "yt-dlp-err":
                    stderr_lines.append(line)
                if any(keyword in line for keyword in [
                    "[download]", "Destination:", "ERROR", "WARNING", "100%",
                    "upload date", "has already been recorded",
                    "Skipping", "not in range",
                    "Downloading webpage", "[download] Destination"
                ]):
                    logger.info(f"{prefix}: {line}")

        stdout_thread = threading.Thread(target=log_stream, args=(process.stdout, "yt-dlp"))
        stderr_thread = threading.Thread(target=log_stream, args=(process.stderr, "yt-dlp-err"))

        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join()
        stderr_thread.join()
        process.wait()
        app.state.current_process = None

        # FALLBACK: если --exec не сработал для некоторых файлов,
        # обрабатываем оставшиеся пачкой. Это защита на случай старых версий
        # yt-dlp или сбоя --exec.
        clean_filenames(channel_dir)
        for mp3_file in channel_dir.glob("*.mp3"):
            fix_date_tag(mp3_file)

        # Снимок состояния папки ПОСЛЕ обработки
        mp3_after = set(channel_dir.glob("*.mp3"))
        mp3_after_count = len(mp3_after)
        mp3_new_count = mp3_after_count - mp3_before_count

        if process.returncode != 0:
            if mp3_new_count > 0:
                # Частичный успех: что-то скачалось, несмотря на код возврата
                logger.warning(
                    f"yt-dlp завершился с кодом {process.returncode}, "
                    f"но скачано {mp3_new_count} новых файлов. Считаем успехом."
                )
                # Записываем в лог как success с пометкой
                db = SessionLocal()
                try:
                    crud.create_sync_log(
                        db, channel_id, "success",
                        f"Скачано файлов: {mp3_after_count} (+{mp3_new_count} новых, "
                        f"yt-dlp код {process.returncode})"
                    )
                finally:
                    db.close()
                # НЕ вызываем check_and_retry — файлы появились, всё ок
                return True
            else:
                # Настоящая ошибка: ни одного нового файла
                logger.error(f"yt-dlp завершился с кодом {process.returncode}, "
                             f"новых файлов нет")
                error_msg = f"yt-dlp завершился с кодом {process.returncode}"
                if stderr_lines:
                    error_msg += "\n" + "\n".join(stderr_lines[-10:])
                db = SessionLocal()
                try:
                    crud.create_sync_log(db, channel_id, "error", error_msg)
                finally:
                    db.close()

                # Проверка и повторное скачивание для orphan .webm файлов
                check_and_retry(
                    channel_dir, url, folder_name, min_date, channel_id,
                    recursion_depth=_depth
                )
                return False

        # check_and_retry не нужен: при успешном завершении
        # orphan .webm файлов не бывает

        # Подсчёт файлов в папке канала (для отчёта)
        file_count = mp3_after_count
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
