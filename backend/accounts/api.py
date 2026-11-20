import base64
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema
from ninja.errors import HttpError

from .models import Account, RecurringGroup, Transaction

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


@router.get("/accounts/{account_id}/transactions", response=list[TransactionOut])
def list_transactions(request: HttpRequest, account_id: int, search: str = "") -> list[TransactionOut]:
    account = get_object_or_404(Account, id=account_id)
    transactions = list(account.transactions.order_by("date").all())

    result = [
        TransactionOut(
            id=t.id,
            date=t.date,
            amount=t.amount,
            category=CategoryOut(id=t.category.id, name=t.category.name) if t.category else None,
            merchant=MerchantOut(id=t.merchant.id, name=t.merchant.name) if t.merchant else None,
            type=t.type,
            account=TransactionAccountOut(id=account.id, name=account.name, account_type=account.account_type),
        )
        for t in transactions
    ]

    if search:
        term = search.lower()
        return [
            t
            for t in result
            if (t.merchant and term in t.merchant.name.lower())
            or (t.category and term in t.category.name.lower())
        ]

    return result


class RecurringGroupOut(Schema):
    id: int
    account_id: int
    merchant: MerchantOut | None
    category: CategoryOut | None
    amount: Decimal
    type: str
    interval: str
    first_date: date
    last_date: date
    count: int


class CursorParams(Schema):
    after: str | None = None
    before: str | None = None
    limit: int = 50


class TransactionPage(Schema):
    items: list[TransactionOut]
    next_cursor: str | None
    previous_cursor: str | None


MAX_PAGE = 200


def _encode_cursor(t: Transaction) -> str:
    return base64.urlsafe_b64encode(f"{t.date.isoformat()}|{t.id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[date, int]:
    try:
        raw_date, raw_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return date.fromisoformat(raw_date), int(raw_id)
    except ValueError as e:
        raise HttpError(400, "invalid cursor") from e


@router.get("/users/{user_id}/recurring-groups", response=list[RecurringGroupOut])
def list_recurring_groups(request: HttpRequest, user_id: int) -> list[RecurringGroupOut]:
    user = get_object_or_404(User, id=user_id)
    groups = (
        RecurringGroup.objects.filter(account__user=user)
        .select_related("merchant", "category")
        .order_by("-last_date", "id")
    )
    return [
        RecurringGroupOut(
            id=g.id,
            account_id=g.account_id,  # ty: ignore[unresolved-attribute]
            merchant=MerchantOut(id=g.merchant.id, name=g.merchant.name) if g.merchant else None,
            category=CategoryOut(id=g.category.id, name=g.category.name) if g.category else None,
            amount=g.amount,
            type=g.type,
            interval=g.interval,
            first_date=g.first_date,
            last_date=g.last_date,
            count=g.count,
        )
        for g in groups
    ]


@router.get("/recurring-groups/{group_id}/transactions", response=TransactionPage)
def list_group_transactions(
    request: HttpRequest, group_id: int, params: Query[CursorParams]
) -> TransactionPage:
    group = get_object_or_404(RecurringGroup.objects.select_related("account"), id=group_id)
    limit = max(1, min(params.limit, MAX_PAGE))
    if params.after and params.before:
        raise HttpError(400, "after and before are mutually exclusive")
    qs = group.transactions.select_related("category", "merchant")
    if params.before:
        d, last_id = _decode_cursor(params.before)
        rows = list(qs.filter(Q(date__lt=d) | Q(date=d, id__lt=last_id)).order_by("-date", "-id")[: limit + 1])
        rows.reverse()
        has_more_before = len(rows) > limit
        page = rows[1:] if has_more_before else rows
        has_next = True
    else:
        if params.after:
            d, last_id = _decode_cursor(params.after)
            qs = qs.filter(Q(date__gt=d) | Q(date=d, id__gt=last_id))
        rows = list(qs.order_by("date", "id")[: limit + 1])
        page = rows[:limit]
        has_next = len(rows) > limit
        has_more_before = bool(params.after)
    acct = group.account
    return TransactionPage(
        items=[
            TransactionOut(
                id=t.id,
                date=t.date,
                amount=t.amount,
                category=CategoryOut(id=t.category.id, name=t.category.name) if t.category else None,
                merchant=MerchantOut(id=t.merchant.id, name=t.merchant.name) if t.merchant else None,
                type=t.type,
                account=TransactionAccountOut(id=acct.id, name=acct.name, account_type=acct.account_type),
            )
            for t in page
        ],
        next_cursor=_encode_cursor(page[-1]) if page and has_next else None,
        previous_cursor=_encode_cursor(page[0]) if page and has_more_before else None,
    )
