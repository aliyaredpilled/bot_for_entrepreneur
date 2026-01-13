#!/usr/bin/env python3
"""
Тест модуля архивации без реального Telegram API
Проверяет задачи 1.1-1.3 из FEATURES.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Добавляем src в путь
sys.path.insert(0, '/app/src')

from archiver import ChatArchiver
from aiogram.types import Message, User, Chat

# Создаём mock объекты для тестирования
class MockUser:
    """Mock объект пользователя Telegram"""
    def __init__(self, id, first_name=None, username=None):
        self.id = id
        self.first_name = first_name
        self.username = username

class MockChat:
    """Mock объект чата"""
    def __init__(self, id):
        self.id = id

class MockMessage:
    """Mock объект сообщения"""
    def __init__(self, chat_id, user, text=None):
        self.chat = MockChat(chat_id)
        self.from_user = user
        self.text = text
        self.new_chat_members = None
        self.left_chat_member = None
        self.new_chat_title = None
        self.new_chat_photo = None


def test_directory_creation():
    """Тест 1.1: Создание структуры директорий"""
    print("\n[TEST 1.1] Создание структуры директорий")

    test_chat_id = 999999
    archiver = ChatArchiver(test_chat_id)

    # Проверяем что директории созданы
    assert archiver.chat_dir.exists(), "❌ Директория чата не создана"
    assert archiver.media_dir.exists(), "❌ Директория media/ не создана"
    assert archiver.agent_files_dir.exists(), "❌ Директория agent_files/ не создана"
    assert archiver.history_file.exists(), "❌ Файл history.txt не создан"

    print("✅ Директории созданы успешно:")
    print(f"   - {archiver.chat_dir}")
    print(f"   - {archiver.media_dir}")
    print(f"   - {archiver.agent_files_dir}")
    print(f"   - {archiver.history_file}")

    return archiver


def test_text_message_archiving(archiver):
    """Тест 1.2: Сохранение текстовых сообщений"""
    print("\n[TEST 1.2] Сохранение текстовых сообщений")

    # Создаём тестовое сообщение
    user = MockUser(id=12345, first_name="Алия")
    message = MockMessage(chat_id=999999, user=user, text="Привет, бот!")

    # Архивируем
    archiver.archive_text_message(message)

    # Проверяем что сообщение записано
    with open(archiver.history_file, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "Алия:" in content, "❌ Имя пользователя не найдено в истории"
    assert "Привет, бот!" in content, "❌ Текст сообщения не найден в истории"

    # Отправляем второе сообщение
    message2 = MockMessage(chat_id=999999, user=user, text="Как дела?")
    archiver.archive_text_message(message2)

    # Проверяем что оба сообщения есть
    with open(archiver.history_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    assert len(lines) >= 2, "❌ Не все сообщения записаны"
    assert "Привет, бот!" in lines[0], "❌ Первое сообщение не на месте"
    assert "Как дела?" in lines[1], "❌ Второе сообщение не дописано в конец"

    print("✅ Текстовые сообщения архивируются корректно")
    print(f"   Записано строк: {len(lines)}")
    print(f"   Первая строка: {lines[0].strip()}")
    print(f"   Вторая строка: {lines[1].strip()}")


def test_system_events(archiver):
    """Тест 1.3: Логирование системных событий"""
    print("\n[TEST 1.3] Логирование системных событий")

    # Читаем текущее количество строк
    with open(archiver.history_file, 'r', encoding='utf-8') as f:
        lines_before = len(f.readlines())

    # Тест 1: Присоединение пользователя
    user = MockUser(id=54321, first_name="Никита")
    message = MockMessage(chat_id=999999, user=user)
    message.new_chat_members = [user]
    archiver.handle_new_chat_members(message)

    # Тест 2: Изменение названия чата
    message2 = MockMessage(chat_id=999999, user=user)
    message2.new_chat_title = "Рабочий чат"
    archiver.handle_new_chat_title(message2)

    # Тест 3: Выход пользователя
    message3 = MockMessage(chat_id=999999, user=user)
    message3.left_chat_member = user
    archiver.handle_left_chat_member(message3)

    # Проверяем что события записаны
    with open(archiver.history_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = ''.join(lines)

    assert "👤" in content, "❌ Событие присоединения не записано"
    assert "Никита присоединился" in content, "❌ Текст события неверный"
    assert "✏️" in content, "❌ Событие смены названия не записано"
    assert "Название изменено: Рабочий чат" in content, "❌ Новое название не записано"
    assert "👋" in content, "❌ Событие выхода не записано"
    assert "покинул чат" in content, "❌ Текст выхода неверный"

    lines_after = len(lines)
    assert lines_after == lines_before + 3, f"❌ Неверное количество событий (ожидалось +3, получено +{lines_after - lines_before})"

    print("✅ Системные события логируются корректно")
    print(f"   Всего событий: {lines_after - lines_before}")
    print(f"   Последние 3 строки:")
    for line in lines[-3:]:
        print(f"      {line.strip()}")


def test_archive_paths():
    """Дополнительный тест: Получение путей архива"""
    print("\n[TEST EXTRA] Получение путей архива для AI-агента")

    archiver = ChatArchiver(123456)
    paths = archiver.get_archive_paths()

    assert 'chat_dir' in paths, "❌ Путь chat_dir не возвращается"
    assert 'media_dir' in paths, "❌ Путь media_dir не возвращается"
    assert 'agent_files_dir' in paths, "❌ Путь agent_files_dir не возвращается"
    assert 'history_file' in paths, "❌ Путь history_file не возвращается"

    print("✅ Пути для AI-агента возвращаются корректно:")
    for key, value in paths.items():
        print(f"   {key}: {value}")


if __name__ == '__main__':
    print("="*70)
    print("  ТЕСТИРОВАНИЕ МОДУЛЯ АРХИВАЦИИ (Задачи 1.1-1.3)")
    print("="*70)

    try:
        # Запускаем тесты
        archiver = test_directory_creation()
        test_text_message_archiving(archiver)
        test_system_events(archiver)
        test_archive_paths()

        print("\n" + "="*70)
        print("  ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*70)
        print("\nЗадачи 1.1, 1.2, 1.3 реализованы и протестированы.")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
