#!/usr/bin/env bash
# ── Backend dev launcher — reliably kill any existing instance, then start fresh ──
# Sole source of truth for managing the ragbase backend process. Uses the project
# venv interpreter, a single pidfile, and port-based kill so restarts never leave
# orphaned duplicates or hit "port already in use".
#
# NOTE: --reload 模式会触发 multiprocessing.spawn 子进程卡死 (LangGraph 底层问题),
#       所以默认不带 --reload。如果非要热更新, 用 PORT=8081 RELOAD=1 make dev-backend。
set -euo pipefail

PORT="${PORT:-8081}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIDFILE="${PIDFILE:-/tmp/ragbase-backend.pid}"
LOGFILE="${LOGFILE:-/tmp/ragbase-backend.log}"
PYTHON="$PROJECT_ROOT/.venv/bin/python"

# ── 1. Kill whatever currently owns the port (most reliable: no stale pidfiles) ──
# fuser -k 精确杀掉监听该端口的进程，避免依赖可能失效的 pidfile / 易误伤的 pgrep -f。
if command -v fuser >/dev/null 2>&1 && ss -tlnp "sport = :$PORT" >/dev/null 2>&1 \
   && ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "🔄 Port $PORT in use — killing listener..."
  fuser -k "$PORT/tcp" 2>/dev/null || true
  sleep 2
fi

# ── 2. Fallback: kill via pidfile (covers --reload spawned children / non-tcp cases) ──
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "🔄 Killing pidfile backend (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# ── 3. Final guard: if port still held after both, force it ──
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "⚠️ Port $PORT still held — forcing kill..."
  fuser -k -9 "$PORT/tcp" 2>/dev/null || true
  sleep 1
fi

# ── 4. Verify the venv interpreter exists before launching ──
if [ ! -x "$PYTHON" ]; then
  echo "❌ venv python not found at $PYTHON (run: uv sync)" >&2
  exit 1
fi

# ── 5. Start backend detached from this shell/session ──
# setsid 使其脱离控制终端与调用方进程组，避免被终端关闭或外层脚本连带杀掉；
# nohup 兜底忽略 SIGHUP；单一日志路径便于统一排查。
export PYTHONPATH="$PROJECT_ROOT/backend/src"
# Force the correct DB URL: the opencode sandbox leaks an unrelated DATABASE_URL
# (file:...sqlite) which would silently point the backend at the wrong DB. The
# ragbase DB is a fixed local host — always use it unless an explicit override
# that actually names our db host is provided.
case "${DATABASE_URL:-}" in
  postgresql*@localhost:5433/ragbase*) : ;;
  *) DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase" ;;
esac
export DATABASE_URL

RELOAD_FLAG=""
if [ "${RELOAD:-}" = "1" ]; then
  RELOAD_FLAG="--reload"
  echo "⚠️  RELOAD=1 模式已启用 — 注意: --reload 可能导致子进程卡死"
fi

echo "🚀 Starting backend on port $PORT${RELOAD_FLAG:+ with --reload}..."
setsid nohup "$PYTHON" -m uvicorn core.app:app \
  --port "$PORT" \
  --host "0.0.0.0" \
  --loop asyncio \
  $RELOAD_FLAG \
  --log-level "${LOG_LEVEL:-info}" < /dev/null >> "$LOGFILE" 2>&1 &

BPID=$!
echo "$BPID" > "$PIDFILE"

# ── 6. Wait for the port to actually accept connections (bounded) ──
for _ in $(seq 1 30); do
  if ss -tln "sport = :$PORT" | grep -q LISTEN; then
    echo "✅ Backend up on port $PORT (PID $BPID)"
    exit 0
  fi
  if ! kill -0 "$BPID" 2>/dev/null; then
    echo "❌ Backend exited during startup — see $LOGFILE" >&2
    exit 1
  fi
  sleep 1
done

echo "⚠️ Backend started (PID $BPID) but not yet listening on $PORT — check $LOGFILE"
exit 0
