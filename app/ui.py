# -*- coding: utf-8 -*-
# dxt_ui.py
dv_file_version = '261012.09'
"""Роутер для веб-интерфейса управления каналами DixTune."""

from collections import deque
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import crud, schemas
from app.database import get_db
from app.config import MUSIC_DIR, DIXTUNE_COOKIES, LOG_PATH
import app.state
from pathlib import Path

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def read_channels_ui(request: Request, db: Session = Depends(get_db)):
    """Главная страница со списком каналов."""
    channels = crud.get_channels(db)

    enabled_channels = crud.get_enabled_channels(db)
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

    status = schemas.StatusResponse(
        last_sync=last_sync,
        total_channels=len(channels),
        enabled_channels=len(enabled_channels),
        downloaded_count=downloaded_count
    )

    last_logs = crud.get_last_sync_logs(db, limit=5)
    stats = crud.get_sync_stats(db)

    # Статистика по каждому каналу
    channel_stats = {}
    for channel in channels:
        channel_dir = MUSIC_DIR / channel.folder_name
        if channel_dir.exists():
            mp3_files = list(channel_dir.glob("*.mp3"))
            file_count = len(mp3_files)
            last_file = None
            if mp3_files:
                # Сортируем по времени изменения, берём последний
                last_file_obj = max(mp3_files, key=lambda f: f.stat().st_mtime)
                last_file = last_file_obj.name
            channel_stats[channel.id] = {
                "file_count": file_count,
                "last_file": last_file
            }
        else:
            channel_stats[channel.id] = {
                "file_count": 0,
                "last_file": None
            }

    return templates.TemplateResponse(
        request=request,
        name="channels.html",
        context={
            "channels": channels,
            "status": status,
            "last_logs": last_logs,
            "stats": stats,
            "channel_stats": channel_stats,
            "is_syncing": app.state.is_syncing
        }
    )


@router.get("/channels/new")
def create_channel_form(request: Request):
    """Форма добавления нового канала."""
    return templates.TemplateResponse(
        request=request,
        name="channel_form.html",
        context={
            "channel": None,
            "action": str(request.url_for("create_channel_submit"))
        }
    )


@router.post("/channels/new")
def create_channel_submit(
        request: Request,
        url: str = Form(...),
        name: Optional[str] = Form(None),
        min_date: Optional[date] = Form(None),
        transliterate: bool = Form(False),
        db: Session = Depends(get_db)
):
    """Обработка формы добавления канала."""
    channel_create = schemas.ChannelCreate(
        url=url,
        name=name,
        min_date=min_date,
        transliterate=transliterate
    )
    try:
        crud.create_channel(db, channel_create)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url=str(request.url_for("create_channel_form")) + "?error=duplicate_url",
            status_code=303
        )
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.get("/channels/{channel_id}/edit")
def edit_channel_form(channel_id: int, request: Request, db: Session = Depends(get_db)):
    """Форма редактирования канала."""
    channel = crud.get_channel(db, channel_id)
    if not channel:
        return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="channel_form.html",
        context={
            "channel": channel,
            "action": str(request.url_for("edit_channel_submit", channel_id=channel_id))
        }
    )


@router.post("/channels/{channel_id}/edit")
def edit_channel_submit(
        channel_id: int,
        request: Request,
        url: str = Form(...),
        name: Optional[str] = Form(None),
        min_date: Optional[date] = Form(None),
        enabled: bool = Form(False),
        db: Session = Depends(get_db)
):
    """Обработка формы редактирования канала."""
    channel_update = schemas.ChannelUpdate(
        url=url,
        name=name,
        min_date=min_date,
        enabled=enabled
    )
    try:
        crud.update_channel(db, channel_id, channel_update)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url=str(request.url_for("edit_channel_form", channel_id=channel_id)) + "?error=duplicate_url",
            status_code=303
        )
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.post("/channels/{channel_id}/delete")
def delete_channel_submit(channel_id: int, request: Request, db: Session = Depends(get_db)):
    """Удаление канала (только запись из БД)."""
    crud.delete_channel(db, channel_id)
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.post("/channels/{channel_id}/check")
def check_channel_submit(channel_id: int, request: Request, db: Session = Depends(get_db)):
    """Запуск проверки конкретного канала."""
    channel = crud.get_channel(db, channel_id)
    if channel:
        from app.downloader import download_channel
        success = download_channel(
            url=channel.url,
            folder_name=channel.folder_name,
            min_date=channel.min_date,
            channel_id=channel_id
        )
        if success:
            crud.update_last_checked(db, channel_id)
            return RedirectResponse(
                url=str(request.url_for("read_channels_ui")),
                status_code=303
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("read_channels_ui")) + "?error=download_failed",
                status_code=303
            )
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.post("/sync")
def trigger_sync_submit(request: Request, background_tasks: BackgroundTasks):
    """Запуск синхронизации всех включённых каналов в фоне."""
    if app.state.is_syncing:
        return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)

    from app.scheduler import sync_all_channels
    background_tasks.add_task(sync_all_channels)
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.post("/sync/stop")
def stop_sync_submit(request: Request):
    """Остановка текущей синхронизации."""
    from app.downloader import stop_download

    app.state.stop_requested = True
    stop_download()
    return RedirectResponse(url=str(request.url_for("read_channels_ui")), status_code=303)


@router.get("/sync/status")
def get_sync_status():
    """Получить статус синхронизации в формате JSON."""
    return JSONResponse(content={"is_syncing": app.state.is_syncing})


@router.get("/settings/cookies")
def cookies_form(request: Request):
    """Страница управления cookies для YouTube."""
    cookies_path = Path(DIXTUNE_COOKIES) if DIXTUNE_COOKIES else None
    cookies_exist = cookies_path.exists() if cookies_path else False
    
    return templates.TemplateResponse(
        request=request,
        name="cookies_form.html",
        context={
            "cookies_exist": cookies_exist,
            "cookies_path": str(cookies_path) if cookies_path else "(не задан)"
        }
    )


@router.post("/settings/cookies")
def save_cookies_submit(
        request: Request,
        cookies_content: str = Form(...)
):
    """Сохранение содержимого cookies в файл."""
    if not DIXTUNE_COOKIES:
        return RedirectResponse(url=str(request.url_for("cookies_form")), status_code=303)

    cookies_path = Path(DIXTUNE_COOKIES)
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cookies_path, "w", encoding="utf-8") as f:
        f.write(cookies_content)
        
    return RedirectResponse(url=str(request.url_for("cookies_form")), status_code=303)


@router.post("/settings/cookies/delete")
def delete_cookies_submit(request: Request):
    """Удаление файла cookies."""
    if not DIXTUNE_COOKIES:
        return RedirectResponse(url=str(request.url_for("cookies_form")), status_code=303)

    cookies_path = Path(DIXTUNE_COOKIES)
    if cookies_path.exists():
        cookies_path.unlink()
        
    return RedirectResponse(url=str(request.url_for("cookies_form")), status_code=303)


@router.get("/logs")
def logs_page(request: Request, lines: int = 200):
    """Страница с логом синхронизации."""
    allowed_lines = [100, 200, 500, 1000]
    if lines not in allowed_lines:
        lines = 200

    log_lines: list[str] = []
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            log_lines = list(deque(f, maxlen=lines))

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "log_lines": log_lines,
            "current_lines": lines,
            "allowed_lines": allowed_lines
        }
    )
