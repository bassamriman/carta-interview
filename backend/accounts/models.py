from typing import TYPE_CHECKING, ClassVar

from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Coalesce

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class Account(models.Model):
    class AccountType(models.TextChoices):
        CHECKING = "checking"
        SAVINGS = "savings"
        CREDIT = "credit"

    # Type-only declarations for what Django adds at runtime: the implicit primary key and
    # the reverse side of Transaction.account.
    id: int
    transactions: "RelatedManager[Transaction]"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.account_type})"


class Category(models.Model):
    id: int
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Merchant(models.Model):
    id: int
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class RecurringGroup(models.Model):
    """Transactions sharing account, merchant, category, amount and type, on a regular date interval."""

    class Interval(models.TextChoices):
        WEEKLY = "weekly"
        BIWEEKLY = "biweekly"
        MONTHLY = "monthly"
        QUARTERLY = "quarterly"
        YEARLY = "yearly"

    id: int
    transactions: "RelatedManager[Transaction]"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="recurring_groups")
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, null=True, blank=True, related_name="recurring_groups"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, related_name="recurring_groups"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10)
    interval = models.CharField(max_length=10, choices=Interval.choices)
    anchor_day = models.PositiveSmallIntegerField()
    first_date = models.DateField()
    last_date = models.DateField()
    count = models.PositiveIntegerField()

    class Meta:
        constraints: ClassVar = [
            # NULL merchant/category must still collide, so they are coalesced to 0 (ids start at 1).
            models.UniqueConstraint(
                "account",
                Coalesce("merchant", 0),
                Coalesce("category", 0),
                "amount",
                "type",
                "interval",
                "anchor_day",
                "first_date",
                name="uniq_recurring_group",
            )
        ]
        indexes: ClassVar = [models.Index(fields=["account", "last_date"])]


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEBIT = "debit"
        CREDIT = "credit"

    id: int
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    merchant = models.ForeignKey(
        Merchant, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    recurring_group = models.ForeignKey(
        RecurringGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes: ClassVar = [models.Index(fields=["recurring_group", "date", "id"])]

    def __str__(self) -> str:
        return f"{self.date} {self.merchant} {self.amount}"
