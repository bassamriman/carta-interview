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
  R->>R: skip if already grouped
  R->>R: extend matching group (conditional UPDATE on last_date)
  R->>R: else pair with prior ungrouped tx, create group
  Note over R: IntegrityError on unique constraint = concurrent twin, skip
```
bulk_create bypasses signals; the backfill command (slice 4) covers it.

## API (slice 5)
```mermaid
sequenceDiagram
  Client->>API: GET /api/users/{id}/recurring-groups
  API-->>Client: 200 list of groups, or 404 unknown user
  Client->>API: GET /api/recurring-groups/{id}/transactions with limit, after or before
  API-->>Client: 200 page, or 400 bad cursor, or 404
```
Cursor: opaque urlsafe-base64 of `date|id`, keyset on (date, id); limit clamped to 1..200 (default 50). next_cursor null on last page.

## Backfill (slice 4)
`manage.py backfill_recurring`: for each key with >=2 ungrouped transactions, replays them in date order through `assign_recurring_group`; grouped rows are skipped, so reruns are no-ops.

## Entities (slice 2)
```mermaid
erDiagram
  Account ||--o{ RecurringGroup : has
  RecurringGroup ||--o{ Transaction : groups
  Merchant ||--o{ RecurringGroup : of
  Category ||--o{ RecurringGroup : of
```
Merchant and category may be null (grouped as their own series). Unique constraint on (account, merchant, category, amount, type, interval, anchor_day, first_date), with NULLs coalesced to 0 makes concurrent creation of the same group fail loudly instead of duplicating.

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| Base lint is red (13 pre-existing ruff findings); lint gate scoped to changed files | .sdlc/stack.json | deferred, not ours |

## After merging api-perf
The group transactions endpoint reuses api-perf's cursor helpers and `TransactionPageOut` (one paging contract). Migrations renumbered to 0007 and 0008 on top of `0006_transaction_keyset_indexes`; `Transaction` has a single `Meta` holding all indexes.
