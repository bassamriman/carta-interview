#!/bin/sh
# Start two instances, hit API + frontend on distinct ports, tear down. Exit non-zero on any failure.
set -eu
A=${A:-vi-a}; B=${B:-vi-b}
cleanup() { make down INSTANCE=$A >/dev/null 2>&1 || true; make down INSTANCE=$B >/dev/null 2>&1 || true; }
trap cleanup EXIT
make up INSTANCE=$A BACKEND_PORT=18001 FRONTEND_PORT=15001
make up INSTANCE=$B BACKEND_PORT=18002 FRONTEND_PORT=15002
wait_for() { for i in $(seq 1 90); do curl -fs "$1" >/dev/null && return 0; sleep 2; done; echo "timeout $1"; return 1; }
for p in 18001 18002; do wait_for "http://localhost:$p/api/users"; done
for p in 15001 15002; do wait_for "http://localhost:$p/"; wait_for "http://localhost:$p/api/users"; done
echo "OK: instances up on API 18001/18002, frontend 15001/15002"
