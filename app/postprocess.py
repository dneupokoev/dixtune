# -*- coding: utf-8 -*-
# postprocess.py
dv_file_version = '261012.01'
"""Постобработка одного MP3-файла после скачивания yt-dlp.

Вызывается через --exec after_move:python -m app.postprocess %(filepath)q
"""

import sys
import logging
from pathlib import Path

from app.downloader import fix_date_tag, clean_one_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DixTune-postprocess")


def main() -> None:
    """Выполнить постобработку одного файла.

    Args:
        sys.argv[1]: Путь к файлу для обработки.
    """
    if len(sys.argv) < 2:
        logger.error("Не передан путь к файлу")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        logger.error(f"Файл не найден: {file_path}")
        sys.exit(1)

    if file_path.suffix.lower() != ".mp3":
        # Пропускаем не-MP3 (например, .webm до конвертации)
        sys.exit(0)

    logger.info(f"Постобработка: {file_path.name}")

    # 1. Исправить тег date (YYYYMMDD -> YYYY-MM)
    fix_date_tag(file_path)

    # 2. Очистить имя файла
    clean_one_filename(file_path)

    logger.info(f"Постобработка завершена: {file_path.name}")


if __name__ == "__main__":
    main()
