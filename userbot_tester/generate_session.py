"""
Генератор String Session для Telethon.

Запусти один раз локально:
    python generate_session.py

Введи номер телефона и код из Telegram.
Полученную строку добавь в .env как TELETHON_STRING_SESSION.
"""

import os

# Попробуем взять из окружения, иначе попросим ввести
API_ID = os.getenv("TELETHON_API_ID")
API_HASH = os.getenv("TELETHON_API_HASH")

if not API_ID:
    API_ID = input("Введи API_ID: ").strip()
if not API_HASH:
    API_HASH = input("Введи API_HASH: ").strip()

API_ID = int(API_ID)

print("\n📱 Генерация String Session...")
print("Получи API_ID и API_HASH на https://my.telegram.org\n")

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    session_string = client.session.save()
    print("\n" + "="*50)
    print("✅ STRING SESSION (добавь в .env):")
    print("="*50)
    print(f"\nTELETHON_STRING_SESSION={session_string}\n")
    print("="*50)
    print("⚠️  Храни в секрете! Это как пароль от аккаунта.")
