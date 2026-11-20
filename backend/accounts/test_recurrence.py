from datetime import date

import pytest

from accounts.recurrence import Interval, infer_interval, next_expected


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (date(2026, 1, 1), date(2026, 1, 8), Interval.WEEKLY),
        (date(2026, 1, 1), date(2026, 1, 15), Interval.BIWEEKLY),
        (date(2026, 1, 15), date(2026, 2, 15), Interval.MONTHLY),
        (date(2026, 1, 31), date(2026, 2, 28), Interval.MONTHLY),
        (date(2026, 1, 15), date(2026, 4, 15), Interval.QUARTERLY),
        (date(2026, 1, 15), date(2027, 1, 15), Interval.YEARLY),
        (date(2026, 1, 1), date(2026, 1, 10), None),
        (date(2026, 1, 15), date(2026, 2, 16), None),
    ],
)
def test_infer_interval(first: date, second: date, expected: Interval | None) -> None:
    assert infer_interval(first, second) == expected


def test_month_end_variation_returns_to_anchor_day() -> None:
    assert next_expected(Interval.MONTHLY, date(2026, 2, 28), 31) == date(2026, 3, 31)
    assert next_expected(Interval.MONTHLY, date(2026, 12, 15), 15) == date(2027, 1, 15)
