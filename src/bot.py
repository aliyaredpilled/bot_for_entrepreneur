#!/usr/bin/env python3
"""
Telegram AI Bot with archiving and Claude Agent SDK integration
"""

import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from archiver import ChatArchiver

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

    # TODO: обработка медиа, активация агента


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
