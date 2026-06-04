# DigitalOcean production (`/root/reware`)

Canonical URL: **https://www.reware-project.com**

## 1. Squarespace DNS（Custom records）

| TYPE | NAME | DATA |
|------|------|------|
| A | `www` | `134.199.145.67` |
| A | `app` | `134.199.145.67` *(optional backup URL)* |
| A | `@` | `134.199.145.67` *(apex → server; Caddy redirects to www)* |

Do **not** remove Mailgun / email TXT / MX records.

After adding `@`, wait a few minutes, then check:

```bash
nslookup reware-project.com 8.8.8.8
nslookup www.reware-project.com 8.8.8.8
```

Both should return `134.199.145.67`.

## 2. Update Caddy on the server

From your laptop (repo root):

```powershell
scp -i $env:USERPROFILE\.ssh\id_ed25519_do deploy/digitalocean/Caddyfile root@134.199.145.67:/root/reware/Caddyfile
```

On the server:

```bash
cd /root/reware
docker compose --env-file .env up -d --force-recreate caddy
docker compose --env-file .env logs -f caddy
```

Logs should list TLS for `reware-project.com`, `www.reware-project.com`, and `app.reware-project.com`.

## 3. Set Odoo `web.base.url`

Copy scripts to the server once (or pull if you keep git there):

```powershell
scp -i $env:USERPROFILE\.ssh\id_ed25519_do scripts/set_odoo_web_base_url.py scripts/set-odoo-web-base-url.sh root@134.199.145.67:/root/reware/scripts/
```

On the server:

```bash
chmod +x /root/reware/scripts/set-odoo-web-base-url.sh
cd /root/reware
./scripts/set-odoo-web-base-url.sh
```

## 4. Verify

- https://www.reware-project.com — Odoo, green lock
- https://reware-project.com — redirects to www
- https://app.reware-project.com — still works (remove DNS + Caddy line when done)

## 5. Optional cleanup

When you no longer need `app`:

1. Delete Squarespace A record for `app`
2. Edit `Caddyfile`: remove `app.reware-project.com` from the site block
3. `docker compose --env-file .env up -d --force-recreate caddy`
