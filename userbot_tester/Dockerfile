FROM python:3.11-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY userbot.py .

# Папка для логов
RUN mkdir -p /app/userbot_logs

CMD ["python", "-u", "userbot.py"]
