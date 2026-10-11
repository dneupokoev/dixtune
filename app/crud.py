# -*- coding: utf-8 -*-
# crud.py
dv_file_version = '261010.01'
"""Операции CRUD для работы с БД."""

import re
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas
from app.utils import sanitize_filename, transliterate


def get_channels(db: Session) -> List[models.Channel]:
    """Получить список всех каналов."""
    return db.query(models.Channel).all()


def get_channel(db: Session, channel_id: int) -> Optional[models.Channel]:
    """Получить канал по ID."""
    return db.query(models.Channel).filter(models.Channel.id == channel_id).first()


def create_channel(db: Session, channel: schemas.ChannelCreate) -> models.Channel:
    """Создать новый канал."""
    if channel.name:
        source_name = channel.name
    else:
        # Извлекаем часть URL после @
        match = re.search(r'@([^/]+)', channel.url)
        if match:
            source_name = match.group(1)
        else:
            source_name = channel.url

    if channel.transliterate:
        folder_name = sanitize_filename(transliterate(source_name))
    else:
        folder_name = sanitize_filename(source_name)

    db_channel = models.Channel(
        url=channel.url,
        name=channel.name,
        folder_name=folder_name,
        min_date=channel.min_date,
        enabled=True,
        transliterate=channel.transliterate
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


def update_channel(db: Session, channel_id: int, channel_update: schemas.ChannelUpdate) -> Optional[models.Channel]:
    """Обновить данные канала."""
    db_channel = get_channel(db, channel_id)
    if not db_channel:
        return None

    # folder_name не обновляется, так как папка фиксируется при создании канала
    if channel_update.url is not None:
        db_channel.url = channel_update.url
    if channel_update.name is not None:
        db_channel.name = channel_update.name

    if channel_update.min_date is not None:
        db_channel.min_date = channel_update.min_date
    if channel_update.enabled is not None:
        db_channel.enabled = channel_update.enabled

    db.commit()
    db.refresh(db_channel)
    return db_channel


def delete_channel(db: Session, channel_id: int) -> bool:
    """Удалить канал."""
    db_channel = get_channel(db, channel_id)
    if not db_channel:
        return False
    db.delete(db_channel)
    db.commit()
    return True


def get_enabled_channels(db: Session) -> List[models.Channel]:
    """Получить список включённых каналов."""
    return db.query(models.Channel).filter(models.Channel.enabled == True).all()


def update_last_checked(db: Session, channel_id: int) -> None:
    """Обновить время последней проверки канала."""
    db_channel = get_channel(db, channel_id)
    if db_channel:
        db_channel.last_checked = datetime.utcnow()
        db.commit()
