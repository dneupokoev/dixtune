# crud.py

## Назначение модуля

Модуль содержит CRUD-операции и вспомогательные функции для работы с базой данных через SQLAlchemy `Session`:

- управление каналами (`Channel`);
- ведение журнала синхронизации (`SyncLog`);
- получение статистики синхронизации за последние 24 часа.

Версия файла: `261012.05`.

## Основные функции

### Каналы

- `get_channels(db: Session) -> List[models.Channel]`
  - Возвращает список всех каналов.

- `get_channel(db: Session, channel_id: int) -> Optional[models.Channel]`
  - Возвращает канал по `channel_id` или `None`, если канал не найден.

- `create_channel(db: Session, channel: schemas.ChannelCreate) -> models.Channel`
  - Создаёт новый канал.
  - Если `channel.name` задан, используется как источник имени.
  - Иначе имя извлекается из URL после `@`; если совпадения нет, используется весь URL.
  - Формирует `folder_name` через `sanitize_filename` и, при `channel.transliterate=True`, через `transliterate`.
  - Устанавливает `enabled=True`.
  - Сохраняет `url`, `name`, `folder_name`, `min_date`, `transliterate`.

- `update_channel(db: Session, channel_id: int, channel_update: schemas.ChannelUpdate) -> Optional[models.Channel]`
  - Обновляет канал по `channel_id`.
  - Обновляет только переданные поля: `url`, `name`, `min_date`, `enabled`.
  - `folder_name` не обновляется, так как папка фиксируется при создании канала.
  - Возвращает обновлённый канал или `None`, если канал не найден.

- `delete_channel(db: Session, channel_id: int) -> bool`
  - Удаляет канал по `channel_id`.
  - Возвращает `True` при успешном удалении и `False`, если канал не найден.

- `get_enabled_channels(db: Session) -> List[models.Channel]`
  - Возвращает список включённых каналов (`enabled == True`).

- `update_last_checked(db: Session, channel_id: int) -> None`
  - Обновляет `last_checked` канала текущим UTC-временем.
  - Если канал не найден, ничего не делает.

### Журнал синхронизации и статистика

- `create_sync_log(db: Session, channel_id: Optional[int], status: str, message: str) -> models.SyncLog`
  - Создаёт запись в журнале синхронизации.
  - `channel_id` может быть `None`.
  - Сохраняет `status` и `message`.

- `get_last_sync_logs(db: Session, limit: int = 10) -> List[models.SyncLog]`
  - Возвращает последние записи журнала синхронизации, отсортированные по `created_at` по убыванию.
  - Количество записей ограничено параметром `limit`.

- `get_sync_stats(db: Session) -> Dict[str, int]`
  - Возвращает статистику синхронизации за последние 24 часа UTC.
  - Считает количество записей со статусом `success` и `error`.
  - Возвращает словарь вида `{"success": int, "error": int}`.

## Зависимости

### Стандартная библиотека Python

- `re` — извлечение имени из URL.
- `datetime.timedelta` — расчёт периода 24 часа.
- `typing.List`, `typing.Optional`, `typing.Dict` — аннотации типов.

### Внешние библиотеки

- `sqlalchemy.orm.Session` — сессия SQLAlchemy для работы с БД.

### Внутренние модули проекта

- `app.models` — ORM-модели `Channel`, `SyncLog`.
- `app.schemas` — Pydantic-схемы `ChannelCreate`, `ChannelUpdate`.
- `app.utils`:
  - `sanitize_filename` — очистка имени папки;
  - `transliterate` — транслитерация имени;
  - `utcnow` — получение текущего UTC-времени.

## Использование другими модулями проекта

В изолированном файле `crud.py` нет импортов этого модуля другими модулями, поэтому конкретные точки вызова не видны. По назначению модуль предназначен для использования сервисным слоем, API-маршрутами или фоновыми задачами, которым нужны операции чтения/создания/обновления/удаления каналов и работа с журналом синхронизации.

## Заметки

- `folder_name` рассчитывается только при создании канала и не изменяется при обновлении.
- `update_last_checked` не возвращает обновлённый объект.
- Статистика `get_sync_stats` учитывает только статусы `success` и `error`.
- Для операций создания, обновления и удаления используется `db.commit()`; для чтения — запросы без коммита.