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

    def _generate_filename_timestamp(self) -> str:
        """Генерация таймштампа для имени файла в формате YYYYMMDD_HHMMSS"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

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

    async def archive_photo(self, message: Message, bot):
        """
        Сохранение фото в media/ (задача 2.1)

        Формат имени: photo_{timestamp}.jpg
        В history.txt добавляется: 📷 photo_{timestamp}.jpg → media/photo_{timestamp}.jpg

        Args:
            message: Сообщение с фото
            bot: Объект бота для скачивания файла
        """
        if not message.photo:
            return

        # Берем фото максимального качества (последнее в списке)
        photo = message.photo[-1]
        timestamp = self._generate_filename_timestamp()
        filename = f"photo_{timestamp}.jpg"
        filepath = self.media_dir / filename

        # Скачивание файла
        await bot.download(photo, destination=filepath)

        # Запись в history.txt
        timestamp_display = self._format_timestamp()
        user_name = self._get_user_name(message.from_user)
        full_path = f"/app/chat_archive/chat_{self.chat_id}/media/{filename}"
        line = f"{timestamp_display} {user_name} отправил файл 📷 {filename} - полный путь {full_path}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved photo {filename} from {user_name} in chat_id={self.chat_id}")

    async def archive_document(self, message: Message, bot):
        """
        Сохранение документа в media/ (задача 2.2)

        Документ сохраняется с оригинальным именем.
        Если файл существует, добавляется таймштамп: filename_{timestamp}.ext

        Args:
            message: Сообщение с документом
            bot: Объект бота для скачивания файла
        """
        if not message.document:
            return

        document = message.document
        original_filename = document.file_name or f"document_{self._generate_filename_timestamp()}"

        # Проверка существования файла
        filepath = self.media_dir / original_filename

        if filepath.exists():
            # Добавляем таймштамп к имени файла
            timestamp = self._generate_filename_timestamp()
            name_parts = original_filename.rsplit('.', 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{original_filename}_{timestamp}"
            filepath = self.media_dir / filename
        else:
            filename = original_filename

        # Скачивание файла
        await bot.download(document, destination=filepath)

        # Запись в history.txt
        timestamp_display = self._format_timestamp()
        user_name = self._get_user_name(message.from_user)
        full_path = f"/app/chat_archive/chat_{self.chat_id}/media/{filename}"
        line = f"{timestamp_display} {user_name} отправил файл 📄 {filename} - полный путь {full_path}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved document {filename} from {user_name} in chat_id={self.chat_id}")

    async def archive_voice(self, message: Message, bot):
        """
        Сохранение голосового сообщения в media/ (задача 2.3)

        Формат имени: voice_{timestamp}.ogg

        Args:
            message: Сообщение с голосовым сообщением
            bot: Объект бота для скачивания файла
        """
        if not message.voice:
            return

        voice = message.voice
        timestamp = self._generate_filename_timestamp()
        filename = f"voice_{timestamp}.ogg"
        filepath = self.media_dir / filename

        # Скачивание файла
        await bot.download(voice, destination=filepath)

        # Запись в history.txt
        timestamp_display = self._format_timestamp()
        user_name = self._get_user_name(message.from_user)
        full_path = f"/app/chat_archive/chat_{self.chat_id}/media/{filename}"
        line = f"{timestamp_display} {user_name} отправил файл 🎤 {filename} - полный путь {full_path}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved voice message {filename} from {user_name} in chat_id={self.chat_id}")

    async def archive_video_note(self, message: Message, bot):
        """
        Сохранение видео-кружка в media/ (задача 2.3)

        Формат имени: videonote_{timestamp}.mp4

        Args:
            message: Сообщение с видео-кружком
            bot: Объект бота для скачивания файла
        """
        if not message.video_note:
            return

        video_note = message.video_note
        timestamp = self._generate_filename_timestamp()
        filename = f"videonote_{timestamp}.mp4"
        filepath = self.media_dir / filename

        # Скачивание файла
        await bot.download(video_note, destination=filepath)

        # Запись в history.txt
        timestamp_display = self._format_timestamp()
        user_name = self._get_user_name(message.from_user)
        full_path = f"/app/chat_archive/chat_{self.chat_id}/media/{filename}"
        line = f"{timestamp_display} {user_name} отправил файл 🎥 {filename} - полный путь {full_path}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved video note {filename} from {user_name} in chat_id={self.chat_id}")

    def archive_bot_response(self, text: str):
        """
        Сохранение текстового ответа бота в history.txt (задача 1.4)

        Формат: [DD.MM HH:MM] 🤖 Бот: текст ответа

        Args:
            text: Текст ответа бота
        """
        if not text:
            return

        timestamp = self._format_timestamp()
        # Убираем переносы строк для компактности
        text_oneline = text.replace('\n', ' ')
        line = f"{timestamp} 🤖 Бот: {text_oneline}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved bot response in chat_id={self.chat_id}")

    def archive_bot_file(self, filepath: str):
        """
        Сохранение информации об отправленном боте файле в history.txt (задача 1.4)

        Формат: [DD.MM HH:MM] 🤖 Бот отправил файл 📊 filename - полный путь /app/chat_archive/chat_ID/agent_files/filename

        Args:
            filepath: Полный путь к отправленному файлу
        """
        if not filepath:
            return

        timestamp = self._format_timestamp()

        # Извлекаем имя файла
        path = Path(filepath)
        filename = path.name

        # Определяем директорию (media/ или agent_files/) и иконку
        if 'media' in filepath:
            icon = "📷" if filename.startswith('photo_') else "📄"
        elif 'agent_files' in filepath:
            # Определяем тип файла по расширению
            ext = path.suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                icon = "📊"  # График/изображение
            elif ext in ['.csv', '.xlsx', '.xls']:
                icon = "📊"  # Данные
            else:
                icon = "📄"  # Документ
        else:
            icon = "📄"

        # Формируем полный путь с правильным chat_id
        full_path = filepath

        line = f"{timestamp} 🤖 Бот отправил файл {icon} {filename} - полный путь {full_path}\n"

        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(line)

        logger.info(f"[ARCHIVE] Saved bot file record: {filename} in chat_id={self.chat_id}")
