import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers import get_root_router
from services.scheduler import setup_scheduler, run_digest_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.init()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Пробрасываем общие зависимости во все хендлеры
    dp["db"] = db
    dp["config"] = config

    dp.include_router(get_root_router())

    scheduler = setup_scheduler(bot, db, config)
    scheduler.start()
    # Первый запуск сразу через интервал (а не мгновенно), чтобы не спамить при рестартах бота
    scheduler.reschedule_job(
        "portfolio_digest",
        trigger="interval",
        hours=config.check_interval_hours,
    )

    logger.info("Бот запускается. Сводки будут отправляться каждые %s ч.", config.check_interval_hours)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
