from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from accounts.factories import (
    AccountFactory,
    CategoryFactory,
    MerchantFactory,
    TransactionFactory,
)


@pytest.mark.django_db
def test_group_endpoints(client: Client) -> None:
    account = AccountFactory()
    merchant, category = MerchantFactory(), CategoryFactory()
    for d in (date(2026, 1, 1), date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22), date(2026, 1, 29)):
        TransactionFactory(
            account=account, merchant=merchant, category=category, date=d, amount=Decimal("5.00"), type="debit"
        )

    groups = client.get(f"/api/users/{account.user_id}/recurring-groups").json()  # ty: ignore[unresolved-attribute]
    assert len(groups) == 1
    assert (groups[0]["interval"], groups[0]["count"]) == ("weekly", 5)

    url = f"/api/recurring-groups/{groups[0]['id']}/transactions"
    first = client.get(url, {"limit": 2}).json()
    assert [t["date"] for t in first["items"]] == ["2026-01-01", "2026-01-08"]
    second = client.get(url, {"limit": 2, "after": first["next_cursor"]}).json()
    assert [t["date"] for t in second["items"]] == ["2026-01-15", "2026-01-22"]
    last = client.get(url, {"limit": 2, "after": second["next_cursor"]}).json()
    assert [t["date"] for t in last["items"]] == ["2026-01-29"]
    assert last["next_cursor"] is None


@pytest.mark.django_db
def test_bad_cursor_and_unknown_ids(client: Client) -> None:
    assert client.get("/api/users/999/recurring-groups").status_code == 404
    assert client.get("/api/recurring-groups/999/transactions").status_code == 404


@pytest.mark.django_db
def test_before_cursor_pages_backwards(client: Client) -> None:
    account = AccountFactory()
    merchant, category = MerchantFactory(), CategoryFactory()
    for d in (date(2026, 1, 1), date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22)):
        TransactionFactory(
            account=account, merchant=merchant, category=category, date=d, amount=Decimal("5.00"), type="debit"
        )
    gid = client.get(f"/api/users/{account.user_id}/recurring-groups").json()[0]["id"]  # ty: ignore[unresolved-attribute]
    url = f"/api/recurring-groups/{gid}/transactions"
    tail = client.get(url, {"limit": 2, "after": client.get(url, {"limit": 2}).json()["next_cursor"]}).json()
    back = client.get(url, {"limit": 2, "before": tail["previous_cursor"]}).json()
    assert [t["date"] for t in back["items"]] == ["2026-01-01", "2026-01-08"]
    assert back["previous_cursor"] is None
    assert back["next_cursor"] is not None
