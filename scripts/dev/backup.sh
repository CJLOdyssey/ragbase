#!/usr/bin/env bash
# ragbase 数据库定时备份（docker exec pg_dump）—— 保留最近 KEEP 份，滚动删除。
# 用法：bash scripts/dev/backup.sh            （手动备份）
#       systemctl --user start ragbase-backup （timer 触发，见 ragbase-backup.timer）
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${RAGBASE_BACKUP_DIR:-$REPO/backups}"
KEEP="${RAGBASE_BACKUP_KEEP:-14}"
DB_CONTAINER="${RAGBASE_DB_CONTAINER:-ragbase-db}"
PGDB="${PGDB:-ragbase}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/ragbase-$STAMP.sql.gz"

docker exec "$DB_CONTAINER" pg_dump -U postgres -d "$PGDB" \
  --no-owner --no-privileges --format=custom | gzip > "$OUT"

# 滚动清理：仅保留最近 KEEP 份
ls -1t "$BACKUP_DIR"/ragbase-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

echo "backup written: $OUT"
echo "retained: $(ls -1 "$BACKUP_DIR"/ragbase-*.sql.gz | wc -l) files"
