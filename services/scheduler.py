import logging

import aiohttp
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from database import Database
from services.analysis import analyze, DISCLAIMER
from services.moex import MoexClient
from services.news import NewsService
from services.telegram_utils import chunk_blocks

logger = logging.getLogger(__name__)

ASSET_TYPE_LABEL = {"bond": "Облигация", "stock": "Акция"}


async def build_holding_block(
    moex: MoexClient, news: NewsService, holding: dict
) -> str:
    ticker = holding["ticker"]
    asset_type = holding["asset_type"]
    quantity = holding["quantity"]

    info = await moex.get_security_info(ticker, asset_type)
    weekly_change = await moex.get_weekly_change_pct(ticker, asset_type)

    display_name = info["name"] if info else holding.get("name") or ticker
    lines = [f"<b>{display_name} ({ticker})</b> — у вас {quantity:g} шт."]

    if info and info.get("last_price") is not None:
        price_line = f"Цена: {info['last_price']:.2f}"
        if info.get("change_pct") is not None:
            price_line += f" ({info['change_pct']:+.2f}% за день)"
        lines.append(price_line)
    else:
        lines.append("Не удалось получить текущую цену с MOEX.")

    rec = analyze(asset_type, weekly_change, info or {})
    lines.append(f"Сигнал: <b>{rec.action}</b> — {rec.reason}")

    headlines = await news.get_headlines(display_name, limit=2)
    if headlines:
        lines.append("Новости:")
        for h in headlines:
            title = h["title"]
            source = f" ({h['source']})" if h.get("source") else ""
            lines.append(f"• {title}{source}")
    else:
        lines.append("Свежих новостей не найдено.")

    return "\n".join(lines)


async def send_digest_to_user(
    bot: Bot, moex: MoexClient, news: NewsService, telegram_id: int, holdings: list[dict]
) -> None:
    blocks = []
    for holding in holdings:
        try:
            block = await build_holding_block(moex, news, holding)
        except Exception as e:
            logger.exception("Ошибка формирования блока для %s: %s", holding.get("ticker"), e)
            block = f"<b>{holding['ticker']}</b>: не удалось получить данные."
        blocks.append(block)

    messages = chunk_blocks(
        blocks, header="📊 <b>Сводка по вашему портфелю</b>", footer=DISCLAIMER
    )
    for chunk in messages:
        try:
            await bot.send_message(telegram_id, chunk, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.warning("Не удалось отправить сводку пользователю %s: %s", telegram_id, e)
            break


async def run_digest_job(bot: Bot, db: Database, config: Config) -> None:
    grouped = await db.get_all_holdings_grouped()
    if not grouped:
        logger.info("Нет пользователей с непустым портфелем — рассылка пропущена.")
        return

    async with aiohttp.ClientSession() as session:
        moex = MoexClient(session)
        news = NewsService(config.news_api_key, session)
        for telegram_id, holdings in grouped.items():
            await send_digest_to_user(bot, moex, news, telegram_id, holdings)


def setup_scheduler(bot: Bot, db: Database, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_digest_job,
        trigger=IntervalTrigger(hours=config.check_interval_hours),
        args=(bot, db, config),
        id="portfolio_digest",
        replace_existing=True,
        next_run_time=None,  # первый запуск планируется явно в main.py
    )
    return scheduler
