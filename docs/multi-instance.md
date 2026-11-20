# Multiple instances with podman

Each instance is its own compose project (`carta-<INSTANCE>`) with its own containers, network and SQLite volume (`db`, seeded from `backend/seed_data` on first start). Host ports come from `BACKEND_PORT` / `FRONTEND_PORT` (defaults 8000 / 5173).

    make up INSTANCE=a BACKEND_PORT=8001 FRONTEND_PORT=5174
    make up INSTANCE=b BACKEND_PORT=8002 FRONTEND_PORT=5175
    make logs INSTANCE=a      # follow logs
    make ps INSTANCE=a
    make down INSTANCE=a      # also removes that instance's DB volume

Without explicit ports, a named instance gets a stable port derived from its name (backend 8100+n, frontend 5300+n); `INSTANCE=default` uses 8000/5173. Use `COMPOSE="podman-compose"` to switch tool. `make verify-instances` starts two instances, checks API and frontend on both, and tears them down.

`DJANGO_DB_PATH` (set by compose to `/data/db.sqlite3`) points Django at the volume; unset, the DB stays `backend/db.sqlite3`.
