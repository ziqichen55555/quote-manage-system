#!/bin/bash
cd /root/reware
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "SELECT pg_typeof(name) FROM product_template LIMIT 1;"
docker compose exec -T db psql -U odoo -d preimport_sep11 -c "SELECT id, default_code, name FROM product_template WHERE active LIMIT 3;"
