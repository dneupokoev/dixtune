# -*- coding: utf-8 -*-
# utils.py
dv_file_version = '261010.01'
"""Вспомогательные функции для DixTune."""

import re
from pathlib import Path

TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def transliterate(text: str) -> str:
    """Преобразовать кириллический текст в латиницу.

    Args:
        text: Исходная строка с кириллицей.

    Returns:
        Строка с транслитерированными символами.
    """
    result = []
    for char in text:
        lower_char = char.lower()
        if lower_char in TRANSLIT_MAP:
            transliterated = TRANSLIT_MAP[lower_char]
            if char.isupper():
                transliterated = transliterated.capitalize()
            result.append(transliterated)
        else:
            result.append(char)
    return ''.join(result)


def sanitize_filename(name: str) -> str:
    """Очистить строку от недопустимых символов для имени файла/папки."""
    # Заменяем недопустимые символы на нижнее подчёркивание
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', name)
    # Удаляем лишние пробелы и точки в начале/конце
    sanitized = sanitized.strip().strip('.')
    # Если строка пустая, возвращаем default
    if not sanitized:
        return "unnamed"
    return sanitized


def ensure_directory(path: Path) -> None:
    """Создать директорию, если она не существует."""
    path.mkdir(parents=True, exist_ok=True)
