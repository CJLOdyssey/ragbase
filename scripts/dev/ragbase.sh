#!/usr/bin/env bash
# ragbase 统一管理脚本 — 后端(systemd) + 前端(tmux)
set -euo pipefail

SERVICE="ragbase-backend"
SESSION="ragbase-frontend"

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start       启动后端 + 前端
  stop        停止后端 + 前端
  restart     重启后端 + 前端
  status      查看状态
  logs        查看后端日志 (journalctl)
  frontend    attach 到前端 tmux session
EOF
}

cmd_start() {
  # 后端 (systemd)
  systemctl --user daemon-reload
  systemctl --user start "$SERVICE"
  echo "✅ Backend (systemd) started on port 8081"

  # 前端 (tmux)
  bash /root/projects/ragbase/scripts/dev/start-frontend-tmux.sh
}

cmd_stop() {
  systemctl --user stop "$SERVICE" 2>/dev/null && echo "✅ Backend stopped" || echo "⚠️ Backend not running"
  tmux kill-session -t "$SESSION" 2>/dev/null && echo "✅ Frontend stopped" || echo "⚠️ Frontend not running"
}

cmd_restart() {
  systemctl --user restart "$SERVICE"
  echo "✅ Backend restarted"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
  fi
  bash /root/projects/ragbase/scripts/dev/start-frontend-tmux.sh
}

cmd_status() {
  echo "=== Backend (systemd) ==="
  systemctl --user status "$SERVICE" --no-pager 2>/dev/null || echo "not running"
  echo ""
  echo "=== Frontend (tmux) ==="
  tmux list-sessions 2>/dev/null | grep "$SESSION" || echo "not running"
}

cmd_logs() {
  journalctl --user -u "$SERVICE" -f --no-pager
}

cmd_frontend() {
  tmux attach -t "$SESSION" 2>/dev/null || echo "Frontend not running. Use: $0 start"
}

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_restart ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  frontend) cmd_frontend ;;
  *)       usage ;;
esac
