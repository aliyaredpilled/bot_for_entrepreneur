# Userbot Tester — Инструкция по созданию

Тестер на базе Telethon для отслеживания работы Telegram-бота с AI-агентом.

---

## Зачем нужен

- Видеть **все редактирования** сообщений бота (статусы инструментов)
- Ловить **отправку файлов** (графики, отчёты)
- Тестировать бота **программно** без ручного ввода
- Логировать всю активность для отладки

---

## Получение credentials

### 1. API ID и API Hash

1. Зайди на https://my.telegram.org
2. Авторизуйся по номеру телефона
3. Перейди в "API development tools"
4. Создай приложение (название любое)
5. Получишь `api_id` и `api_hash`

### 2. String Session

String Session — это зашифрованная сессия авторизации. Генерируется один раз.

```python
# generate_session.py
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 12345678  # твой api_id
api_hash = "abc123..."  # твой api_hash

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("String Session:")
    print(client.session.save())
```

Запусти скрипт, введи код из Telegram — получишь длинную строку. Это и есть `STRING_SESSION`.

**Важно:** String Session — это как пароль! Не публикуй и не коммить в git.

---

## Тонкости и подводные камни

### 1. Формат Chat ID

В Telegram разные форматы ID для разных типов чатов:

| Тип | Формат в боте (aiogram) | Формат в Telethon |
|-----|------------------------|-------------------|
| Личный чат | `123456789` | `123456789` |
| Группа | `-123456789` | `-123456789` |
| Супергруппа/Канал | `-1001234567890` | `1234567890` (без -100) |

**Проблема:** Бот видит супергруппу как `-1001234567890`, а Telethon entity имеет ID `1234567890`.

**Решение:** При поиске чата проверяй оба формата:
```python
for dialog in dialogs:
    entity_id = dialog.entity.id
    full_id = -int(f"100{entity_id}")  # Добавляем -100 prefix

    if full_id == TARGET_CHAT_ID:
        target = dialog.entity
```

### 2. Фильтры событий

По умолчанию Telethon **не показывает свои собственные сообщения**!

```python
# ❌ НЕ увидит свои сообщения
@client.on(events.NewMessage())

# ✅ Увидит ВСЕ сообщения
@client.on(events.NewMessage(incoming=True, outgoing=True))
```

То же самое для редактирований:
```python
@client.on(events.MessageEdited(incoming=True, outgoing=True))
```

### 3. Конфликт сессий

**Проблема:** Если запустить два скрипта с одной StringSession — один "отберёт" соединение у другого.

**Симптомы:**
- Userbot перестаёт получать события
- События приходят только в один из скриптов

**Решение:** Встроить отправку сообщений прямо в userbot через файл:
```python
# Userbot следит за файлом
SEND_FILE = Path("/app/send.txt")

async def check_send_file():
    while True:
        if SEND_FILE.exists():
            text = SEND_FILE.read_text().strip()
            if text:
                await client.send_message(target_chat, text)
            SEND_FILE.unlink()
        await asyncio.sleep(1)

asyncio.create_task(check_send_file())
```

Теперь отправка:
```bash
echo "@bot привет" > /app/send.txt
```

### 4. Кеширование entities

**Проблема:** Telethon не может отправить сообщение в чат по ID если не знает о нём.

```python
# ❌ Ошибка: Could not find the input entity
await client.send_message(-1001234567890, "test")
```

**Решение:** Сначала загрузи диалоги:
```python
# ✅ Сначала кешируем
dialogs = await client.get_dialogs()

# Теперь можно искать и отправлять
for d in dialogs:
    if d.entity.id == target_id:
        await client.send_message(d.entity, "test")
```

### 5. Catch Up

После запуска Telethon может пропустить события которые произошли пока он был выключен.

```python
await client.start()
await client.catch_up()  # Получить пропущенные обновления
```

---

## Структура проекта

```
project/
├── userbot.py          # Основной тестер
├── send.sh             # Скрипт для отправки
├── .env                # Credentials
├── userbot_logs/       # Логи
│   ├── log_20260113.txt
│   └── send.txt        # Файл для отправки сообщений
└── docker-compose.yml
```

---

## Минимальный userbot.py

```python
import asyncio
from pathlib import Path
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 12345678
API_HASH = "your_hash"
STRING_SESSION = "your_session"
TARGET_CHAT_ID = -1005022916429

LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_DIR / f"log_{datetime.now():%Y%m%d}.txt", "a") as f:
        f.write(f"[{ts}] {msg}\n")

async def main():
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    @client.on(events.NewMessage(incoming=True, outgoing=True))
    async def on_message(event):
        log(f"📨 chat={event.chat_id} | {event.message.text[:50]}")

        # Проверяем медиа
        if event.message.photo:
            log("   📷 Фото!")
        elif event.message.document:
            log("   📄 Документ!")

    @client.on(events.MessageEdited(incoming=True, outgoing=True))
    async def on_edit(event):
        log(f"✏️ edit chat={event.chat_id} | {event.message.text[:50]}")

    await client.start()
    await client.catch_up()

    # Загружаем диалоги для кеширования
    dialogs = await client.get_dialogs()

    # Ищем целевой чат
    target_chat = None
    for d in dialogs:
        if d.is_group or d.is_channel:
            full_id = -int(f"100{d.entity.id}")
            if full_id == TARGET_CHAT_ID:
                target_chat = d.entity
                log(f"✅ Нашли чат: {d.name}")

    # Фоновая отправка через файл
    SEND_FILE = Path("./logs/send.txt")

    async def send_loop():
        while True:
            if SEND_FILE.exists():
                text = SEND_FILE.read_text().strip()
                if text and target_chat:
                    await client.send_message(target_chat, text)
                    log(f"📤 Отправлено: {text[:30]}...")
                SEND_FILE.unlink()
            await asyncio.sleep(1)

    asyncio.create_task(send_loop())

    log("🎧 Слушаю события...")
    await client.run_until_disconnected()

asyncio.run(main())
```

---

## Docker

### docker-compose.yml

```yaml
services:
  userbot:
    build: .
    command: python -u userbot.py
    environment:
      - TELETHON_API_ID=${TELETHON_API_ID}
      - TELETHON_API_HASH=${TELETHON_API_HASH}
      - TELETHON_STRING_SESSION=${TELETHON_STRING_SESSION}
    volumes:
      - ./userbot_logs:/app/userbot_logs
    profiles:
      - testing  # Запускается только с --profile testing
```

### Команды

```bash
# Собрать
docker compose --profile testing build userbot

# Запустить
docker compose --profile testing up -d userbot

# Логи в реальном времени
docker logs -f telegram-userbot-tester

# Отправить сообщение
docker exec telegram-userbot-tester sh -c 'echo "@bot тест" > /app/userbot_logs/send.txt'
```

---

## send.sh — удобный скрипт

```bash
#!/bin/bash
docker exec telegram-userbot-tester sh -c "echo '$1' > /app/userbot_logs/send.txt"
echo "✅ Отправлено: $1"
```

Использование:
```bash
./send.sh "@useful_and_chill_bot сколько строк в истории?"
```

---

## Что можно автоматизировать

### Инфраструктурные тесты (автоматически)

```python
def test_bot_responds():
    """Бот отвечает на сообщение"""
    send("@bot привет")
    events = wait_events(timeout=15)

    assert any(e.from_bot for e in events), "Бот не ответил!"

def test_bot_edits():
    """Бот редактирует сообщение (показывает статус)"""
    send("@bot найди слово тест")
    events = wait_events(timeout=20)

    edits = [e for e in events if e.is_edit and e.from_bot]
    assert len(edits) >= 1, "Не было редактирований!"

def test_bot_sends_files():
    """Бот отправляет файлы"""
    send("@bot создай график")
    events = wait_events(timeout=30)

    files = [e for e in events if e.has_media and e.from_bot]
    assert len(files) >= 1, "Файл не отправлен!"
```

### Качество ответов (вручную)

- Правильно ли понял вопрос
- Насколько полезный ответ
- Красиво ли оформлено
- Нет ли галлюцинаций

---

## Частые проблемы

| Проблема | Причина | Решение |
|----------|---------|---------|
| Не видит события | Нет `incoming=True, outgoing=True` | Добавь в декоратор |
| `Could not find entity` | Чат не закеширован | Вызови `get_dialogs()` |
| События пропадают | Конфликт сессий | Используй отправку через файл |
| Неправильный chat_id | Формат -100 | Конвертируй ID правильно |
| Userbot молчит | Session истекла | Сгенерируй новую |

---

## Итого

1. **Получи credentials** — api_id, api_hash, string_session
2. **Используй правильные фильтры** — `incoming=True, outgoing=True`
3. **Кешируй диалоги** — `get_dialogs()` перед отправкой
4. **Избегай конфликта сессий** — отправляй через файл, не через отдельный скрипт
5. **Конвертируй chat_id** — добавляй/убирай `-100` для супергрупп

Удачного тестирования! 🚀
