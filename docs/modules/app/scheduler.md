# `app/scheduler.py`

## Назначение
Модуль реализует фоновый планировщик периодической синхронизации YouTube-каналов на базе `APScheduler`. Синхронизация запускается через случайный интервал в заданном диапазоне, а следующая задача планируется после завершения текущей.

Версия файла: `261012.07`.

## Основные функции и объекты

### `scheduler`
Глобальный экземпляр `BackgroundScheduler` с часовым поясом из переменной окружения `TZ` (по умолчанию `Europe/Moscow`).

### `schedule_next_sync() -> None`
Планирует следующую синхронизацию:
- выбирает случайное количество часов между `SYNC_INTERVAL_HOURS_MIN` и `SYNC_INTERVAL_HOURS_MAX`;
- вычисляет время следующего запуска как `datetime.now() + timedelta(hours=random_hours)`;
- добавляет задачу `sync_all_channels` с `DateTrigger`;
- использует фиксированный `id="sync_channels"` и `replace_existing=True`, поэтому новая задача заменяет предыдущую;
- логирует запланированное время.

### `sync_all_channels() -> None`
Синхронизирует все включённые каналы:
- проверяет `app.state.is_syncing`; если синхронизация уже идёт, пишет лог и выходит;
- устанавливает `app.state.is_syncing = True` и `app.state.stop_requested = False`;
- открывает сессию БД через `SessionLocal`;
- получает включённые каналы через `get_enabled_channels(db)`;
- для каждого канала:
  - проверяет `app.state.stop_requested` и прерывает цикл по запросу пользователя;
  - вызывает `download_channel(url, folder_name, min_date, channel_id)`;
  - при успехе обновляет отметку проверки через `update_last_checked(db, channel.id)`;
  - при ошибке пишет предупреждение в лог;
- перехватывает общие исключения и логирует ошибку;
- в `finally` закрывает сессию БД, сбрасывает флаги `stop_requested` и `is_syncing`, затем вызывает `schedule_next_sync()`.

### `start_scheduler() -> None`
Запускает планировщик:
- вызывает `scheduler.start()`;
- сразу планирует первую синхронизацию через `schedule_next_sync()`;
- логирует запуск и настроенный интервал.

### `stop_scheduler() -> None`
Останавливает планировщик, если он запущен:
- вызывает `scheduler.shutdown()`;
- логирует остановку.

## Зависимости
Внешние библиотеки:
- `logging`, `os`, `random`;
- `datetime`, `timedelta`;
- `apscheduler.schedulers.background.BackgroundScheduler`;
- `apscheduler.triggers.date.DateTrigger`.

Внутренние модули проекта:
- `app.config` — константы `SYNC_INTERVAL_HOURS_MIN`, `SYNC_INTERVAL_HOURS_MAX`;
- `app.database` — `SessionLocal`;
- `app.crud` — `get_enabled_channels`, `update_last_checked`;
- `app.downloader` — `download_channel`;
- `app.state` — флаги `is_syncing`, `stop_requested`.

## Использование в проекте
Модуль предоставляет публичные функции `start_scheduler()`, `stop_scheduler()`, `sync_all_channels()`, `schedule_next_sync()` и объект `scheduler`. Обычно он используется точкой входа приложения для запуска и остановки фонового планировщика.

Внутри модуля `sync_all_channels` зарегистрирована как задача APScheduler, а `schedule_next_sync()` вызывается при старте планировщика и после завершения каждой синхронизации. Для управления ходом синхронизации модуль использует общие флаги из `app.state`.

## Заметки
- Следующая синхронизация планируется в `finally`, то есть даже при ошибке во время синхронизации.
- Одновременный запуск синхронизаций предотвращается флагом `app.state.is_syncing`.
- Остановка текущей синхронизации выполняется через `app.state.stop_requested`.
- Существующая документация по модулю отсутствовала.