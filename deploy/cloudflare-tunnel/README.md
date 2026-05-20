# 方案 B：本地 Docker + Cloudflare Tunnel（免费公网访问）

让 `https://reware-project.com` 指向你 Mac 上运行的 Odoo（`localhost:8070`）。

## 前提

- 本地 Docker 已启动：`docker compose up -d`
- 本机可访问：http://localhost:8070
- 已安装 `cloudflared`：`brew install cloudflared`

## 第一步：把 DNS 迁到 Cloudflare（一次性，约 10 分钟）

1. 打开 https://dash.cloudflare.com → **Add a site** → 输入 `reware-project.com`
2. 选择 **Free** 计划
3. Cloudflare 会扫描现有 DNS（Mailgun 等记录会保留）→ 确认后 Continue
4. 记下 Cloudflare 给你的两个 Nameserver，例如：
   - `xxx.ns.cloudflare.com`
   - `yyy.ns.cloudflare.com`
5. 登录 **Squarespace** → Domains → `reware-project.com` → **Domain Nameservers**
6. 把 Squarespace 的 NS 改成 Cloudflare 提供的两个（替换掉默认 NS）
7. 回到 Cloudflare 点 **Continue**，等待状态变为 **Active**（通常 5 分钟～几小时）

> 域名仍归 Squarespace 所有，只是 DNS 由 Cloudflare 管理。

## 第二步：登录并创建 Tunnel（本机终端执行）

```bash
cd /Users/chrischan/quote-manage-system

# 1. 浏览器授权（选 reware-project.com）
cloudflared tunnel login

# 2. 创建隧道
cloudflared tunnel create reware-local

# 3. 记下输出的 Tunnel ID（UUID），填入下面 config 文件名
```

## 第三步：写入 Tunnel 配置

把 `deploy/cloudflare-tunnel/config.yml.example` 复制到 `~/.cloudflared/config.yml`，并把 `TUNNEL_ID` 换成你的 UUID：

```bash
mkdir -p ~/.cloudflared
cp deploy/cloudflare-tunnel/config.yml.example ~/.cloudflared/config.yml
# 编辑 ~/.cloudflared/config.yml，替换 TUNNEL_ID
```

## 第四步：绑定域名 DNS

```bash
cloudflared tunnel route dns reware-local reware-project.com
cloudflared tunnel route dns reware-local www.reware-project.com
```

## 第五步：重启 Nginx 并启动 Tunnel

```bash
cd /Users/chrischan/quote-manage-system
docker compose restart nginx

# 前台运行（看日志）
./deploy/cloudflare-tunnel/start-tunnel.sh

# 或安装为开机自启（可选）
# sudo cloudflared service install
# sudo cloudflared service start
```

## 验证

- 浏览器打开：https://reware-project.com
- 应看到 Odoo 登录页，地址栏有 HTTPS 锁

## 注意事项

| 情况 | 结果 |
|------|------|
| Mac 关机/睡眠 | 网站不可访问 |
| Docker 未启动 | 网站 502 |
| 仅适合演示/内测 | 正式上线请改用 DigitalOcean |

## 以后升级到 DigitalOcean

1. 在 DO 部署 Odoo，拿到服务器 IP
2. Cloudflare DNS：把 `@` / `www` 从 Tunnel CNAME 改为 **A 记录** 指向 DO IP
3. 停止本机 Tunnel：`cloudflared tunnel cleanup reware-local`（可选）
