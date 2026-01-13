"""
Модуль форматирования Markdown → Telegram HTML
Реализует задачу 7.1 из FEATURES.md

УПРОЩЕННАЯ ВЕРСИЯ - без вложенных тегов
"""

import re
import html


def markdown_to_telegram_html(text: str) -> str:
    """
    Конвертация markdown в Telegram HTML (упрощенная версия)

    Поддерживает (БЕЗ вложенности):
    - ```code block``` → <pre>code</pre>
    - `inline code` → <code>inline</code>
    - **bold** → <b>bold</b>
    - *italic* → <i>italic</i>
    - ~~strikethrough~~ или ~strikethrough~ → <s>strikethrough</s>
    - [text](url) → <a href="url">text</a>
    - ## Headers → <b>Headers</b>
    - > quotes → ▎ quotes

    Args:
        text: Markdown текст

    Returns:
        HTML текст для Telegram
    """

    # Шаг 1: Сохраняем code blocks и inline code
    code_blocks = []
    inline_codes = []

    def save_code_block(match):
        # Убираем лишние переносы и язык
        code = match.group(1).strip()
        code_blocks.append(code)
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    def save_inline_code(match):
        code = match.group(1)
        inline_codes.append(code)
        return f"__INLINE_CODE_{len(inline_codes)-1}__"

    # Извлекаем code blocks
    text = re.sub(r'```(.*?)```', save_code_block, text, flags=re.DOTALL)

    # Извлекаем inline code
    text = re.sub(r'`([^`\n]+)`', save_inline_code, text)

    # Шаг 2: Экранируем HTML (но не маркеры)
    def escape_text(text):
        """Экранирует HTML, сохраняя маркеры"""
        parts = []
        last_end = 0

        # Находим все маркеры
        for match in re.finditer(r'__(?:CODE_BLOCK|INLINE_CODE)_\d+__', text):
            # Экранируем текст до маркера
            parts.append(html.escape(text[last_end:match.start()]))
            # Маркер как есть
            parts.append(match.group(0))
            last_end = match.end()

        # Экранируем остаток
        parts.append(html.escape(text[last_end:]))
        return ''.join(parts)

    text = escape_text(text)

    # Шаг 3: Простое форматирование (без вложенности)

    # Headers ## Text → <b>Text</b>
    text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # Links [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)

    # Strikethrough ~~text~~ или ~text~ → <s>text</s>
    # Сначала двойные, потом одинарные
    text = re.sub(r'~~([^~]+)~~', r'<s>\1</s>', text)
    text = re.sub(r'~([^~\n]+)~', r'<s>\1</s>', text)

    # Bold **text** → <b>text</b>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)

    # Italic *text* → <i>text</i> (только если не **)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', text)

    # Quotes > text → ▎ text
    text = re.sub(r'^&gt;\s+(.+)$', r'▎ \1', text, flags=re.MULTILINE)

    # Шаг 4: Восстанавливаем code
    for i, code in enumerate(code_blocks):
        # Код уже экранирован не будет, экранируем сейчас
        escaped = html.escape(code)
        text = text.replace(f"__CODE_BLOCK_{i}__", f"<pre>{escaped}</pre>")

    for i, code in enumerate(inline_codes):
        escaped = html.escape(code)
        text = text.replace(f"__INLINE_CODE_{i}__", f"<code>{escaped}</code>")

    return text


def test_formatter():
    """Тестирование форматтера"""

    # Test 1: Bold
    result = markdown_to_telegram_html("**важно**")
    assert result == "<b>важно</b>", f"Got: {result}"
    print("✅ Test 1: Bold")

    # Test 2: Italic
    result = markdown_to_telegram_html("*курсив*")
    assert result == "<i>курсив</i>", f"Got: {result}"
    print("✅ Test 2: Italic")

    # Test 3: Inline code
    result = markdown_to_telegram_html("`code`")
    assert result == "<code>code</code>", f"Got: {result}"
    print("✅ Test 3: Inline code")

    # Test 4: Code block
    result = markdown_to_telegram_html("```python\nprint('hello')\n```")
    assert result == "<pre>python\nprint(&#x27;hello&#x27;)</pre>", f"Got: {result}"
    print("✅ Test 4: Code block")

    # Test 5: Header
    result = markdown_to_telegram_html("## Заголовок")
    assert result == "<b>Заголовок</b>", f"Got: {result}"
    print("✅ Test 5: Header")

    # Test 6: Quote
    result = markdown_to_telegram_html("> цитата")
    assert result == "▎ цитата", f"Got: {result}"
    print("✅ Test 6: Quote")

    # Test 7: Strikethrough (double tilde)
    result = markdown_to_telegram_html("~~зачеркнуто~~")
    assert result == "<s>зачеркнуто</s>", f"Got: {result}"
    print("✅ Test 7: Strikethrough (double)")

    # Test 7b: Strikethrough (single tilde)
    result = markdown_to_telegram_html("~зачеркнуто~")
    assert result == "<s>зачеркнуто</s>", f"Got: {result}"
    print("✅ Test 7b: Strikethrough (single)")

    # Test 8: Link
    result = markdown_to_telegram_html("[Ссылка](https://example.com)")
    assert result == '<a href="https://example.com">Ссылка</a>', f"Got: {result}"
    print("✅ Test 8: Link")

    # Test 9: HTML escaping
    result = markdown_to_telegram_html("5 < 10 & 3 > 1")
    assert result == "5 &lt; 10 &amp; 3 &gt; 1", f"Got: {result}"
    print("✅ Test 9: HTML escaping")

    # Test 10: Mixed formatting (БЕЗ вложенности)
    text = """**Анализ продаж**

📊 Итого: 1234567₽
*Рост: +15%*
~~Старая цена~~

> Примечание: январь

Файл: `report.xlsx`
[Документация](https://docs.example.com)"""

    result = markdown_to_telegram_html(text)
    assert "<b>Анализ продаж</b>" in result
    assert "<i>Рост: +15%</i>" in result
    assert "<s>Старая цена</s>" in result
    assert "<code>report.xlsx</code>" in result
    assert '<a href="https://docs.example.com">Документация</a>' in result
    assert "▎ Примечание: январь" in result
    print("✅ Test 10: Mixed formatting")

    print("\n🎉 All tests passed!")


if __name__ == '__main__':
    test_formatter()
