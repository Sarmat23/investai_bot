import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace

from handlers.portfolio import is_form_input, MENU_BUTTON_TEXTS


def fake_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def run():
    # Валидный ввод тикера/количества — должен приниматься формой
    assert is_form_input(fake_message("SBER")) is True
    assert is_form_input(fake_message("SU26238RMFS4")) is True
    assert is_form_input(fake_message("10")) is True
    assert is_form_input(fake_message("12.5")) is True

    # Команды — не должны перехватываться формой (иначе /cancel не работает)
    assert is_form_input(fake_message("/cancel")) is False
    assert is_form_input(fake_message("/start")) is False

    # Кнопки главного меню — не должны перехватываться формой
    for label in MENU_BUTTON_TEXTS:
        assert is_form_input(fake_message(label)) is False, label

    # Пустое сообщение (например, стикер без текста) — не должно валить хендлер
    assert is_form_input(fake_message(None)) is False
    assert is_form_input(fake_message("")) is False

    print("test_fsm_guard.py: ALL TESTS PASSED")


if __name__ == "__main__":
    run()
