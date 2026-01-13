"""
Модуль форматирования Markdown → Telegram HTML
Реализует задачу 7.1 из FEATURES.md
"""

import re
import html


def markdown_to_telegram_html(text: str) -> str:
    """
    Конвертация markdown в Telegram HTML

    Поддерживает:
    - **bold** → <b>bold</b>
    - *italic* → <i>italic</i>
    - __underline__ → <u>underline</u>
    - `inline code` → <code>inline code</code>
    - ```code block``` → <pre>code block</pre>
    - ## Headers → <b>Headers</b>
    - > quotes → ▎ quotes

    Args:
        text: Markdown текст

    Returns:
        HTML текст для Telegram
    """

    # 1. Сначала экранируем HTML-символы (кроме тех что мы сами добавим)
    # НО сначала сохраняем code blocks чтобы их не повредить

    # Временные маркеры для code blocks
    code_blocks = []
    inline_codes = []

    # Извлекаем triple backtick code blocks
    def save_code_block(match):
        # Группа 1 - всё содержимое между ```
        code_blocks.append(match.group(1))
        return f"<<CODE_BLOCK_{len(code_blocks)-1}>>"

    # Захватываем всё между ``` (включая опциональный язык и переносы)
    text = re.sub(r'```(.*?)```', save_code_block, text, flags=re.DOTALL)

    # Извлекаем inline code
    def save_inline_code(match):
        inline_codes.append(match.group(1))
        return f"<<INLINE_CODE_{len(inline_codes)-1}>>"

    text = re.sub(r'`([^`\n]+)`', save_inline_code, text)

    # 2. Обрабатываем markdown ДО экранирования HTML

    # Headers (## Header) → <b>Header</b>
    text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # Bold (**text**) → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic (*text*) → <i>text</i>
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)

    # Underline (__text__) → <u>text</u>
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)

    # Quotes (> text) → ▎ text
    text = re.sub(r'^>\s+(.+)$', r'▎ \1', text, flags=re.MULTILINE)

    # 3. Экранируем HTML в оставшемся тексте
    # Но НЕ внутри наших HTML-тегов и маркеров
    # Для простоты: заменяем только опасные символы вне тегов
    def escape_non_tags(text):
        """Экранирует HTML, но сохраняет наши теги"""
        # Сохраняем наши HTML-теги
        tags_to_save = ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>', '<code>', '</code>', '<pre>', '</pre>']

        # Временно заменяем теги на маркеры
        tag_markers = {}
        for i, tag in enumerate(tags_to_save):
            marker = f"<<HTML_TAG_{i}>>"
            tag_markers[marker] = tag
            text = text.replace(tag, marker)

        # Экранируем HTML
        text = html.escape(text)

        # Восстанавливаем теги
        for marker, tag in tag_markers.items():
            text = text.replace(marker, tag)

        return text

    text = escape_non_tags(text)

    # 7. Восстанавливаем code blocks
    for i, code in enumerate(code_blocks):
        # Убираем лишние переносы строк в начале и конце
        code = code.strip()
        # Экранируем содержимое code block
        escaped_code = html.escape(code)
        text = text.replace(f"<<CODE_BLOCK_{i}>>", f"<pre>{escaped_code}</pre>")

    # 8. Восстанавливаем inline code
    for i, code in enumerate(inline_codes):
        # Экранируем содержимое inline code
        escaped_code = html.escape(code)
        text = text.replace(f"<<INLINE_CODE_{i}>>", f"<code>{escaped_code}</code>")

    return text


def test_formatter():
    """Тестирование форматтера"""

    # Test 1: Bold
    assert markdown_to_telegram_html("**важно**") == "<b>важно</b>"
    print("✅ Test 1 passed: Bold")

    # Test 2: Italic
    assert markdown_to_telegram_html("*курсив*") == "<i>курсив</i>"
    print("✅ Test 2 passed: Italic")

    # Test 3: Inline code
    assert markdown_to_telegram_html("`code`") == "<code>code</code>"
    print("✅ Test 3 passed: Inline code")

    # Test 4: Code block
    result = markdown_to_telegram_html("```python\nprint('hello')\n```")
    # html.escape преобразует кавычки в &#x27;
    assert result == "<pre>python\nprint(&#x27;hello&#x27;)</pre>"
    print("✅ Test 4 passed: Code block")

    # Test 5: Header
    assert markdown_to_telegram_html("## Заголовок") == "<b>Заголовок</b>"
    print("✅ Test 5 passed: Header")

    # Test 6: Quote
    assert markdown_to_telegram_html("> цитата") == "▎ цитата"
    print("✅ Test 6 passed: Quote")

    # Test 7: HTML escaping
    assert markdown_to_telegram_html("5 < 10 & 3 > 1") == "5 &lt; 10 &amp; 3 &gt; 1"
    print("✅ Test 7 passed: HTML escaping")

    # Test 8: Complex example
    text = """**Анализ продаж:**

📊 Итого: 1 234 567₽
📈 Рост: +15%

> Примечание: данные за январь

Код:
```python
import pandas as pd
df.head()
```

Подробнее в `report.xlsx`"""

    result = markdown_to_telegram_html(text)
    assert "<b>Анализ продаж:</b>" in result
    assert "<pre>python\nimport pandas as pd\ndf.head()</pre>" in result
    assert "<code>report.xlsx</code>" in result
    assert "▎ Примечание: данные за январь" in result
    print("✅ Test 8 passed: Complex example")

    print("\n🎉 All tests passed!")


if __name__ == '__main__':
    test_formatter()
