# -*- coding: utf-8 -*-
# dxt_ui.py
dv_file_version = '261010.02'
"""Роутер для веб-интерфейса управления каналами DixTune."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.config import MUSIC_DIR

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

    return templates.TemplateResponse(
        request=request,
        name="channels.html",
        context={
            "channels": channels,
            "status": status
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
            "action": "/ui/channels/new"
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
    crud.create_channel(db, channel_create)
    return RedirectResponse(url="/ui/", status_code=303)


@router.get("/channels/{channel_id}/edit")
def edit_channel_form(channel_id: int, request: Request, db: Session = Depends(get_db)):
    """Форма редактирования канала."""
    channel = crud.get_channel(db, channel_id)
    if not channel:
        return RedirectResponse(url="/ui/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="channel_form.html",
        context={
            "channel": channel,
            "action": f"/ui/channels/{channel_id}/edit"
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
    crud.update_channel(db, channel_id, channel_update)
    return RedirectResponse(url="/ui/", status_code=303)


@router.post("/channels/{channel_id}/delete")
def delete_channel_submit(channel_id: int, db: Session = Depends(get_db)):
    """Удаление канала (только запись из БД)."""
    crud.delete_channel(db, channel_id)
    return RedirectResponse(url="/ui/", status_code=303)


@router.post("/channels/{channel_id}/check")
def check_channel_submit(channel_id: int, db: Session = Depends(get_db)):
    """Запуск проверки конкретного канала."""
    channel = crud.get_channel(db, channel_id)
    if channel:
        from app.downloader import download_channel
        download_channel(
            url=channel.url,
            folder_name=channel.folder_name,
            min_date=channel.min_date
        )
        crud.update_last_checked(db, channel_id)
    return RedirectResponse(url="/ui/", status_code=303)


@router.post("/sync")
def trigger_sync_submit():
    """Запуск синхронизации всех включённых каналов."""
    from app.scheduler import sync_all_channels
    sync_all_channels()
    return RedirectResponse(url="/ui/", status_code=303)
