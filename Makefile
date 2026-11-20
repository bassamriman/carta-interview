.PHONY: up down logs ps verify-instances run stop run-backend restore-db test test-v typecheck generate-migrations migrate

run:
	docker compose up --build

stop:
	docker compose down

# Reassemble + decompress the committed, split, gzipped seed database.
# Idempotent: does nothing if db.sqlite3 already exists.
restore-db:
	cd backend && [ -f db.sqlite3 ] || cat seed_data/db.sqlite3.gz.part-* | gunzip -c > db.sqlite3

run-backend: restore-db
	cd backend && uv sync && uv run python manage.py migrate && uv run python manage.py runserver 8000

test:
	cd backend && uv sync && uv run python -m pytest

test-v:
	cd backend && uv run python -m pytest -v

typecheck:
	cd backend && uv run ty check

generate-migrations:
	cd backend && uv run python manage.py makemigrations

migrate:
	cd backend && uv run python manage.py migrate

# --- Multiple isolated instances (podman compose) ---
# make up INSTANCE=a [BACKEND_PORT=8001 FRONTEND_PORT=5174]; ports default to a stable per-name offset.
INSTANCE ?= default
COMPOSE ?= podman compose
OFFSET := $(shell printf '%s' "$(INSTANCE)" | cksum | cut -d' ' -f1 | awk '{print $$1 % 500}')
ifeq ($(INSTANCE),default)
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173
else
BACKEND_PORT ?= $(shell expr 8100 + $(OFFSET))
FRONTEND_PORT ?= $(shell expr 5300 + $(OFFSET))
endif
export BACKEND_PORT FRONTEND_PORT
INST = COMPOSE_PROJECT_NAME=carta-$(INSTANCE) $(COMPOSE)

up:
	$(INST) up -d --build
	@echo "[$(INSTANCE)] API http://localhost:$(BACKEND_PORT)/api/docs  app http://localhost:$(FRONTEND_PORT)"

down:
	$(INST) down -v

logs:
	$(INST) logs -f

ps:
	$(INST) ps

verify-instances:
	./scripts/verify-instances.sh
