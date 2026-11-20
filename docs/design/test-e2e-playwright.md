# test/e2e-playwright

Playwright E2E for the existing users → accounts → transactions flows.

```mermaid
sequenceDiagram
  participant PW as Playwright
  participant V as vite :5173
  participant D as Django :8000
  PW->>V: webServer boots (reuseExistingServer)
  PW->>D: webServer boots via make run-backend
  PW->>V: goto /users/2/accounts/3/transactions
  V->>D: GET /api/accounts/3/transactions?search=
```

| Pitfall | Where | Status |
|---|---|---|
| Account 1 (~1M rows) never returns | specs use user 2 / account 3 only | fixed (avoided) |
| Counts (247 txns, 13 pages) tied to seed DB | frontend/e2e/flows.spec.ts | deferred: seed is committed |
| Transactions API shape changes on feat/api-perf | search/pagination specs | deferred: update after that merges |
