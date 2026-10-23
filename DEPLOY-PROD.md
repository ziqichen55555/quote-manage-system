# Production deploy (Re-Ware / Odoo)

**Site:** https://www.reware-project.com  
**Branch:** `main` (merge does **not** auto-deploy — deploy is manual only.)

---

## Prerequisites

- [GitHub CLI](https://cli.github.com/) (`gh`) installed and logged in: `gh auth status`
- Repo cloned locally; latest `main`: `git pull origin main`
- Changes you want live are **committed and pushed** to `main`

---

## 1. Check for running production jobs (required)

Never start Deploy while **Deploy production**, **Repair production**, or **Run Odoo shell on production** is `queued` / `in_progress`.  
The server is ~1GB RAM — **one Odoo shell at a time**, no parallel Deploy + shell.

### Option A — script (recommended)

```powershell
cd C:\Users\User\quote-management-system\quote-manage-system
.\scripts\check-prod-jobs.ps1
```

- Exit **0** → safe to deploy  
- Exit **1** → wait; URLs of blocking runs are printed

### Option B — manual

```powershell
gh run list --limit 15
```

Look for **in_progress** / **queued** on:

| Workflow name |
|---------------|
| Deploy production |
| Repair production |
| Run Odoo shell on production |

---

## 2. Trigger deploy

### Interactive (you type `DEPLOY`)

```powershell
cd C:\Users\User\quote-management-system\quote-manage-system
.\scripts\trigger-prod-deploy.ps1
```

The script **also** blocks if a prod job is already running (same rules as step 1).

### Non-interactive (after you decided to deploy)

```powershell
.\scripts\trigger-prod-deploy.ps1 -ConfirmDeploy DEPLOY
```

Equivalent:

```powershell
gh workflow run "Deploy production" --ref main -f confirm_deploy=DEPLOY
```

---

## 3. Watch until finished

After trigger, the script prints a run URL. Watch it:

```powershell
gh run watch <RUN_ID> --exit-status
```

Or list recent deploys:

```powershell
gh run list --workflow "Deploy production" --limit 5
```

Typical duration: **~4–5 minutes** (validate on CI + upload + `odoo -u` on server).

---

## 4. Smoke check

```powershell
curl.exe -sS -o NUL -w "home %{http_code}`n" https://www.reware-project.com/
curl.exe -sS -o NUL -w "shop %{http_code}`n" https://www.reware-project.com/shop
curl.exe -sS -o NUL -w "cart %{http_code}`n" https://www.reware-project.com/shop/cart
```

All should be **200**. Open the shop in a browser and spot-check cart/checkout if you changed `quote_manage_ui`.

---

## Quick reference (copy-paste)

```powershell
cd C:\Users\User\quote-management-system\quote-manage-system
git pull origin main
.\scripts\check-prod-jobs.ps1
.\scripts\trigger-prod-deploy.ps1
# then: gh run watch <id> --exit-status
```

---

## What deploy does

1. **validate** job — install/upgrade all `custom_addons` on a throwaway DB in GitHub Actions  
2. **deploy** job — SCP addons + scripts to the droplet, run module upgrade on production  

Workflow file: `.github/workflows/deploy-prod.yml`

---

## If deploy fails or site is down

- Read the failed step log on the GitHub run URL  
- Do **not** start a second Deploy while one is still running  
- If SSH/timeouts persist for **>5 minutes**, follow team runbook (Repair workflow / DigitalOcean power cycle — see `.cursor/rules/prod-safety.mdc`)

---

## 中文摘要

1. **先查进程**：`.\scripts\check-prod-jobs.ps1` 或 `gh run list --limit 15`，确认没有正在跑的 **Deploy / Repair / Odoo shell**。  
2. **再部署**：`.\scripts\trigger-prod-deploy.ps1`，提示时输入 **DEPLOY**（或 `-ConfirmDeploy DEPLOY`）。  
3. **盯完成**：`gh run watch <RUN_ID> --exit-status`。  
4. **冒烟**：访问首页、`/shop`、`/shop/cart` 应为 200。  

**注意：** 推送到 `main` 不会自动上线；必须手动跑上述部署。不要并行多个生产 Odoo shell。

---

## Local cart debugging

See [docs/DEBUG-WEBSITE-CART.md](docs/DEBUG-WEBSITE-CART.md) (`QUOTE_WEBSITE_CART_DEBUG=1`, logs, `/shop/cart/debug`).
