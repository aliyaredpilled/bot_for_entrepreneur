FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (jq для работы с JSON)
RUN apt-get update && \
    apt-get install -y --no-install-recommends jq && \
    rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY src/ ./src/

# Создание директории для архивов
RUN mkdir -p /app/chat_archive

# Запуск бота
CMD ["python", "-u", "src/bot.py"]
