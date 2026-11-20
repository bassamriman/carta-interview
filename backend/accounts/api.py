import base64
from typing import Final
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from pydantic import ConfigDict
from ninja import Query, Router, Schema
from ninja.errors import HttpError

from .models import Account, Category, Merchant, Transaction

router = Router()


class UserOut(Schema):
    id: int
    username: str
    email: str
    transaction_count: int


class AccountOut(Schema):
    id: int
    name: str
    account_type: str
    notes: str | None
    balance: Decimal


class CategoryOut(Schema):
    id: int
    name: str


class MerchantOut(Schema):
    id: int
    name: str


class TransactionAccountOut(Schema):
    id: int
    name: str
    account_type: str


class TransactionOut(Schema):
    id: int
    date: date
    amount: Decimal
    category: CategoryOut | None
    merchant: MerchantOut | None
    type: str
    account: TransactionAccountOut


@router.get("/users", response=list[UserOut])
def list_users(request: HttpRequest) -> list[UserOut]:
    users = User.objects.annotate(transaction_count=Count("accounts__transactions"))
    return [
        UserOut(
            id=u.id,  # ty: ignore[unresolved-attribute]
            username=u.username,
            email=u.email,
            transaction_count=u.transaction_count,  # ty: ignore[unresolved-attribute]
        )
        for u in users
    ]


def _compute_balance(transactions: list[Transaction]) -> Decimal:
    return sum(
        (t.amount if t.type == Transaction.TransactionType.CREDIT else -t.amount for t in transactions),
        Decimal(0),
    )


@router.get("/users/{user_id}/accounts", response=list[AccountOut])
def list_accounts(request: HttpRequest, user_id: int) -> list[AccountOut]:
    user = get_object_or_404(User, id=user_id)
    accounts = user.accounts.all()  # ty: ignore[unresolved-attribute]
    return [
        AccountOut(
            id=a.id,
            name=a.name,
            account_type=a.account_type,
            notes=a.notes,
            balance=_compute_balance(list(a.transactions.all())),
        )
        for a in accounts
    ]


class TransactionPageOut(Schema):
    model_config = ConfigDict(frozen=True)

    items: tuple[TransactionOut, ...]
    next_cursor: str | None
    previous_cursor: str | None


MAX_LIMIT: Final = 200
NARROW_MATCHES: Final = 20


def encode_cursor(t: Transaction) -> str:
    raw = f"{t.date.isoformat()}|{t.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[date, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        day, pk = raw.split("|")
        return date.fromisoformat(day), int(pk)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HttpError(400, "Invalid cursor") from exc


def _after(qs: QuerySet[Transaction], key: tuple[date, int]) -> QuerySet[Transaction]:
    day, pk = key
    return qs.filter(Q(date__gt=day) | Q(date=day, id__gt=pk))


def _before(qs: QuerySet[Transaction], key: tuple[date, int]) -> QuerySet[Transaction]:
    day, pk = key
    return qs.filter(Q(date__lt=day) | Q(date=day, id__lt=pk))


def _rows(qs: QuerySet[Transaction], term: str, *, backward: bool, n: int) -> list[Transaction]:
    order = ("-date", "-id") if backward else ("date", "id")
    if not term:
        return list(qs.order_by(*order)[:n])
    merchants = Merchant.objects.filter(name__icontains=term)
    categories = Category.objects.filter(name__icontains=term)
    merchant_ids = list(merchants.values_list("id", flat=True)[: NARROW_MATCHES + 1])
    category_ids = list(categories.values_list("id", flat=True)[: NARROW_MATCHES + 1])
    if len(merchant_ids) > NARROW_MATCHES or len(category_ids) > NARROW_MATCHES:
        # Broad term: matches are dense, so the date-ordered scan finds n rows quickly.
        broad = qs.filter(Q(merchant_id__in=merchants.values("id")) | Q(category_id__in=categories.values("id")))
        return list(broad.order_by(*order)[:n])
    # Narrow term: one index-bound query per match (account, merchant|category, date, id), merged here.
    # A scan ordered by date would read the whole account when few rows match.
    branches = [qs.filter(merchant_id=i) for i in merchant_ids] + [qs.filter(category_id=i) for i in category_ids]
    unique = {t.id: t for branch in branches for t in branch.order_by(*order)[:n]}
    return sorted(unique.values(), key=lambda t: (t.date, t.id), reverse=backward)[:n]


def _to_out(t: Transaction, account: Account) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        date=t.date,
        amount=t.amount,
        category=CategoryOut(id=t.category.id, name=t.category.name) if t.category else None,
        merchant=MerchantOut(id=t.merchant.id, name=t.merchant.name) if t.merchant else None,
        type=t.type,
        account=TransactionAccountOut(id=account.id, name=account.name, account_type=account.account_type),
    )


@router.get("/accounts/{account_id}/transactions", response=TransactionPageOut)
def list_transactions(
    request: HttpRequest,
    account_id: int,
    search: str = "",
    limit: int = Query(50, ge=1, le=MAX_LIMIT),  # ty: ignore[call-non-callable]  # ninja Query is an alias ty cannot call
    after: str | None = None,
    before: str | None = None,
) -> TransactionPageOut:
    if after and before:
        raise HttpError(400, "Pass only one of 'after' and 'before'")
    account = get_object_or_404(Account, id=account_id)
    qs = Transaction.objects.filter(account_id=account_id).select_related("category", "merchant")

    if before:
        rows = _rows(_before(qs, decode_cursor(before)), search, backward=True, n=limit + 1)
        page = rows[:limit][::-1]
        has_previous, has_next = len(rows) > limit, True
    else:
        if after:
            qs = _after(qs, decode_cursor(after))
        rows = _rows(qs, search, backward=False, n=limit + 1)
        page = rows[:limit]
        has_previous, has_next = bool(after), len(rows) > limit

    return TransactionPageOut(
        items=tuple(_to_out(t, account) for t in page),
        next_cursor=encode_cursor(page[-1]) if page and has_next else None,
        previous_cursor=encode_cursor(page[0]) if page and has_previous else None,
    )
