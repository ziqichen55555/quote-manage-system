#!/usr/bin/env bash
# CI validation: XML well-formedness + install quote_manage_ui on a throwaway DB.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODULE_DIR="quote-manage-system/custom_addons/quote_manage_ui"
DB="ci_quote_manage_ui_$$"

log() { printf '[validate] %s\n' "$*"; }

log "Checking XML files in quote_manage_ui..."
python3 - <<'PY'
import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

module = Path("quote-manage-system/custom_addons/quote_manage_ui")
manifest = module / "__manifest__.py"
ast.literal_eval(manifest.read_text(encoding="utf-8"))  # syntax check

paths = sorted(module.rglob("*.xml"))
if not paths:
    print("No XML files found", file=sys.stderr)
    sys.exit(1)
for path in paths:
    ET.parse(path)
    print(f"OK {path}")
PY

log "Starting db for module install test..."
docker compose up -d db

log "Waiting for Postgres..."
for _ in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose run --rm --no-deps web odoo \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  -i quote_manage_ui \
  --stop-after-init \
  --without-demo=all

log "Running template sync on CI database..."
docker compose run --rm --no-deps -T web odoo shell \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  --stop-after-init < scripts/sync_rw_templates.py

log "All checks passed."
