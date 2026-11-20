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
