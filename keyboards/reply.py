from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить бумагу")],
            [KeyboardButton(text="📊 Мой портфель")],
            [KeyboardButton(text="🗑 Удалить бумагу")],
            [KeyboardButton(text="📰 Сводка сейчас")],
        ],
        resize_keyboard=True,
    )
