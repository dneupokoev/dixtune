#!/bin/bash
# deploy.sh - Скрипт подготовки и запуска DixTune в продакшене

set -e # Остановить выполнение при любой ошибке

# --- НАСТРОЙКИ ---
PROJECT_DIR="/opt/dix/dixtune"
MUSIC_DIR="/media/music/dixtune"

echo "--- 1. Проверка прав на папку с музыкой ---"
sudo mkdir -p "$MUSIC_DIR"
sudo chown -R 0:0 "$MUSIC_DIR"
echo "Права на $MUSIC_DIR выставлены."

echo "--- 2. Скачивание образа ---"
cd "$PROJECT_DIR"
sudo docker compose pull

echo "--- 3. Запуск сервисов ---"
sudo docker compose up -d --remove-orphans

echo "--- 4. Проверка статуса ---"
sleep 5
sudo docker compose ps

echo "--- DixTune развернут! ---"
echo "Откройте в браузере: http://<IP_СЕРВЕРА>:8020/ui"