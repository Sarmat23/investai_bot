"""
Получение свежих новостей по названию компании.

Если задан NEWS_API_KEY — используется https://newsapi.org (более качественная выдача).
Если ключа нет — используется бесплатный Google News RSS (без ключа, но менее точный).
"""

import logging
from typing import Optional
from urllib.parse import quote_plus

import aiohttp
import feedparser

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"


class NewsService:
    def __init__(self, api_key: str = "", session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key
        self._session = session
        self._own_session = session is None

    async def __aenter__(self) -> "NewsService":
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own_session and self._session:
            await self._session.close()

    async def get_headlines(self, query: str, limit: int = 3) -> list[dict]:
        if self.api_key:
            headlines = await self._from_newsapi(query, limit)
            if headlines:
                return headlines
        return self._from_google_rss(query, limit)

    async def _from_newsapi(self, query: str, limit: int) -> list[dict]:
        assert self._session is not None
        params = {
            "q": query,
            "language": "ru",
            "sortBy": "publishedAt",
            "pageSize": limit,
            "apiKey": self.api_key,
        }
        try:
            async with self._session.get(
                NEWSAPI_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.warning("NewsAPI вернул статус %s для %s", resp.status, query)
                    return []
                data = await resp.json()
        except Exception as e:
            logger.warning("Ошибка запроса к NewsAPI для %s: %s", query, e)
            return []

        articles = data.get("articles", [])[:limit]
        return [
            {"title": a.get("title", ""), "url": a.get("url", ""), "source": (a.get("source") or {}).get("name", "")}
            for a in articles
        ]

    def _from_google_rss(self, query: str, limit: int) -> list[dict]:
        url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.warning("Ошибка парсинга Google News RSS для %s: %s", query, e)
            return []

        entries = feed.entries[:limit]
        return [
            {"title": e.get("title", ""), "url": e.get("link", ""), "source": e.get("source", {}).get("title", "Google News")}
            for e in entries
        ]
