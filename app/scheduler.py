# -*- coding: utf-8 -*-
# scheduler.py
dv_file_version = '261010.01'
"""Планировщик периодических задач APScheduler."""

import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import SYNC_INTERVAL_HOURS
from app.database import SessionLocal
from app.crud import get_enabled_channels, update_last_checked
from app.downloader import download_channel

logger = logging.getLogger("DixTune")
timezone = os.getenv("TZ", "Europe/Moscow")
scheduler = BackgroundScheduler(timezone=timezone)


def sync_all_channels() -> None:
    """Синхронизировать все включённые каналы."""
    db = SessionLocal()
    try:
        channels = get_enabled_channels(db)
        logger.info(f"Запуск синхронизации {len(channels)} каналов")

        for channel in channels:
            logger.info(f"Проверка канала: {channel.name or channel.url}")
            success = download_channel(
                url=channel.url,
                folder_name=channel.folder_name,
                min_date=channel.min_date
            )
            update_last_checked(db, channel.id)

    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {str(e)}")
    finally:
        db.close()


def start_scheduler() -> None:
    """Запустить планировщик."""
    scheduler.add_job(
        sync_all_channels,
        trigger=IntervalTrigger(hours=SYNC_INTERVAL_HOURS),
        id="sync_channels",
        name="Sync YouTube Channels",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Планировщик запущен, интервал: {SYNC_INTERVAL_HOURS} часов")


def stop_scheduler() -> None:
    """Остановить планировщик."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")
