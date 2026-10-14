#!/bin/bash
set -euo pipefail
cd /root/reware
docker ps -a --filter name=reware-web-run --format '{{.ID}}' | xargs -r docker rm -f
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS preimport_sep11;"
echo "cleanup_done"
