# feat/ui

## Flow: transactions paging
```mermaid
sequenceDiagram
  participant P as TransactionsPage
  participant A as GET /api/accounts/ID/transactions
  P->>A: limit=20 (+search)
  A-->>P: items, next_cursor, previous_cursor
  P->>A: Next: after=next_cursor
  P->>A: Previous: before=previous_cursor
  Note over P: search or account change drops the cursor (first page)
```
No total count or page numbers: the API returns none (a count is a full scan at scale).

## Flow: recurring groups (/users/ID/recurring)
```mermaid
sequenceDiagram
  participant P as RecurringGroupsPage
  participant A as recurring-api
  P->>A: GET /api/users/ID/recurring-groups
  A-->>P: groups (id, merchant, category, amount, type, interval, first_date, last_date, count)
  Note over P: click a group selects it (aria-pressed)
  P->>A: GET /api/recurring-groups/GID/transactions?limit=20
  A-->>P: items, next_cursor (previous_cursor after the first page)
  P->>A: Next: after=next_cursor / Previous: before=previous_cursor
```
Built against the recurring-api PR 5 contract; that branch is not merged into this one.

## Navigation
Users -> Accounts -> (account) Transactions, and Accounts -> Recurring transactions (/users/ID/recurring).
