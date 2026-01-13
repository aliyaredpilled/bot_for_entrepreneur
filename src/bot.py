#!/usr/bin/env python3
"""
Telegram AI Bot with archiving and Claude Agent SDK integration
"""

import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

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


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer("Привет! Бот запущен и готов к работе.")
    logger.info(f"[START] chat_id={message.chat.id}")


@dp.message()
async def handle_message(message: Message):
    """Обработчик всех входящих сообщений"""
    text_preview = message.text[:50] if message.text else '<media>'
    logger.info(f"[MESSAGE] chat_id={message.chat.id}: {text_preview}")
    # TODO: архивация, агент, и т.д.


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
