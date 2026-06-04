"""Set Odoo web.base.url (and freeze) for production. Run via odoo shell on the server."""
import os

url = (os.environ.get("WEB_BASE_URL") or "https://www.reware-project.com").rstrip("/")
icp = env["ir.config_parameter"].sudo()
icp.set_param("web.base.url", url)
icp.set_param("web.base.url.freeze", "True")
env.cr.commit()
print(f"web.base.url = {url!r}, web.base.url.freeze = True")
