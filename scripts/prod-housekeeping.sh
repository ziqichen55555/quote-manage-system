#!/usr/bin/env bash
# Periodic production housekeeping (DigitalOcean /root/reware).
# Frees disk (logs, stale manual backups) and RAM (stuck odoo one-shot containers).
#
# Run on the server:
#   chmod +x /root/reware/scripts/prod-housekeeping.sh
#   /root/reware/scripts/prod-housekeeping.sh              # dry-run (default)
#   DRY_RUN=0 CONFIRM=APPLY /root/reware/scripts/prod-housekeeping.sh
#   /root/reware/scripts/prod-housekeeping.sh --apply
#
# From Windows (repo root):
#   .\scripts\run-prod-housekeeping.ps1
#   .\scripts\run-prod-housekeeping.ps1 -ConfirmApply APPLY
#
# Optional env:
#   JOURNAL_MAX=400M          max size for systemd journal after vacuum
#   KEEP_BACKUP_DAYS=14       db-*.dump + filestore-*.tar.gz (matches odoo-backup.sh)
#   KEEP_SQL_GZ_DAYS=7        manual db-*.sql.gz from deploy/shell exports
#   DROP_CACHES=1             also drop Linux page cache (brief spike; frees RAM cache only)
#   REWARE_DIR=/root/reware
#
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
CONFIRM="${CONFIRM:-}"
JOURNAL_MAX="${JOURNAL_MAX:-400M}"
KEEP_BACKUP_DAYS="${KEEP_BACKUP_DAYS:-14}"
KEEP_SQL_GZ_DAYS="${KEEP_SQL_GZ_DAYS:-7}"
DROP_CACHES="${DROP_CACHES:-0}"
REWARE_DIR="${REWARE_DIR:-/root/reware}"
BACKUP_DIR="${BACKUP_DIR:-$REWARE_DIR/backups}"

usage() {
  sed -n '2,20p' "$0" | tail -n +2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      DRY_RUN=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --drop-caches)
      DROP_CACHES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$DRY_RUN" == "0" && "$CONFIRM" != "APPLY" ]]; then
  echo "Refusing to apply without CONFIRM=APPLY (or run via run-prod-housekeeping.ps1 -ConfirmApply APPLY)." >&2
  echo "Dry-run preview: DRY_RUN=1 $0" >&2
  exit 1
fi

log() { echo "[housekeeping $(date '+%F %T')] $*"; }

run_or_print() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: $*"
  else
    log "RUN: $*"
    eval "$@"
  fi
}

report() {
  log "--- $1 ---"
  df -h / | tail -n 1 || true
  free -h | sed -n '1,2p' || true
  journalctl --disk-usage 2>/dev/null || true
  docker ps -a --filter name=reware-web-run --format 'stuck: {{.Names}} {{.Status}}' 2>/dev/null || true
  docker system df 2>/dev/null || true
}

log "mode=$([[ "$DRY_RUN" == "1" ]] && echo dry-run || echo APPLY) journal_max=$JOURNAL_MAX keep_dump_days=$KEEP_BACKUP_DAYS keep_sql_gz_days=$KEEP_SQL_GZ_DAYS drop_caches=$DROP_CACHES"
report "before"

# --- RAM: stuck one-shot Odoo containers ---
stuck_ids="$(docker ps -aq --filter name=reware-web-run 2>/dev/null || true)"
if [[ -n "$stuck_ids" ]]; then
  run_or_print "docker rm -f $stuck_ids"
else
  log "No reware-web-run containers."
fi

# --- Docker: exited containers + dangling images (not used images) ---
run_or_print "docker container prune -f"
run_or_print "docker image prune -f"

# --- Disk: systemd journal ---
if [[ "$DRY_RUN" == "1" ]]; then
  log "DRY-RUN: journalctl --vacuum-size=$JOURNAL_MAX"
else
  journalctl --vacuum-size="$JOURNAL_MAX"
fi

# --- Disk: failed SSH login logs (often huge from bots) ---
for f in /var/log/btmp /var/log/btmp.1; do
  if [[ -f "$f" && -s "$f" ]]; then
    run_or_print "truncate -s 0 '$f'"
  fi
done

run_or_print "apt-get clean"

# --- Backups: same retention as odoo-backup.sh for scheduled dumps ---
if [[ -d "$BACKUP_DIR" ]]; then
  while IFS= read -r -d '' f; do
    if [[ "$DRY_RUN" == "1" ]]; then
      log "DRY-RUN: would delete old dump/filestore: $f"
    else
      log "delete: $f"
      rm -f "$f"
    fi
  done < <(find "$BACKUP_DIR" -type f \( -name 'db-*.dump' -o -name 'filestore-*.tar.gz' \) -mtime +"$KEEP_BACKUP_DAYS" -print0 2>/dev/null || true)

  while IFS= read -r -d '' f; do
    if [[ "$DRY_RUN" == "1" ]]; then
      log "DRY-RUN: would delete old sql.gz: $f"
    else
      log "delete: $f"
      rm -f "$f"
    fi
  done < <(find "$BACKUP_DIR" -type f -name 'db-*.sql.gz' -mtime +"$KEEP_SQL_GZ_DAYS" -print0 2>/dev/null || true)

  # Empty placeholder files
  while IFS= read -r -d '' f; do
    if [[ "$DRY_RUN" == "1" ]]; then
      log "DRY-RUN: would delete empty backup: $f"
    else
      rm -f "$f"
    fi
  done < <(find "$BACKUP_DIR" -type f -empty -print0 2>/dev/null || true)
else
  log "Backup dir missing (skip): $BACKUP_DIR"
fi

# --- RAM: page cache only (optional; does not replace upgrading RAM/swap) ---
if [[ "$DROP_CACHES" == "1" ]]; then
  run_or_print "sync"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY-RUN: echo 3 > /proc/sys/vm/drop_caches"
  else
    echo 3 > /proc/sys/vm/drop_caches
  fi
fi

report "after"
log "Done."
