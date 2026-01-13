"""
Модуль AI-агента на базе Claude Agent SDK
Реализует задачи 3.1-3.4 из FEATURES.md
"""

import os
import time
import logging
from typing import Dict, Optional
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

logger = logging.getLogger(__name__)

# Таймаут сессии в секундах (30 минут)
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 30 * 60))


class ClaudeAgent:
    """AI-агент на базе Claude Agent SDK с управлением сессиями"""

    def __init__(self):
        """Инициализация агента"""
        self.active_clients: Dict[int, ClaudeSDKClient] = {}
        self.last_activity: Dict[int, float] = {}

        # Проверка токена
        self.oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
        if not self.oauth_token:
            raise ValueError("CLAUDE_CODE_OAUTH_TOKEN not found in environment")

        logger.info("[AGENT] ClaudeAgent initialized")

    def get_system_prompt(self, chat_id: int, archive_paths: dict) -> str:
        """
        Динамический system prompt с путями к архиву (задача 3.3)

        Args:
            chat_id: ID чата
            archive_paths: Словарь с путями к директориям архива

        Returns:
            System prompt для агента
        """
        chat_dir = archive_paths['chat_dir']
        history_file = archive_paths['history_file']
        media_dir = archive_paths['media_dir']
        agent_files_dir = archive_paths['agent_files_dir']

        return f"""Ты AI-ассистент для Telegram чата {chat_id}.

Твоя задача — помогать пользователям работать с архивом переписки и данными.

КРИТИЧЕСКИ ВАЖНО - ПАМЯТЬ:
- Ты ПОМНИШЬ всю нашу текущую беседу с начала сессии
- Ты ПОМНИШЬ свои предыдущие ответы и вопросы пользователя
- Когда пользователь говорит "а сколько их было?", "а какой самый большой?" -
  он имеет в виду информацию из ТВОЕГО ПРЕДЫДУЩЕГО ОТВЕТА В ЭТОМ РАЗГОВОРЕ
- НЕ говори что "не помнишь" или что нужно "посмотреть в файл"
- Используй файлы для НОВЫХ запросов, но помни что ты уже говорил в этой беседе

ВАЖНАЯ ИНФОРМАЦИЯ О ТВОЕЙ РАБОЧЕЙ СРЕДЕ:
- Текущая рабочая директория: {chat_dir}
- История переписки: {history_file}
- Файлы пользователей: {media_dir}/
- Твои файлы (графики, отчёты): {agent_files_dir}/

ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
- Read: читать файлы (history.txt, Excel, CSV, JSON)
- Grep: искать по паттернам в истории переписки
- Glob: находить файлы по маске
- Bash: выполнять команды, запускать python-скрипты для анализа данных

ПРАВИЛА РАБОТЫ:
1. АНАЛИЗ ДАННЫХ:
   - Используй pandas для работы с Excel/CSV
   - Используй matplotlib/seaborn для графиков
   - Сохраняй все результаты в {agent_files_dir}/

2. СТИЛЬ ОТВЕТОВ:
   - Пиши КРАТКО и КОМПАКТНО
   - Используй эмодзи для структуры (📊💰📈)
   - НИКОГДА не используй markdown-таблицы
   - Вместо таблиц — списки с эмодзи
   - Детальные данные выноси в файлы (Excel, CSV)

3. РАБОТА С ФАЙЛАМИ:
   - Всегда указывай ПОЛНЫЙ ПУТЬ при создании файлов
   - Пример: {agent_files_dir}/chart.png
   - Пример: {agent_files_dir}/report.xlsx
   - После создания файла упомяни его в ответе

4. БЕЗОПАСНОСТЬ:
   - Работай ТОЛЬКО в директории {chat_dir}
   - НЕ обращайся к другим чатам

ПРИМЕР ХОРОШЕГО ОТВЕТА:
"📊 Проанализировал продажи за январь:

💰 Итого: 1 234 567₽
📈 Рост: +15% к декабрю

Топ-3 товара:
• Товар A — 456К₽
• Товар B — 345К₽
• Товар C — 234К₽

📁 Детальный отчёт → report.xlsx
📊 График динамики → sales_chart.png"

Начинай работу!"""

    def get_tool_description(self, block: ToolUseBlock) -> str:
        """
        Маппинг технических имен инструментов на понятные описания (задача 3.4)

        Args:
            block: Блок вызова инструмента

        Returns:
            Понятное описание действия
        """
        tool_name = block.name
        tool_input = block.input or {}

        if tool_name == "Bash":
            # Bash может иметь description
            if "description" in tool_input:
                return f"⚙️ {tool_input['description']}"
            else:
                cmd = tool_input.get('command', '')[:50]
                return f"⚙️ Выполняю: {cmd}..."

        elif tool_name == "Read":
            file_path = tool_input.get('file_path', '')
            filename = file_path.split('/')[-1] if file_path else 'файл'
            return f"📖 Читаю: {filename}"

        elif tool_name == "Grep":
            pattern = tool_input.get('pattern', '')
            return f"🔍 Ищу: «{pattern}»"

        elif tool_name == "Glob":
            pattern = tool_input.get('pattern', '')
            return f"📁 Ищу файлы: {pattern}"

        else:
            return f"🔧 {tool_name}"

    async def get_or_create_client(
        self,
        chat_id: int,
        archive_paths: dict
    ) -> ClaudeSDKClient:
        """
        Получение или создание клиента с проверкой таймаута (задача 4.1, 4.3)

        Args:
            chat_id: ID чата
            archive_paths: Пути к директориям архива

        Returns:
            Клиент Claude SDK
        """
        current_time = time.time()

        # Проверка таймаута существующей сессии
        if chat_id in self.active_clients:
            last_time = self.last_activity.get(chat_id, 0)

            if current_time - last_time > SESSION_TIMEOUT:
                # Сессия устарела - закрываем
                logger.info(f"[SESSION] Session expired for chat_id={chat_id}, creating new")
                old_client = self.active_clients[chat_id]
                await old_client.__aexit__(None, None, None)
                del self.active_clients[chat_id]

        # Создание нового клиента если нет
        if chat_id not in self.active_clients:
            logger.info(f"[SESSION] New session for chat_id={chat_id}")

            options = ClaudeAgentOptions(
                system_prompt=self.get_system_prompt(chat_id, archive_paths),
                allowed_tools=["Read", "Bash", "Grep", "Glob"],
                model="sonnet",
                include_partial_messages=True,
            )

            client = ClaudeSDKClient(options=options)
            await client.__aenter__()
            self.active_clients[chat_id] = client
        else:
            logger.info(f"[SESSION] Continue session for chat_id={chat_id}")

        # Обновление времени активности
        self.last_activity[chat_id] = current_time

        return self.active_clients[chat_id]

    async def query(
        self,
        chat_id: int,
        message: str,
        archive_paths: dict,
        on_status_update=None
    ) -> str:
        """
        Отправка запроса агенту с обработкой стриминга (задача 3.2, 3.4)

        Args:
            chat_id: ID чата
            message: Текст запроса
            archive_paths: Пути к архиву
            on_status_update: Колбэк для обновления статуса (опционально)

        Returns:
            Финальный ответ агента
        """
        logger.info(f"[QUERY] chat_id={chat_id}: {message[:100]}")

        # Получение или создание клиента
        client = await self.get_or_create_client(chat_id, archive_paths)

        # Отправка запроса
        await client.query(message)

        # Обработка стриминга ответа
        all_text_blocks = []
        tools_used = []

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:

                    if isinstance(block, TextBlock):
                        # Сохраняем текст
                        all_text_blocks.append(block.text)

                        # Показываем короткие реплики как статусы
                        if on_status_update and len(block.text) < 200:
                            await on_status_update(f"💭 {block.text}")

                    elif isinstance(block, ToolUseBlock):
                        # Вызов инструмента - показываем что делает
                        tools_used.append(block.name)
                        description = self.get_tool_description(block)
                        logger.info(f"[TOOL] {block.name} in chat_id={chat_id}")

                        if on_status_update:
                            await on_status_update(description)

            elif isinstance(msg, ResultMessage):
                # Финал - логируем статистику
                total_tokens = 0
                if hasattr(msg.usage, 'input_tokens'):
                    total_tokens = msg.usage.input_tokens + msg.usage.output_tokens
                elif isinstance(msg.usage, dict):
                    total_tokens = msg.usage.get('input_tokens', 0) + msg.usage.get('output_tokens', 0)

                logger.info(
                    f"[RESULT] chat_id={chat_id}, "
                    f"tokens={total_tokens}, "
                    f"cost=${msg.total_cost_usd:.4f}, "
                    f"tools={','.join(tools_used) if tools_used else 'none'}"
                )
                break

        # Финальный ответ = последний TextBlock
        final_response = all_text_blocks[-1] if all_text_blocks else "Извини, не смог сформулировать ответ."

        return final_response

    async def cleanup(self):
        """Закрытие всех активных сессий"""
        logger.info(f"[AGENT] Closing {len(self.active_clients)} active sessions")

        for chat_id, client in self.active_clients.items():
            try:
                await client.__aexit__(None, None, None)
                logger.info(f"[SESSION] Closed session for chat_id={chat_id}")
            except Exception as e:
                logger.error(f"[SESSION] Error closing session for chat_id={chat_id}: {e}")

        self.active_clients.clear()
        self.last_activity.clear()
