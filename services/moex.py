"""
Клиент для публичного API Московской биржи (MOEX ISS).
Документация: https://iss.moex.com/iss/reference/

API не требует ключа. Используется для получения текущей цены,
доходности облигаций и истории цен акций/облигаций.
"""

import asyncio
import datetime as dt
import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://iss.moex.com/iss"

MARKET_BY_TYPE = {
    "bond": "bonds",
    "stock": "shares",
}


MOEX_TIMEOUT = aiohttp.ClientTimeout(total=12, connect=5, sock_connect=5, sock_read=8)
MOEX_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioBot/1.0)"}
MOEX_MAX_ATTEMPTS = 4
MOEX_RETRY_DELAY_SEC = 2

# Ошибки, при которых имеет смысл повторить запрос: сетевые сбои/таймауты,
# а также битый/неполный JSON в ответе (MOEX иногда отдаёт 200 OK с
# оборванным телом при сетевых проблемах — resp.json() в этом случае кидает
# json.JSONDecodeError, который является ValueError, а не aiohttp.ClientError,
# поэтому его нужно перечислить отдельно).
RETRYABLE_ERRORS = (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError)


def _rows_from_block(payload: dict, block: str) -> list[dict]:
    """Преобразует блок ISS-ответа {columns: [...], data: [[...]]} в список словарей."""
    block_data = payload.get(block)
    if not block_data:
        return []
    columns = block_data.get("columns", [])
    rows = block_data.get("data", [])
    return [dict(zip(columns, row)) for row in rows]


class MoexClient:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = session is None

    async def __aenter__(self) -> "MoexClient":
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own_session and self._session:
            await self._session.close()

    async def _get_json(self, url: str, params: dict | None = None) -> dict:
        assert self._session is not None
        last_error: Exception | None = None
        for attempt in range(1, MOEX_MAX_ATTEMPTS + 1):
            try:
                async with self._session.get(
                    url, params=params, timeout=MOEX_TIMEOUT, headers=MOEX_HEADERS
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < MOEX_MAX_ATTEMPTS:
                    logger.info(
                        "Попытка %s/%s к MOEX не удалась (%s: %s), повтор через %sс: %s",
                        attempt, MOEX_MAX_ATTEMPTS, type(e).__name__, e or "нет деталей",
                        MOEX_RETRY_DELAY_SEC, url,
                    )
                    await asyncio.sleep(MOEX_RETRY_DELAY_SEC)
        assert last_error is not None
        raise last_error

    async def get_security_info(self, ticker: str, asset_type: str) -> Optional[dict]:
        """
        Возвращает словарь с текущими рыночными данными по бумаге:
        {name, last_price, change_pct, yield (только для облигаций)} либо None,
        если бумага не найдена.
        """
        market = MARKET_BY_TYPE.get(asset_type)
        if market is None:
            raise ValueError(f"Неизвестный тип бумаги: {asset_type}")

        url = f"{BASE_URL}/engines/stock/markets/{market}/securities/{ticker}.json"
        try:
            payload = await self._get_json(url)
        except Exception as e:
            logger.warning(
                "Ошибка запроса к MOEX для %s (%s): %s: %s",
                ticker, url, type(e).__name__, e or repr(e),
            )
            return None

        sec_rows = _rows_from_block(payload, "securities")
        md_rows = _rows_from_block(payload, "marketdata")

        if not sec_rows:
            return None

        sec = sec_rows[0]
        md = md_rows[0] if md_rows else {}

        result = {
            "ticker": ticker.upper(),
            "name": sec.get("SECNAME") or sec.get("SHORTNAME") or ticker.upper(),
            "last_price": md.get("LAST") or md.get("MARKETPRICE") or sec.get("PREVPRICE"),
            "change_pct": md.get("CHANGE"),
            "yield_pct": md.get("YIELD") if asset_type == "bond" else None,
            "coupon_pct": sec.get("COUPONPERCENT") if asset_type == "bond" else None,
        }
        return result

    async def get_weekly_change_pct(self, ticker: str, asset_type: str) -> Optional[float]:
        """Изменение цены за последние ~7 календарных дней в процентах, если данных достаточно."""
        market = MARKET_BY_TYPE.get(asset_type)
        till = dt.date.today()
        frm = till - dt.timedelta(days=10)
        url = f"{BASE_URL}/history/engines/stock/markets/{market}/securities/{ticker}.json"
        params = {"from": frm.isoformat(), "till": till.isoformat()}
        try:
            payload = await self._get_json(url, params=params)
        except Exception as e:
            logger.warning(
                "Ошибка запроса истории MOEX для %s (%s): %s: %s",
                ticker, url, type(e).__name__, e or repr(e),
            )
            return None

        rows = _rows_from_block(payload, "history")
        closes = [r.get("CLOSE") for r in rows if r.get("CLOSE")]
        if len(closes) < 2:
            return None
        first, last = closes[0], closes[-1]
        if not first:
            return None
        return round((last - first) / first * 100, 2)
