FROM python:3.12-slim

# Установка системных зависимостей
# --no-install-recommends не ставит рекомендованные пакеты (экономит место)
# rm -rf /var/lib/apt/lists/* очищает кеш apt (экономит место)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && curl -fsSL https://deno.land/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Добавляем Deno в PATH
ENV PATH="/root/.deno/bin:$PATH"

# Рабочая директория
WORKDIR /app

# Копирование зависимостей и установка
# --no-cache-dir не сохраняет кеш pip в образе (экономит место)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY app/ ./app/

# Запуск приложения DixTune
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "*"]
