from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards import main_menu_kb

router = Router(name="common")


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=main_menu_kb())
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())
