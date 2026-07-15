from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import Database
from keyboards import main_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    user_id, is_new = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if is_new:
        text = (
            f"Здравствуйте, {message.from_user.full_name}! Вы зарегистрированы. 🎉\n\n"
            "Этот бот помогает следить за портфелем облигаций и акций: "
            "раз в несколько часов он присылает краткие новости по вашим бумагам "
            "и информационный сигнал (не финансовая рекомендация в юридическом смысле).\n\n"
            "Добавьте первую бумагу через кнопку «➕ Добавить бумагу»."
        )
    else:
        text = f"С возвращением, {message.from_user.full_name}! Выберите действие в меню."

    await message.answer(text, reply_markup=main_menu_kb())
