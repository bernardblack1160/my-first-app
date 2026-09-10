from datetime import date


class JalaliError(ValueError):
    pass


def parse_jalali(value: str) -> tuple[int, int, int]:
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    parts = value.translate(translation).replace("-", "/").split("/")
    if len(parts) != 3:
        raise JalaliError("تاریخ باید به شکل ۱۴۰۵/۰۱/۰۱ باشد")
    year, month, day = (int(part) for part in parts)
    if month < 1 or month > 12 or day < 1 or day > days_in_month(year, month):
        raise JalaliError("تاریخ شمسی معتبر نیست")
    return year, month, day


def format_jalali(value: tuple[int, int, int]) -> str:
    return f"{value[0]:04d}/{value[1]:02d}/{value[2]:02d}"


def days_in_month(year: int, month: int) -> int:
    if 1 <= month <= 6:
        return 31
    if 7 <= month <= 11:
        return 30
    return 30 if is_leap_jalali(year) else 29


def is_leap_jalali(year: int) -> bool:
    return jalali_to_gregorian(year, 12, 30) != jalali_to_gregorian(year, 12, 29)


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    if jm < 1 or jm > 12 or jd < 1 or jd > days_in_month_safe(jy, jm):
        raise JalaliError("تاریخ شمسی معتبر نیست")
    jy -= 979
    days = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
    days += jd - 1
    days += (jm - 1) * 31 if jm <= 7 else (jm - 7) * 30 + 186
    days += 79
    gy = 1600 + 400 * (days // 146097)
    days %= 146097
    leap = True
    if days >= 36525:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
        else:
            leap = False
    gy += 4 * (days // 1461)
    days %= 1461
    if days >= 366:
        leap = False
        days -= 1
        gy += days // 365
        days %= 365
    month_lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while days >= month_lengths[gm - 1]:
        days -= month_lengths[gm - 1]
        gm += 1
    return date(gy, gm, days + 1)


def days_in_month_safe(year: int, month: int) -> int:
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if _is_leap_without_recursion(year) else 29


def _is_leap_without_recursion(year: int) -> bool:
    return jalali_to_gregorian_raw(year, 12, 30) != jalali_to_gregorian_raw(year, 12, 29)


def jalali_to_gregorian_raw(jy: int, jm: int, jd: int) -> date:
    jy -= 979
    days = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
    days += jd - 1 + ((jm - 1) * 31 if jm <= 7 else (jm - 7) * 30 + 186) + 79
    gy = 1600 + 400 * (days // 146097)
    days %= 146097
    leap = True
    if days >= 36525:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
        else:
            leap = False
    gy += 4 * (days // 1461)
    days %= 1461
    if days >= 366:
        leap = False
        days -= 1
        gy += days // 365
        days %= 365
    lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while days >= lengths[gm - 1]:
        days -= lengths[gm - 1]
        gm += 1
    return date(gy, gm, days + 1)


def gregorian_to_jalali(value: date) -> tuple[int, int, int]:
    gy, gm, gd = value.year, value.month, value.day
    g_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + g_days[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm = 1 + days // 31 if days < 186 else 7 + (days - 186) // 30
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd


def add_months(value: tuple[int, int, int], count: int) -> tuple[int, int, int]:
    year, month, day = value
    total = year * 12 + (month - 1) + count
    new_year, new_month = divmod(total, 12)
    new_month += 1
    return new_year, new_month, min(day, days_in_month_safe(new_year, new_month))
