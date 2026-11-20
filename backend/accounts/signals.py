from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transaction
from .recurring import assign_recurring_group


@receiver(post_save, sender=Transaction)
def group_new_transaction(sender: type[Transaction], instance: Transaction, created: bool, **kwargs: Any) -> None:
    if created:
        assign_recurring_group(instance)
