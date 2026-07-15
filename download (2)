import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiosqlite

from database import Database


async def run():
    path = "/tmp/test_bond_bot.db"
    if os.path.exists(path):
        os.remove(path)

    db = Database(path)
    await db.init()

    user_id, is_new = await db.get_or_create_user(111, "ivan", "Ivan Ivanov")
    assert is_new is True, "первый вызов должен создать пользователя"

    user_id2, is_new2 = await db.get_or_create_user(111, "ivan", "Ivan Ivanov")
    assert is_new2 is False, "повторный вызов не должен создавать дубликат"
    assert user_id == user_id2

    holding_id, total_qty, was_merged = await db.add_holding(user_id, "SBER", "Сбербанк", "stock", 10)
    assert was_merged is False
    assert total_qty == 10
    await db.add_holding(user_id, "SU26238RMFS4", "ОФЗ 26238", "bond", 5)

    holdings = await db.get_holdings(user_id)
    assert len(holdings) == 2, f"ожидалось 2 бумаги, получено {len(holdings)}"

    # Повторное добавление того же тикера и типа -> не новая строка, а суммирование
    holding_id2, total_qty2, was_merged2 = await db.add_holding(
        user_id, "sber", "Сбербанк", "stock", 4  # намеренно нижним регистром, как ISIN/тикер
    )
    assert was_merged2 is True, "повторное добавление той же бумаги должно суммироваться, а не дублироваться"
    assert holding_id2 == holding_id, "должна обновиться та же строка"
    assert total_qty2 == 14, f"ожидалось 10+4=14, получено {total_qty2}"

    holdings_after_merge = await db.get_holdings(user_id)
    assert len(holdings_after_merge) == 2, "количество строк не должно вырасти при повторном добавлении"
    sber_row = next(h for h in holdings_after_merge if h["ticker"] == "SBER")
    assert sber_row["quantity"] == 14

    grouped = await db.get_all_holdings_grouped()
    assert 111 in grouped
    assert len(grouped[111]) == 2

    removed = await db.remove_holding(user_id, holding_id)
    assert removed is True

    holdings_after = await db.get_holdings(user_id)
    assert len(holdings_after) == 1

    os.remove(path)

    # Отдельно проверяем миграцию: если в базе уже были дубли (например, из
    # версии бота без суммирования), Database.init() должен их объединить.
    migration_path = "/tmp/test_bond_bot_migration.db"
    if os.path.exists(migration_path):
        os.remove(migration_path)

    async with aiosqlite.connect(migration_path) as raw_db:
        await raw_db.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT, full_name TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, ticker TEXT NOT NULL, name TEXT,
                asset_type TEXT NOT NULL, quantity REAL NOT NULL, added_at TEXT NOT NULL
            );
            """
        )
        await raw_db.execute(
            "INSERT INTO users (id, telegram_id, username, full_name, created_at) "
            "VALUES (1, 222, 'petr', 'Petr Petrov', '2024-01-01')"
        )
        # Три "старых" дублирующихся строки для одной и той же облигации
        for qty, ts in [(3, "2024-01-01"), (2, "2024-02-01"), (5, "2024-03-01")]:
            await raw_db.execute(
                "INSERT INTO portfolio (user_id, ticker, name, asset_type, quantity, added_at) "
                "VALUES (1, 'SU26238RMFS4', 'ОФЗ 26238', 'bond', ?, ?)",
                (qty, ts),
            )
        await raw_db.commit()

    migrated_db = Database(migration_path)
    await migrated_db.init()  # должен объединить дубли и создать уникальный индекс

    holdings_migrated = await migrated_db.get_holdings(1)
    assert len(holdings_migrated) == 1, (
        f"после миграции должна остаться одна строка, получено {len(holdings_migrated)}"
    )
    assert holdings_migrated[0]["quantity"] == 10, "3 + 2 + 5 = 10"

    # Повторный init() не должен падать на уже созданном уникальном индексе
    await migrated_db.init()

    os.remove(migration_path)
    print("test_database.py: ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
