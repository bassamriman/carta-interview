# feat/api-perf design

## Entities
```mermaid
erDiagram
  Account ||--o{ Transaction : has
  Merchant ||--o{ Transaction : "indexed (account,merchant,date,id)"
  Category ||--o{ Transaction : "indexed (account,category,date,id)"
```
New indexes on Transaction: (account,date,id), (account,merchant,date,id), (account,category,date,id).

## Flow
```mermaid
sequenceDiagram
  Client->>API: GET /accounts/{id}/transactions?search&limit&after|before
  API->>DB: merchant/category ids matching search (small tables)
  API->>DB: one query, select_related, keyset WHERE (date,id) > cursor, LIMIT n+1
  API-->>Client: items, next_cursor, previous_cursor
  Note over API: bad cursor or both after+before -> 400; unknown account -> 404
```

## API
See backend/docs/transactions-api.md. Response changed from list to {items,next_cursor,previous_cursor}.

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| N+1 per row for category/merchant | backend/accounts/api.py list_transactions | fixed, verified (query-count test) |
| Search/LIKE on 1B rows, balance aggregates | backend/docs/transactions-api.md | deferred, SQLite scale note |
