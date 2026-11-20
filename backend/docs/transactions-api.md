# Transactions API contract

`GET /api/accounts/{account_id}/transactions`

| Param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int 1..200 | 50 | page size (422 outside range) |
| `search` | string | "" | case-insensitive substring of merchant or category name, filtered in the DB |
| `after` | opaque cursor | - | items strictly after this cursor (forward) |
| `before` | opaque cursor | - | items strictly before this cursor (backward) |

`after` and `before` are mutually exclusive (400); a malformed cursor is 400; unknown account 404.

Order is `(date, id)` ascending. Response (**breaking change**: was a bare list):

```json
{ "items": [TransactionOut...], "next_cursor": "string|null", "previous_cursor": "string|null" }
```

- `next_cursor` is null on the last page; pass it as `after`.
- `previous_cursor` is null on the first page; pass it as `before`. Backward pages come back in ascending order.
- Cursors are opaque (base64 of `date|id`); keep `search` and `limit` the same across a walk.
- No total count is returned (a count is a full scan at scale).

## Indexes
`(account, date, id)`, `(account, merchant, date, id)`, `(account, category, date, id)`.

## Scale note: 1B transactions on SQLite
- Single writer, single file: ~100+ GB database, no horizontal scale; backups and index builds lock or take hours.
- Keyset paging itself is O(limit) at any depth; the unfiltered account walk is fine.
- Search is `icontains` on lookup names, so a term matching many merchants becomes a huge `IN` list; unanchored LIKE cannot use an index. Needs full-text/trigram (Postgres pg_trgm, or a search service).
- `users` transaction_count and account `balance` still aggregate over all rows (full scans); need maintained running balances/counters or materialized rollups.
- Concurrent read/write load, replication and partitioning (by account or date) require Postgres or similar. Not migrated: out of scope per brief.
