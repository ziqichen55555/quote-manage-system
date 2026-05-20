#!/usr/bin/env bash
set -euo pipefail

CONFIG="${HOME}/.cloudflared/config.yml"

if [[ ! -f "${CONFIG}" ]]; then
  echo "缺少 ${CONFIG}"
  echo "请先按 deploy/cloudflare-tunnel/README.md 完成配置。"
  exit 1
fi

echo "检查本地 Odoo (http://localhost:8070) ..."
if ! curl -sf -o /dev/null --max-time 3 http://localhost:8070; then
  echo "本地服务未响应。请先运行: docker compose up -d"
  exit 1
fi

echo "启动 Cloudflare Tunnel (reware-project.com → localhost:8070)"
echo "按 Ctrl+C 停止"
exec cloudflared tunnel run reware-local
