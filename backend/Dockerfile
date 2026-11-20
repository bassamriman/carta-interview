FROM python:3.14-slim-trixie

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "DB=${DJANGO_DB_PATH:-db.sqlite3}; mkdir -p $(dirname $DB); [ -f $DB ] || cat seed_data/db.sqlite3.gz.part-* | gunzip -c > $DB; uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8000"]
