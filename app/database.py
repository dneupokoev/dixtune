# -*- coding: utf-8 -*-
# database.py
dv_file_version = '261010.01'
"""Подключение к базе данных SQLite."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DB_PATH

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Получить сессию базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
