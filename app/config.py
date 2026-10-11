# -*- coding: utf-8 -*-
# config.py
dv_file_version = '261010.01'
"""Настройки приложения DixTune."""

import os
from pathlib import Path

# Базовые пути (можно переопределить через переменные окружения)
BASE_DIR = Path(__file__).resolve().parent.parent

# Локальные пути по умолчанию (для разработки в PyCharm)
DATA_DIR = Path(os.getenv("DIXTUNE_DATA_DIR", BASE_DIR / "data"))
MUSIC_DIR = Path(os.getenv("DIXTUNE_MUSIC_DIR", "/media/music/dixtune"))

# Производные пути
ARCHIVE_FILE = DATA_DIR / ".yt-dlp-archive.txt"
DB_PATH = DATA_DIR / "channels.db"
LOG_PATH = DATA_DIR / "logs" / "sync.log"

# Интервал синхронизации
SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", "6"))

# Аутентификация
DIXTUNE_USERNAME = os.getenv("DIXTUNE_USERNAME", "admin")
DIXTUNE_PASSWORD = os.getenv("DIXTUNE_PASSWORD", "admin123")

# Корневой путь для работы за прокси с подпутём
DIXTUNE_ROOT_PATH = os.getenv("DIXTUNE_ROOT_PATH", "")

# Настройки для обхода блокировок YouTube
DIXTUNE_PROXY = os.getenv("DIXTUNE_PROXY", "")

# Создаём папки при старте
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
