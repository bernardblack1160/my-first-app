from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .jalali import add_months, format_jalali, gregorian_to_jalali

MONEY = Decimal("0.01")


def money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def months_due(start: tuple[int, int, int], today: tuple[int, int, int]) -> int:
    if today < start:
        return 0
    difference = (today[0] - start[0]) * 12 + today[1] - start[1]
    return difference + (1 if today[2] >= start[2] else 0)


def calculate_status(*, contract_start: tuple[int, int, int], monthly_rent: Decimal, penalty_rate: Decimal, payments: list[tuple[tuple[int, int, int], Decimal]], today: tuple[int, int, int]) -> dict:
    due_months = months_due(contract_start, today)
    due = money(monthly_rent * due_months)
    paid = money(sum((amount for paid_on, amount in payments if paid_on <= today), Decimal("0")))
    balance = money(max(Decimal("0"), due - paid))
    due_dates = [add_months(contract_start, index) for index in range(due_months)]
    paid_months = min(due_months, int(paid // monthly_rent) if monthly_rent else 0)
    first_unpaid = due_dates[paid_months] if paid_months < len(due_dates) else None
    today_g = _jalali_to_date(today)
    late_days = max(0, (today_g - _jalali_to_date(first_unpaid)).days) if first_unpaid else 0
    penalty = money(balance * penalty_rate / Decimal("100") * late_days)
    last_payment = max((item for item in payments if item[0] <= today), default=None, key=lambda item: item[0])
    if balance == 0 and due_months:
        status = "settled"
        last_event = "پرداخت کامل اجاره"
    elif balance > 0:
        status = "overdue" if late_days else "due"
        last_event = f"واریز {money(last_payment[1]):,.0f} در {format_jalali(last_payment[0])}" if last_payment else "هنوز پرداختی ثبت نشده"
    else:
        status = "not_started"
        last_event = "قرارداد هنوز شروع نشده"
    return {"months_due": due_months, "amount_due": due, "amount_paid": paid, "balance": balance, "days_late": late_days, "penalty": penalty, "status": status, "last_event": last_event}


def _jalali_to_date(value: tuple[int, int, int]) -> date:
    from .jalali import jalali_to_gregorian
    return jalali_to_gregorian(*value)
