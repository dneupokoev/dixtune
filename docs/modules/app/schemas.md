# schemas.py

Версия файла: `261010.01`.

## Назначение

Модуль содержит Pydantic-схемы для API. Схемы описывают валидацию входных данных и формат ответов для каналов YouTube и статуса приложения. Исполняемой бизнес-логики нет, кроме валидаторов поля `url`.

## Основные классы

### `ChannelBase(BaseModel)`

Базовая схема канала. Аргументы конструктора соответствуют полям:

- `url: str` — обязательный URL канала или плейлиста YouTube.
- `name: Optional[str]` — понятное имя канала, по умолчанию `None`.
- `min_date: Optional[date]` — минимальная дата публикации видео, по умолчанию `None`.
- `transliterate: bool` — транслитерировать имя папки в латиницу, по умолчанию `False`.

Валидатор `validate_url` проверяет, что `url` начинается с одного из префиксов:

- `https://www.youtube.com`
- `https://youtube.com`
- `https://youtu.be`

При несоответствии выбрасывается `ValueError`.

### `ChannelCreate(ChannelBase)`

Схема для создания канала. Наследует все поля и валидатор `ChannelBase`, дополнительных полей не добавляет.

### `ChannelUpdate(BaseModel)`

Схема для обновления канала. Все поля необязательные:

- `url: Optional[str]`
- `name: Optional[str]`
- `min_date: Optional[date]`
- `enabled: Optional[bool]`

Валидатор `validate_url` проверяет URL только если он передан и не равен `None`. В этой схеме отсутствует поле `transliterate`, поэтому через `ChannelUpdate` нельзя обновить этот флаг.

### `ChannelResponse(ChannelBase)`

Схема ответа с данными канала. Наследует поля `ChannelBase` и добавляет:

- `id: int`
- `folder_name: str`
- `enabled: bool`
- `last_checked: Optional[datetime]`
- `created_at: datetime`

`Config.from_attributes = True` позволяет создавать схему из объектов, у которых есть соответствующие атрибуты, например из ORM-моделей.

### `StatusResponse(BaseModel)`

Схема статуса приложения:

- `last_sync: Optional[datetime]`
- `total_channels: int`
- `enabled_channels: int`
- `downloaded_count: int`

## Зависимости

Внешние зависимости:

- `datetime.date`, `datetime.datetime` — типы для дат и времени.
- `pydantic.BaseModel`, `pydantic.Field`, `pydantic.field_validator` — описание и валидация схем.
- `typing.Optional` — описание необязательных полей.

Внутренних импортов из других модулей проекта в файле нет.

## Использование в проекте

По содержимому файла невозможно точно определить конкретные модули проекта, которые импортируют эти схемы. Судя по назначению и именам классов, модуль предназначен для использования в API-слое и/или сервисном слое:

- `ChannelCreate` — для валидации данных при создании канала.
- `ChannelUpdate` — для валидации частичного обновления канала.
- `ChannelResponse` — для сериализации данных канала в ответах API и, благодаря `from_attributes = True`, для преобразования ORM-объектов.
- `StatusResponse` — для ответа со статусом приложения.
- `ChannelBase` — как общая база и/или самостоятельная схема.

## Ограничения и заметки

- Валидация `url` проверяет только строковый префикс, а не полную корректность URL и не факт существования канала.
- Поле `min_date` не имеет дополнительных валидаторов.
- `ChannelUpdate` не наследует `ChannelBase`, поэтому набор полей для обновления ограничен явно перечисленными полями.
- Поле `transliterate` доступно при создании канала, но не при обновлении через `ChannelUpdate`.
- `ChannelResponse` включает поля базовой схемы: `url`, `name`, `min_date`, `transliterate`, а также дополнительные поля ответа.