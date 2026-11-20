from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from accounts.factories import (
    AccountFactory,
    CategoryFactory,
    MerchantFactory,
    TransactionFactory,
)
from accounts.models import RecurringGroup


@pytest.mark.django_db
def test_group_model_constraints() -> None:
    fields = {
        "account": AccountFactory(),
        "merchant": MerchantFactory(),
        "category": CategoryFactory(),
        "amount": Decimal("9.99"),
        "type": "debit",
        "interval": "monthly",
        "anchor_day": 15,
        "first_date": date(2026, 1, 15),
        "last_date": date(2026, 2, 15),
        "count": 2,
    }
    group = RecurringGroup.objects.create(**fields)
    tx = TransactionFactory(account=fields["account"], recurring_group=group)

    assert list(group.transactions.all()) == [tx]
    with pytest.raises(IntegrityError), transaction.atomic():
        RecurringGroup.objects.create(**fields)


def _tx(account, merchant, category, d: date, amount: str = "10.00"):
    return TransactionFactory(
        account=account, merchant=merchant, category=category, date=d, amount=Decimal(amount), type="debit"
    )


@pytest.fixture
def parts():
    return AccountFactory(), MerchantFactory(), CategoryFactory()


@pytest.mark.django_db
def test_assign_on_create(parts) -> None:
    a, m, c = parts
    first = _tx(a, m, c, date(2026, 1, 31))
    assert first.recurring_group is None
    second = _tx(a, m, c, date(2026, 2, 28))
    third = _tx(a, m, c, date(2026, 3, 31))

    group = RecurringGroup.objects.get()
    assert (group.interval, group.count, group.last_date) == ("monthly", 3, date(2026, 3, 31))
    first.refresh_from_db()
    assert {first.recurring_group_id, second.recurring_group_id, third.recurring_group_id} == {group.id}


@pytest.mark.django_db
def test_changed_attribute_or_pattern_starts_new_group(parts) -> None:
    a, m, c = parts
    for d in (date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)):
        _tx(a, m, c, d)
    other_amount = _tx(a, m, c, date(2026, 4, 15), "11.00")
    off_pattern = _tx(a, m, c, date(2026, 4, 20))

    assert RecurringGroup.objects.count() == 1
    assert other_amount.recurring_group is None
    assert off_pattern.recurring_group is None
    # the changed-amount series becomes its own group
    _tx(a, m, c, date(2026, 5, 15), "11.00")
    assert RecurringGroup.objects.count() == 2


@pytest.mark.django_db
def test_assignment_is_idempotent(parts) -> None:
    from accounts.recurring import assign_recurring_group

    a, m, c = parts
    _tx(a, m, c, date(2026, 1, 1))
    last = _tx(a, m, c, date(2026, 1, 8))
    assign_recurring_group(last)
    last.refresh_from_db()
    assign_recurring_group(last)

    group = RecurringGroup.objects.get()
    assert group.count == 2
