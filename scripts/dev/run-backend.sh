#!/usr/bin/env bash
# ── Backend dev launcher — kills all existing instances first, then starts ──
# NOTE: --reload 模式会触发 multiprocessing.spawn 子进程卡死 (LangGraph 底层问题),
#       所以默认不带 --reload。如果非要热更新, 用 PORT=8081 RELOAD=1 make dev-backend。
set -euo pipefail

PIDFILE="/tmp/content-studio-backend.pid"
PORT="${PORT:-8081}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# ── 1. Kill ALL existing uvicorn instances of this app ──────────────────────
for pid in $(pgrep -f "uvicorn.*core.app:app" 2>/dev/null || true); do
  if [ "$pid" != "$$" ]; then
    echo "🔄 Killing existing uvicorn instance (PID $pid)..."
    kill "$pid" 2>/dev/null || true
  fi
done
sleep 1
# SIGKILL survivors
for pid in $(pgrep -f "uvicorn.*core.app:app" 2>/dev/null || true); do
  if [ "$pid" != "$$" ]; then
    kill -9 "$pid" 2>/dev/null || true
  fi
done
sleep 1

# ── 2. Kill any leftover multiprocessing.spawn children ─────────────────────
# These are orphaned when their uvicorn parent dies but the child keeps running.
for pid in $(pgrep -f "multiprocessing.spawn" 2>/dev/null || true); do
  if [ "$pid" != "$$" ]; then
    echo "🧹 Cleaning up orphaned multiprocessing child (PID $pid)..."
    kill -9 "$pid" 2>/dev/null || true
  fi
done

# ── 3. Kill via pidfile ─────────────────────────────────────────────────────
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "🔄 Killing pidfile backend (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# ── 4. Port conflict check ─────────────────────────────────────────────────
if command -v ss &>/dev/null && ss -tlnp "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
  echo "⚠️ Port $PORT still in use — force killing..."
  fuser -k "$PORT/tcp" 2>/dev/null || true
  sleep 1
fi

# ── 5. Start backend ────────────────────────────────────────────────────────
export PYTHONPATH="$PROJECT_ROOT/backend/src"
cd "$PROJECT_ROOT"

RELOAD_FLAG=""
if [ "${RELOAD:-}" = "1" ]; then
  RELOAD_FLAG="--reload"
  echo "⚠️  RELOAD=1 模式已启用 — 注意: --reload 可能导致子进程卡死"
fi

echo "🚀 Starting backend on port $PORT${RELOAD_FLAG:+ with --reload}..."
nohup /usr/bin/python3 -m uvicorn core.app:app \
  --port "$PORT" \
  --host "0.0.0.0" \
  --loop asyncio \
  $RELOAD_FLAG \
  --log-level "${LOG_LEVEL:-info}" </dev/null >> /tmp/backend.log 2>&1 &

BPID=$!
echo "$BPID" > "$PIDFILE"
echo "Backend started (PID $BPID)"
