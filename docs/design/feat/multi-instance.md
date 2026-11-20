# feat/multi-instance

## Flow
```mermaid
sequenceDiagram
  participant M as make up INSTANCE=a
  participant P as podman compose (project carta-a)
  participant B as backend container
  participant V as volume carta-a_db
  M->>P: BACKEND_PORT/FRONTEND_PORT env, COMPOSE_PROJECT_NAME
  P->>B: start, DJANGO_DB_PATH=/data/db.sqlite3
  B->>V: if missing, gunzip seed_data parts to /data/db.sqlite3
  B->>B: migrate, runserver 0.0.0.0:8000
  Note over P: frontend proxies to backend:8000 on the project network
```

## Pitfalls
| Hazard | Where | Status |
|---|---|---|
| Shared host db.sqlite3 via ./backend bind mount across instances | docker-compose.yml, settings.py | fixed (DB on per-project named volume), verified |
| Derived ports can collide (cksum mod 500) | Makefile | deferred: override with BACKEND_PORT/FRONTEND_PORT |
| Source tree bind-mounted into every instance (dev hot reload) | docker-compose.yml | deferred: intended for dev |
