# feat/recurring-api

## Flow (slice 1: date rules)
```mermaid
flowchart LR
  A[prev date, new date] --> B{next_expected per Interval == new?}
  B -->|yes| C[Interval]
  B -->|no| D[None: no pattern]
```
Month-based intervals clamp the anchor day to month length (31st -> 28th -> 31st).

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| Base lint is red (13 pre-existing ruff findings); lint gate scoped to changed files | .sdlc/stack.json | deferred, not ours |
