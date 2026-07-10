from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from services.user_service import UserService
from keyboards.menu import main_menu

router = Router()


class RegisterState(StatesGroup):
    waiting_name = State()


@router.message(Command("register"))
async def register_start(message: Message, state: FSMContext):
    """
    Запуск регистрации.
    """

    user = await UserService.get_user(message.from_user.id)

    if user:
        await message.answer(
            "✅ Вы уже зарегистрированы.",
            reply_markup=main_menu()
        )
        return

    await state.set_state(RegisterState.waiting_name)

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Введите Ваше имя:"
    )


@router.message(RegisterState.waiting_name)
async def register_name(message: Message, state: FSMContext):

    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "❌ Имя должно содержать минимум 2 символа.\n"
            "Попробуйте еще раз."
        )
        return

    await UserService.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        name=name
    )

    await state.clear()

    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"Добро пожаловать, {name}!",
        reply_markup=main_menu()
    )
