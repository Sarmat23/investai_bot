import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp

from services.moex import MoexClient, MOEX_MAX_ATTEMPTS


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self._payload


class _BadJsonResponse:
    """Отвечает 200 OK, но с телом, которое не парсится как JSON (обрыв связи посередине)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        import json as json_module
        raise json_module.JSONDecodeError("Expecting value", "", 0)


class _FlakySession:
    """Первые N вызовов кидают TimeoutError, затем отдаёт валидный ответ."""

    def __init__(self, fail_times: int, payload: dict):
        self.fail_times = fail_times
        self.calls = 0
        self.payload = payload

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise asyncio.TimeoutError()
        return _FakeResponse(self.payload)


class _BadJsonThenGoodSession:
    """Первый вызов отдаёт битый JSON (200 OK), второй — валидный ответ."""

    def __init__(self, payload: dict):
        self.calls = 0
        self.payload = payload

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls += 1
        if self.calls == 1:
            return _BadJsonResponse()
        return _FakeResponse(self.payload)


class _AlwaysFailSession:
    def __init__(self):
        self.calls = 0

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls += 1
        raise asyncio.TimeoutError()


async def run():
    # Сценарий 1: первая попытка неудачна, вторая — успешна -> ретрай должен спасти запрос
    payload = {"securities": {"columns": ["SECID"], "data": [["SBER"]]}}
    session = _FlakySession(fail_times=1, payload=payload)
    client = MoexClient(session)  # type: ignore[arg-type]

    # ускоряем тест — не ждём реальные секунды между попытками
    import services.moex as moex_module
    original_delay = moex_module.MOEX_RETRY_DELAY_SEC
    moex_module.MOEX_RETRY_DELAY_SEC = 0
    try:
        result = await client._get_json("http://fake")
        assert result == payload
        assert session.calls == 2, f"ожидалось 2 попытки, было {session.calls}"

        # Сценарий 1б: битый JSON на первой попытке (обрыв связи) -> тоже должен ретраиться
        bad_json_session = _BadJsonThenGoodSession(payload)
        client_bad_json = MoexClient(bad_json_session)  # type: ignore[arg-type]
        result2 = await client_bad_json._get_json("http://fake")
        assert result2 == payload
        assert bad_json_session.calls == 2, f"ожидалось 2 попытки, было {bad_json_session.calls}"

        # Сценарий 2: все попытки неудачны -> должно дойти до последней и поднять исключение
        fail_session = _AlwaysFailSession()
        client2 = MoexClient(fail_session)  # type: ignore[arg-type]
        raised = False
        try:
            await client2._get_json("http://fake")
        except asyncio.TimeoutError:
            raised = True
        assert raised, "ожидалось исключение после исчерпания всех попыток"
        assert fail_session.calls == MOEX_MAX_ATTEMPTS, (
            f"ожидалось {MOEX_MAX_ATTEMPTS} попыток, было {fail_session.calls}"
        )
    finally:
        moex_module.MOEX_RETRY_DELAY_SEC = original_delay

    print("test_moex_retry.py: ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
