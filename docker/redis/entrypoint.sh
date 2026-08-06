#!/bin/sh
set -e
# ── Redis / Sentinel entrypoint ────────────────────────────────────────────────
# Applies auth configuration (requirepass / masterauth / sentinel auth-pass)
# from the REDIS_PASSWORD env var, then starts redis-server or redis-sentinel.
#
# REDIS_MODE = server | sentinel   (required)
# REDIS_PASSWORD                   (optional — skip auth when empty)
# Redis config is mounted at /etc/redis/redis.conf

CONF="/etc/redis/redis.conf"
TMP="/tmp/redis-running.conf"

cp "$CONF" "$TMP"

if [ -n "${REDIS_PASSWORD}" ]; then
    case "${REDIS_MODE}" in
        sentinel)
            echo "sentinel auth-pass virtual-team-redis ${REDIS_PASSWORD}" >> "$TMP"
            ;;
        server)
            echo "requirepass ${REDIS_PASSWORD}" >> "$TMP"
            echo "masterauth ${REDIS_PASSWORD}" >> "$TMP"
            ;;
    esac
fi

case "${REDIS_MODE}" in
    sentinel)
        exec redis-sentinel "$TMP" "$@"
        ;;
    *)
        exec redis-server "$TMP" "$@"
        ;;
esac
