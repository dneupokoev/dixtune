# -*- coding: utf-8 -*-
# state.py
dv_file_version = '261012.04'
"""Общее состояние приложения для предотвращения циклических импортов."""

import subprocess
from typing import Optional

# Текущий процесс yt-dlp для возможности остановки
current_process: Optional[subprocess.Popen] = None
# Флаг остановки синхронизации
stop_requested = False
