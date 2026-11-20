# test/frontend design

Vitest + Testing Library + jsdom for the existing pages (Users, Accounts, Transactions). `fetch` is stubbed per test.

```mermaid
sequenceDiagram
  Test->>Page: render in MemoryRouter
  Page->>fetch(stub): GET /api/...
  fetch(stub)-->>Page: json or !ok (HTTP n)
  Page-->>Test: rows / "Error: HTTP n"
```

| Pitfall | Status |
|---|---|
| TS6 `baseUrl` deprecation broke `tsc -b` (frontend/tsconfig.app.json) | fixed: removed, `paths` works alone |
| TransactionsPage tests assume bare-list API; api-perf changes it to cursor pages | deferred: tests only cover code at clone time |
