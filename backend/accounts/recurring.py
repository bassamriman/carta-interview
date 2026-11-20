"""Write-time assignment of transactions to recurring groups."""

from django.db import IntegrityError, transaction
from django.db.models import F

from .models import RecurringGroup, Transaction
from .recurrence import infer_interval, next_expected


def _key(tx: Transaction) -> dict[str, object]:
    return {
        "account_id": tx.account_id,  # ty: ignore[unresolved-attribute]
        "merchant_id": tx.merchant_id,  # ty: ignore[unresolved-attribute]
        "category_id": tx.category_id,  # ty: ignore[unresolved-attribute]
        "amount": tx.amount,
        "type": tx.type,
    }


def _extend(group: RecurringGroup, tx: Transaction) -> bool:
    """Attach tx when it lands exactly on the group's next expected date."""
    expected = next_expected(RecurringGroup.Interval(group.interval), group.last_date, group.anchor_day)  # ty: ignore[invalid-argument-type]
    if tx.date != expected:
        return False
    # Conditional update: a concurrent writer that already advanced last_date makes this a no-op.
    updated = RecurringGroup.objects.filter(pk=group.pk, last_date=group.last_date).update(
        last_date=tx.date, count=F("count") + 1
    )
    if updated:
        Transaction.objects.filter(pk=tx.pk).update(recurring_group=group)
        tx.recurring_group = group
    return bool(updated)


def _start_group(tx: Transaction) -> None:
    """Pair tx with the latest ungrouped earlier transaction of the same key, if their dates recur."""
    prev = (
        Transaction.objects.filter(**_key(tx), recurring_group__isnull=True, date__lt=tx.date)
        .exclude(pk=tx.pk)
        .order_by("-date", "-id")
        .first()
    )
    interval = infer_interval(prev.date, tx.date) if prev else None
    if prev is None or interval is None:
        return
    try:
        with transaction.atomic():
            group = RecurringGroup.objects.create(
                **_key(tx),
                interval=interval.value,
                anchor_day=prev.date.day,
                first_date=prev.date,
                last_date=tx.date,
                count=2,
            )
    except IntegrityError:
        return  # a concurrent writer created the same group and claimed the pair
    Transaction.objects.filter(pk__in=[prev.pk, tx.pk]).update(recurring_group=group)
    tx.recurring_group = group


def assign_recurring_group(tx: Transaction) -> None:
    """Idempotent: a transaction already in a group is left alone."""
    if tx.recurring_group_id:  # ty: ignore[unresolved-attribute]
        return
    with transaction.atomic():
        for group in RecurringGroup.objects.filter(**_key(tx)).order_by("-last_date"):
            if _extend(group, tx):
                return
        _start_group(tx)

