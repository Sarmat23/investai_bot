import aiohttp
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import Config
from database import Database
from keyboards import main_menu_kb, asset_type_kb, holdings_list_kb
from services.analysis import DISCLAIMER
from services.moex import MoexClient
from services.news import NewsService
from services.scheduler import build_holding_block
from states import AddHolding

router = Router(name="portfolio")

ASSET_TYPE_LABEL = {"bond": "Облигация", "stock": "Акция"}


# ---------------------------------------------------------------------- #
# Добавление бумаги
# ---------------------------------------------------------------------- #
@router.message(F.text == "➕ Добавить бумагу")
async def start_add_holding(message: Message, state: FSMContext) -> None:
    await state.set_state(AddHolding.choosing_type)
    await message.answer("Выберите тип бумаги:", reply_markup=asset_type_kb())


@router.callback_query(AddHolding.choosing_type, F.data.startswith("type:"))
async def choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    asset_type = callback.data.split(":", 1)[1]
    await state.update_data(asset_type=asset_type)
    await state.set_state(AddHolding.entering_ticker)
    await callback.message.edit_text(
        f"Тип: {ASSET_TYPE_LABEL[asset_type]}.\n"
        "Введите тикер бумаги на MOEX (например, SBER для акции или SU26238RMFS4 для ОФЗ):"
    )
    await callback.answer()


@router.message(AddHolding.entering_ticker)
async def enter_ticker(message: Message, state: FSMContext) -> None:
    ticker = message.text.strip().upper()
    data = await state.get_data()
    asset_type = data["asset_type"]

    async with aiohttp.ClientSession() as session:
        moex = MoexClient(session)
        info = await moex.get_security_info(ticker, asset_type)

    if info is None:
        await message.answer(
            "Не удалось найти такую бумагу на MOEX. Проверьте тикер и попробуйте ещё раз, "
            "или /cancel для отмены."
        )
        return

    await state.update_data(ticker=ticker, name=info["name"])
    await state.set_state(AddHolding.entering_quantity)
    await message.answer(
        f"Найдено: {info['name']} ({ticker}).\nВведите количество бумаг в портфеле (число):"
    )


@router.message(AddHolding.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        quantity = float(raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число, например 10 или 1000.")
        return

    data = await state.get_data()
    user_id, _ = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await db.add_holding(
        user_id=user_id,
        ticker=data["ticker"],
        name=data["name"],
        asset_type=data["asset_type"],
        quantity=quantity,
    )
    await state.clear()
    await message.answer(
        f"Добавлено: {data['name']} ({data['ticker']}) — {quantity:g} шт.",
        reply_markup=main_menu_kb(),
    )


# ---------------------------------------------------------------------- #
# Просмотр портфеля
# ---------------------------------------------------------------------- #
@router.message(F.text == "📊 Мой портфель")
async def show_portfolio(message: Message, db: Database) -> None:
    user_id, _ = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    holdings = await db.get_holdings(user_id)
    if not holdings:
        await message.answer("Ваш портфель пуст. Добавьте бумагу через «➕ Добавить бумагу».")
        return

    lines = ["<b>Ваш портфель:</b>"]
    for h in holdings:
        label = ASSET_TYPE_LABEL.get(h["asset_type"], h["asset_type"])
        lines.append(f"• {h['name']} ({h['ticker']}) — {label}, {h['quantity']:g} шт.")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------------- #
# Удаление бумаги
# ---------------------------------------------------------------------- #
@router.message(F.text == "🗑 Удалить бумагу")
async def start_remove_holding(message: Message, db: Database) -> None:
    user_id, _ = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    holdings = await db.get_holdings(user_id)
    if not holdings:
        await message.answer("Ваш портфель пуст — нечего удалять.")
        return
    await message.answer("Выберите бумагу для удаления:", reply_markup=holdings_list_kb(holdings, "remove"))


@router.callback_query(F.data.startswith("remove:"))
async def remove_holding(callback: CallbackQuery, db: Database) -> None:
    holding_id = int(callback.data.split(":", 1)[1])
    user_id, _ = await db.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
    )
    removed = await db.remove_holding(user_id, holding_id)
    if removed:
        await callback.message.edit_text("Бумага удалена из портфеля.")
    else:
        await callback.message.edit_text("Не удалось найти эту бумагу.")
    await callback.answer()


# ---------------------------------------------------------------------- #
# Сводка по запросу (вне расписания)
# ---------------------------------------------------------------------- #
@router.message(F.text == "📰 Сводка сейчас")
async def send_digest_now(message: Message, db: Database, config: Config) -> None:
    user_id, _ = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    holdings = await db.get_holdings(user_id)
    if not holdings:
        await message.answer("Ваш портфель пуст. Добавьте бумагу через «➕ Добавить бумагу».")
        return

    status_msg = await message.answer("Собираю новости и данные по вашим бумагам…")

    async with aiohttp.ClientSession() as session:
        moex = MoexClient(session)
        news = NewsService(config.news_api_key, session)
        blocks = []
        for h in holdings:
            blocks.append(await build_holding_block(moex, news, h))

    text = "📊 <b>Сводка по вашему портфелю</b>\n\n" + "\n\n".join(blocks) + DISCLAIMER
    await status_msg.delete()
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
