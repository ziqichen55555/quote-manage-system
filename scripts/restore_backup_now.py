#!/usr/bin/env python3
"""Restore cocreativeit-quote from gzip pg_dump (Windows-safe, LF script)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP = ROOT / "backups" / "db-before-merged-import-20260618-102906.sql.gz"
DB = "cocreativeit-quote"
DUMP = "/tmp/odoo-restore.sql.gz"
SCRIPT = "/tmp/restore_db_inside.sh"

SH = f"""#!/bin/sh
set -eu
psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \\"{DB}\\";"
psql -U odoo -d postgres -c "CREATE DATABASE \\"{DB}\\" OWNER odoo;"
gunzip -c {DUMP} | psql -U odoo -d "{DB}"
rm -f {DUMP} {SCRIPT}
"""


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    backup = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_BACKUP
    if not backup.is_file():
        print(f"Backup not found: {backup}", file=sys.stderr)
        return 1
    local_sh = ROOT / "scripts" / "_restore_run.sh"
    local_sh.write_text(SH, encoding="utf-8", newline="\n")
    try:
        run("docker", "compose", "stop", "web")
        run("docker", "compose", "cp", str(backup), f"db:{DUMP}")
        run("docker", "compose", "cp", str(local_sh), f"db:{SCRIPT}")
        run("docker", "compose", "exec", "-T", "db", "sh", SCRIPT)
        run("docker", "compose", "start", "web")
    finally:
        if local_sh.exists():
            local_sh.unlink()
    print("[restore] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
