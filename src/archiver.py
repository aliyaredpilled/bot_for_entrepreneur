"""
Модуль архивации сообщений для Telegram AI Bot
Реализует задачи 1.1-1.3 из FEATURES.md
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from aiogram.types import Message, User

logger = logging.getLogger(__name__)

ARCHIVE_BASE = "/app/chat_archive"


class ChatArchiver:
    """Класс для архивации сообщений и событий чата"""

    def __init__(self, chat_id: int):
        """
        Инициализация архиватора для конкретного чата

        Args:
            chat_id: ID чата в Telegram
        """
        self.chat_id = chat_id
        self.chat_dir = Path(ARCHIVE_BASE) / f"chat_{chat_id}"
        self.media_dir = self.chat_dir / "media"
        self.agent_files_dir = self.chat_dir / "agent_files"
        self.history_file = self.chat_dir / "history.txt"

        # Создание структуры директорий при первом обращении
        self._ensure_directories()

    def _ensure_directories(self):
        """
        Создание структуры директорий для чата (задача 1.1)

        Создаёт:
        - /app/chat_archive/chat_{id}/
        - /app/chat_archive/chat_{id}/media/
        - /app/chat_archive/chat_{id}/agent_files/
        - /app/chat_archive/chat_{id}/history.txt
        """
        if not self.chat_dir.exists():
            logger.info(f"[ARCHIVE] Creating directory structure for chat_id={self.chat_id}")
            self.chat_dir.mkdir(parents=True, exist_ok=True)
            self.media_dir.mkdir(exist_ok=True)
            self.agent_files_dir.mkdir(exist_ok=True)

            # Создание пустого history.txt
            self.history_file.touch()
            logger.info(f"[ARCHIVE] Directory structure created: {self.chat_dir}")

    def _format_timestamp(self) -> str:
        """Форматирование текущего времени в формат [DD.MM HH:MM]"""
        return datetime.now().strftime("[%d.%m %H:%M]")

    def _get_user_name(self, user: Optional[User]) -> str:
        """
        Получение имени пользователя

        Args:
            user: Объект пользователя Telegram

        Returns:
            Имя пользователя или "Unknown"
        """
        if not user:
            return "Unknown"

        # Приоритет: first_name, username, id
        if user.first_name:
            return user.first_name
        elif user.username:
            return user.username
        else:
            return f"User_{user.id}"

    def archive_text_message(self, message: Message):
        """
        Сохранение текстового сообщения в history.txt (задача 1.2)

        Формат: [DD.MM HH:MM] Имя: текст сообщения

        Args:
            message: Объект сообщения из aiogram
        """
        if not message.text:
            return

        timestamp = self._format_timestamp()
        user_name = self._get_user_name(message.from_user)
        text = message.text.replace('\n', ' ')  # Однострочный формат

        line = f"{timestamp} {user_name}: {text}\n"

        # Дописывание в конец файла
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved text message from {user_name} in chat_id={self.chat_id}")

    def archive_system_event(self, event_type: str, details: str):
        """
        Логирование системных событий в history.txt (задача 1.3)

        Формат: [DD.MM HH:MM] 👤 событие

        Args:
            event_type: Тип события (user_joined, user_left, title_changed, etc.)
            details: Детали события
        """
        timestamp = self._format_timestamp()

        # Маппинг типов событий на эмодзи
        event_icons = {
            'user_joined': '👤',
            'user_left': '👋',
            'title_changed': '✏️',
            'photo_changed': '🖼️',
        }

        icon = event_icons.get(event_type, '📌')
        line = f"{timestamp} {icon} {details}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Logged system event '{event_type}' in chat_id={self.chat_id}")

    def handle_new_chat_members(self, message: Message):
        """
        Обработка события присоединения участников

        Args:
            message: Сообщение с событием new_chat_members
        """
        if not message.new_chat_members:
            return

        for user in message.new_chat_members:
            user_name = self._get_user_name(user)
            self.archive_system_event('user_joined', f"{user_name} присоединился")

    def handle_left_chat_member(self, message: Message):
        """
        Обработка события выхода участника

        Args:
            message: Сообщение с событием left_chat_member
        """
        if not message.left_chat_member:
            return

        user_name = self._get_user_name(message.left_chat_member)
        self.archive_system_event('user_left', f"{user_name} покинул чат")

    def handle_new_chat_title(self, message: Message):
        """
        Обработка изменения названия чата

        Args:
            message: Сообщение с событием new_chat_title
        """
        if not message.new_chat_title:
            return

        self.archive_system_event('title_changed', f"Название изменено: {message.new_chat_title}")

    def handle_new_chat_photo(self, message: Message):
        """
        Обработка изменения фото чата

        Args:
            message: Сообщение с событием new_chat_photo
        """
        if not message.new_chat_photo:
            return

        self.archive_system_event('photo_changed', "Фото чата изменено")

    def get_archive_paths(self) -> dict:
        """
        Получение путей к директориям архива (для AI-агента)

        Returns:
            Словарь с путями к директориям
        """
        return {
            'chat_dir': str(self.chat_dir),
            'media_dir': str(self.media_dir),
            'agent_files_dir': str(self.agent_files_dir),
            'history_file': str(self.history_file),
        }
