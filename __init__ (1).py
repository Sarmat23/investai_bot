"""
Простая эвристика для формирования информационной подсказки по бумаге.

ВАЖНО: это не инвестиционная рекомендация в юридическом смысле, а базовый
сигнал на основе изменения цены/доходности за последние ~7 дней. Итоговое
сообщение пользователю всегда должно сопровождаться дисклеймером
(см. handlers/portfolio.py и services/scheduler.py).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Recommendation:
    action: str      # короткий заголовок сигнала
    reason: str       # пояснение, на чём основан сигнал


def analyze_stock(weekly_change_pct: Optional[float]) -> Recommendation:
    if weekly_change_pct is None:
        return Recommendation(
            action="Недостаточно данных",
            reason="Не удалось получить историю цены за последнюю неделю.",
        )
    if weekly_change_pct >= 7:
        return Recommendation(
            action="Возможна частичная фиксация прибыли",
            reason=f"Цена выросла на {weekly_change_pct:+.1f}% за неделю.",
        )
    if weekly_change_pct <= -7:
        return Recommendation(
            action="Возможна докупка при сохранении уверенности в компании",
            reason=f"Цена снизилась на {weekly_change_pct:+.1f}% за неделю.",
        )
    return Recommendation(
        action="Держать позицию",
        reason=f"Заметных ценовых сигналов нет (изменение {weekly_change_pct:+.1f}% за неделю).",
    )


def analyze_bond(
    weekly_change_pct: Optional[float],
    yield_pct: Optional[float],
    coupon_pct: Optional[float],
) -> Recommendation:
    if weekly_change_pct is None:
        return Recommendation(
            action="Недостаточно данных",
            reason="Не удалось получить историю цены за последнюю неделю.",
        )

    extra = ""
    if yield_pct is not None:
        extra = f" Текущая доходность к погашению ≈ {yield_pct:.1f}%."

    if weekly_change_pct <= -3:
        return Recommendation(
            action="Можно рассмотреть докупку",
            reason=f"Цена облигации снизилась на {weekly_change_pct:+.1f}% за неделю, доходность выросла.{extra}",
        )
    if weekly_change_pct >= 3:
        return Recommendation(
            action="Можно рассмотреть частичную продажу",
            reason=f"Цена облигации выросла на {weekly_change_pct:+.1f}% за неделю, доходность снизилась.{extra}",
        )
    return Recommendation(
        action="Держать позицию",
        reason=f"Цена стабильна ({weekly_change_pct:+.1f}% за неделю).{extra}",
    )


def analyze(asset_type: str, weekly_change_pct: Optional[float], info: dict) -> Recommendation:
    if asset_type == "bond":
        return analyze_bond(weekly_change_pct, info.get("yield_pct"), info.get("coupon_pct"))
    return analyze_stock(weekly_change_pct)


DISCLAIMER = (
    "\n\n⚠️ Это автоматический информационный сигнал на основе изменения цены, "
    "а не индивидуальная инвестиционная рекомендация. Перед сделками сверяйтесь "
    "с проспектом эмиссии/отчётностью эмитента и, при необходимости, "
    "консультируйтесь с лицензированным финансовым советником."
)
