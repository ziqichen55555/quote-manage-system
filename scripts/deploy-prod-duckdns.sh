#!/usr/bin/env bash
# 方案 B：Oracle Cloud + DuckDNS + Caddy（生产）
# 在 Ubuntu VM 上、仓库根目录执行：
#   chmod +x scripts/deploy-prod-duckdns.sh
#   ./scripts/deploy-prod-duckdns.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ROOT}/.env"
EXAMPLE="${ROOT}/.env.prod.example"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"
DB="cocreativeit-quote"
MODULE="quote_manage_ui"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 .env，先从模板复制并填写 DuckDNS 域名和密码："
  echo "  cp .env.prod.example .env && nano .env"
  exit 1
fi

# shellcheck disable=SC1091
source "${ENV_FILE}"

if [[ "${SITE_HOSTNAME}" == *"your-subdomain"* ]] || [[ -z "${SITE_HOSTNAME:-}" ]]; then
  echo "请在 .env 里设置 SITE_HOSTNAME=你的子域名.duckdns.org"
  exit 1
fi

if [[ "${POSTGRES_PASSWORD}" == *"please-change"* ]] || [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "请在 .env 里设置强密码 POSTGRES_PASSWORD"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "未安装 Docker。请先: curl -fsSL https://get.docker.com | sudo sh"
  exit 1
fi

echo "同步 config/odoo.conf 的 db_password ..."
if grep -q '^db_password = ' config/odoo.conf; then
  sed -i "s|^db_password = .*|db_password = ${POSTGRES_PASSWORD}|" config/odoo.conf
else
  echo "db_password = ${POSTGRES_PASSWORD}" >> config/odoo.conf
fi

echo "启动生产栈 (Caddy + Odoo + Postgres) ..."
eval "${COMPOSE}" up -d

echo "等待数据库就绪 ..."
sleep 8

if ! eval "${COMPOSE}" exec -T db psql -U odoo -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "${DB}"; then
  echo "首次部署：创建数据库并安装 ${MODULE} ..."
  eval "${COMPOSE}" run --rm web odoo \
    -c /etc/odoo/odoo.conf \
    -d "${DB}" \
    -i "${MODULE}" \
    --stop-after-init
  eval "${COMPOSE}" restart web caddy
else
  echo "数据库 ${DB} 已存在，跳过 -i 安装。"
fi

echo ""
echo "完成。请在浏览器打开:"
echo "  https://${SITE_HOSTNAME}"
echo ""
echo "若证书未签发，检查 Oracle 安全组是否放行 80/443，以及 DuckDNS 是否指向本机公网 IP。"
echo "日常升级模块: git pull && ./scripts/upgrade-quote-manage-ui-prod.sh"
