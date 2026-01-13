#!/bin/bash
# Отправка команды через userbot тестер
#
# Использование:
#   ./command.sh "change_title:Новое название"
#   ./command.sh "change_photo:/path/to/photo.jpg"
#   ./command.sh "add_member:user_id"

if [ -z "$1" ]; then
    echo "Использование: ./command.sh \"команда:значение\""
    echo ""
    echo "Доступные команды:"
    echo "  change_title:Название чата"
    echo "  change_photo:/path/to/photo.jpg"
    echo "  add_member:user_id"
    exit 1
fi

# Отправляем через docker exec
docker exec telegram-userbot-tester sh -c "echo '$1' > /app/userbot_logs/command.txt"

echo "✅ Команда отправлена: $1"
