#!/usr/bin/env python3
"""
Telegram AI Bot with archiving and Claude Agent SDK integration
"""

import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from archiver import ChatArchiver
from agent import ClaudeAgent
from formatter import markdown_to_telegram_html

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
CLAUDE_CODE_OAUTH_TOKEN = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment")
if not CLAUDE_CODE_OAUTH_TOKEN:
    raise ValueError("CLAUDE_CODE_OAUTH_TOKEN not found in environment")

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь архиваторов для каждого чата
archivers = {}

# AI-агент
agent = ClaudeAgent()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer("Привет! Бот запущен и готов к работе.")
    logger.info(f"[START] chat_id={message.chat.id}")


def get_archiver(chat_id: int) -> ChatArchiver:
    """Получение или создание архиватора для чата"""
    if chat_id not in archivers:
        archivers[chat_id] = ChatArchiver(chat_id)
    return archivers[chat_id]


def is_bot_mentioned(message: Message) -> bool:
    """
    Проверка упоминания бота (задача 3.2)

    Активация по:
    - @bot_username
    - reply на сообщение бота
    """
    # Проверка reply на сообщение бота
    if message.reply_to_message and message.reply_to_message.from_user.is_bot:
        return True

    # Проверка @mention
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                # Извлекаем текст упоминания
                mention = message.text[entity.offset:entity.offset + entity.length]
                # Проверяем что это наш бот
                # Примечание: сравниваем с username бота
                return True  # Упрощённая проверка - любой @mention активирует

    return False


@dp.message()
async def handle_message(message: Message):
    """Обработчик всех входящих сообщений"""
    chat_id = message.chat.id
    archiver = get_archiver(chat_id)

    # Архивация системных событий
    if message.new_chat_members:
        archiver.handle_new_chat_members(message)

    if message.left_chat_member:
        archiver.handle_left_chat_member(message)

    if message.new_chat_title:
        archiver.handle_new_chat_title(message)

    if message.new_chat_photo:
        archiver.handle_new_chat_photo(message)

    # Архивация текстового сообщения
    if message.text:
        archiver.archive_text_message(message)
        text_preview = message.text[:50]
        logger.info(f"[MESSAGE] chat_id={chat_id}: {text_preview}")

        # Проверка активации агента (задача 3.2)
        if is_bot_mentioned(message):
            await handle_agent_query(message, archiver)

    # Архивация медиа (задачи 2.1-2.3)
    if message.photo:
        await archiver.archive_photo(message, bot)

    if message.document:
        await archiver.archive_document(message, bot)

    if message.voice:
        await archiver.archive_voice(message, bot)

    if message.video_note:
        await archiver.archive_video_note(message, bot)


async def handle_agent_query(message: Message, archiver: ChatArchiver):
    """
    Обработка запроса к AI-агенту

    Args:
        message: Сообщение от пользователя
        archiver: Архиватор чата
    """
    chat_id = message.chat.id

    # Получаем пути к архиву
    archive_paths = archiver.get_archive_paths()

    # Создаём статусное сообщение
    status_msg = await message.answer("⏳ Секунду...")

    # Колбэк для обновления статуса
    async def update_status(text: str):
        try:
            await status_msg.edit_text(text)
        except Exception as e:
            logger.debug(f"[STATUS] Could not update status: {e}")

    try:
        # Отправка запроса агенту
        response = await agent.query(
            chat_id=chat_id,
            message=message.text,
            archive_paths=archive_paths,
            on_status_update=update_status
        )

        # Форматируем markdown → HTML (задача 7.1)
        formatted_response = markdown_to_telegram_html(response)

        # Заменяем статус на финальный ответ с HTML-форматированием
        await status_msg.edit_text(formatted_response, parse_mode=ParseMode.HTML)

        logger.info(f"[AGENT] Response sent to chat_id={chat_id}")

    except Exception as e:
        logger.error(f"[AGENT] Error processing query: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка при обработке запроса: {str(e)}")



async def main():
    """Запуск бота"""
    logger.info("[STARTUP] Starting Telegram AI Bot...")
    logger.info(f"[CONFIG] BOT_TOKEN configured: {BOT_TOKEN[:10]}...")
    logger.info(f"[CONFIG] CLAUDE_CODE_OAUTH_TOKEN configured: {CLAUDE_CODE_OAUTH_TOKEN[:15]}...")

    logger.info("[STARTUP] Bot started successfully!")

    # Запуск polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
