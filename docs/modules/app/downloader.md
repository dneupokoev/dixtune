# downloader.py

## Назначение

Модуль отвечает за скачивание аудио с YouTube-каналов и плейлистов через внешнюю утилиту **yt-dlp**. Реализует:

- формирование и запуск команды `yt-dlp` с фиксированным набором опций (извлечение MP3 128K, SponsorBlock, архив скачанного, cookies, прокси, PO Token и т.д.);
- фильтрацию по дате публикации и типу контента (без стримов и Shorts);
- потоковый разбор stdout/stderr с логированием важных строк;
- постобработку каждого скачанного файла (сразу по `--exec after_move`, плюс пакетный fallback);
- защиту от «осиротевших» `.webm` без `.mp3` через повторный запуск с ограниченной глубиной рекурсии;
- запись результата синхронизации в БД через `crud.create_sync_log`;
- корректную остановку процесса через `SIGINT` всей группы процессов.

Версия файла: `261012.10`. Константа `MAX_RETRY_DEPTH = 3` ограничивает повторы.

## Основные функции

### `stop_download() -> None`
Останавливает текущий процесс yt-dlp. Если `app.state.current_process` ещё жив, отправляет `SIGINT` всей группе процессов (`os.killpg`), чтобы yt-dlp успел корректно завершить текущий файл. Ошибки `ProcessLookupError` / `PermissionError` логируются.

### `fix_date_tag(file_path: Path) -> None`
Приводит тег `date` в MP3 к формату `YYYY-MM`. Использует `mutagen.easyid3.EasyID3`; при значении длиной ≥ 6 символов преобразует `YYYYMMDD` → `YYYY-MM` и сохраняет. Исключения логируются.

### `clean_one_filename(file_path: Path) -> Path`
Санитайзит имя одного файла:
- схлопывает повторяющиеся `_`;
- заменяет полноширинные и «умные» символы (`？｜：＊“”‘’／＼`) на `_`;
- срезает `_` по краям;
- при коллизии имён добавляет числовой суффикс `_1`, `_2`, ...;
- при `OSError` оставляет исходное имя.

Возвращает новый (или прежний) `Path`.

### `clean_filenames(channel_dir: Path) -> None`
Применяет `clean_one_filename` ко всем `*.mp3` в директории канала. Используется как fallback, если `--exec` не сработал.

### `check_and_retry(channel_dir, url, folder_name, min_date, channel_id, recursion_depth=0) -> None`
Ищет в `channel_dir` файлы `*.webm`, для которых нет соответствующего `*.mp3`. Если такие есть — удаляет `.webm` (чтобы yt-dlp не считал видео скачанным) и рекурсивно вызывает `download_channel` с увеличенной глубиной. По достижении `MAX_RETRY_DEPTH` прекращает попытки.

### `download_channel(url, folder_name, min_date=None, channel_id=None, _depth=0) -> bool`
Главная функция модуля.

Аргументы:
- `url` — URL канала или плейлиста YouTube (авто-нормализация `/videos` для `@name`);
- `folder_name` — подпапка внутри `MUSIC_DIR`;
- `min_date` — минимальная дата публикации (`--dateafter`);
- `channel_id` — ID канала для журнала синхронизации;
- `_depth` — служебная глубина рекурсии.

Поведение:
- проверяет `app.state.stop_requested` и `_depth`;
- формирует команду `yt-dlp` (см. «Параметры yt-dlp»);
- запускает процесс в отдельной сессии (`start_new_session=True`) и сохраняет в `app.state.current_process`;
- читает stdout/stderr в двух потоках, фильтруя ключевые строки;
- после завершения: fallback-очистка имён и фикс тегов для всех `.mp3`;
- сравнивает число `.mp3` до/после (`mp3_before_count` vs `mp3_after_count`);
- при `returncode != 0` и наличии новых файлов — считает это частичным успехом;
- при `returncode != 0` и отсутствии новых файлов — пишет ошибку в журнал и вызывает `check_and_retry`;
- при `returncode == 0` — пишет успех в журнал;
- ловит `FileNotFoundError` (нет yt-dlp/ffmpeg) и прочие исключения, логируя их.

Возвращает `True` при успехе (в т.ч. частичном), иначе `False`.

## Параметры yt-dlp

- Аудио: `-x --audio-format mp3 --audio-quality 128K`;
- SponsorBlock: удаление `default` через `https://api.sponsor.ajay.app`;
- архив: `--download-archive ARCHIVE_FILE`, `--no-overwrites`, `--ignore-errors`;
- шаблон имени: `%(title)s.%(ext)s` внутри директории канала;
- фильтры: `--dateafter min_date`, `--lazy-playlist`, `--playlist-end 10`, `--match-filter "!is_live & duration > 60"`;
- совместимость: `--windows-filenames`;
- сеть: `--proxy DIXTUNE_PROXY`, `--sleep-requests 1`, `--cookies` при наличии файла;
- метаданные: `--embed-metadata` + серия `--parse-metadata` / `--replace-in-metadata` (album_artist, album = "YouTube", artist = uploader);
- обход блокировок: `--extractor-args youtube:player_client=mweb`, `youtubepot-bgutilhttp:base_url=...`, `--extractor-retries 3`, `--retries 3`, `--remote-components ejs:github`;
- постобработка: `--exec "after_move:python -m app.postprocess %(filepath)q"`.

## Зависимости

Стандартная библиотека:
- `subprocess`, `logging`, `re`, `os`, `signal`, `threading`;
- `pathlib.Path`, `datetime.date`, `typing.Optional`.

Сторонние:
- `mutagen.easyid3.EasyID3` — правка ID3-тегов.

Внутренние модули проекта:
- `app.config`: `MUSIC_DIR`, `ARCHIVE_FILE`, `DIXTUNE_PROXY`, `DIXTUNE_COOKIES`, `DIXTUNE_POT_PROVIDER_URL`;
- `app.utils`: `ensure_directory`;
- `app.database`: `SessionLocal`;
- `app.crud`: `create_sync_log` (пишет результат синхронизации);
- `app.state`: `current_process`, `stop_requested` (импортируются именами, но внутри используются как атрибуты модуля `app.state`; это принципиально для работы `stop_download` и проверки остановки).

Внешние утилиты: **yt-dlp**, **ffmpeg**, а также модуль `app.postprocess` (запускается как `python -m app.postprocess`).

## Использование в проекте

- `download_channel(...)` вызывается из логики синхронизации каналов (sync scheduler / API-эндпоинт запуска загрузки). Внутри модуля — рекурсивно из `check_and_retry`.
- `stop_download()` вызывается из слоя управления (API/UI), когда пользователь инициирует остановку синхронизации; опирается на `app.state.current_process`.
- Флаг `app.state.stop_requested` выставляется снаружи и проверяется в начале `download_channel`.
- `fix_date_tag` и `clean_one_filename` / `clean_filenames` — служебные, но открыты для использования другими модулями (например, из `app.postprocess` или утилит обслуживания библиотеки).
- Все результаты скачивания фиксируются в БД через `crud.create_sync_log(db, channel_id, status, message)` — статусы `"success"` / `"error"` читаются веб-интерфейсом журнала синхронизации.