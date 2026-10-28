# Changelog

## [Unreleased]

### Added
- feat: добавить модуль постобработки
- feat: добавить фоновую синхронизацию с защитой от повторного запуска и статусом в UI
- feat: добавить замену полноширинных символов в clean_filenames
- feat: добавить DNS-серверы в сервис dixtune для обхода блокировок
- feat: добавить страницу логов, статистику каналов и исправить часовой пояс
- feat: добавить теги date и artist для MP3
- feat: добавить дату в тег title и убрать её из имени файла
- feat: добавить ссылку на дашборд ByeDPI в навигацию
- feat: добавить автоматическое заполнение тегов MP3 через yt-dlp
- feat: добавить bgutil PO Token Provider для обхода блокировки YouTube
- feat: добавить журнал синхронизации и отображение статуса на главной странице
- feat: добавить расширенное логирование и --verbose для отладки yt-dlp
- feat: добавить break-on-existing и нормализацию URL канала в downloader.py
- feat: добавить флаг --remote-components ejs:github для загрузки скриптов-решателей
- feat: добавить установку Deno в Dockerfile для обхода n challenge
- feat: добавить медиа-запросы для адаптивности интерфейса на мобильных устройствах
- feat: добавить поддержку root_path для работы за прокси с подпутём
- feat(ci): добавить поддержку ветки dev и условный деплой для main

### Fixed
- fix: вынести общее состояние в app/state.py для устранения циклического импорта
- fix: вызывать очистку имён и тегов при ошибке yt-dlp
- fix: разделить --extractor-args для корректной передачи base_url
- fix: заменить player_client на web_safari и убрать --verbose
- fix: изменить порт ByeDPI на 1081 в docker-compose.yml
- fix: заменить абсолютные пути к статике на url_for в base.html

### Changed
- refactor: убрать поддержку cookies из DixTune
- refactor: заменить жёстко закодированные пути на url_for в шаблонах, использовать request.url_for в редиректе
- refactor: унифицировать конфигурацию через переменные окружения feat: добавить редирект с корня на /ui/ и исключить его из авторизации

### Documentation
- docs: переписать раздел «Быстрый старт (Prod)» в пошаговый формат

### Other
- [non-conventional] sponsorblock
- [non-conventional] docker
- [non-conventional] docker
- [non-conventional] Initial commit: DixTune — automatic audio downloader from YouTube
