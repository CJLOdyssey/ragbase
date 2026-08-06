#!/usr/bin/env bash
# ── Docker entrypoint for virtual-team backend ──────────────────────────────
#  1. Wait for Postgres (up to 60s)
#  2. Run alembic migrations
#  3. Exec CMD (uvicorn)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── 1. Wait for Postgres ──────────────────────────────────────────────────────
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"

echo "⏳ Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 30); do
  if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q 2>/dev/null; then
    echo "✅ Postgres is ready (attempt ${i})"
    break
  fi
  if [ "${i}" -eq 30 ]; then
    echo "❌ Postgres did not become ready in time — continuing anyway"
    break
  fi
  echo "  ... waiting (${i}/30)"
  sleep 2
done

# ── 2. Run Alembic migrations (skipped when SKIP_MIGRATIONS=1; K8s 由独立 Job 执行) ──
if [ "${SKIP_MIGRATIONS:-0}" = "1" ]; then
  echo "⏭️ SKIP_MIGRATIONS=1 — skipping alembic migrations"
else
  echo "🚀 Running alembic migrations..."
  if ! alembic upgrade head; then
    echo "❌ Migration failed — refusing to start backend"
    exit 1
  fi
  echo "✅ Migrations applied"
fi

# ── 3. Kill any existing uvicorn instances of this app ──────────────────────────
for pid in $(pgrep -f "uvicorn.*core.app:app" 2>/dev/null || true); do
  if [ "$pid" != "$BASHPID" ]; then
    echo "🔄 Killing existing uvicorn instance (PID $pid)..."
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  fi
done
sleep 1

# ── 4. Port conflict check (last resort) ───────────────────────────────────────
PORT="${PORT:-8080}"
if command -v ss &>/dev/null && ss -tlnp "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
  echo "⚠️ Port $PORT still in use — force killing..."
  fuser -k "$PORT/tcp" 2>/dev/null || true
  sleep 1
fi

# ── 5. Exec CMD ────────────────────────────────────────────────────────────────
exec "$@"
