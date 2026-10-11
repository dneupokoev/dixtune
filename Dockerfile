FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Создание директорий
RUN mkdir -p /media/music/dixtune /data/logs

# Копирование файлов проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Запуск приложения DixTune
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
