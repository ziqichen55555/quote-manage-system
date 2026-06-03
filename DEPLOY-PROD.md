# 生产部署指南（Oracle Cloud + DuckDNS + Caddy）

> 目标：完全免费、24/7 在线、HTTPS 锁。
> 现在用 `xxx.duckdns.org` 临时子域名，将来再切回 `reware-project.com`。

## 文件清单（仓库根目录）

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 本地开发用（nginx 反代，无 HTTPS） |
| `docker-compose.prod.yml` | 生产用（Caddy 自动 HTTPS） |
| `Caddyfile` | Caddy 反代 + 证书配置 |
| `.env.prod.example` | 生产环境变量模板，复制为 `.env` 后填值 |

---

## 0. 准备阶段

### 0.1 Oracle Cloud Free Tier 申请
1. https://www.oracle.com/cloud/free/ 注册（需信用卡验证，不扣款）
2. 创建 Compute Instance
   - Image: **Canonical Ubuntu 22.04**
   - Shape: **VM.Standard.A1.Flex** → 4 OCPU / 24 GB（永久免费上限）
   - 勾选 **Assign a public IPv4 address**
   - 下载 SSH 私钥
3. 记下 Public IP

### 0.2 DuckDNS 子域名
1. https://www.duckdns.org → 用 GitHub / Google 登录
2. 在 `sub domain` 框输入想要的名字，例如 `reware-app`，点 **add domain**
3. 完整域名变成 `reware-app.duckdns.org`
4. 在 **current ip** 那一列填入 Oracle Public IP → 点 **update ip**
5. 记下页面顶部的 **token**（一长串 UUID，做 IP 自动同步要用）

> 验证：在自己电脑执行 `nslookup reware-app.duckdns.org`，应返回 Oracle IP。

### 0.3 Oracle 防火墙放行 80/443

**在 Oracle Console**：
- VCN → **Default Security List** → **Add Ingress Rule**
- Source CIDR `0.0.0.0/0`，Destination Port Range `80`，重复加 `443`

**在 VM 内**（Ubuntu 默认 iptables 把入站都关了）：
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## 1. 服务器初始化

```bash
ssh -i ~/.ssh/oracle.key ubuntu@<PUBLIC_IP>

sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2. 拉代码并配置

```bash
git clone https://github.com/ziqichen55555/quote-manage-system.git
cd quote-manage-system

# 复制环境变量并编辑
cp .env.prod.example .env
nano .env
```

`.env` 填三项：
```ini
SITE_HOSTNAME=reware-app.duckdns.org
ACME_EMAIL=your-real-email@example.com
POSTGRES_PASSWORD=$(openssl rand -base64 24 已经生成的强密码)
```

**重要**：同步修改 `config/odoo.conf` 的 `db_password` 为同一个值：
```bash
sed -i "s|^db_password = .*|db_password = $(grep ^POSTGRES_PASSWORD .env | cut -d= -f2-)|" config/odoo.conf
```

---

## 3. 启动服务

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d

# 看日志确认起来了
docker compose -f docker-compose.prod.yml logs -f caddy
# 应该看到 "certificate obtained successfully"
# Ctrl+C 退出日志（不会停服务）
```

---

## 4. 首次初始化数据库（仅第一次）

```bash
docker compose -f docker-compose.prod.yml --env-file .env run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d cocreativeit-quote \
  -i quote_manage_ui \
  --stop-after-init

docker compose -f docker-compose.prod.yml --env-file .env restart web caddy
```

---

## 5. 验证

浏览器打开 `https://reware-app.duckdns.org`：
- Odoo 登录页
- 地址栏 HTTPS 锁
- 证书颁发者 **Let's Encrypt**

---

## 6. DuckDNS IP 自动同步（推荐做）

Oracle Free Tier 公网 IP 一般稳定不变，但加上保险：

```bash
# 替换 <token> 和 <subdomain>
crontab -e
```

加一行：
```
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=<subdomain>&token=<token>&ip=" > /dev/null 2>&1
```

每 5 分钟检测并自动更新 IP。

---

## 7. 日常运维

```bash
# 看服务状态
docker compose -f docker-compose.prod.yml ps

# 看日志
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f caddy

# 升级 quote_manage_ui 模块（改完代码后）
git pull

# 推荐：一键脚本（含 DB 备份 + 升级 + sync 锁定模板 + 重启）
chmod +x scripts/deploy-prod.sh
./scripts/deploy-prod.sh

# 或手动四步（缺一不可）：
# 1) 升级模块
docker compose -f docker-compose.prod.yml --env-file .env run --rm web odoo \
  -c /etc/odoo/odoo.conf -d cocreativeit-quote \
  -u quote_manage_ui --stop-after-init
# 2) 同步 Website Builder 锁定的模板（header / 页面 arch 等）
docker compose -f docker-compose.prod.yml --env-file .env run --rm -T web odoo shell \
  -c /etc/odoo/odoo.conf -d cocreativeit-quote --stop-after-init \
  < scripts/sync_rw_templates.py
# 3) 重启
docker compose -f docker-compose.prod.yml --env-file .env restart web caddy

# 停止
docker compose -f docker-compose.prod.yml down

# 完全清空（含数据，谨慎）
docker compose -f docker-compose.prod.yml down -v
```

---

## 8. 数据备份（推荐做）

```bash
sudo tee /usr/local/bin/odoo-backup.sh > /dev/null <<'EOF'
#!/usr/bin/env bash
set -e
DATE=$(date +%Y%m%d-%H%M)
DEST=/home/ubuntu/backups
mkdir -p $DEST

cd /home/ubuntu/quote-manage-system

# 数据库
docker compose -f docker-compose.prod.yml --env-file .env exec -T db \
  pg_dump -U odoo cocreativeit-quote | gzip > $DEST/db-$DATE.sql.gz

# 文件存储（图片、附件）
docker run --rm \
  -v quote-manage-system_odoo-web-data:/data \
  -v $DEST:/backup alpine \
  tar czf /backup/filestore-$DATE.tar.gz -C /data .

# 保留 14 天
find $DEST -type f -mtime +14 -delete
EOF

sudo chmod +x /usr/local/bin/odoo-backup.sh

crontab -e
# 加一行（每天凌晨 3 点）
0 3 * * * /usr/local/bin/odoo-backup.sh >> /var/log/odoo-backup.log 2>&1
```

---

## 9. 未来切回 reware-project.com 的迁移步骤

到时候你只需要做这三件事：

### 9.1 把 reware-project.com 的 DNS 指过来
两种方式选一种：

**A. 不迁 NS（保留 Squarespace 主网站）**
- 登 Squarespace DNS 管理
- 加一条 A 记录：`@` 或 `app` 子域名 → `<Oracle Public IP>`
- 比如让 `app.reware-project.com` 指向 Odoo，主站 `reware-project.com` 继续给 Squarespace

**B. 迁 NS 到 Cloudflare（更灵活、可选）**
- 跟之前讨论一样，把 NS 改成 Cloudflare 的两个 NS
- 在 Cloudflare DNS 加 A 记录指 Oracle IP

### 9.2 改一行 `.env`
```bash
ssh ubuntu@<PUBLIC_IP>
cd quote-manage-system
nano .env
# 把 SITE_HOSTNAME=reware-app.duckdns.org
# 改成 SITE_HOSTNAME=app.reware-project.com（或你定的最终域名）
```

### 9.3 重启 Caddy（自动签新证书）
```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d
# Caddy 会自动给新域名签 Let's Encrypt 证书
docker compose -f docker-compose.prod.yml logs -f caddy
```

完成。**无需重新部署、无需停机超过 10 秒**。

---

## 10. GitHub Actions（CI/CD）

仓库已包含两个 workflow：

| Workflow | 触发 | 作用 |
|---|---|---|
| `.github/workflows/ci-quote-manage-ui.yml` | 开 PR 且改了 `custom_addons` / `scripts` | 校验 XML + 在临时库试装 `quote_manage_ui` |
| `.github/workflows/deploy-prod.yml` | push 到 `main` 且改了模块/脚本/配置 | SSH 登录生产机 → `git pull` → `scripts/deploy-prod.sh` |

### 10.1 一次性配置 GitHub Secrets

在 GitHub 仓库 **Settings → Secrets and variables → Actions → New repository secret**：

| Secret | 示例值 | 说明 |
|---|---|---|
| `PROD_SSH_HOST` | `123.45.67.89` 或 `reware-app.duckdns.org` | Oracle VM 公网地址 |
| `PROD_SSH_USER` | `ubuntu` | SSH 用户名 |
| `PROD_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | 登录 VM 的私钥全文 |
| `PROD_APP_DIR` | `/home/ubuntu/quote-manage-system` | 服务器上仓库路径 |

### 10.2 服务器端准备（只需一次）

```bash
# 确保 deploy 脚本能执行
chmod +x ~/quote-manage-system/scripts/deploy-prod.sh

# 若用 GitHub Actions 拉代码，确保 ubuntu 用户能 git pull（HTTPS 或 deploy key）
cd ~/quote-manage-system
git remote -v
```

### 10.3 日常开发流程

1. 开分支改代码 → 提 PR → CI 自动跑校验
2. 合并到 `main` → CD 自动 SSH 部署（约 2–5 分钟）
3. 也可手动 SSH 部署：`./scripts/deploy-prod.sh`

> **注意**：`-u quote_manage_ui`  alone 不会刷新 Website Builder 锁定的视图；`deploy-prod.sh` 已包含 `sync_rw_templates.py` 步骤。

---

## 故障排查

| 现象 | 原因 / 解决 |
|---|---|
| 浏览器 502 | 看 `docker compose -f docker-compose.prod.yml logs web`，多半是 db 没起来 |
| 浏览器 "证书无效" | 检查 80/443 防火墙、检查域名是否真的解析到 VM、看 caddy 日志 |
| "Database not found" | 没跑第 4 步初始化数据库 |
| 一直转圈不响应 | WebSocket 没生效；确认用了 `docker-compose.prod.yml` 而不是旧的 nginx 版 |
| Caddy 日志报 "challenge failed" | 80 端口被占或防火墙没开；先 `curl http://<DOMAIN>` 看通不通 |
