# feat/recurring-api

## Flow (slice 1: date rules)
```mermaid
flowchart LR
  A[prev date, new date] --> B{next_expected per Interval == new?}
  B -->|yes| C[Interval]
  B -->|no| D[None: no pattern]
```
Month-based intervals clamp the anchor day to month length (31st -> 28th -> 31st).

## Flow (slice 3: write path)
```mermaid
sequenceDiagram
  participant W as Transaction.save (create)
  participant S as post_save signal
  participant R as assign_recurring_group
  W->>S: created
  S->>R: tx
  R->>R: skip if grouped / no merchant or category
  R->>R: extend matching group (conditional UPDATE on last_date)
  R->>R: else pair with prior ungrouped tx, create group
  Note over R: IntegrityError on unique constraint = concurrent twin, skip
```
bulk_create bypasses signals; the backfill command (slice 4) covers it.

## Entities (slice 2)
```mermaid
erDiagram
  Account ||--o{ RecurringGroup : has
  RecurringGroup ||--o{ Transaction : groups
  Merchant ||--o{ RecurringGroup : of
  Category ||--o{ RecurringGroup : of
```
Unique constraint on (account, merchant, category, amount, type, interval, anchor_day, first_date) makes concurrent creation of the same group fail loudly instead of duplicating.

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| Base lint is red (13 pre-existing ruff findings); lint gate scoped to changed files | .sdlc/stack.json | deferred, not ours |
