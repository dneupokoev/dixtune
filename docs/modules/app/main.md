# app/main.py — точка входа FastAPI-приложения DixTune

## Назначение модуля

Модуль является главной точкой входа приложения **DixTune** — автоматического загрузчика аудио с YouTube-каналов. Здесь:

- создаётся FastAPI-приложение `app`;
- настраивается логирование в файл с ротацией и в консоль;
- создаются таблицы БД через SQLAlchemy `Base.metadata.create_all`;
- запускается и останавливается планировщик в `lifespan`;
- подключается Basic Auth middleware;
- монтируется статика `/static` и подключается UI-роутер;
- регистрируются REST-эндпоинты для управления каналами, ручной синхронизации, health-check и статуса;
- выполняется редирект с `/` на веб-интерфейс.

Версия файла/приложения хранится в переменной `dv_file_version = '261012.03'` и возвращается в `/health`.

## Основные объекты и функции

### Глобальные настройки и инициализация

- `dv_file_version` — строковая версия, отдаётся в `/health`.
- `logger` — логгер `DixTune`.
- `app` — экземпляр `FastAPI` с названием `DixTune`, описанием и `root_path=DIXTUNE_ROOT_PATH`.
- Логирование настраивается через `RotatingFileHandler`: файл `LOG_PATH`, максимум 10 МБ, 5 бэкапов, кодировка UTF-8, плюс вывод в `StreamHandler`.
- Папка для логов создаётся заранее через `ensure_directory(LOG_PATH.parent)`.
- Таблицы БД создаются при импорте модуля.

### `lifespan(app: FastAPI)`

Асинхронный контекстный менеджер жизненного цикла приложения.

- При старте вызывает `start_scheduler()`.
- Логирует запуск приложения.
- После завершения работы вызывает `stop_scheduler()`.
- Логирует остановку.

Аргумент:
- `app` — экземпляр FastAPI.

### `auth_middleware(request: Request, call_next)`

HTTP-middleware для Basic Auth.

- Исключения без авторизации: `/health`, `/favicon.ico`, `/`.
- Учитывает `DIXTUNE_ROOT_PATH`: если путь начинается с root_path, префикс отбрасывается перед проверкой.
- Проверяет наличие заголовка `Authorization: Basic ...`.
- Декодирует Basic Auth, разделяет логин и пароль по первому `:`.
- Сравнивает логин и пароль с `DIXTUNE_USERNAME` и `DIXTUNE_PASSWORD` через `secrets.compare_digest`.
- При ошибке возвращает `401` с `WWW-Authenticate: Basic`.
- При успехе передаёт запрос дальше через `call_next`.

### `root_redirect(request: Request)`

Редирект с `/` на UI-страницу каналов.

- Аргумент: `request`.
- Использует `request.url_for("read_channels_ui")`.
- Возвращает `RedirectResponse` со статусом `307`.

### `read_channels(db: Session = Depends(get_db))`

Возвращает список всех каналов.

- Аргумент: сессия БД.
- Вызывает `crud.get_channels(db)`.
- Ответ соответствует `list[schemas.ChannelResponse]`.

### `create_channel(channel: schemas.ChannelCreate, db: Session = Depends(get_db))`

Создаёт новый канал.

- Аргументы: данные канала `ChannelCreate`, сессия БД.
- Вызывает `crud.create_channel`.
- При `IntegrityError` откатывает транзакцию и возвращает `409`, если канал с таким URL уже существует.

### `update_channel(channel_id: int, channel_update: schemas.ChannelUpdate, db: Session = Depends(get_db))`

Обновляет данные канала.

- Аргументы: ID канала, данные обновления, сессия БД.
- Вызывает `crud.update_channel`.
- При `IntegrityError` откатывает транзакцию и возвращает `409`.
- Если канал не найден — `404`.

### `delete_channel(channel_id: int, db: Session = Depends(get_db))`

Удаляет канал.

- Аргументы: ID канала, сессия БД.
- Вызывает `crud.delete_channel`.
- Если канал не найден — `404`.
- При успехе возвращает `{"detail": "Канал удалён"}`.

### `check_channel(channel_id: int, db: Session = Depends(get_db))`

Запускает ручную проверку конкретного канала.

- Аргументы: ID канала, сессия БД.
- Получает канал через `crud.get_channel`; если не найден — `404`.
- Импортирует `download_channel` из `app.downloader` внутри функции.
- Вызывает `download_channel` с `url`, `folder_name`, `min_date`, `channel_id`.
- При успехе обновляет `last_checked` через `crud.update_last_checked`.
- При ошибке скачивания возвращает `500`.

### `trigger_sync()`

Запускает синхронизацию всех включённых каналов вручную.

- Вызывает `sync_all_channels()`.
- Возвращает `{"detail": "Синхронизация запущена"}`.
- Важно: вызов выполняется синхронно в рамках запроса, ответ формируется после завершения `sync_all_channels()`.

### `health_check(response: Response)`

Проверка живости сервиса и доступности БД.

- Аргумент: `response` для установки статуса.
- Выполняет `SELECT 1` через `engine.connect()`.
- При ошибке БД логирует ошибку, устанавливает `503` и возвращает `status: error`, `detail`.
- При успехе возвращает `status: ok`, `version` и UTC-время в ISO-формате.

### `get_status(db: Session = Depends(get_db))`

Возвращает статус приложения.

- Аргументы: сессия БД.
- Получает все и включённые каналы через `crud`.
- Считает количество `.mp3` в подпапках `MUSIC_DIR` как примерную оценку скачанных файлов.
- Определяет `last_sync` как максимальный `last_checked` среди каналов.
- Возвращает `schemas.StatusResponse`: `last_sync`, `total_channels`, `enabled_channels`, `downloaded_count`.

## HTTP-эндпоинты

- `GET /` — редирект на `read_channels_ui`.
- `GET /channels` — список каналов.
- `POST /channels` — создать канал.
- `PUT /channels/{channel_id}` — обновить канал.
- `DELETE /channels/{channel_id}` — удалить канал.
- `POST /channels/{channel_id}/check` — проверить канал вручную.
- `POST /sync` — запустить синхронизацию всех включённых каналов.
- `GET /health` — health-check без Basic Auth.
- `GET /status` — статус приложения.
- `/static` — смонтированная статика из `app/static`.
- UI-роутер подключается через `app.include_router(ui_router)`.

Все эндпоинты, кроме `/health`, `/favicon.ico` и `/`, защищены Basic Auth middleware.

## Зависимости от других модулей

### Внешние библиотеки

- `fastapi` — `FastAPI`, `Depends`, `HTTPException`, `Request`, `Response`.
- `fastapi.staticfiles.StaticFiles` — раздача статики.
- `fastapi.responses.RedirectResponse` — редиректы.
- `sqlalchemy` — `text`, `Session`, `IntegrityError`.
- `uvicorn` — запуск приложения в блоке `__main__`.

### Стандартная библиотека

- `base64` — декодирование Basic Auth.
- `logging`, `logging.handlers` — логирование.
- `secrets` — безопасное сравнение логина и пароля.
- `contextlib.asynccontextmanager` — lifespan.
- `datetime`, `timezone` — время в health-check.

### Внутренние модули проекта

- `app.models` — импортируется для регистрации моделей перед `create_all`.
- `app.schemas` — Pydantic-схемы ответов и запросов.
- `app.crud` — операции с каналами и статусами.
- `app.database` — `engine`, `Base`, `get_db`.
- `app.config` — `MUSIC_DIR`, `LOG_PATH`, `DIXTUNE_USERNAME`, `DIXTUNE_PASSWORD`, `DIXTUNE_ROOT_PATH`.
- `app.scheduler` — `start_scheduler`, `stop_scheduler`, `sync_all_channels`.
- `app.utils` — `ensure_directory`.
- `app.ui` — `router` с UI-маршрутами.
- `app.downloader.download_channel` — динамический импорт внутри `check_channel`.

## Использование модуля другими частями проекта

- Модуль является composition root: именно здесь собираются конфигурация, БД, роутеры, middleware, планировщик и UI.
- ASGI-сервер запускает приложение как `app.main:app`.
- В блоке `if __name__ == "__main__"` используется `uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)`.
- `app.ui.router` подключается к основному приложению и предоставляет обработчик `read_channels_ui`, на который ведёт редирект с `/`.
- Планировщик из `app.scheduler` управляется через lifespan и ручной эндпоинт `/sync`.
- Загрузка конкретного канала делегируется в `app.downloader.download_channel`.
- Работа с каналами и статусами делегируется в `app.crud`, схемы ответов — в `app.schemas`.

## Особенности и ограничения

- Basic Auth применяется ко всем путям, кроме `/health`, `/favicon.ico` и `/`.
- При использовании `DIXTUNE_ROOT_PATH` middleware корректно отбрасывает префикс root_path перед проверкой исключений.
- `/sync` вызывает `sync_all_channels()` синхронно, поэтому длительная синхронизация может удерживать HTTP-запрос.
- `/status` оценивает количество скачанных файлов сканированием `MUSIC_DIR` по подпапкам и файлам `*.mp3`.
- Таблицы БД создаются при импорте модуля, до старта lifespan.
- Логи пишутся в `LOG_PATH` с ротацией до 5 архивов по 10 МБ.
- Существующая документация по модулю отсутствовала, поэтому сохранённых разделов нет.