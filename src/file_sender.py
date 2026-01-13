"""
Модуль для работы с файлами в ответах агента
Реализует задачи 5.1-5.3 из FEATURES.md
"""

import os
import re
import logging
from typing import List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_file_paths(text: str, chat_id: int) -> List[str]:
    """
    Парсинг путей к файлам в ответе агента (задача 5.1)

    Находит:
    - Абсолютные пути: /app/chat_archive/chat_123/agent_files/chart.png
    - Относительные имена в backticks: `chart.png`

    Args:
        text: Текст ответа агента
        chat_id: ID чата для резолва относительных путей

    Returns:
        Список полных путей к существующим файлам
    """
    found_files = []

    # Базовая директория для относительных путей
    base_dir = f"/app/chat_archive/chat_{chat_id}/agent_files"

    # 1. Поиск абсолютных путей
    # Паттерн: /app/chat_archive/chat_{id}/agent_files/filename.ext
    # Поддерживаем отрицательные chat_id
    absolute_pattern = r'/app/chat_archive/chat_-?\d+/agent_files/[^\s\'"<>|]+\.\w+'
    absolute_matches = re.findall(absolute_pattern, text)

    for path in absolute_matches:
        # Проверяем существование файла
        if os.path.exists(path) and os.path.isfile(path):
            if path not in found_files:
                found_files.append(path)
                logger.info(f"[FILE_PARSER] Found absolute path: {path}")
        else:
            logger.debug(f"[FILE_PARSER] Absolute path not found: {path}")

    # 2. Поиск относительных путей в backticks
    # Паттерн: `filename.ext` или `path/to/file.ext`
    backtick_pattern = r'`([^`]+\.\w+)`'
    backtick_matches = re.findall(backtick_pattern, text)

    for relative_path in backtick_matches:
        # Пробуем найти файл в разных местах

        # Попытка 1: относительно agent_files/
        full_path = os.path.join(base_dir, relative_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            if full_path not in found_files:
                found_files.append(full_path)
                logger.info(f"[FILE_PARSER] Found backtick path: {relative_path} -> {full_path}")
                continue

        # Попытка 2: относительно media/
        media_path = f"/app/chat_archive/chat_{chat_id}/media/{relative_path}"
        if os.path.exists(media_path) and os.path.isfile(media_path):
            if media_path not in found_files:
                found_files.append(media_path)
                logger.info(f"[FILE_PARSER] Found backtick path in media: {relative_path} -> {media_path}")
                continue

        # Попытка 3: полный путь как есть (если это уже абсолютный путь)
        if os.path.exists(relative_path) and os.path.isfile(relative_path):
            if relative_path not in found_files:
                found_files.append(relative_path)
                logger.info(f"[FILE_PARSER] Found backtick path as absolute: {relative_path}")
                continue

        logger.debug(f"[FILE_PARSER] Backtick path not found: {relative_path}")

    logger.info(f"[FILE_PARSER] Total files found: {len(found_files)}")
    return found_files


def mask_file_paths(text: str) -> str:
    """
    Маскировка длинных системных путей в тексте (задача 5.3)

    Заменяет:
    /app/chat_archive/chat_123/agent_files/report.xlsx -> report.xlsx
    /app/chat_archive/chat_123/media/photo.jpg -> photo.jpg
    `/app/chat_archive/chat_123/agent_files/report.xlsx` -> `report.xlsx`

    Args:
        text: Исходный текст с путями

    Returns:
        Текст с замаскированными путями
    """
    # Паттерн для замены: /app/chat_archive/chat_{id}/{subdir}/filename.ext
    # Поддерживаем отрицательные chat_id (группы начинаются с минуса)
    # Включаем backtick в список stop-символов, чтобы правильно обрабатывать пути в backticks
    pattern = r'/app/chat_archive/chat_-?\d+/(?:agent_files|media)/([^\s\'"<>|`]+)'

    def replace_with_filename(match):
        full_path = match.group(0)
        filename = match.group(1)
        logger.info(f"[PATH_MASK] Replacing {full_path} with {filename}")
        return filename

    masked_text = re.sub(pattern, replace_with_filename, text)

    return masked_text


def get_file_type(filepath: str) -> str:
    """
    Определение типа файла по расширению (для задачи 5.2)

    Args:
        filepath: Путь к файлу

    Returns:
        Тип файла: 'photo', 'video', 'document'
    """
    ext = Path(filepath).suffix.lower()

    # Изображения
    photo_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    if ext in photo_extensions:
        return 'photo'

    # Видео
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    if ext in video_extensions:
        return 'video'

    # Всё остальное - документ
    return 'document'
