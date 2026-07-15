import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.telegram_utils import chunk_blocks


def run():
    # Всё помещается в одно сообщение
    chunks = chunk_blocks(["A" * 100, "B" * 100], header="H", footer="F", max_len=3500)
    assert len(chunks) == 1
    assert chunks[0].startswith("H")
    assert chunks[0].endswith("F")

    # Ни одно сообщение не должно превышать max_len
    max_len = 200
    blocks = [f"Блок {i}: " + ("x" * 150) for i in range(10)]
    chunks = chunk_blocks(blocks, header="Заголовок", footer="\n\nДисклеймер", max_len=max_len)
    assert len(chunks) > 1, "ожидалось разбиение на несколько сообщений"
    for c in chunks:
        assert len(c) <= max_len, f"чанк превышает лимит: {len(c)} > {max_len}"

    # Ни один блок не потерян — каждый исходный блок должен встречаться целиком
    # хотя бы в одном из чанков (проверяем по маркеру "Блок i:")
    joined = "\n".join(chunks)
    for i in range(10):
        assert f"Блок {i}:" in joined

    # Один блок больше max_len — должен быть разрезан построчно, а не выброшен
    huge_block = "\n".join(f"строка {i} " + "y" * 50 for i in range(20))
    chunks = chunk_blocks([huge_block], max_len=200)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 200
    joined = "\n".join(chunks)
    for i in range(20):
        assert f"строка {i} " in joined

    # Пустой список блоков без header/footer -> пустой результат, без падения
    assert chunk_blocks([]) == []

    print("test_telegram_utils.py: ALL TESTS PASSED")


if __name__ == "__main__":
    run()
