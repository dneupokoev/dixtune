# -*- coding: utf-8 -*-
# scheduler.py
dv_file_version = '261012.07'
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
import app.state

logger = logging.getLogger("DixTune")
tz_string = os.getenv("TZ", "Europe/Moscow")
scheduler = BackgroundScheduler(timezone=tz_string)


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
    if app.state.is_syncing:
        logger.info("Синхронизация уже идёт")
        return

    app.state.is_syncing = True
    app.state.stop_requested = False
    db = SessionLocal()
    try:
        channels = get_enabled_channels(db)
        logger.info(f"Запуск синхронизации {len(channels)} каналов")

        for channel in channels:
            if app.state.stop_requested:
                logger.info("Синхронизация остановлена по запросу пользователя")
                break
            logger.info(f"Проверка канала: {channel.name or channel.url}")
            success = download_channel(
                url=channel.url,
                folder_name=channel.folder_name,
                min_date=channel.min_date,
                channel_id=channel.id
            )
            if success:
                update_last_checked(db, channel.id)
            else:
                logger.warning(f"Канал {channel.name or channel.url} не обновлён "
                               f"из-за ошибки скачивания")

    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {str(e)}")
    finally:
        db.close()
        app.state.stop_requested = False
        app.state.is_syncing = False
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
