#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Locust headless load test — configurable users, spawn rate, duration.
# Generates HTML report + CSV stats + locust_results.json percentiles.
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

HOST="${LOCUST_HOST:-http://localhost:8080}"
USERS="${LOCUST_USERS:-100}"
SPAWN_RATE="${LOCUST_SPAWN_RATE:-10}"
RUN_TIME="${LOCUST_RUN_TIME:-5m}"
OUT_DIR="${LOCUST_OUT_DIR:-./loadtest_output}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCUSTFILE="${SCRIPT_DIR}/locustfile.py"
RESULTS_JSON="${OUT_DIR}/locust_results.json"
RESULTS_HTML="${OUT_DIR}/locust_report.html"
RESULTS_CSV_STATS="${OUT_DIR}/locust_stats.csv"
RESULTS_CSV_FAILURES="${OUT_DIR}/locust_failures.csv"

# ── Preflight ────────────────────────────────────────────────────────
if ! python -c "import locust" &>/dev/null; then
  echo "ERROR: locust is not installed. Run: pip install locust"
  exit 1
fi

if [ ! -f "$LOCUSTFILE" ]; then
  echo "ERROR: locustfile not found at $LOCUSTFILE"
  exit 1
fi

# ── Run ───────────────────────────────────────────────────────────────
mkdir -p "$OUT_DIR"
export LOCUST_RESULTS_FILE="$RESULTS_JSON"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Locust Headless Load Test                                 ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Host     : $HOST"
echo "║  Users    : $USERS"
echo "║  Spawn    : $SPAWN_RATE / sec"
echo "║  Duration : $RUN_TIME"
echo "║  Out Dir  : $OUT_DIR"
echo "╚══════════════════════════════════════════════════════════════╝"

locust -f "$LOCUSTFILE" \
  --headless \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$RUN_TIME" \
  --host "$HOST" \
  --html "$RESULTS_HTML" \
  --csv "$OUT_DIR/locust" \
  --csv-full-history

# Rename CSV output for clarity (locust appends the suffix internally)
if [ -f "${OUT_DIR}/locust_stats.csv" ]; then
  mv "${OUT_DIR}/locust_stats.csv" "$RESULTS_CSV_STATS"
fi
if [ -f "${OUT_DIR}/locust_failures.csv" ]; then
  mv "${OUT_DIR}/locust_failures.csv" "$RESULTS_CSV_FAILURES"
fi

echo ""
echo "Done. Reports:"
echo "  HTML    → $RESULTS_HTML"
echo "  Stats   → $RESULTS_CSV_STATS"
echo "  Perc.   → $RESULTS_JSON"
echo ""
