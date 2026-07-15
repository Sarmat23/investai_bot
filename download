import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis import analyze, analyze_stock, analyze_bond


def run():
    # Акция сильно выросла -> сигнал на фиксацию прибыли
    r = analyze_stock(8.5)
    assert "фиксац" in r.action.lower(), r.action

    # Акция сильно упала -> сигнал на докупку
    r = analyze_stock(-9.0)
    assert "докуп" in r.action.lower(), r.action

    # Акция без изменений -> держать
    r = analyze_stock(0.5)
    assert "держать" in r.action.lower(), r.action

    # Нет данных
    r = analyze_stock(None)
    assert "недостаточно" in r.action.lower(), r.action

    # Облигация просела в цене -> докупка
    r = analyze_bond(-4.0, yield_pct=15.2, coupon_pct=12.0)
    assert "докуп" in r.action.lower(), r.action
    assert "15.2" in r.reason

    # Облигация выросла в цене -> частичная продажа
    r = analyze_bond(5.0, yield_pct=10.0, coupon_pct=12.0)
    assert "продаж" in r.action.lower(), r.action

    # Универсальная функция analyze() маршрутизирует по типу
    r = analyze("bond", -4.0, {"yield_pct": 15.0, "coupon_pct": 12.0})
    assert "докуп" in r.action.lower()

    r = analyze("stock", 8.0, {})
    assert "фиксац" in r.action.lower()

    print("test_analysis.py: ALL TESTS PASSED")


if __name__ == "__main__":
    run()
