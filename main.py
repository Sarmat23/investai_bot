
import asyncio
from aiogram import Bot, Dispatcher
from config import Config
from database.db import init_db
from handlers import start
from utils.logger import logger

async def main():
    await init_db()

    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)

    logger.info("Bot started")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
