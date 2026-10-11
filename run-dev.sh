#!/bin/bash
# run-dev.sh - Запуск DixTune в режиме разработки (локально, без Docker)

set -e

PROJECT_DIR="/opt/dix/dixtune"
PORT="${PORT:-8000}"

cd "$PROJECT_DIR"

echo "=== DixTune (dev) ==="
echo "Проект: $PROJECT_DIR"
echo "Порт: $PORT"
echo ""

# Проверяем, установлен ли pipenv
if ! command -v pipenv &> /dev/null; then
    echo "Ошибка: pipenv не установлен."
    echo "Установите его: sudo apt install pipenv"
    exit 1
fi

# Проверяем, есть ли виртуальное окружение
if [ ! -d ".venv" ]; then
    echo "Виртуальное окружение не найдено. Устанавливаем зависимости..."
    pipenv install
fi

# Проверяем, свободен ли порт
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Ошибка: порт $PORT уже занят."
    echo "Остановите процесс или запустите с другим портом: PORT=8001 ./run-dev.sh"
    exit 1
fi

echo "Запуск Uvicorn на http://0.0.0.0:$PORT"
echo "Веб-интерфейс: http://localhost:$PORT/ui"
echo "Swagger: http://localhost:$PORT/docs"
echo "Для остановки нажмите Ctrl+C"
echo ""

# Запускаем Uvicorn с автоперезагрузкой
pipenv run uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
