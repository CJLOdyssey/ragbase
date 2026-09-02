#!/usr/bin/env bash
# 启动前端 dev server (tmux)
set -euo pipefail

SESSION="ragbase-frontend"
PORT="${VITE_DEV_PORT:-5174}"
FRONTEND_DIR="/root/projects/ragbase/frontend"

# 如果 session 已存在，attach 即可
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "📎 Session '$SESSION' already exists, attaching..."
  tmux attach -t "$SESSION"
  exit 0
fi

echo "🚀 Starting frontend on port $PORT in tmux session '$SESSION'..."
tmux new-session -d -s "$SESSION" \
  "cd $FRONTEND_DIR && npx vite --port $PORT; exec bash"

echo "✅ Frontend started. Attach with: tmux attach -t $SESSION"
tmux attach -t "$SESSION"
