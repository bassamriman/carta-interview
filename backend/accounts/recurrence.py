"""Pure date-pattern rules for recurring transaction groups."""

import calendar
from datetime import date, timedelta
from enum import StrEnum


class Interval(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


_DAYS = {Interval.WEEKLY: 7, Interval.BIWEEKLY: 14}
_MONTHS = {Interval.MONTHLY: 1, Interval.QUARTERLY: 3, Interval.YEARLY: 12}


def _add_months(d: date, months: int, anchor_day: int) -> date:
    """Shift by whole months, clamping the anchor day to the month's length (31st -> 28th)."""
    year, month0 = divmod(d.year * 12 + (d.month - 1) + months, 12)
    month = month0 + 1
    return date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))


def next_expected(interval: Interval, last: date, anchor_day: int) -> date:
    if interval in _DAYS:
        return last + timedelta(days=_DAYS[interval])
    return _add_months(last, _MONTHS[interval], anchor_day)


def infer_interval(first: date, second: date) -> Interval | None:
    """The interval implied by two consecutive dates, or None when they fit no pattern."""
    for interval in Interval:
        if next_expected(interval, first, first.day) == second:
            return interval
    return None
