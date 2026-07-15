import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

    holding_id = await db.add_holding(user_id, "SBER", "Сбербанк", "stock", 10)
    await db.add_holding(user_id, "SU26238RMFS4", "ОФЗ 26238", "bond", 5)

    holdings = await db.get_holdings(user_id)
    assert len(holdings) == 2, f"ожидалось 2 бумаги, получено {len(holdings)}"

    grouped = await db.get_all_holdings_grouped()
    assert 111 in grouped
    assert len(grouped[111]) == 2

    removed = await db.remove_holding(user_id, holding_id)
    assert removed is True

    holdings_after = await db.get_holdings(user_id)
    assert len(holdings_after) == 1

    os.remove(path)
    print("test_database.py: ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
