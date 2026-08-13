#!/usr/bin/env bash
# 生成自签名 TLS 证书（本地/内网 TLS 验证用）—— SAN 含 localhost/127.0.0.1。
# 公网生产请改用受信 CA（Let's Encrypt / 云证书），见 docs/deploy-tls.md。
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CERT_DIR="${RAGBASE_TLS_DIR:-$REPO/tls}"
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -days 365 \
  -subj "/CN=ragbase-local" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/server.key"
echo "cert written: $CERT_DIR/server.crt + server.key (自签名，勿用于公网)"
