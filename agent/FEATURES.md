# Features & BDD Tests

Трекинг фич для Telegram AI Bot.

**Статусы:**
- `[ ]` — TODO
- `[~]` — IN_PROGRESS (агент работает)
- `[x]` — DONE

---

## 1. Архивация текста

### 1.1 [x] Создание структуры директорий
**Описание:** При первом сообщении в чате создаётся папка `/app/chat_archive/chat_{id}/`

```gherkin
Feature: Chat directory creation

  Scenario: New chat creates directory structure
    Given a message arrives from chat_id 123456
    And directory /app/chat_archive/chat_123456/ does not exist
    When the bot processes the message
    Then directory /app/chat_archive/chat_123456/ is created
    And subdirectory media/ exists
    And subdirectory agent_files/ exists
    And file history.txt exists
```

### 1.2 [x] Сохранение текстовых сообщений
**Описание:** Каждое текстовое сообщение дописывается в `history.txt`

```gherkin
Feature: Text message archiving

  Scenario: Text message is saved to history
    Given user "Алия" sends message "Привет, бот!"
    And current time is "13.01 15:30"
    When the message is processed
    Then history.txt contains line "[13.01 15:30] Алия: Привет, бот!"

  Scenario: Multiple messages are appended
    Given history.txt already has 5 lines
    When new message arrives
    Then history.txt has 6 lines
    And new line is at the end
```

### 1.3 [x] Логирование системных событий
**Описание:** Вход/выход участников, смена названия чата

```gherkin
Feature: System events logging

  Scenario: User joins chat
    Given user "Никита" joins the chat
    When event is processed
    Then history.txt contains "[DD.MM HH:MM] 👤 Никита присоединился"

  Scenario: Chat title changed
    Given chat title changes to "Рабочий чат"
    When event is processed
    Then history.txt contains "[DD.MM HH:MM] ✏️ Название изменено: Рабочий чат"
```

### 1.4 [ ] Архивация ответов бота
**Описание:** Ответы бота и отправленные им файлы сохраняются в историю

```gherkin
Feature: Bot responses archiving

  Scenario: Bot text response is saved
    Given bot sends text message "Нашёл 15 файлов в архиве"
    And current time is "13.01 15:35"
    When response is sent
    Then history.txt contains "[13.01 15:35] 🤖 Бот: Нашёл 15 файлов в архиве"

  Scenario: Bot sends file from agent_files
    Given bot sends file "chart.png" from agent_files/
    And current time is "13.01 15:36"
    When file is sent
    Then history.txt contains "[13.01 15:36] 🤖 Бот: 📊 chart.png → agent_files/chart.png"

  Scenario: Bot sends multiple files
    Given bot sends "report.xlsx" and "chart.png"
    When files are sent
    Then history.txt contains two lines with "🤖 Бот:" prefix
    And both file paths are recorded
```

---

## 2. Архивация медиа

### 2.1 [x] Сохранение фото
**Описание:** Фотографии сохраняются в `media/` с уникальным именем

```gherkin
Feature: Photo archiving

  Scenario: Photo is saved with timestamp
    Given user sends a photo
    And current timestamp is "20260113_153045"
    When photo is processed
    Then file media/photo_20260113_153045.jpg exists
    And history.txt contains "📷 photo_20260113_153045.jpg → media/photo_20260113_153045.jpg"
```

### 2.2 [x] Сохранение документов
**Описание:** Документы сохраняются с оригинальным именем + таймштамп при конфликте

```gherkin
Feature: Document archiving

  Scenario: Document with original name
    Given user sends document "report.xlsx"
    When document is processed
    Then file media/report.xlsx exists

  Scenario: Document name conflict
    Given media/report.xlsx already exists
    When user sends another "report.xlsx"
    Then file media/report_20260113_153045.xlsx is created
```

### 2.3 [x] Сохранение голосовых и видео-кружков
**Описание:** Voice messages и video notes сохраняются с генерированным именем

```gherkin
Feature: Voice and video notes archiving

  Scenario: Voice message saved
    Given user sends voice message
    When processed
    Then file media/voice_20260113_153045.ogg exists

  Scenario: Video note saved
    Given user sends video note (кружок)
    When processed
    Then file media/videonote_20260113_153045.mp4 exists
```

---

## 3. AI-агент

### 3.1 [x] Базовая интеграция Claude Agent SDK
**Описание:** Подключение SDK, создание клиента с опциями

```gherkin
Feature: Claude SDK integration

  Scenario: Agent client initialization
    Given CLAUDE_CODE_OAUTH_TOKEN is set
    When agent is initialized
    Then ClaudeSDKClient is created
    And allowed_tools includes Read, Bash, Grep, Glob
    And model is "sonnet"
```

### 3.2 [x] Активация по упоминанию
**Описание:** Агент активируется при @mention или reply

```gherkin
Feature: Agent activation

  Scenario: Activation by mention
    Given message text is "@bot_username что в архиве?"
    When message is received
    Then agent processes the query "что в архиве?"

  Scenario: Activation by reply
    Given user replies to bot's message with "а подробнее?"
    When reply is received
    Then agent processes the query with context

  Scenario: No activation without trigger
    Given message text is "просто сообщение"
    When message is received
    Then agent is NOT activated
    And message is only archived
```

### 3.3 [x] Динамический system prompt
**Описание:** Промпт содержит актуальные пути для текущего чата

```gherkin
Feature: Dynamic system prompt

  Scenario: Prompt includes chat paths
    Given current chat_id is 123456
    When agent is initialized for this chat
    Then system_prompt contains "/app/chat_archive/chat_123456/"
    And system_prompt contains path to history.txt
    And system_prompt contains path to media/
    And system_prompt contains path to agent_files/
```

### 3.4 [x] Инструменты агента
**Описание:** Агент использует Read, Grep, Glob, Bash для работы с файлами

```gherkin
Feature: Agent tools

  Scenario: Agent reads history
    Given user asks "сколько сообщений в архиве?"
    When agent processes query
    Then agent calls Read tool with history.txt
    And returns message count

  Scenario: Agent searches in history
    Given user asks "найди сообщения про отчёт"
    When agent processes query
    Then agent calls Grep tool with pattern "отчёт"

  Scenario: Agent creates file
    Given user asks "построй график продаж"
    When agent processes query
    Then agent calls Bash with python/matplotlib
    And file is saved to agent_files/
```

### 3.5 [ ] Улучшенный системный промпт
**Описание:** Добавить в промпт ключевые правила для работы агента

```gherkin
Feature: Enhanced system prompt

  Scenario: Capabilities explained
    Given agent receives system prompt
    When prompt is read
    Then prompt states agent can do data analysis
    And mentions: Excel, CSV, graphs, reports, calculations

  Scenario: Folder structure shown
    Given agent needs to understand structure
    When system prompt is read
    Then prompt contains ASCII tree of folders
    And shows: chat_dir/, history.txt, media/, agent_files/

  Scenario: Compact responses rule
    Given agent formats response
    When system prompt is read
    Then prompt says: NO markdown tables
    And says: keep answers compact in chat
    And says: move large content to .txt/.xlsx files

  Scenario: Auto-send files explained
    Given agent wants to send file to user
    When system prompt is read
    Then prompt says: write FULL path ONLY when you want to send file
    And explains: mentioning full path auto-sends file to user
    Example: "Готово: /app/chat_archive/chat_123/agent_files/chart.png"
```

---

## 4. Сессии и память

### 4.1 [x] Создание сессии для чата
**Описание:** Каждый chat_id имеет свою изолированную сессию

```gherkin
Feature: Session creation

  Scenario: New session for new chat
    Given chat_id 111 sends first message to agent
    When message is processed
    Then new session is created for chat_id 111
    And session is stored in active_clients dict

  Scenario: Separate sessions for different chats
    Given chat_id 111 has active session
    And chat_id 222 sends message
    When processed
    Then chat_id 222 gets its own session
    And sessions are independent
```

### 4.2 [x] Сохранение контекста между сообщениями
**Описание:** Агент помнит предыдущие сообщения в рамках сессии

```gherkin
Feature: Context preservation

  Scenario: Agent remembers previous messages
    Given user asked "сколько файлов в архиве?" and got answer "15 файлов"
    When user asks "а какой самый большой?"
    Then agent understands context
    And answers about the largest of those 15 files
```

### 4.3 [x] Таймаут сессии (30 минут)
**Описание:** После 30 минут бездействия сессия сбрасывается

```gherkin
Feature: Session timeout

  Scenario: Session expires after 30 minutes
    Given session for chat_id 111 was active at 15:00
    And current time is 15:35
    When new message arrives
    Then old session is closed
    And new session is created
    And log shows "Session expired, creating new"

  Scenario: Session continues within timeout
    Given session was active at 15:00
    And current time is 15:25
    When new message arrives
    Then same session continues
    And context is preserved
```

---

## 5. Отправка файлов

### 5.1 [x] Парсинг путей в ответах агента
**Описание:** Бот находит пути к файлам в тексте ответа

```gherkin
Feature: File path parsing

  Scenario: Absolute path detected
    Given agent response contains "/app/chat_archive/chat_123/agent_files/chart.png"
    When response is parsed
    Then path "/app/chat_archive/chat_123/agent_files/chart.png" is extracted

  Scenario: Path in backticks detected
    Given agent response contains "`chart.png`"
    When response is parsed
    Then relative path "chart.png" is extracted
    And resolved to full path
```

### 5.2 [x] Отправка файлов по типу
**Описание:** Изображения как фото, видео как видео, остальное как документ

```gherkin
Feature: File type detection and sending

  Scenario: PNG sent as photo
    Given file chart.png exists
    When bot sends file
    Then file is sent as photo (not document)

  Scenario: MP4 sent as video
    Given file demo.mp4 exists
    When bot sends file
    Then file is sent as video

  Scenario: XLSX sent as document
    Given file report.xlsx exists
    When bot sends file
    Then file is sent as document
```

### 5.3 [x] Маскировка путей в ответах
**Описание:** Длинные системные пути заменяются на имена файлов

```gherkin
Feature: Path masking

  Scenario: Long path replaced with filename
    Given agent response is "Сохранил в /app/chat_archive/chat_123/agent_files/report.xlsx"
    When response is formatted
    Then user sees "Сохранил в report.xlsx"
```

---

## 6. UX: Live-статусы

### 6.1 [x] Редактируемое сообщение со статусом
**Описание:** Бот создаёт сообщение и редактирует его по мере работы

```gherkin
Feature: Editable status message

  Scenario: Initial status shown
    Given user sends query to agent
    When processing starts
    Then bot sends message "⏳ Секунду..."

  Scenario: Status updates during work
    Given bot is processing query
    When agent calls Grep tool
    Then message is edited to "🔍 Ищу..."
```

### 6.2 [x] Минимальное время показа статуса (2 сек)
**Описание:** Каждый статус показывается минимум 2 секунды

```gherkin
Feature: Minimum status display time

  Scenario: Fast tool calls are throttled
    Given agent calls Read at t=0
    And agent calls Grep at t=0.5
    When statuses are shown
    Then "📖 Читаю..." shown from t=0 to t=2
    And "🔍 Ищу..." shown from t=2
```

### 6.3 [x] Маппинг инструментов на человеческие названия
**Описание:** Технические имена инструментов → понятные статусы

```gherkin
Feature: Tool name mapping

  Scenario: Grep mapped to search
    Given agent calls Grep with pattern "продажи"
    When status is shown
    Then user sees "🔍 Ищу «продажи»"

  Scenario: Bash mapped to calculation
    Given agent calls Bash with python script
    When status is shown
    Then user sees "⚙️ Выполняю расчёты..."

  Scenario: Read mapped to reading
    Given agent calls Read on history.txt
    When status is shown
    Then user sees "📖 Читаю файл..."
```

### 6.4 [x] Показ промежуточных реплик агента
**Описание:** Короткие фразы агента показываются как статусы

```gherkin
Feature: Intermediate replies as status

  Scenario: Short reply shown as status
    Given agent outputs "Сейчас посмотрю в архиве..."
    When text block is received
    Then status shows "💭 Сейчас посмотрю в архиве..."
```

### 6.5 [x] Финальный ответ заменяет статусы
**Описание:** В конце статус-сообщение заменяется на полный ответ

```gherkin
Feature: Final response replaces status

  Scenario: Status replaced with answer
    Given status message shows "⚙️ Строю график..."
    When agent finishes with final response
    Then status message is edited
    And contains full agent response
    And no status prefix remains
```

### 6.6 [ ] Чистые промежуточные реплики и дедупликация финала
**Описание:** Промежуточные реплики без префикса "💭", и не редактировать если финал = последней реплике

```gherkin
Feature: Clean intermediate messages and deduplication

  Scenario: Intermediate messages without thought bubble
    Given agent outputs text block "Сейчас посмотрю в архиве..."
    When status is shown
    Then message shows "Сейчас посмотрю в архиве..."
    And no "💭" prefix is added
    And no emoji prefix at all

  Scenario: Final response duplicates last intermediate
    Given last status shows "Нашёл 15 файлов в архиве"
    When agent finishes with final response "Нашёл 15 файлов в архиве"
    Then status message is NOT edited
    And no duplicate message appears

  Scenario: Final response differs from last status
    Given last status shows "⚙️ Строю график..."
    When agent finishes with final response "Вот график продаж: chart.png"
    Then status message is edited
    And shows new final response
```

---

## 7. Форматирование

### 7.1 [x] Markdown → Telegram HTML конвертер
**Описание:** Преобразование markdown в поддерживаемый Telegram HTML

```gherkin
Feature: Markdown to HTML conversion

  Scenario: Bold text converted
    Given agent response contains "**важно**"
    When formatted for Telegram
    Then output contains "<b>важно</b>"

  Scenario: Code block converted
    Given agent response contains triple backtick code
    When formatted for Telegram
    Then output contains "<pre>code</pre>"

  Scenario: Headers converted to bold
    Given agent response contains "## Заголовок"
    When formatted for Telegram
    Then output contains "<b>Заголовок</b>"

  Scenario: Quotes converted
    Given agent response contains "> цитата"
    When formatted for Telegram
    Then output contains "▎ цитата"
```

---

## 8. Docker & Инфраструктура

### 8.1 [x] Dockerfile с зависимостями
**Описание:** Образ с Python, pandas, matplotlib, jq

```gherkin
Feature: Docker image

  Scenario: Image has required dependencies
    Given Dockerfile is built
    When container starts
    Then python3.11+ is available
    And pandas is importable
    And matplotlib is importable
    And jq command works
```

### 8.2 [x] docker-compose.yml
**Описание:** Оркестрация сервисов с volumes и env

```gherkin
Feature: Docker Compose setup

  Scenario: Bot starts with compose
    Given .env file has BOT_TOKEN and CLAUDE_CODE_OAUTH_TOKEN
    When docker-compose up is run
    Then bot container starts
    And chat_archive volume is mounted
    And environment variables are loaded
```

---

## 9. Логирование

### 9.1 [ ] Структурированные логи в stdout
**Описание:** События сессий, запросы, инструменты, токены

```gherkin
Feature: Structured logging

  Scenario: Session start logged
    Given new session is created for chat_id 123
    When log is written
    Then stdout contains "[SESSION] New session for chat_id=123"

  Scenario: Query logged
    Given user sends "построй график"
    When query is processed
    Then stdout contains "[QUERY] chat_id=123: построй график"

  Scenario: Tool calls logged
    Given agent calls Grep, then Bash
    When tools execute
    Then stdout contains "[TOOL] Grep → [TOOL] Bash"

  Scenario: Cost logged
    Given request used 1500 tokens
    When request completes
    Then stdout contains "[COST] tokens=1500, cost=$0.0045"
```

---

## Прогресс

| Модуль | Задач | Готово | Статус |
|--------|-------|--------|--------|
| 1. Архивация текста | 4 | 3 | 🟡 |
| 2. Архивация медиа | 3 | 3 | ✅ |
| 3. AI-агент | 5 | 4 | 🟡 |
| 4. Сессии и память | 3 | 3 | ✅ |
| 5. Отправка файлов | 3 | 3 | ✅ |
| 6. UX: Live-статусы | 5 | 5 | ✅ |
| 7. Форматирование | 1 | 1 | ✅ |
| 8. Docker | 2 | 2 | ✅ |
| 9. Логирование | 1 | 0 | ⬜ |
| **ИТОГО** | **25** | **24** | **96%** |

---

## Как работать с файлом

### Для агента:
1. Найди задачу со статусом `[ ]`
2. Поменяй статус на `[~]` (IN_PROGRESS)
3. Выполни задачу
4. Поменяй статус на `[x]` (DONE)
5. Обнови таблицу прогресса

### Пример:
```diff
- ### 1.1 [ ] Создание структуры директорий
+ ### 1.1 [x] Создание структуры директорий
```

---

*Создано: 2026-01-13*
