"""
Асинхронный слой доступа к SQLite базе данных.

Таблицы:
    users     — зарегистрированные пользователи бота
    portfolio — бумаги (облигации/акции), добавленные пользователем
"""

import datetime as dt
import os
from typing import Iterable, Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username    TEXT,
    full_name   TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    ticker      TEXT NOT NULL,
    name        TEXT,
    asset_type  TEXT NOT NULL CHECK (asset_type IN ('bond', 'stock')),
    quantity    REAL NOT NULL,
    added_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio (user_id);
"""


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        dirname = os.path.dirname(self.path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
            await self._merge_duplicate_holdings(db)
            # Уникальный индекс защищает от повторного появления дублей на
            # уровне БД (например, при параллельных запросах). Создаём его
            # только после объединения дублей выше, иначе CREATE UNIQUE INDEX
            # упадёт с ошибкой на уже существующих повторах.
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_unique "
                "ON portfolio (user_id, ticker, asset_type)"
            )
            await db.commit()

    @staticmethod
    async def _merge_duplicate_holdings(db: aiosqlite.Connection) -> None:
        """
        Разовая миграция для баз, созданных до появления уникальности по
        (user_id, ticker, asset_type): схлопывает задублированные строки одной
        бумаги в одну, суммируя количество, и оставляет самую раннюю запись.
        """
        cur = await db.execute(
            """
            SELECT user_id, ticker, asset_type, MIN(id) AS keep_id, SUM(quantity) AS total_qty
            FROM portfolio
            GROUP BY user_id, ticker, asset_type
            HAVING COUNT(*) > 1
            """
        )
        duplicate_groups = await cur.fetchall()
        if not duplicate_groups:
            return

        for user_id, ticker, asset_type, keep_id, total_qty in duplicate_groups:
            await db.execute(
                "UPDATE portfolio SET quantity = ? WHERE id = ?", (total_qty, keep_id)
            )
            await db.execute(
                "DELETE FROM portfolio WHERE user_id = ? AND ticker = ? AND asset_type = ? AND id != ?",
                (user_id, ticker, asset_type, keep_id),
            )
        await db.commit()

    # ------------------------------------------------------------------ #
    # Пользователи
    # ------------------------------------------------------------------ #
    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str], full_name: Optional[str]
    ) -> tuple[int, bool]:
        """Возвращает (internal_user_id, is_new)."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cur.fetchone()
            if row:
                return row[0], False

            now = dt.datetime.utcnow().isoformat()
            cur = await db.execute(
                "INSERT INTO users (telegram_id, username, full_name, created_at) "
                "VALUES (?, ?, ?, ?)",
                (telegram_id, username, full_name, now),
            )
            await db.commit()
            return cur.lastrowid, True

    async def get_all_users(self) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Портфель
    # ------------------------------------------------------------------ #
    async def add_holding(
        self,
        user_id: int,
        ticker: str,
        name: str,
        asset_type: str,
        quantity: float,
    ) -> tuple[int, float, bool]:
        """
        Добавляет бумагу в портфель. Если у пользователя уже есть такая же
        бумага (совпадают ticker и asset_type) — не создаёт новую строку,
        а увеличивает существующее количество.

        Возвращает (holding_id, итоговое_количество, was_merged), где
        was_merged=True означает, что количество было прибавлено к уже
        существующей позиции, а False — что создана новая строка.
        """
        ticker = ticker.upper()
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT id, quantity FROM portfolio WHERE user_id = ? AND ticker = ? AND asset_type = ?",
                (user_id, ticker, asset_type),
            )
            existing = await cur.fetchone()

            if existing:
                holding_id, existing_qty = existing
                new_qty = existing_qty + quantity
                await db.execute(
                    "UPDATE portfolio SET quantity = ?, name = ? WHERE id = ?",
                    (new_qty, name, holding_id),
                )
                await db.commit()
                return holding_id, new_qty, True

            now = dt.datetime.utcnow().isoformat()
            cur = await db.execute(
                "INSERT INTO portfolio (user_id, ticker, name, asset_type, quantity, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, ticker, name, asset_type, quantity, now),
            )
            await db.commit()
            return cur.lastrowid, quantity, False

    async def get_holdings(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM portfolio WHERE user_id = ? ORDER BY added_at", (user_id,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def remove_holding(self, user_id: int, holding_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM portfolio WHERE id = ? AND user_id = ?", (holding_id, user_id)
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_all_holdings_grouped(self) -> dict[int, list[dict]]:
        """Возвращает {telegram_id: [holding, ...]} для всех пользователей с непустым портфелем."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT u.telegram_id AS telegram_id, p.*
                FROM portfolio p
                JOIN users u ON u.id = p.user_id
                ORDER BY u.telegram_id
                """
            )
            rows = [dict(r) for r in await cur.fetchall()]

        grouped: dict[int, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row["telegram_id"], []).append(row)
        return grouped
