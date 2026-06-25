#!/usr/bin/env bash
# Run ON the server (DigitalOcean web console or SSH when responsive).
# Kills stuck deploy/audit jobs and brings the site back — NO module upgrade.
set -euo pipefail
cd /root/reware
COMPOSE=(docker compose --env-file .env)

echo "[kill] Stopping one-off odoo run containers..."
docker ps -a --filter "name=reware-web-run" --format '{{.ID}}' | xargs -r docker rm -f

echo "[kill] Stopping heavy host processes..."
pkill -9 -f 'pg_dump.*cocreativeit-quote' 2>/dev/null || true
pkill -9 -f 'odoo -u quote_manage_ui' 2>/dev/null || true
pkill -9 -f 'odoo shell' 2>/dev/null || true

echo "[kill] Restarting stack (same as deploy-reware-remote.sh tail)..."
"${COMPOSE[@]}" restart web caddy

sleep 4
"${COMPOSE[@]}" ps
echo "[kill] Done. Check https://www.reware-project.com"
