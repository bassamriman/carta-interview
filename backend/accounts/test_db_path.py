import subprocess
import sys


def _db_name(env_value: str | None) -> str:
    env = {"PATH": "/usr/bin:/bin", "DJANGO_SETTINGS_MODULE": "bank.settings"}
    if env_value is not None:
        env["DJANGO_DB_PATH"] = env_value
    code = "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def test_default_db_path_is_unchanged():
    assert _db_name(None).endswith("backend/db.sqlite3")


def test_db_path_overridable_by_env():
    assert _db_name("/data/db.sqlite3") == "/data/db.sqlite3"
