# feat/api-perf design

## Entities
```mermaid
erDiagram
  Account ||--o{ Transaction : has
  Merchant ||--o{ Transaction : "indexed by account, merchant, date, id"
  Category ||--o{ Transaction : "indexed by account, category, date, id"
```
New indexes on Transaction: (account, date, id), (account, merchant, date, id), (account, category, date, id).

## Flow
```mermaid
sequenceDiagram
  participant Client
  participant API
  participant DB
  Client->>API: GET transactions with search, limit, after or before
  API->>DB: merchant and category ids matching search (capped at 21 each)
  alt narrow term, 20 matches or fewer
    API->>DB: one indexed keyset query per match, LIMIT n+1, merged in Python
  else broad term or no search
    API->>DB: one keyset query with select_related, LIMIT n+1
  end
  API-->>Client: items, next_cursor, previous_cursor
  Note over API,Client: bad cursor or both after and before gives 400, unknown account gives 404
```

## API
See backend/docs/transactions-api.md. The response changed from a bare list to an object with items, next_cursor and previous_cursor.

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| N+1 per row for category and merchant | backend/accounts/api.py list_transactions | fixed, verified by a query-count test |
| No-match search scanned the whole account (2.0s to 84ms) | backend/accounts/api.py _rows | fixed, verified on the seed DB |
| Mid-density search can still scan a lot | backend/accounts/api.py _rows | deferred, needs trigram search or a statement deadline |
| Frontend read the response as a bare list | frontend/src/pages/TransactionsPage.tsx fetchAllPages | fixed: follows next_cursor (200 per request, at most 10 requests), PR #3 and #4 tests pass; accounts over 2000 rows are truncated until recurring-ui adds cursor paging |
| Substring search and balance aggregates at 1B rows | backend/docs/transactions-api.md | deferred, SQLite scale note |
