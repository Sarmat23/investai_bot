from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Портфель")],
            [KeyboardButton(text="➕ Добавить актив")],
            [KeyboardButton(text="📈 Анализ")],
        ],
        resize_keyboard=True
    )
