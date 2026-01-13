#!/usr/bin/env python3
"""
Скрипт для отправки медиа-файлов через userbot
"""
import asyncio
import os
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

# Конфигурация
API_ID = int(os.getenv("TELETHON_API_ID", "0"))
API_HASH = os.getenv("TELETHON_API_HASH", "")
STRING_SESSION = os.getenv("TELETHON_STRING_SESSION", "")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))

async def send_media(file_path: str, caption: str = ""):
    """Отправка медиа-файла в целевой чат"""
    if not all([API_ID, API_HASH, STRING_SESSION]):
        print("❌ Не заданы переменные окружения")
        return

    client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    await client.start()

    try:
        # Сначала загружаем диалоги для кеширования
        await client.get_dialogs()

        # Отправляем файл напрямую по ID
        await client.send_file(
            TARGET_CHAT_ID,
            file_path,
            caption=caption
        )
        print(f"✅ Отправлен файл: {file_path}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python send_media.py <путь_к_файлу> [подпись]")
        sys.exit(1)

    file_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else ""

    asyncio.run(send_media(file_path, caption))
