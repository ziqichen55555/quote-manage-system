#!/bin/sh
set -eu
DBNAME="cocreativeit-quote"
DUMP="/tmp/odoo-restore.sql.gz"
psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DBNAME}' AND pid != pg_backend_pid();"
psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \"${DBNAME}\";"
psql -U odoo -d postgres -c "CREATE DATABASE \"${DBNAME}\" OWNER odoo;"
gunzip -c "${DUMP}" | psql -U odoo -d "${DBNAME}"
rm -f "${DUMP}"
