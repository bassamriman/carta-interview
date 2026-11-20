from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Count

from accounts.models import RecurringGroup, Transaction
from accounts.recurring import assign_recurring_group

KEY = ("account_id", "merchant_id", "category_id", "amount", "type")


class Command(BaseCommand):
    help = "Group existing transactions into recurring groups. Idempotent; safe to rerun."

    def handle(self, *args: Any, **options: Any) -> None:
        before = RecurringGroup.objects.count()
        keys = (
            Transaction.objects.filter(
                recurring_group__isnull=True, merchant__isnull=False, category__isnull=False
            )
            .values(*KEY)
            .annotate(n=Count("id"))
            .filter(n__gte=2)
            .values(*KEY)
        )
        for key in keys.iterator():
            txs = Transaction.objects.filter(**key, recurring_group__isnull=True).order_by("date", "id")
            for tx in txs:
                assign_recurring_group(tx)
        created = RecurringGroup.objects.count() - before
        self.stdout.write(f"created {created} recurring groups")
