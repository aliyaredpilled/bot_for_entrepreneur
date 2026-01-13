# Claude Agent SDK — Cookbook

Практические рецепты для создания агентов на базе Claude Agent SDK.
Эти паттерны проверены в продакшене на Telegram-боте.

---

## Оглавление

1. [Базовый агент со стримингом](#1-базовый-агент-со-стримингом)
2. [Типы сообщений](#2-типы-сообщений)
3. [Обработка стриминга](#3-обработка-стриминга)
4. [Стриминг с чередованием текста и инструментов](#4-стриминг-с-чередованием-текста-и-инструментов)
5. [Сессии и память](#5-сессии-и-память)
6. [receive_response vs receive_messages](#6-receive_response-vs-receive_messages)
7. [Маппинг инструментов](#7-маппинг-инструментов)
8. [Дедупликация финального текста](#8-дедупликация-финального-текста)
9. [Динамический system_prompt](#9-динамический-system_prompt)
10. [Таймауты сессий](#10-таймауты-сессий)
11. [Доступные инструменты](#11-доступные-инструменты)

---

## 1. Базовый агент со стримингом

Минимальный пример агента который стримит ответы:

```python
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

async def run_agent(question: str):
    options = ClaudeAgentOptions(
        system_prompt="Ты полезный ассистент.",
        allowed_tools=["Read", "Bash", "Grep", "Glob"],
        model="sonnet",  # или "opus", "haiku"
        include_partial_messages=True,  # для стриминга
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(question)

        async for msg in client.receive_messages():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)

            elif isinstance(msg, ResultMessage):
                print(f"\nГотово! Стоимость: ${msg.total_cost_usd:.4f}")
                break
```

---

## 2. Типы сообщений

SDK возвращает несколько типов сообщений при стриминге:

```python
from claude_agent_sdk import (
    SystemMessage,      # Системное сообщение (обычно игнорируем)
    AssistantMessage,   # Ответ ассистента (текст, инструменты, thinking)
    ResultMessage,      # Финальный результат (стоимость, токены)
)
```

**AssistantMessage.content** содержит блоки:

```python
from claude_agent_sdk import (
    TextBlock,      # Текстовый ответ: block.text
    ToolUseBlock,   # Вызов инструмента: block.name, block.input
    ThinkingBlock,  # Размышления агента: block.thinking
)
```

---

## 3. Обработка стриминга

Полный пример обработки всех типов:

```python
async for msg in client.receive_messages():
    # Системное — пропускаем
    if isinstance(msg, SystemMessage):
        continue

    # Ответ ассистента
    elif isinstance(msg, AssistantMessage):
        for block in msg.content:

            if isinstance(block, TextBlock):
                # Текст агента
                print(block.text)

            elif isinstance(block, ToolUseBlock):
                # Вызов инструмента
                tool_name = block.name      # "Bash", "Read", "Grep"...
                tool_input = block.input    # dict с параметрами
                print(f"Инструмент: {tool_name}")

            elif isinstance(block, ThinkingBlock):
                # Размышления (extended thinking)
                print(f"Думает: {block.thinking[:100]}...")

    # Финал
    elif isinstance(msg, ResultMessage):
        print(f"Токены: {msg.usage}")
        print(f"Стоимость: ${msg.total_cost_usd:.4f}")
        break
```

---

## 4. Стриминг с чередованием текста и инструментов

Агент работает итеративно: говорит → вызывает инструмент → говорит → вызывает → финальный ответ.

**Типичная последовательность:**

```
AssistantMessage: TextBlock("Сейчас посмотрю в архиве...")
AssistantMessage: ToolUseBlock(name="Grep", input={pattern: "продажи"})
AssistantMessage: TextBlock("Нашёл! Теперь проанализирую...")
AssistantMessage: ToolUseBlock(name="Bash", input={command: "python ..."})
AssistantMessage: TextBlock("📊 Вот результаты анализа:\n\n...")  ← финальный
ResultMessage: {cost: 0.02, tokens: 1500}
```

**Как это обрабатывать:**

```python
async def stream_with_progress(client, on_status, on_tool, on_final):
    """
    Стриминг с колбэками для разных событий.

    on_status(text) — промежуточная реплика агента
    on_tool(name, description) — вызов инструмента
    on_final(text) — финальный ответ
    """

    all_text_blocks = []

    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:

                if isinstance(block, TextBlock):
                    all_text_blocks.append(block.text)

                    # Короткий текст = промежуточная реплика
                    # Показываем как статус
                    if len(block.text) < 200:
                        await on_status(block.text)

                elif isinstance(block, ToolUseBlock):
                    # Вызов инструмента — показываем что делает
                    description = get_tool_description(block)
                    await on_tool(block.name, description)

        elif isinstance(msg, ResultMessage):
            # Конец — отдаём финальный ответ
            # Берём последний длинный блок текста
            final = get_final_response(all_text_blocks)
            await on_final(final)
            break


def get_final_response(text_blocks: list) -> str:
    """Извлекает финальный ответ из всех блоков текста"""

    if not text_blocks:
        return ""

    # Финальный ответ = последний TextBlock перед ResultMessage
    # Claude Agent SDK отправляет текст порциями:
    # - промежуточные реплики ("Сейчас посмотрю...")
    # - финальный развёрнутый ответ (последний блок)
    return text_blocks[-1]
```

**Пример использования с Telegram-ботом:**

```python
async def handle_question(message, bot, status_msg):
    """Обрабатывает вопрос с показом прогресса"""

    async def on_status(text):
        # Показываем реплику агента как статус
        await status_msg.edit_text(f"💭 {text}")

    async def on_tool(name, description):
        # Показываем что делает инструмент
        await status_msg.edit_text(description)

    async def on_final(text):
        # Показываем финальный ответ
        await status_msg.edit_text(text)

    await stream_with_progress(
        client,
        on_status=on_status,
        on_tool=on_tool,
        on_final=on_final
    )
```

**Продвинутый вариант с минимальным временем показа:**

```python
import asyncio

MIN_DISPLAY_TIME = 2.0  # секунды

async def stream_with_timing(client, update_status):
    """Стриминг с минимальным временем показа каждого шага"""

    last_update_time = asyncio.get_event_loop().time()
    all_text = []

    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:

                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - last_update_time

                # Ждём минимальное время перед сменой статуса
                if elapsed < MIN_DISPLAY_TIME:
                    await asyncio.sleep(MIN_DISPLAY_TIME - elapsed)

                if isinstance(block, TextBlock):
                    all_text.append(block.text)
                    if len(block.text) < 200:
                        await update_status(f"💭 {block.text}")
                        last_update_time = asyncio.get_event_loop().time()

                elif isinstance(block, ToolUseBlock):
                    desc = get_tool_description(block)
                    await update_status(desc)
                    last_update_time = asyncio.get_event_loop().time()

        elif isinstance(msg, ResultMessage):
            # Финальный ответ
            await asyncio.sleep(MIN_DISPLAY_TIME)  # даём прочитать последний статус
            return get_final_response(all_text)
```

**Что видит пользователь:**

```
⏳ Секунду...
    ↓ (2 сек)
💭 Сейчас посмотрю данные о продажах...
    ↓ (2 сек)
🔍 Ищу: «продажи»
    ↓ (2 сек)
💭 Нашёл! Сейчас построю график...
    ↓ (2 сек)
⚙️ Строю график с matplotlib
    ↓ (2 сек)
📊 Вот анализ продаж за январь:
   ... полный ответ ...
```

---

## 5. Сессии и память

Агент может помнить контекст между сообщениями. Для этого нужно сохранять клиента:

```python
# Глобальное хранилище клиентов (по chat_id или user_id)
active_clients: Dict[int, ClaudeSDKClient] = {}

async def query_with_memory(chat_id: int, message: str):
    # Создаём клиента если нет
    if chat_id not in active_clients:
        options = ClaudeAgentOptions(
            system_prompt="...",
            allowed_tools=["Read", "Bash"],
            model="sonnet",
            include_partial_messages=True,
        )
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        active_clients[chat_id] = client

    client = active_clients[chat_id]

    # Отправляем запрос
    await client.query(message)

    # Читаем ответ через receive_response() — это ключевой момент!
    async for msg in client.receive_response():
        # обработка...
        pass
```

---

## 6. receive_response vs receive_messages

**Критически важно для памяти между сообщениями!**

```python
# receive_messages() — читает ВСЮ историю с начала
# Используй для одноразовых запросов
async for msg in client.receive_messages():
    ...

# receive_response() — читает только ПОСЛЕДНИЙ ответ
# Используй для многократных запросов к одному клиенту!
async for msg in client.receive_response():
    ...
```

**Почему это важно:**

Если использовать `receive_messages()` для второго запроса — получишь всю историю заново (первый вопрос, первый ответ, второй вопрос, второй ответ). Это сломает логику.

`receive_response()` возвращает только ответ на последний `query()`.

---

## 7. Маппинг инструментов

Превращаем технические вызовы в понятные описания:

```python
def get_tool_description(block: ToolUseBlock) -> str:
    tool_name = block.name
    tool_input = block.input or {}

    if tool_name == "Bash":
        # Bash имеет поле description
        if "description" in tool_input:
            return f"⚙️ {tool_input['description']}"
        else:
            cmd = tool_input.get('command', '')[:50]
            return f"⚙️ Выполняю: {cmd}..."

    elif tool_name == "Read":
        file_path = tool_input.get('file_path', '')
        filename = file_path.split('/')[-1]
        return f"📖 Читаю: {filename}"

    elif tool_name == "Grep":
        pattern = tool_input.get('pattern', '')
        return f"🔍 Ищу: «{pattern}»"

    elif tool_name == "Glob":
        pattern = tool_input.get('pattern', '')
        return f"📁 Ищу файлы: {pattern}"

    else:
        return f"🔧 {tool_name}"
```

**Использование:**

```python
elif isinstance(block, ToolUseBlock):
    description = get_tool_description(block)
    await show_status(description)  # Показываем пользователю
```

---

## 8. Дедупликация финального текста

**Проблема:** При стриминге агент выдаёт промежуточные фразы ("Сейчас посмотрю...", "Нашёл!") и финальный ответ. Нужно показать только финальный.

**Как работает Claude Agent SDK:**

```
TextBlock("Сейчас посмотрю...")     ← промежуточный
ToolUseBlock(Grep)
TextBlock("Нашёл! Анализирую...")   ← промежуточный
ToolUseBlock(Bash)
TextBlock("📊 Вот результаты...")   ← ФИНАЛЬНЫЙ (последний перед done)
ResultMessage                       ← done
```

**Решение:** Финальный ответ = **последний TextBlock** перед ResultMessage.

```python
async def stream_and_get_final(client):
    all_text_blocks = []

    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    all_text_blocks.append(block.text)

                    # Каждый блок показываем как статус
                    # (потом заменится следующим или финальным)
                    await show_status(block.text[:200])

        elif isinstance(msg, ResultMessage):
            break

    # Финальный ответ = последний TextBlock
    final_response = all_text_blocks[-1] if all_text_blocks else ""
    return final_response
```

**Почему это работает:**

Claude Agent SDK отправляет текст порциями. Агент сначала "думает вслух" (короткие реплики), потом выдаёт развёрнутый ответ. Последний TextBlock перед ResultMessage — это и есть финальный ответ.

---

## 9. Динамический system_prompt

Подставляем переменные (chat_id, пути) в промпт:

```python
class MyAgent:
    def get_system_prompt(self, chat_id: int) -> str:
        chat_dir = f"/app/data/chat_{chat_id}"

        return f"""Ты ассистент для чата {chat_id}.

Твоя рабочая папка: {chat_dir}

Файлы:
- {chat_dir}/history.txt — история чата
- {chat_dir}/media/ — файлы пользователей
- {chat_dir}/output/ — твои файлы

Сохраняй результаты в {chat_dir}/output/
"""

    def get_options(self, chat_id: int) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            system_prompt=self.get_system_prompt(chat_id),
            allowed_tools=["Read", "Bash", "Grep", "Glob"],
            model="sonnet",
            include_partial_messages=True,
        )
```

---

## 10. Таймауты сессий

Очищаем старые сессии чтобы не держать память вечно:

```python
import time

SESSION_TIMEOUT = 30 * 60  # 30 минут

active_clients: Dict[int, ClaudeSDKClient] = {}
last_activity: Dict[int, float] = {}

async def get_or_create_client(chat_id: int, options: ClaudeAgentOptions):
    current_time = time.time()

    # Проверяем таймаут
    if chat_id in active_clients:
        last_time = last_activity.get(chat_id, 0)

        if current_time - last_time > SESSION_TIMEOUT:
            # Сессия устарела — закрываем
            old_client = active_clients[chat_id]
            await old_client.__aexit__(None, None, None)
            del active_clients[chat_id]
            print(f"Сессия {chat_id} истекла, создаю новую")

    # Создаём если нет
    if chat_id not in active_clients:
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        active_clients[chat_id] = client

    # Обновляем время активности
    last_activity[chat_id] = current_time

    return active_clients[chat_id]
```

---

## 11. Доступные инструменты

Стандартные инструменты Claude Agent SDK:

| Инструмент | Описание | Ключевые параметры |
|------------|----------|-------------------|
| `Read` | Чтение файлов | `file_path`, `offset`, `limit` |
| `Bash` | Выполнение команд | `command`, `description`, `timeout` |
| `Grep` | Поиск в файлах | `pattern`, `path`, `glob` |
| `Glob` | Поиск файлов | `pattern`, `path` |
| `Write` | Запись файлов | `file_path`, `content` |
| `Edit` | Редактирование | `file_path`, `old_string`, `new_string` |

**Пример конфигурации:**

```python
ClaudeAgentOptions(
    allowed_tools=[
        "Read",   # Читать файлы
        "Bash",   # Команды (осторожно!)
        "Grep",   # Поиск текста
        "Glob",   # Поиск файлов
    ],
    # НЕ включаем Write/Edit если не нужно менять файлы
)
```

---

## Полный пример: Агент с памятью

```python
import asyncio
import time
from typing import Dict
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

SESSION_TIMEOUT = 30 * 60
active_clients: Dict[int, ClaudeSDKClient] = {}
last_activity: Dict[int, float] = {}

async def chat(user_id: int, message: str):
    """Отправить сообщение агенту с сохранением контекста"""

    current_time = time.time()

    # Проверяем таймаут
    if user_id in active_clients:
        if current_time - last_activity.get(user_id, 0) > SESSION_TIMEOUT:
            await active_clients[user_id].__aexit__(None, None, None)
            del active_clients[user_id]

    # Создаём клиента
    if user_id not in active_clients:
        options = ClaudeAgentOptions(
            system_prompt="Ты дружелюбный ассистент.",
            allowed_tools=["Read", "Grep", "Glob", "Bash"],
            model="sonnet",
            include_partial_messages=True,
        )
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        active_clients[user_id] = client

    last_activity[user_id] = current_time
    client = active_clients[user_id]

    # Запрос
    await client.query(message)

    # Стриминг ответа
    final_text = []

    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    final_text.append(block.text)
                    print(f"[текст] {block.text[:50]}...")

                elif isinstance(block, ToolUseBlock):
                    print(f"[инструмент] {block.name}")

        elif isinstance(msg, ResultMessage):
            print(f"[готово] ${msg.total_cost_usd:.4f}")
            break

    return final_text[-1] if final_text else ""


# Использование
async def main():
    # Первый вопрос
    response1 = await chat(123, "Сколько файлов в текущей папке?")
    print(f"Ответ: {response1}\n")

    # Второй вопрос — агент помнит контекст!
    response2 = await chat(123, "А какой из них самый большой?")
    print(f"Ответ: {response2}\n")

asyncio.run(main())
```

---

## Частые ошибки

### 1. Используют receive_messages() вместо receive_response()

```python
# НЕПРАВИЛЬНО — получишь всю историю заново
async for msg in client.receive_messages():
    ...

# ПРАВИЛЬНО — только последний ответ
async for msg in client.receive_response():
    ...
```

### 2. Забывают await client.__aenter__()

```python
# НЕПРАВИЛЬНО
client = ClaudeSDKClient(options=options)
await client.query(message)  # Ошибка!

# ПРАВИЛЬНО
client = ClaudeSDKClient(options=options)
await client.__aenter__()  # Инициализация!
await client.query(message)
```

### 3. Не закрывают старые сессии

```python
# НЕПРАВИЛЬНО — утечка памяти
if timeout_expired:
    del active_clients[chat_id]  # Клиент не закрыт!

# ПРАВИЛЬНО
if timeout_expired:
    await active_clients[chat_id].__aexit__(None, None, None)
    del active_clients[chat_id]
```

### 4. Показывают промежуточный текст как финальный

```python
# НЕПРАВИЛЬНО — покажет "Сейчас посмотрю..." как часть ответа
all_text = []
async for msg in client.receive_response():
    if isinstance(block, TextBlock):
        all_text.append(block.text)
return "\n".join(all_text)  # Включает промежуточные фразы!

# ПРАВИЛЬНО — берём только последний блок
return all_text[-1] if all_text else ""
```

---

## Советы

1. **Всегда используй `include_partial_messages=True`** для стриминга
2. **`receive_response()`** для многократных запросов к одному клиенту
3. **Сохраняй клиентов** в dict по user_id/chat_id для памяти
4. **Закрывай старые сессии** через `__aexit__()`
5. **Финальный ответ = последний TextBlock** перед ResultMessage
6. **Маппи инструменты** на понятные описания для UX
7. **Динамический system_prompt** — подставляй пути и ID

---

*Этот cookbook основан на реальном Telegram-боте с AI-агентом.*
