from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def asset_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Облигация", callback_data="type:bond")
    builder.button(text="Акция", callback_data="type:stock")
    builder.adjust(2)
    return builder.as_markup()


def holdings_list_kb(holdings: list[dict], action_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for h in holdings:
        label = f"{h['ticker']} · {h['quantity']:g} шт."
        builder.button(text=label, callback_data=f"{action_prefix}:{h['id']}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm:yes")
    builder.button(text="❌ Отмена", callback_data="confirm:no")
    builder.adjust(2)
    return builder.as_markup()
