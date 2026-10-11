# -*- coding: utf-8 -*-
# main.py
dv_file_version = '261010.01'
"""Точка входа FastAPI-приложения DixTune."""

import base64
import logging
import logging.handlers
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models, schemas, crud
from app.database import engine, Base, get_db
from app.config import MUSIC_DIR, LOG_PATH, DIXTUNE_USERNAME, DIXTUNE_PASSWORD, DIXTUNE_ROOT_PATH
from app.scheduler import start_scheduler, stop_scheduler, sync_all_channels
from app.utils import ensure_directory
from app.ui import router as ui_router

# Создаём папку для логов ДО настройки логирования
ensure_directory(LOG_PATH.parent)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_PATH,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DixTune")

# Создание таблиц БД
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Запуск планировщика
    start_scheduler()
    logger.info("Приложение DixTune запущено")
    yield
    # Остановка планировщика
    stop_scheduler()
    logger.info("Приложение DixTune остановлено")


app = FastAPI(
    title="DixTune",
    description="Автоматический загрузчик аудио с YouTube-каналов.",
    lifespan=lifespan,
    root_path=DIXTUNE_ROOT_PATH
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware для проверки Basic Auth на всех эндпоинтах, кроме /health, /favicon.ico и /."""
    path = request.url.path
    if DIXTUNE_ROOT_PATH and path.startswith(DIXTUNE_ROOT_PATH):
        path = path[len(DIXTUNE_ROOT_PATH):]
    if path in ("/health", "/favicon.ico", "/"):
        return await call_next(request)
    
    # Проверка наличия заголовка Authorization
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return Response(
            content="Необходима аутентификация",
            status_code=401,
            headers={"WWW-Authenticate": "Basic"}
        )
    
    try:
        # Декодируем Basic Auth
        scheme, credentials = auth_header.split(" ")
        decoded = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
        
        correct_username = secrets.compare_digest(username.encode("utf8"), DIXTUNE_USERNAME.encode("utf8"))
        correct_password = secrets.compare_digest(password.encode("utf8"), DIXTUNE_PASSWORD.encode("utf8"))
        
        if not (correct_username and correct_password):
            return Response(
                content="Неверные логин или пароль",
                status_code=401,
                headers={"WWW-Authenticate": "Basic"}
            )
    except Exception:
        return Response(
            content="Неверный формат аутентификации",
            status_code=401,
            headers={"WWW-Authenticate": "Basic"}
        )
        
    return await call_next(request)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(ui_router)


@app.get("/")
def root_redirect(request: Request):
    """Редирект с корня на веб-интерфейс."""
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=307)


@app.get("/channels", response_model=list[schemas.ChannelResponse])
def read_channels(db: Session = Depends(get_db)):
    """Получить список всех каналов."""
    return crud.get_channels(db)


@app.post("/channels", response_model=schemas.ChannelResponse)
def create_channel(channel: schemas.ChannelCreate, db: Session = Depends(get_db)):
    """Добавить новый канал."""
    return crud.create_channel(db, channel)


@app.put("/channels/{channel_id}", response_model=schemas.ChannelResponse)
def update_channel(channel_id: int, channel_update: schemas.ChannelUpdate, db: Session = Depends(get_db)):
    """Обновить данные канала."""
    db_channel = crud.update_channel(db, channel_id, channel_update)
    if not db_channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    return db_channel


@app.delete("/channels/{channel_id}")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """Удалить канал."""
    if not crud.delete_channel(db, channel_id):
        raise HTTPException(status_code=404, detail="Канал не найден")
    return {"detail": "Канал удалён"}


@app.post("/channels/{channel_id}/check")
def check_channel(channel_id: int, db: Session = Depends(get_db)):
    """Запустить проверку конкретного канала вручную."""
    channel = crud.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    from app.downloader import download_channel
    success = download_channel(
        url=channel.url,
        folder_name=channel.folder_name,
        min_date=channel.min_date
    )
    crud.update_last_checked(db, channel_id)

    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при скачивании")
    return {"detail": "Канал проверен"}


@app.post("/sync")
def trigger_sync():
    """Запустить синхронизацию всех включённых каналов вручную."""
    sync_all_channels()
    return {"detail": "Синхронизация запущена"}


@app.get("/health")
def health_check(response: Response):
    """Проверка живости сервиса и доступности БД."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Ошибка проверки БД: {e}")
        response.status_code = 503
        return {
            "status": "error",
            "detail": str(e)
        }

    return {
        "status": "ok",
        "version": dv_file_version,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/status", response_model=schemas.StatusResponse)
def get_status(db: Session = Depends(get_db)):
    """Получить статус приложения."""
    channels = crud.get_channels(db)
    enabled_channels = crud.get_enabled_channels(db)

    # Подсчёт скачанных файлов (примерная оценка)
    downloaded_count = 0
    if MUSIC_DIR.exists():
        for folder in MUSIC_DIR.iterdir():
            if folder.is_dir():
                downloaded_count += len(list(folder.glob("*.mp3")))

    last_sync = None
    if channels:
        last_checked_dates = [c.last_checked for c in channels if c.last_checked]
        if last_checked_dates:
            last_sync = max(last_checked_dates)

    return schemas.StatusResponse(
        last_sync=last_sync,
        total_channels=len(channels),
        enabled_channels=len(enabled_channels),
        downloaded_count=downloaded_count
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
