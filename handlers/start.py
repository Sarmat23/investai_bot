
from aiogram import Router, types
from services.user_service import UserService
from keyboards.menu import main_menu

router = Router()

@router.message(commands=["start"])
async def start(message: types.Message):
    user = await UserService.get_user(message.from_user.id)

    if not user:
        await UserService.create_user(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name,
            username=message.from_user.username
        )

        await message.answer(
            "👋 Добро пожаловать в InvestAI!\n\n"
            "Я помогу вести ваш инвестиционный портфель."
        )

    await message.answer(
        "Главное меню:",
        reply_markup=main_menu()
    )
