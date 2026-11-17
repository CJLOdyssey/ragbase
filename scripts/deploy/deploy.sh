#!/usr/bin/env bash
# RagBase 生产部署脚本（路线 B：runner 构建 dist → 服务器执行本脚本）
#
# 由 .github/workflows/cd-pipeline.yml 通过 SSH 调用。职责：
#   1. 前端：把 runner 传来的 dist 压缩包解到带 SHA 的版本目录，切换软链，reload nginx
#   2. 后端：本脚本执行前 workflow 已 git reset 到目标 commit，这里负责重启 + 健康检查
#   3. 失败自动回滚：前端切回上一软链；后端回退到 .deployed_sha 记录的旧 commit
#
# 用法：
#   bash scripts/deploy/deploy.sh --sha <commit-sha> --dist <dist.tar.gz 路径> [--mode all|frontend|backend]
set -euo pipefail

REPO="/root/projects/ragbase"
WEB_ROOT="/var/www"
RELEASES_DIR="${WEB_ROOT}/ragbase-releases"
CURRENT_LINK="${WEB_ROOT}/ragbase"
NGINX_CONF="/etc/nginx/conf.d/ragbase.conf"
KEEP=3
HEALTH_URL="http://127.0.0.1:8081/api/health"
PUBLIC_URL="https://ragbase.odopen.top/"

SHA=""
DIST_ARCHIVE=""
MODE="all"

usage() {
  echo "Usage: $0 --sha <sha> --dist <path> [--mode all|frontend|backend]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sha) SHA="${2:?--sha 需要值}"; shift 2 ;;
    --dist) DIST_ARCHIVE="${2:?--dist 需要值}"; shift 2 ;;
    --mode) MODE="${2:?--mode 需要值}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

[[ -n "$SHA" ]] || { echo "缺少 --sha" >&2; usage; }
[[ "$MODE" =~ ^(all|frontend|backend)$ ]] || { echo "mode 非法: $MODE" >&2; usage; }

log() { printf '[deploy %s] %s\n' "$(date '+%F %T')" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

export XDG_RUNTIME_DIR="/run/user/$(id -u)"

deploy_frontend() {
  [[ -f "$DIST_ARCHIVE" ]] || fail "dist 压缩包不存在: $DIST_ARCHIVE"
  command -v nginx >/dev/null 2>&1 || fail "nginx 未安装"

  mkdir -p "$RELEASES_DIR"

  # 首次运行：把现有的真实目录迁成 releases/bootstrap，再用软链接管
  if [[ -d "$CURRENT_LINK" && ! -L "$CURRENT_LINK" ]]; then
    log "首次运行：迁移现有 dist 到 releases/bootstrap"
    mv "$CURRENT_LINK" "$RELEASES_DIR/bootstrap"
  fi

  local prev=""
  [[ -L "$CURRENT_LINK" ]] && prev="$(readlink "$CURRENT_LINK")"

  local target="${RELEASES_DIR}/${SHA}"
  rm -rf "$target"
  mkdir -p "$target"
  tar xzf "$DIST_ARCHIVE" -C "$target" || fail "解包失败: $DIST_ARCHIVE"

  # 产物完整性校验（在切软链前做，避免坏包上线）：必须有 index.html、
  # 引用了带哈希的 /assets/ 资源且该资源存在。仅查 HTTP 200 不够——
  # SPA fallback 对任何路径都返回 index.html + 200。
  local entry="${target}/index.html"
  [[ -s "$entry" ]] || fail "dist 缺少 index.html"
  grep -qE '/assets/[^" ]+\.(js|css)' "$entry" || fail "index.html 未引用 /assets 资源"
  local asset
  asset="$(grep -oE '/assets/[^" ]+\.js' "$entry" | head -1)"
  [[ -s "${target}${asset}" ]] || fail "dist 缺少资源文件: $asset"

  chown -R www-data:www-data "$target"
  chmod -R a+rX "$target"

  ln -sfn "$target" "$CURRENT_LINK"
  log "前端软链切换到 $target"

  nginx -t >/dev/null 2>&1 || fail "nginx 配置校验失败"
  systemctl reload nginx

  # 健康检查：首页可取到且含应用标记（<title>RagBase</title>）
  if curl -fsS --max-time 15 "$PUBLIC_URL" | grep -q "RagBase"; then
    log "前端健康检查通过"
  else
    log "前端健康检查失败，回滚软链"
    [[ -n "$prev" ]] && ln -sfn "$prev" "$CURRENT_LINK"
    systemctl reload nginx
    fail "前端部署失败，已回滚"
  fi

  # 滚动清理旧版本（保留 KEEP）
  ls -1dt "$RELEASES_DIR"/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf
}

deploy_backend() {
  cd "$REPO" || fail "无法进入 $REPO"
  [[ -f .env.systemd ]] || fail ".env.systemd 缺失"

  local prev_sha=""
  [[ -f .deployed_sha ]] && prev_sha="$(cat .deployed_sha)"

  # 迁移：由 alembic 手动执行（DB 当前 p9g3n027 / main 链止于 p9g3n015，
  # 自动 upgrade 会报 Can't locate revision，故此处不自动迁移）
  # PYTHONPATH=backend/src .venv/bin/python -m alembic -c alembic.ini upgrade head

  systemctl --user restart ragbase-backend ragbase-celery
  sleep 6

  if curl -fsS --max-time 10 -o /dev/null "$HEALTH_URL"; then
    echo "$SHA" > .deployed_sha
    log "后端健康检查通过，记录 .deployed_sha=$SHA"
  else
    log "后端健康检查失败，回滚到 $prev_sha"
    if [[ -n "$prev_sha" ]]; then
      git reset --hard "$prev_sha" >/dev/null 2>&1 || true
      systemctl --user restart ragbase-backend ragbase-celery
      sleep 5
    fi
    fail "后端部署失败，已回滚"
  fi
}

log "开始部署 sha=$SHA mode=$MODE"
case "$MODE" in
  all) deploy_frontend; deploy_backend ;;
  frontend) deploy_frontend ;;
  backend) deploy_backend ;;
esac
log "部署完成 sha=$SHA"
