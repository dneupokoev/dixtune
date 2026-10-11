# -*- coding: utf-8 -*-
# scheduler.py
dv_file_version = '261010.01'
"""Планировщик периодических задач APScheduler."""

import logging
import os
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from app.config import SYNC_INTERVAL_HOURS_MIN, SYNC_INTERVAL_HOURS_MAX
from app.database import SessionLocal
from app.crud import get_enabled_channels, update_last_checked
from app.downloader import download_channel

logger = logging.getLogger("DixTune")
timezone = os.getenv("TZ", "Europe/Moscow")
scheduler = BackgroundScheduler(timezone=timezone)


def schedule_next_sync() -> None:
    """Запланировать следующую синхронизацию со случайным интервалом."""
    random_hours = random.uniform(SYNC_INTERVAL_HOURS_MIN, SYNC_INTERVAL_HOURS_MAX)
    next_run = datetime.now() + timedelta(hours=random_hours)
    scheduler.add_job(
        sync_all_channels,
        trigger=DateTrigger(run_date=next_run),
        id="sync_channels",
        name="Sync YouTube Channels",
        replace_existing=True
    )
    logger.info(f"Следующая синхронизация запланирована на {next_run.strftime('%Y-%m-%d %H:%M:%S')} (через {random_hours:.2f} ч.)")


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
        schedule_next_sync()


def start_scheduler() -> None:
    """Запустить планировщик."""
    scheduler.start()
    schedule_next_sync()
    logger.info(f"Планировщик запущен, интервал: {SYNC_INTERVAL_HOURS_MIN}-{SYNC_INTERVAL_HOURS_MAX} часов")


def stop_scheduler() -> None:
    """Остановить планировщик."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")
