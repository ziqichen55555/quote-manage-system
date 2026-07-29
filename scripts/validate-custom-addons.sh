#!/usr/bin/env bash
# CI / pre-deploy: validate all custom_addons (manifest, XML, py compile)
# then install them on a throwaway Odoo database.
#
# Catches the class of failures that previously hit production:
#   * Odoo view ParseError (missing fields in modifiers, bad xpath)
#   * Broken model inheritance / TypeError on registry load
#   * Invalid __manifest__.py / malformed XML
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ADDONS_DIR="quote-manage-system/custom_addons"
DB="ci_custom_addons_$$"

log() { printf '[validate-custom-addons] %s\n' "$*"; }

MODULES=()
for manifest in "$ADDONS_DIR"/*/__manifest__.py; do
  [[ -f "$manifest" ]] || continue
  MODULES+=("$(basename "$(dirname "$manifest")")")
done
IFS=$'\n' MODULES=($(printf '%s\n' "${MODULES[@]}" | sort))
unset IFS

if [[ ${#MODULES[@]} -eq 0 ]]; then
  log "ERROR: no custom modules found under ${ADDONS_DIR}"
  exit 1
fi

MODULE_CSV="$(IFS=,; echo "${MODULES[*]}")"
log "Modules: ${MODULE_CSV}"

log "Checking manifests, Python syntax, and XML..."
python3 - <<'PY'
import ast
import compileall
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

addons = Path("quote-manage-system/custom_addons")
modules = sorted(
    p for p in addons.iterdir()
    if p.is_dir() and (p / "__manifest__.py").exists()
)
if not modules:
    print("No custom modules found", file=sys.stderr)
    sys.exit(1)

errors = 0
for module in modules:
    manifest = module / "__manifest__.py"
    try:
        ast.literal_eval(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL manifest {manifest}: {exc}", file=sys.stderr)
        errors += 1
        continue
    print(f"OK manifest {manifest}")

    if not compileall.compile_dir(str(module), quiet=1, force=True):
        print(f"FAIL python compile {module}", file=sys.stderr)
        errors += 1

    for path in sorted(module.rglob("*.xml")):
        try:
            ET.parse(path)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL xml {path}: {exc}", file=sys.stderr)
            errors += 1
        else:
            print(f"OK xml {path}")

if errors:
    sys.exit(1)
PY

log "Starting Postgres..."
docker compose up -d db

log "Waiting for Postgres..."
ready=0
for _ in $(seq 1 60); do
  if docker compose exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  log "ERROR: Postgres did not become ready"
  exit 1
fi

log "Installing modules on throwaway DB ${DB}: ${MODULE_CSV}"
# Odoo resolves dependency order. Failures here (view ParseError, registry
# TypeError, missing deps) must block merge / production deploy.
docker compose run --rm --no-deps web odoo \
  -c /etc/odoo/odoo.conf \
  -d "$DB" \
  -i "$MODULE_CSV" \
  --stop-after-init \
  --without-demo=all

if [[ -f scripts/sync_rw_templates.py ]] && printf '%s\n' "${MODULES[@]}" | grep -qx 'quote_manage_ui'; then
  log "Running template sync on CI database..."
  docker compose run --rm --no-deps -T web odoo shell \
    -c /etc/odoo/odoo.conf \
    -d "$DB" \
    --stop-after-init < scripts/sync_rw_templates.py
fi

log "Dropping throwaway database ${DB}..."
docker compose exec -T db dropdb -U odoo --if-exists "$DB" >/dev/null 2>&1 || true

log "All custom_addons checks passed."
