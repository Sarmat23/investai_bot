"""
Telegram ограничивает длину текстового сообщения 4096 символами
(https://core.telegram.org/bots/api#sendmessage, поле text).
Портфель из нескольких бумаг с новостями легко превышает этот лимит,
поэтому сводку нужно резать на несколько сообщений.
"""

# Берём с запасом от официального лимита в 4096, чтобы не словить
# ошибку из-за HTML-разметки/отступов.
TELEGRAM_SAFE_LIMIT = 3500


def _split_long_block(block: str, max_len: int) -> list[str]:
    """Режет один слишком длинный блок построчно (используется как fallback)."""
    lines = block.split("\n")
    parts: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > max_len and current:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def chunk_blocks(
    blocks: list[str],
    header: str = "",
    footer: str = "",
    max_len: int = TELEGRAM_SAFE_LIMIT,
) -> list[str]:
    """
    Собирает список независимых текстовых блоков (по одному на бумагу) в
    минимально возможное число сообщений, каждое из которых не превышает
    max_len символов. header добавляется в начало первого сообщения,
    footer — в конец последнего.
    """
    normalized_blocks: list[str] = []
    for block in blocks:
        if len(block) > max_len:
            normalized_blocks.extend(_split_long_block(block, max_len))
        else:
            normalized_blocks.append(block)

    chunks: list[str] = []
    current = header.rstrip() if header else ""

    for block in normalized_blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > max_len and current:
            chunks.append(current)
            current = block
        else:
            current = candidate

    if footer:
        candidate = f"{current}{footer}" if current else footer.strip()
        if len(candidate) > max_len and current:
            chunks.append(current)
            chunks.append(footer.strip())
        else:
            current = candidate
            chunks.append(current)
    elif current:
        chunks.append(current)

    if not chunks and header:
        chunks.append(header.strip())
    return chunks
