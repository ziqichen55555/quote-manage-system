# -*- coding: utf-8 -*-
import subprocess

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except Exception as e:
        return str(e)

print("=== FETCHING PRODUCTION WEB LOGS ===")
# Adjust path to where docker-compose.prod.yml is, usually in the app dir
# We use the environment variables from the workflow to find the dir
print(run_cmd("cd /home/odoo/reware && docker compose logs --tail=50 web"))
