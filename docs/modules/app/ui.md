# dxt_ui.py

## Назначение

Модуль реализует веб-интерфейс управления каналами DixTune через FastAPI-роутер с префиксом `/ui`.

Основные возможности:
- просмотр списка каналов, статистики и последних логов;
- создание, редактирование и удаление каналов;
- запуск проверки отдельного канала;
- запуск и остановка общей синхронизации;
- получение JSON-статуса синхронизации;
- управление файлом cookies для YouTube;
- просмотр хвоста лог-файла.

Модуль возвращает HTML-страницы через `Jinja2Templates`, выполняет редиректы после POST-форм и предоставляет один JSON-эндпоинт.

## Глобальные объекты

- `router` — `APIRouter(prefix="/ui", tags=["ui"])`.
- `templates` — `Jinja2Templates(directory="app/templates")`.
- `dv_file_version` — строковая версия файла.

## Основные функции

| Функция | Метод и путь | Аргументы | Назначение |
|---|---|---|---|
| `read_channels_ui` | `GET /ui/` | `request: Request`, `db: Session = Depends(get_db)` | Главная страница со списком каналов, общим статусом, последними логами, статистикой и информацией о синхронизации. |
| `create_channel_form` | `GET /ui/channels/new` | `request: Request` | Форма добавления нового канала. |
| `create_channel_submit` | `POST /ui/channels/new` | `request`, `url: str = Form(...)`, `name: Optional[str] = Form(None)`, `min_date: Optional[date] = Form(None)`, `transliterate: bool = Form(False)`, `db` | Создание канала. При `IntegrityError` откатывает транзакцию и редиректит с `?error=duplicate_url`. |
| `edit_channel_form` | `GET /ui/channels/{channel_id}/edit` | `channel_id: int`, `request`, `db` | Форма редактирования канала. Если канал не найден — редирект на главную. |
| `edit_channel_submit` | `POST /ui/channels/{channel_id}/edit` | `channel_id`, `request`, `url`, `name`, `min_date`, `enabled`, `db` | Обновление канала. При `IntegrityError` откатывает транзакцию и редиректит с `?error=duplicate_url`. |
| `delete_channel_submit` | `POST /ui/channels/{channel_id}/delete` | `channel_id`, `request`, `db` | Удаляет только запись канала из БД. |
| `check_channel_submit` | `POST /ui/channels/{channel_id}/check` | `channel_id`, `request`, `db` | Запускает проверку конкретного канала через `app.downloader.download_channel`. При успехе обновляет `last_checked`. |
| `trigger_sync_submit` | `POST /ui/sync` | `request`, `background_tasks: BackgroundTasks` | Запускает синхронизацию всех включённых каналов в фоне через `app.scheduler.sync_all_channels`, если синхронизация уже не идёт. |
| `stop_sync_submit` | `POST /ui/sync/stop` | `request` | Устанавливает `app.state.stop_requested = True` и вызывает `app.downloader.stop_download()`. |
| `get_sync_status` | `GET /ui/sync/status` | — | Возвращает JSON `{"is_syncing": ...}`. |
| `cookies_form` | `GET /ui/settings/cookies` | `request` | Страница управления cookies. Показывает наличие файла и путь. |
| `save_cookies_submit` | `POST /ui/settings/cookies` | `request`, `cookies_content: str = Form(...)` | Сохраняет переданное содержимое в файл cookies, создавая родительские директории. |
| `delete_cookies_submit` | `POST /ui/settings/cookies/delete` | `request` | Удаляет файл cookies, если он существует. |
| `logs_page` | `GET /ui/logs` | `request`, `lines: int = 200` | Показывает последние строки лога. Допустимые значения `lines`: `100`, `200`, `500`, `1000`; иначе используется `200`. |

## Зависимости

Импорты из стандартной библиотеки и сторонних пакетов:
- `collections.deque` — чтение хвоста лог-файла;
- `datetime.date` — тип поля `min_date`;
- `typing.Optional` — необязательные параметры форм;
- `pathlib.Path` — работа с путями cookies;
- `fastapi.APIRouter`, `Depends`, `Request`, `Form`, `BackgroundTasks` — маршрутизация и обработка форм;
- `fastapi.responses.RedirectResponse`, `JSONResponse` — ответы;
- `fastapi.templating.Jinja2Templates` — рендеринг HTML;
- `sqlalchemy.orm.Session` — сессия БД;
- `sqlalchemy.exc.IntegrityError` — обработка конфликтов уникальности.

Импорты проекта:
- `app.crud` — операции с каналами, логами и статистикой;
- `app.schemas` — `StatusResponse`, `ChannelCreate`, `ChannelUpdate`;
- `app.database.get_db` — зависимость сессии БД;
- `app.config.MUSIC_DIR`, `DIXTUNE_COOKIES`, `LOG_PATH` — пути к музыке, cookies и логам;
- `app.state` — общее состояние приложения, в частности `is_syncing` и `stop_requested`.

Ленивые импорты внутри функций:
- `app.downloader.download_channel`;
- `app.downloader.stop_download`;
- `app.scheduler.sync_all_channels`.

## Использование другими модулями

Судя по структуре, модуль предназначен для подключения `router` в основное FastAPI-приложение. Другие части проекта могут:
- использовать имена эндпоинтов через `request.url_for(...)`;
- изменять и читать `app.state.is_syncing`;
- устанавливать `app.state.stop_requested`;
- вызывать `sync_all_channels`, `download_channel` и `stop_download` из соответствующих модулей.

HTML-шаблоны, используемые модулем:
- `channels.html`;
- `channel_form.html`;
- `cookies_form.html`;
- `logs.html`.

## Особенности и ограничения

- Удаление канала удаляет только запись из БД, но не скачанные файлы.
- Проверка отдельного канала в `check_channel_submit` выполняется синхронно в рамках запроса.
- Общая синхронизация запускается через `BackgroundTasks`.
- Повторный запуск синхронизации игнорируется, если `app.state.is_syncing` уже истинно.
- Остановка синхронизации выставляет флаг `stop_requested` и вызывает `stop_download()`.
- Работа с cookies выполняется только при заданном `DIXTUNE_COOKIES`.
- Страница логов читает только хвост файла и ограничивает число строк допустимыми значениями.