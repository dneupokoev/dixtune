# DixTune

[![GitHub Actions](https://github.com/dneupokoev/dixtune/actions/workflows/deploy.yml/badge.svg)](https://github.com/dneupokoev/dixtune/actions)
[![GitHub release](https://img.shields.io/github/v/release/dneupokoev/dixtune)](https://github.com/dneupokoev/dixtune/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

DixTune — автоматический загрузчик аудио с YouTube-каналов. Скачивает аудио, вырезает рекламные вставки через SponsorBlock и предоставляет веб-интерфейс для управления каналами.

## Возможности

- Скачивание аудио с YouTube-каналов (музыка, подкасты, лекции).
- Вырезание рекламных вставок через SponsorBlock.
- Веб-интерфейс для управления каналами.
- Автоматическая синхронизация (APScheduler, каждые 6 часов).
- Ограничение по дате (не качать старое).
- Опциональная транслитерация имён папок.
- Ротация логов.
- REST API + Swagger.
- Basic Auth для защиты от несанкционированного доступа.

## Быстрый старт (Prod)

Для установки нужны только **Docker** и **Git**. Python и другие зависимости устанавливать не нужно — всё уже внутри образа.

### Шаг 1: Клонируйте репозиторий в `/opt/dix/dixtune`

```bash
sudo mkdir -p /opt/dix
cd /opt/dix
sudo git clone https://github.com/dneupokoev/dixtune.git
cd dixtune
sudo chown -R $USER:$USER /opt/dix/dixtune
```

> **Примечание:** `chown` нужен, чтобы вы могли редактировать файлы без `sudo`. Если вы работаете от root, этот шаг можно пропустить.

### Шаг 2: Отредактируйте `docker-compose.yml`

Откройте файл `docker-compose.yml` и замените путь к музыке и пароль на свои:

```yaml
services:
  dixtune:
    image: ghcr.io/dneupokoev/dixtune:latest
    container_name: dixtune
    restart: unless-stopped
    ports:
      - "8020:8000"
    volumes:
      - /путь/к/вашей/музыке:/media/music/dixtune   # <-- замените на свой путь
      - /opt/dix/dixtune/data:/data              # <-- данные будут здесь
    environment:
      - DIXTUNE_DATA_DIR=/data
      - DIXTUNE_MUSIC_DIR=/media/music/dixtune
      - SYNC_INTERVAL_HOURS=6
      - TZ=Europe/Moscow
      - DIXTUNE_USERNAME=admin
      - DIXTUNE_PASSWORD=admin123   # <-- замените на свой пароль
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Примеры путей к музыке:
- **Linux**: `/media/music/dixtune`
- **macOS**: `/Users/user/Music`
- **Windows**: `D:/Music`

### Шаг 3: Запустите

```bash
cd /opt/dix/dixtune
sudo docker compose up -d
```

### Шаг 4: Откройте в браузере

Перейдите по адресу: [http://localhost:8020/ui](http://localhost:8020/ui)

Введите логин (`admin`) и пароль (`admin123` или тот, который вы указали в шаге 2).

### Что дальше?

1. Добавьте канал через веб-интерфейс.
2. Нажмите «Синхронизировать все» — DixTune начнёт скачивать аудио.
3. Файлы появятся в `/media/music/dixtune/<имя_канала>/`.

### Обновление

Чтобы получить последнюю версию приложения:

```bash
cd /opt/dix/dixtune
sudo git pull
sudo docker compose pull
sudo docker compose up -d
```

### Удаление

```bash
cd /opt/dix/dixtune
sudo docker compose down
cd /opt/dix
sudo rm -rf dixtune
```

*Примечание: папка с данными (`/opt/dix/dixtune/data`) и музыка останутся на диске, если вы их не удалите.*

### Docker Run (для опытных пользователей)

Замените `/path/to/music` на реальный путь к вашей папке с музыкой.

```bash
docker run -d \
  --name dixtune \
  -p 8020:8000 \
  -v /path/to/music:/media/music/dixtune \
  -v /opt/dix/dixtune/data:/data \
  -e DIXTUNE_USERNAME=admin \
  -e DIXTUNE_PASSWORD=admin123 \
  ghcr.io/dneupokoev/dixtune:latest
```

## Локальная разработка (без Docker)

1. Клонируйте репозиторий:

```bash
cd /opt/dix
git clone https://github.com/dneupokoev/dixtune.git
cd dixtune
```

2. Установите зависимости:

```bash
pipenv install
```

3. Запустите сервер:

```bash
pipenv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Откройте веб-интерфейс: [http://localhost:8000/ui](http://localhost:8000/ui)

## Структура проекта

```text
dixtune/
├── app/                    # Исходный код
│   ├── __init__.py         # Пакет DixTune
│   ├── main.py             # Точка входа FastAPI, настройка логирования, роутеры
│   ├── config.py           # Настройки (пути, интервалы), чтение из env
│   ├── database.py         # Подключение к SQLite (SQLAlchemy)
│   ├── models.py           # Модель Channel (url, name, folder_name, min_date, enabled, transliterate, last_checked)
│   ├── schemas.py          # Pydantic-схемы для API
│   ├── crud.py             # Операции CRUD для работы с БД
│   ├── downloader.py       # Логика скачивания через yt-dlp
│   ├── scheduler.py        # Планировщик APScheduler
│   ├── ui.py               # Роутер для веб-интерфейса (/ui)
│   ├── utils.py            # Вспомогательные функции (sanitize_filename, transliterate, ensure_directory)
│   ├── static/             # CSS, favicon
│   │   └── style.css
│   └── templates/          # Jinja2-шаблоны
│       ├── base.html       # Базовый шаблон
│       ├── channels.html   # Список каналов
│       └── channel_form.html # Форма добавления/редактирования
├── data/                   # БД, логи, архив yt-dlp (в .gitignore)
├── .github/workflows/      # CI/CD
│   └── deploy.yml          # Сборка образа + деплой на сервер
├── deploy.sh               # Скрипт деплоя на прод
├── Dockerfile              # Сборка образа
├── docker-compose.yml      # Запуск на проде
├── .env.example            # Пример переменных окружения
├── .gitignore
├── LICENSE
├── Pipfile                 # Зависимости для разработки (pipenv)
├── Pipfile.lock
├── README.md
└── requirements.txt        # Зависимости для Docker
```

## Описание API

- `GET /channels` — список каналов
- `POST /channels` — добавить канал
- `PUT /channels/{id}` — редактировать
- `DELETE /channels/{id}` — удалить
- `POST /channels/{id}/check` — проверить канал вручную
- `POST /sync` — синхронизировать все каналы
- `GET /status` — статус приложения
- `GET /health` — проверка живости сервиса (без аутентификации)
- `GET /docs` — Swagger
- `GET /ui` — веб-интерфейс

## Переменные окружения

| Переменная | Описание | По умолчанию |
| :--- | :--- | :--- |
| `DIXTUNE_DATA_DIR` | Путь к данным (БД, логи) | `./data` |
| `DIXTUNE_MUSIC_DIR` | Путь к музыке | `/media/music/dixtune` |
| `SYNC_INTERVAL_HOURS` | Интервал синхронизации (часов) | `6` |
| `TZ` | Часовой пояс | `Europe/Moscow` |
| `DIXTUNE_USERNAME` | Логин для Basic Auth | `admin` |
| `DIXTUNE_PASSWORD` | Пароль для Basic Auth | `admin123` |
| `DIXTUNE_ROOT_PATH` | Путь, если приложение за прокси с подпутём | `` (пусто) |

## Аутентификация

Все эндпоинты, кроме `/health`, требуют Basic Auth.
Логин и пароль задаются через переменные окружения `DIXTUNE_USERNAME` и `DIXTUNE_PASSWORD`.

Пример запроса с аутентификацией:
```bash
curl -u admin:admin123 http://localhost:8020/status
```

### Как сменить пароль

Пароль задаётся через переменные окружения при запуске контейнера. Есть два способа:

**Способ 1: Через `docker-compose.yml`**

1. Откройте `docker-compose.yml`.
2. В секции `environment` измените строки:
   ```yaml
   environment:
     - DIXTUNE_USERNAME=admin
     - DIXTUNE_PASSWORD=ваш_новый_пароль
   ```
3. Перезапустите контейнер:
   ```bash
   cd /opt/dix/dixtune
   sudo docker compose down
   sudo docker compose up -d
   ```

**Способ 2: Через `.env` (рекомендуется)**

1. Создайте файл `.env` рядом с `docker-compose.yml`:
   ```env
   DIXTUNE_USERNAME=admin
   DIXTUNE_PASSWORD=ваш_новый_пароль
   ```

2. В `docker-compose.yml` используйте переменные из `.env`:
   ```yaml
   environment:
     - DIXTUNE_USERNAME=${DIXTUNE_USERNAME}
     - DIXTUNE_PASSWORD=${DIXTUNE_PASSWORD}
   ```

3. Перезапустите:
   ```bash
   cd /opt/dix/dixtune
   sudo docker compose down
   sudo docker compose up -d
   ```

**Важно:** после смены пароля все активные сессии Basic Auth сбросятся — браузер снова запросит логин и пароль.

## Как вносить правки (для разработчиков и LLM)

- Все Python-файлы имеют заголовок: кодировка, имя файла, версия (`dv_file_version`), docstring.
- При добавлении нового поля в модель `Channel` — обновить `models.py`, `schemas.py`, `crud.py`, `ui.py`, шаблоны.
- При изменении API — обновить README (раздел API).
- Логика скачивания — в `downloader.py` (флаги yt-dlp).
- Расписание — в `scheduler.py`.
- UI — в `ui.py` и шаблонах.
- Перед коммитом: проверить, что приложение запускается локально.

## Лицензия

Этот проект распространяется под лицензией MIT. Подробности — в файле [LICENSE](LICENSE).

## Автор

Дмитрий Неупокоев (Dmitriy Neupokoev)

## Ссылка на репозиторий

[https://github.com/dneupokoev/dixtune](https://github.com/dneupokoev/dixtune)
