from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from accounts.factories import (
    AccountFactory,
    CategoryFactory,
    MerchantFactory,
    TransactionFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_list_users(client: Client) -> None:
    users = UserFactory.create_batch(3)

    resp = client.get("/api/users")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    returned_usernames = {u["username"] for u in data}
    assert returned_usernames == {u.username for u in users}


@pytest.mark.django_db
def test_list_users_includes_transaction_count(client: Client) -> None:
    busy_user = UserFactory()
    busy_account = AccountFactory(user=busy_user)
    TransactionFactory.create_batch(3, account=busy_account)

    quiet_user = UserFactory()
    AccountFactory(user=quiet_user)

    resp = client.get("/api/users")

    assert resp.status_code == 200
    counts = {u["username"]: u["transaction_count"] for u in resp.json()}
    assert counts[busy_user.username] == 3
    assert counts[quiet_user.username] == 0


@pytest.mark.django_db
def test_list_accounts_with_balance(client: Client) -> None:
    user = UserFactory()
    account = AccountFactory(user=user, name="Checking", account_type="checking")
    TransactionFactory(account=account, amount=Decimal("500.00"), type="credit")
    TransactionFactory(account=account, amount=Decimal("150.00"), type="debit")

    resp = client.get(f"/api/users/{user.id}/accounts")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Checking"
    assert Decimal(data[0]["balance"]) == Decimal("350.00")


@pytest.mark.django_db
def test_list_transactions_search(client: Client) -> None:
    account = AccountFactory()
    category = CategoryFactory(name="Groceries")
    merchant = MerchantFactory(name="Whole Foods")
    TransactionFactory(
        account=account,
        category=category,
        merchant=merchant,
        date=date(2025, 1, 15),
    )
    TransactionFactory(
        account=account,
        date=date(2025, 1, 16),
    )

    # search by merchant name
    resp = client.get(f"/api/accounts/{account.id}/transactions?search=whole")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["merchant"]["name"] == "Whole Foods"


@pytest.mark.django_db
def test_list_users_empty(client: Client) -> None:
    resp = client.get("/api/users")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_list_users_counts_transactions_across_accounts(client: Client) -> None:
    user = UserFactory()
    TransactionFactory.create_batch(2, account=AccountFactory(user=user))
    TransactionFactory.create_batch(3, account=AccountFactory(user=user))

    resp = client.get("/api/users")

    assert [u["transaction_count"] for u in resp.json()] == [5]


@pytest.mark.django_db
def test_list_accounts_unknown_user_404(client: Client) -> None:
    assert client.get("/api/users/9999/accounts").status_code == 404


@pytest.mark.django_db
def test_list_accounts_empty_for_user_without_accounts(client: Client) -> None:
    user = UserFactory()

    resp = client.get(f"/api/users/{user.id}/accounts")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_list_accounts_zero_balance_without_transactions(client: Client) -> None:
    user = UserFactory()
    AccountFactory(user=user)

    data = client.get(f"/api/users/{user.id}/accounts").json()

    assert Decimal(data[0]["balance"]) == Decimal(0)


@pytest.mark.django_db
def test_list_accounts_negative_balance_when_debits_exceed_credits(client: Client) -> None:
    user = UserFactory()
    account = AccountFactory(user=user)
    TransactionFactory(account=account, amount=Decimal("10.00"), type="credit")
    TransactionFactory(account=account, amount=Decimal("25.50"), type="debit")

    data = client.get(f"/api/users/{user.id}/accounts").json()

    assert Decimal(data[0]["balance"]) == Decimal("-15.50")


@pytest.mark.django_db
def test_list_accounts_only_returns_own_accounts_and_fields(client: Client) -> None:
    user = UserFactory()
    mine = AccountFactory(user=user, name="Mine", account_type="savings", notes="hello")
    AccountFactory()

    data = client.get(f"/api/users/{user.id}/accounts").json()

    assert len(data) == 1
    assert data[0]["id"] == mine.id
    assert data[0]["account_type"] == "savings"
    assert data[0]["notes"] == "hello"


@pytest.mark.django_db
def test_list_accounts_balance_ignores_other_accounts(client: Client) -> None:
    user = UserFactory()
    account = AccountFactory(user=user)
    TransactionFactory(account=account, amount=Decimal("100.00"), type="credit")
    TransactionFactory(account=AccountFactory(user=user), amount=Decimal("40.00"), type="credit")

    data = {a["id"]: a for a in client.get(f"/api/users/{user.id}/accounts").json()}

    assert Decimal(data[account.id]["balance"]) == Decimal("100.00")


@pytest.mark.django_db
def test_list_transactions_unknown_account_404(client: Client) -> None:
    assert client.get("/api/accounts/9999/transactions").status_code == 404


@pytest.mark.django_db
def test_list_transactions_empty(client: Client) -> None:
    account = AccountFactory()

    resp = client.get(f"/api/accounts/{account.id}/transactions")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_list_transactions_ordered_by_date_and_scoped_to_account(client: Client) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, date=date(2025, 3, 1))
    TransactionFactory(account=account, date=date(2025, 1, 1))
    TransactionFactory(account=account, date=date(2025, 2, 1))
    TransactionFactory(account=AccountFactory(), date=date(2025, 1, 15))

    data = client.get(f"/api/accounts/{account.id}/transactions").json()

    assert [t["date"] for t in data] == ["2025-01-01", "2025-02-01", "2025-03-01"]


@pytest.mark.django_db
def test_list_transactions_shape(client: Client) -> None:
    account = AccountFactory(name="Main", account_type="checking")
    category = CategoryFactory(name="Food")
    merchant = MerchantFactory(name="Deli")
    TransactionFactory(
        account=account,
        category=category,
        merchant=merchant,
        amount=Decimal("12.34"),
        type="debit",
        date=date(2025, 5, 5),
    )

    (item,) = client.get(f"/api/accounts/{account.id}/transactions").json()

    assert Decimal(item["amount"]) == Decimal("12.34")
    assert item["type"] == "debit"
    assert item["category"] == {"id": category.id, "name": "Food"}
    assert item["merchant"] == {"id": merchant.id, "name": "Deli"}
    assert item["account"] == {"id": account.id, "name": "Main", "account_type": "checking"}


@pytest.mark.django_db
def test_list_transactions_null_category_and_merchant(client: Client) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, category=None, merchant=None)

    (item,) = client.get(f"/api/accounts/{account.id}/transactions").json()

    assert item["category"] is None
    assert item["merchant"] is None


@pytest.mark.django_db
def test_list_transactions_search_by_category_case_insensitive(client: Client) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, category=CategoryFactory(name="Groceries"))
    TransactionFactory(account=account, category=CategoryFactory(name="Travel"))

    data = client.get(f"/api/accounts/{account.id}/transactions?search=GROCER").json()

    assert [t["category"]["name"] for t in data] == ["Groceries"]


@pytest.mark.django_db
def test_list_transactions_search_no_match_and_null_fields(client: Client) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, category=None, merchant=None)
    TransactionFactory(account=account, merchant=MerchantFactory(name="Shell"))

    assert client.get(f"/api/accounts/{account.id}/transactions?search=zzz").json() == []
    assert len(client.get(f"/api/accounts/{account.id}/transactions?search=shell").json()) == 1


@pytest.mark.django_db
def test_list_transactions_empty_search_returns_all(client: Client) -> None:
    account = AccountFactory()
    TransactionFactory.create_batch(3, account=account)

    assert len(client.get(f"/api/accounts/{account.id}/transactions?search=").json()) == 3


@pytest.mark.django_db
def test_models_str() -> None:
    account = AccountFactory(name="Main", account_type="checking")
    assert str(account) == "Main (checking)"
    assert str(CategoryFactory(name="Food")) == "Food"
    merchant = MerchantFactory(name="Deli")
    assert str(merchant) == "Deli"
    t = TransactionFactory(
        account=account, date=date(2025, 1, 2), amount=Decimal("3.00"), merchant=merchant
    )
    assert str(t) == "2025-01-02 Deli 3.00"
