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
- **Обход блокировок YouTube через ByeDPI** (опционально, для серверов в России).
- **Поддержка Deno** для решения n challenge (автоматически устанавливается в Docker).
- **Поддержка cookies** для авторизации на YouTube (опционально).

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

### Шаг 2: Создайте файл `.env`

Файл `.env` не хранится в репозитории (он в `.gitignore`). Создайте его из шаблона:

```bash
cd /opt/dix/dixtune
cp .env.example .env
nano .env
```

Заполните файл своими значениями:

```env
# Логин и пароль для Basic Auth
DIXTUNE_USERNAME=admin
DIXTUNE_PASSWORD=ваш_надёжный_пароль

# Путь к папке с музыкой (куда скачивать аудио)
DIXTUNE_MUSIC_DIR=/media/music/dixtune

# Путь к папке с данными (БД, логи, архив yt-dlp)
DIXTUNE_DATA_DIR=/opt/dix/dixtune/data

# Интервал синхронизации в часах
SYNC_INTERVAL_HOURS=6

# Часовой пояс
TZ=Europe/Moscow

# Путь, если приложение за прокси с подпутём (например, /dixtune)
# Оставьте пустым для локального запуска
DIXTUNE_ROOT_PATH=/dixtune

# Прокси для yt-dlp (если YouTube блокируется)
# Если ByeDPI используется, укажите socks5://byedpi:1081
# Если прокси не нужен, оставьте пустым
DIXTUNE_PROXY=

# Путь к файлу cookies для yt-dlp (например, /data/cookies.txt)
# Оставьте пустым, если cookies не нужны
DIXTUNE_COOKIES=
```

Примеры путей к музыке:
- **Linux**: `/media/music/dixtune`
- **macOS**: `/Users/user/Music`
- **Windows**: `D:/Music`

> **Важно:** для продакшена обязательно укажите `DIXTUNE_ROOT_PATH=/dixtune`, если приложение работает за Nginx с подпутём. Для локального запуска оставьте пустым.

### Шаг 3: Проверьте `docker-compose.yml`

Файл `docker-compose.yml` уже настроен на использование переменных из `.env`:

```yaml
services:
  dixtune:
    image: ghcr.io/dneupokoev/dixtune:latest
    container_name: dixtune
    restart: unless-stopped
    ports:
      - "8020:8000"
    volumes:
      - ${DIXTUNE_MUSIC_DIR}:/media/music/dixtune
      - ${DIXTUNE_DATA_DIR}:/data
    environment:
      - DIXTUNE_DATA_DIR=/data
      - DIXTUNE_MUSIC_DIR=/media/music/dixtune
      - SYNC_INTERVAL_HOURS=${SYNC_INTERVAL_HOURS}
      - TZ=${TZ}
      - DIXTUNE_USERNAME=${DIXTUNE_USERNAME}
      - DIXTUNE_PASSWORD=${DIXTUNE_PASSWORD}
      - DIXTUNE_ROOT_PATH=${DIXTUNE_ROOT_PATH}
      - DIXTUNE_PROXY=${DIXTUNE_PROXY}
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Шаг 4: Запустите

```bash
cd /opt/dix/dixtune
sudo docker compose up -d
```

### Шаг 5: Откройте в браузере

Перейдите по адресу: [http://localhost:8020/ui](http://localhost:8020/ui)

Введите логин (`admin`) и пароль из `.env`.

### Что дальше?

1. Добавьте канал через веб-интерфейс.
2. Нажмите «Синхронизировать все» — DixTune начнёт скачивать аудио.
3. Файлы появятся в `${DIXTUNE_MUSIC_DIR}/<имя_канала>/`.

### Обход блокировок YouTube (ByeDPI)

Если ваш сервер находится в России и провайдер блокирует YouTube на уровне DPI, `yt-dlp` будет падать с ошибкой `SSL handshake timed out`. Для обхода используется **ByeDPI** — локальный SOCKS5-прокси, который маскирует TLS-рукопожатие.

**1. Добавьте сервис ByeDPI в `docker-compose.yml`:**

```yaml
services:
  dixtune:
    # ... (см. выше)
    depends_on:
      - byedpi

  byedpi:
    image: andromedi4/byedpi-orchestrator:latest
    container_name: byedpi
    restart: unless-stopped
    volumes:
      - ./byedpi-data:/app
      - ./byedpi-config:/opt/orchestrator/config
    ports:
      - "1080:1080"
```

**2. В `.env` укажите прокси:**

```env
DIXTUNE_PROXY=socks5://byedpi:1081
```

> **Важно:** ByeDPI слушает порт **1081** внутри контейнера, а не 1080. Порт 1080 — это внешний проброс.

**3. Перезапустите:**

```bash
cd /opt/dix/dixtune
sudo docker compose down
sudo docker compose up -d
```

**4. Дождитесь, пока ByeDPI выберет стратегию.** Это занимает 1–2 минуты. В логах появится строка:
```
[orchestrator] global | '...' => score=0.799 avail=0.90 median=0.589
```

**5. Проверьте логи DixTune:**
```bash
sudo docker compose logs -f dixtune
```

Если `yt-dlp` начал скачивать — всё работает.

### Deno и n challenge

Для решения n challenge (защита YouTube от ботов) DixTune использует **Deno**. Deno автоматически устанавливается в Docker-образе, поэтому дополнительных действий не требуется.

Также `yt-dlp` использует флаг `--remote-components ejs:github` для загрузки скриптов-решателей с GitHub. Это происходит автоматически при первом запуске (скрипты кешируются).

### Обновление

Чтобы получить последнюю версию приложения, выполните на сервере:

```bash
cd /opt/dix/dixtune
sudo git pull
sudo docker compose pull
sudo docker compose down
sudo docker compose up -d
```

> Так как все настройки в `.env`, а `docker-compose.yml` не меняется — `git pull` не вызовет конфликтов.

### Удаление

```bash
cd /opt/dix/dixtune
sudo docker compose down
cd /opt/dix
sudo rm -rf dixtune
```

*Примечание: папка с данными (`${DIXTUNE_DATA_DIR}`) и музыка останутся на диске, если вы их не удалите.*

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
  -e DIXTUNE_ROOT_PATH= \
  -e DIXTUNE_PROXY= \
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
├── byedpi-data/            # Данные ByeDPI (в .gitignore)
├── byedpi-config/          # Конфиги ByeDPI (в .gitignore)
├── .github/workflows/      # CI/CD
│   └── deploy.yml          # Сборка образа и публикация в GHCR
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
| `DIXTUNE_PROXY` | Прокси для yt-dlp (например, `socks5://byedpi:1081`) | `` (пусто) |
| `DIXTUNE_COOKIES` | Путь к файлу cookies для yt-dlp | `` (пусто) |

## Аутентификация

Все эндпоинты, кроме `/health`, требуют Basic Auth.
Логин и пароль задаются через переменные окружения `DIXTUNE_USERNAME` и `DIXTUNE_PASSWORD`.

Пример запроса с аутентификацией:
```bash
curl -u admin:admin123 http://localhost:8020/status
```

### Как сменить пароль

Пароль задаётся через `.env`. Измените его и перезапустите контейнер:

1. Откройте `.env`:
   ```bash
   nano /opt/dix/dixtune/.env
   ```

2. Измените `DIXTUNE_PASSWORD`:
   ```env
   DIXTUNE_PASSWORD=ваш_новый_пароль
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
