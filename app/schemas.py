# -*- coding: utf-8 -*-
# schemas.py
dv_file_version = '261010.01'
"""Pydantic-схемы для API."""

from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ChannelBase(BaseModel):
    """Базовая схема канала."""

    url: str = Field(..., description="URL канала или плейлиста YouTube")
    name: Optional[str] = Field(None, description="Понятное имя канала")
    min_date: Optional[date] = Field(None, description="Минимальная дата публикации видео (YYYY-MM-DD)")
    transliterate: bool = Field(False, description="Транслитерировать имя папки в латиницу")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Проверить, что URL ведёт на YouTube."""
        if not v.startswith(("https://www.youtube.com", "https://youtube.com", "https://youtu.be")):
            raise ValueError("URL должен вести на youtube.com или youtu.be")
        return v


class ChannelCreate(ChannelBase):
    """Схема для создания канала."""
    pass


class ChannelUpdate(BaseModel):
    """Схема для обновления канала."""

    url: Optional[str] = None
    name: Optional[str] = None
    min_date: Optional[date] = None
    enabled: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Проверить URL при обновлении."""
        if v is not None:
            if not v.startswith(("https://www.youtube.com", "https://youtube.com", "https://youtu.be")):
                raise ValueError("URL должен вести на youtube.com или youtu.be")
        return v


class ChannelResponse(ChannelBase):
    """Схема ответа с данными канала."""

    id: int
    folder_name: str
    enabled: bool
    last_checked: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class StatusResponse(BaseModel):
    """Схема статуса приложения."""

    last_sync: Optional[datetime]
    total_channels: int
    enabled_channels: int
    downloaded_count: int
