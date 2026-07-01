"""Configure Google Custom Search for Odoo product_images module.

Run on the server via odoo shell (stdin):

  docker compose -f docker-compose.prod.yml --env-file .env run --rm -T web \\
    odoo shell -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init \\
    < scripts/setup_google_product_images.py

Required environment variables:
  GOOGLE_CUSTOM_SEARCH_KEY   API key (Custom Search API enabled in Google Cloud)
  GOOGLE_PSE_ID              Programmable Search Engine ID (cx)

Optional:
  INSTALL_PRODUCT_IMAGES=1   Also install/upgrade the product_images module

Idempotent: safe to re-run. Prints whether each parameter is set (not the secret).
"""
import os

API_KEY = (os.environ.get("GOOGLE_CUSTOM_SEARCH_KEY") or "").strip()
PSE_ID = (os.environ.get("GOOGLE_PSE_ID") or "").strip()
INSTALL = os.environ.get("INSTALL_PRODUCT_IMAGES", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

if not API_KEY or not PSE_ID:
    raise SystemExit(
        "Missing GOOGLE_CUSTOM_SEARCH_KEY and/or GOOGLE_PSE_ID.\n"
        "Get them from:\n"
        "  1. Google Cloud Console → enable Custom Search API → create API key\n"
        "  2. programmablesearchengine.google.com → create engine → copy Search engine ID\n"
        "Then re-run with both env vars set."
    )

icp = env["ir.config_parameter"].sudo()
icp.set_param("google.custom_search.key", API_KEY)
icp.set_param("google.pse.id", PSE_ID)

if INSTALL:
    Module = env["ir.module.module"].sudo()
    mod = Module.search([("name", "=", "product_images")], limit=1)
    if not mod:
        raise SystemExit("product_images module record not found.")
    if mod.state != "installed":
        mod.button_immediate_install()
        print("product_images: installed")
    else:
        print("product_images: already installed")

env.cr.commit()

def _masked(value):
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

print("google.custom_search.key =", _masked(API_KEY))
print("google.pse.id =", _masked(PSE_ID))
print("Done. Retry 'Get pictures from Google' on products.")
