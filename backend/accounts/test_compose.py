import re
from pathlib import Path

COMPOSE = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text()


def test_host_ports_are_configurable_with_old_defaults():
    assert '"${BACKEND_PORT:-8000}:8000"' in COMPOSE
    assert '"${FRONTEND_PORT:-5173}:5173"' in COMPOSE


def test_each_instance_has_its_own_db_volume():
    assert re.search(r"^volumes:\n  db:", COMPOSE, re.MULTILINE)
    assert "db:/data" in COMPOSE and "DJANGO_DB_PATH=/data/db.sqlite3" in COMPOSE


def test_no_fixed_container_names_that_would_collide():
    assert "container_name" not in COMPOSE
