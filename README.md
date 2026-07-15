import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    news_api_key: str
    db_path: str
    check_interval_hours: int


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен, "
            "полученный у @BotFather."
        )

    return Config(
        bot_token=bot_token,
        news_api_key=os.getenv("NEWS_API_KEY", "").strip(),
        db_path=os.getenv("DB_PATH", "bot.db").strip(),
        check_interval_hours=int(os.getenv("CHECK_INTERVAL_HOURS", "6")),
    )
