#!/bin/bash
# Отправка сообщения через userbot тестер
#
# Использование:
#   ./send.sh "@bot привет"
#   ./send.sh "построй график продаж"

if [ -z "$1" ]; then
    echo "Использование: ./send.sh \"сообщение\""
    exit 1
fi

# Отправляем через docker exec
docker exec telegram-userbot-tester sh -c "echo '$1' > /app/userbot_logs/send.txt"

echo "✅ Отправлено: $1"
