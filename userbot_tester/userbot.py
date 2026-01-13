"""
Telegram Userbot Tester
Интерактивное тестирование AI-бота через Telethon.

Функции:
- Отслеживание всех сообщений и редактирований
- Логирование статусов бота (инструменты, промежуточные реплики)
- Отправка тестовых сообщений через файл
- Проверка получения файлов от бота
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ============ КОНФИГУРАЦИЯ ============

API_ID = int(os.getenv("TELETHON_API_ID", "0"))
API_HASH = os.getenv("TELETHON_API_HASH", "")
STRING_SESSION = os.getenv("TELETHON_STRING_SESSION", "")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "")  # без @

# ============ ЛОГИРОВАНИЕ ============

LOG_DIR = Path("/app/userbot_logs")
LOG_DIR.mkdir(exist_ok=True)

def log(msg: str, level: str = "INFO"):
    """Логирование в консоль и файл"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{ts}] [{level}] {msg}"
    print(log_line, flush=True)

    log_file = LOG_DIR / f"log_{datetime.now():%Y%m%d}.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def log_event(event_type: str, chat_id: int, text: str, extra: str = ""):
    """Форматированный лог события"""
    short_text = text[:80].replace("\n", " ") if text else "(пусто)"
    extra_str = f" | {extra}" if extra else ""
    log(f"{event_type} chat={chat_id} | {short_text}{extra_str}")


# ============ СТАТИСТИКА ============

class Stats:
    """Статистика тестирования"""
    def __init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.bot_responses = 0
        self.bot_edits = 0
        self.files_received = 0
        self.start_time = datetime.now()

    def summary(self) -> str:
        elapsed = datetime.now() - self.start_time
        return (
            f"📊 Статистика:\n"
            f"  Отправлено: {self.messages_sent}\n"
            f"  Получено: {self.messages_received}\n"
            f"  Ответов бота: {self.bot_responses}\n"
            f"  Редактирований: {self.bot_edits}\n"
            f"  Файлов: {self.files_received}\n"
            f"  Время: {elapsed}"
        )

stats = Stats()

# ============ ОПРЕДЕЛЕНИЕ БОТА ============

def is_from_bot(event) -> bool:
    """Проверяет, от бота ли сообщение"""
    if not event.message.sender:
        return False

    sender = event.message.sender
    # Проверяем по username или is_bot флагу
    if hasattr(sender, 'username') and sender.username:
        if sender.username.lower() == BOT_USERNAME.lower():
            return True
    if hasattr(sender, 'bot') and sender.bot:
        return True
    return False


def get_media_type(message) -> str:
    """Определяет тип медиа в сообщении"""
    if message.photo:
        return "📷 Фото"
    elif message.video:
        return "🎬 Видео"
    elif message.document:
        doc_name = ""
        if message.document.attributes:
            for attr in message.document.attributes:
                if hasattr(attr, 'file_name'):
                    doc_name = attr.file_name
                    break
        return f"📄 Документ: {doc_name}" if doc_name else "📄 Документ"
    elif message.voice:
        return "🎤 Голосовое"
    elif message.video_note:
        return "⚫ Видео-кружок"
    elif message.sticker:
        return "🎨 Стикер"
    return ""


# ============ ГЛАВНАЯ ЛОГИКА ============

async def main():
    if not all([API_ID, API_HASH, STRING_SESSION]):
        log("❌ Не заданы TELETHON_API_ID, TELETHON_API_HASH, TELETHON_STRING_SESSION", "ERROR")
        return

    log("🚀 Запуск Userbot Tester...")

    client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )

    # ===== ОБРАБОТЧИКИ СОБЫТИЙ =====

    @client.on(events.NewMessage(incoming=True, outgoing=True))
    async def on_new_message(event):
        """Обработка новых сообщений"""
        stats.messages_received += 1

        # Определяем источник
        is_bot = is_from_bot(event)
        is_outgoing = event.out

        if is_bot:
            stats.bot_responses += 1
            prefix = "🤖 БОТ"
        elif is_outgoing:
            stats.messages_sent += 1
            prefix = "📤 Я"
        else:
            prefix = "👤 Юзер"

        # Проверяем медиа
        media_type = get_media_type(event.message)
        if media_type and is_bot:
            stats.files_received += 1

        log_event(
            prefix,
            event.chat_id,
            event.message.text or "(медиа)",
            media_type
        )

    @client.on(events.MessageEdited(incoming=True, outgoing=True))
    async def on_message_edited(event):
        """Обработка редактирований - ключевое для отслеживания статусов бота"""
        is_bot = is_from_bot(event)

        if is_bot:
            stats.bot_edits += 1
            prefix = "✏️ БОТ EDIT"
        else:
            prefix = "✏️ Edit"

        log_event(prefix, event.chat_id, event.message.text or "(пусто)")

    # ===== ЗАПУСК =====

    await client.start()
    await client.catch_up()

    log("✅ Подключено к Telegram")

    # Загружаем диалоги для кеширования entity
    dialogs = await client.get_dialogs()
    log(f"📁 Загружено {len(dialogs)} диалогов")

    # Ищем целевой чат
    target_chat = None
    if TARGET_CHAT_ID:
        for d in dialogs:
            # Проверяем разные форматы ID
            entity_id = d.entity.id

            # Для супергрупп: -100XXXXXXXXXX
            if d.is_group or d.is_channel:
                full_id = -int(f"100{entity_id}")
                if full_id == TARGET_CHAT_ID or entity_id == TARGET_CHAT_ID:
                    target_chat = d.entity
                    log(f"🎯 Целевой чат: {d.name} (id={TARGET_CHAT_ID})")
                    break
            # Для личных чатов
            elif entity_id == TARGET_CHAT_ID or entity_id == abs(TARGET_CHAT_ID):
                target_chat = d.entity
                log(f"🎯 Целевой чат: {d.name} (id={TARGET_CHAT_ID})")
                break

        if not target_chat:
            log(f"⚠️ Чат {TARGET_CHAT_ID} не найден в диалогах", "WARN")

    # ===== ОТПРАВКА ЧЕРЕЗ ФАЙЛ =====

    SEND_FILE = LOG_DIR / "send.txt"
    COMMAND_FILE = LOG_DIR / "command.txt"

    async def send_file_watcher():
        """Следит за файлом send.txt и отправляет сообщения"""
        while True:
            try:
                if SEND_FILE.exists():
                    text = SEND_FILE.read_text(encoding="utf-8").strip()
                    if text and target_chat:
                        await client.send_message(target_chat, text)
                        log(f"📤 Отправлено: {text[:50]}...")
                    elif text and not target_chat:
                        log("⚠️ Целевой чат не найден, сообщение не отправлено", "WARN")
                    SEND_FILE.unlink()
            except Exception as e:
                log(f"❌ Ошибка отправки: {e}", "ERROR")
            await asyncio.sleep(1)

    async def command_file_watcher():
        """Следит за файлом command.txt и выполняет команды"""
        while True:
            try:
                if COMMAND_FILE.exists():
                    command = COMMAND_FILE.read_text(encoding="utf-8").strip()
                    if command and target_chat:
                        # Формат: change_title:Новое название
                        if ":" in command:
                            cmd, value = command.split(":", 1)
                            cmd = cmd.strip().lower()
                            value = value.strip()

                            if cmd == "change_title":
                                # Работает для обычных групп и супергрупп
                                from telethon.tl.functions.channels import EditTitleRequest
                                from telethon.tl.functions.messages import EditChatTitleRequest
                                try:
                                    # Попытка для супергруппы/канала
                                    await client(EditTitleRequest(
                                        channel=target_chat,
                                        title=value
                                    ))
                                except:
                                    # Для обычной группы
                                    await client(EditChatTitleRequest(
                                        chat_id=target_chat.id,
                                        title=value
                                    ))
                                log(f"✏️ Название изменено на: {value}")

                            elif cmd == "change_photo":
                                await client.edit_photo(target_chat, value)
                                log(f"🖼️ Фото изменено: {value}")

                            elif cmd == "add_member":
                                await client.add_chat_user(target_chat, value)
                                log(f"👤 Добавлен участник: {value}")

                            else:
                                log(f"⚠️ Неизвестная команда: {cmd}", "WARN")
                        else:
                            log("⚠️ Неверный формат команды. Используй: команда:значение", "WARN")
                    COMMAND_FILE.unlink()
            except Exception as e:
                log(f"❌ Ошибка выполнения команды: {e}", "ERROR")
            await asyncio.sleep(1)

    asyncio.create_task(send_file_watcher())
    asyncio.create_task(command_file_watcher())

    # ===== ПЕРИОДИЧЕСКАЯ СТАТИСТИКА =====

    async def stats_reporter():
        """Выводит статистику каждые 5 минут"""
        while True:
            await asyncio.sleep(300)  # 5 минут
            log(stats.summary())

    asyncio.create_task(stats_reporter())

    # ===== ОЖИДАНИЕ =====

    log("🎧 Слушаю события... (Ctrl+C для выхода)")
    log(f"📝 Для отправки: echo 'текст' > {SEND_FILE}")
    log(f"🎮 Для команд: echo 'команда:значение' > {COMMAND_FILE}")
    log(f"   Команды: change_title:Название | change_photo:path | add_member:user_id")

    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        log("\n👋 Завершение...")
        log(stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
