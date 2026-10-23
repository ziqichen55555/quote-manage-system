# Website cart debug (localhost)

Use when you see **MissingError** on `sale.order.line`, or **cart badge ≠ cart page** (session qty vs order lines).

---

## 1. Turn on debug

**Option A — environment variable (good for local Odoo)**

```powershell
$env:QUOTE_WEBSITE_CART_DEBUG = "1"
# then start Odoo as you usually do
```

**Option B — system parameter (any environment)**

Settings → Technical → System Parameters → create:

| Key | Value |
|-----|--------|
| `quote_manage_ui.website_cart_debug` | `1` |

Turn off with `0` when finished. **Do not leave `1` on production** unless you are actively investigating.

If the URL shows **404 Page Not Found**, debug is usually **still off** (older builds hid the route). After setting the parameter, **restart Odoo** (`docker compose restart web`). Newer code returns **403** with plain text when debug is off.

---

## 2. Log output

Run Odoo with the addon logger at INFO (adjust path to your Odoo start command):

```text
--log-handler=odoo.addons.quote_manage_ui.website_cart_debug:INFO
```

Or broader:

```text
--log-handler=odoo.addons.quote_manage_ui:INFO
```

Reproduce: add to cart → open `/shop/cart` → change qty. Look for lines starting with:

```text
[quote cart] sale_get_order...
[quote cart] cart_sync...
[quote cart] repair_cart...
[quote cart] cart_update...
```

Each line includes **user**, **session** (`sale_order_id`, `website_sale_cart_quantity`), **path**, and **extra** fields (line ids, stale cache ids, etc.).

---

## 3. JSON snapshot (guest or logged-in)

Use the **same browser session** as your test (important for guests: same incognito window).

**Guest / 访客:** log out of Odoo, or use a private/incognito window — do **not** log in. Add to cart, then open debug URL in that **same** window.

While debug is enabled:

```text
http://localhost:8069/shop/cart/debug
http://localhost:8069/quote-cart-debug
```

Or open **`/shop/cart`** — a yellow **Cart debug** box appears at the top (same JSON).

Check routes from PowerShell: `.\scripts\test-local-cart-debug.ps1`

Use **8069** (Odoo) or **8070** (nginx). Do **not** use the production URL while testing locally.

(Use your local port / db if different.)

Returns JSON:

- session vs order id  
- `db_line_ids` vs `cached_order_line_ids` vs `stale_cached_line_ids`  
- `website_order_lines` (what the cart template uses)  
- `cart_quantity`  

If `stale_cached_line_ids` is non-empty, the ORM cache still references deleted lines — that matches **MissingError** stack traces.

---

## 4. Reproduce checklist

1. Enable debug (step 1) + logging (step 2).  
2. Note **user id** (internal user vs public).  
3. Add product on `/shop` — watch `cart_update_json` / `_cart_update` logs.  
4. Open `/shop/cart/debug` — save JSON.  
5. If you also edit the **same** quotation in the backend, repeat step 4 and compare line ids.  
6. Compare header badge (`website_sale_cart_quantity` in session) with `cart_quantity` in JSON.

---

## 中文

1. 设 `QUOTE_WEBSITE_CART_DEBUG=1` 或系统参数 `quote_manage_ui.website_cart_debug=1`。  
2. Odoo 日志级别 INFO，搜 `[quote cart]`。  
3. **访客**：无痕窗口加购后，同一窗口打开 `/shop/cart/debug`（无需登录；JSON 里 `visitor.is_public` 应为 true）。  
4. 查完记得关掉 debug，生产环境不要长期开着。
