# -*- coding: utf-8 -*-
# models.py
dv_file_version = '261010.01'
"""Модели данных SQLAlchemy."""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Channel(Base):
    """Модель канала YouTube."""

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    folder_name = Column(String, nullable=False)
    min_date = Column(Date, nullable=True)
    enabled = Column(Boolean, default=True)
    transliterate = Column(Boolean, default=False)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
