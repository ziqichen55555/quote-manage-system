# Re-Ware merge — How to use

**Merge logic version:** `20260708-import-all-cmos`  
**Folder:** put receipt / scan list + Blancco report here, then double-click `run_merge.bat`.

---

## 1. What this does

Joins your **product list** (model/MTM + serial) with the **Blancco export** and produces CSV/Excel files for Odoo import.

- **CMOS Pass** → shop SKU ends with `-CMOSP` (website when in stock)
- **CMOS Fail** → `-CMOSFL` (warehouse only; fix CMOS in Odoo later → CMOSP)
- **Sold serials** in `sold_serials_exclude.txt` are skipped (sales history stays on old orders)

---

## 2. Files you need in this folder

| File | What it is |
|------|------------|
| Product list | e.g. `SCANNED STOCK FOR PORTAL merged …csv` — columns **Device MTM** + **Serial** |
| Blancco report | e.g. `reports.csv` — many columns (CPU, disk, RAM, motherboard test, …) |
| `run_merge.bat` | Double-click to merge |
| `merge_receipt_blancco.py` | Auto-synced from git repo on each run (see below) |
| `sold_serials_exclude.txt` | One sold serial per line — do not import again |

### Blancco matching (merge script)

**Automatic (no guessing):**
1. ThinkCentre split scan → rebuild full SN (`3209A93PBL` + `VRWE` → `PBLVRWE`)
2. Exact match on reports System serial

**Not automatic:** single-char OCR swaps (`PC1450A6` vs `PC14S0A6`) — may be two different units.
Use `py probe_match_methods.py` to see *possible* matches, then verify the physical label.


Older ThinkCentre rows in the portal scan are **split across two columns**:

| Column A (model + SN prefix) | Column B (SN suffix) | Blancco system serial |
|------------------------------|----------------------|------------------------|
| `3209A93PBL` | `VRWE` | `PBLVRWE` |
| `5536RE5R85` | `PRX4` | `R85PRX4` |
| `4518PT1PBM` | `DFG4` | `PBMDFG4` |

- **Digit-start** = Lenovo **model** code in Blancco (e.g. `3209A93`, `5536RE5`)
- **P-start / R-start** (full or partial) = **serial number** in Blancco

The merge script rebuilds the full serial before matching `reports.csv`. Laptop rows (`20NYS4CP00`, `PC1ACMY3`) are unchanged.

**Merge multiple portal scans first (optional):**

```bat
py merge_scanned_stock.py
```

→ creates `SCANNED STOCK FOR PORTAL merged <date>.csv`

---

## 3. Run merge

1. Copy latest Blancco `reports.csv` into this folder.
2. Double-click **`run_merge.bat`**.
3. Confirm auto-detected files (or pick manually).
4. Check the console for:

   ```
   Merge logic version: 20260708-thinkcentre-sn
   Syncing merge_receipt_blancco.py from repo...
   ```

5. When finished, open the **Analysis** sheet in the Excel output.

### Script updates

`run_merge.bat` **overwrites** `merge_receipt_blancco.py` from:

`c:\Users\User\quote-management-system\quote-manage-system\tools\reware_merge\`

If you still see CMOS Fail machines in **import-not-ready**, the script is outdated — re-copy from repo or run from that repo folder.

---

## 4. Three output files — which one to upload?

| Output | Upload to Odoo? | Contents |
|--------|-----------------|----------|
| **`MERGED import-all <date>.csv`** | **YES — this one** | SUCCESS + CMOS Pass **and** CMOS Fail |
| `MERGED import-ready <date>.csv` | No | Pass only (subset; CMOS Fail **not** included) |
| `MERGED import-not-ready <date>.csv` | No | Blancco match failures + sold serials |

### import-not-ready is normal for:

- `Serial not found in Blancco` — fix serial in scan list or re-export Blancco
- `Sold (excluded from catalog)` — listed in `sold_serials_exclude.txt`

### import-not-ready is **wrong** if you see many rows with:

- `Status = SUCCESS` and `Not ready reason = CMOS Fail`  
  → **Old merge script.** Re-sync `merge_receipt_blancco.py` and run again. Those machines belong in **import-all** as `-CMOSFL`.

---

## 5. Upload to Odoo (production)

**One-time cleanup (fresh catalog):**

1. Backup production database.
2. Archive obsolete SKUs (admin script).
3. Upload **`MERGED import-all`** CSV.

**Regular import:**

1. Odoo → **Inventory** → **Upload inventory CSV**
2. Select **`MERGED import-all <date>.csv`**
3. Read the result summary (created / updated / retired orphans / sold skipped).

**After import:**

- CMOS Fail units are in warehouse on `*-CMOSFL` SKUs (not on website).
- When CMOS is fixed on the bench, change CMOS attribute to **Successful** (or move stock to CMOSP) in Odoo.

**Update sold list after each sale:**

Edit `sold_serials_exclude.txt`, then re-run merge before the next import.

---

## 6. Shop SKU pattern (Lenovo laptops)

Examples:

- `20NYS4CP00-BT70-CMOSP` — battery ≥70%, CMOS pass, on shop when stocked
- `20NYS4CP00-BT70-CMOSFL` — CMOS fail, warehouse only
- `20NYS4CP00-8G-256G-T-BT70-CMOSP` — same MTM, multiple RAM/SSD configs (different SKUs)

Desktops / HP / Dell use Blancco system SKU as MTM where applicable.

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| No `MERGED import-all` file | Old `merge_receipt_blancco.py` — sync from repo |
| 100+ CMOS Fail in not-ready | Same — old script treats Fail as not-ready |
| Upload rejected: import-not-ready file | Upload **import-all**, not not-ready |
| Upload rejected: import-ready only | Use **import-all** for CMOS Fail stock |
| Version line missing in console | Old `run_merge.bat` — copy from repo |

---

# 中文说明

## 1. 用途

把 **收货/扫描清单**（MTM + 序列号）和 **Blancco 报告** 合并，生成 Odoo 导入用的 CSV。

- **CMOS Pass** → `-CMOSP`（有货可上架）
- **CMOS Fail** → `-CMOSFL`（只进仓库，不上网站；以后在 Odoo 改成 Successful）
- **已售 SN** 写在 `sold_serials_exclude.txt`，不会进入新目录

## 2. 文件夹里要有什么

| 文件 | 说明 |
|------|------|
| 扫描清单 | 如 `SCANNED STOCK FOR PORTAL merged …csv` |
| Blancco | `reports.csv` |
| 双击 `run_merge.bat` | 运行合并 |

### ThinkCentre 台式机扫码格式（重要）

老型号 ThinkCentre 扫码是 **两列拆开** 的：

| A 列（型号 + SN 前缀） | B 列（SN 后缀） | Blancco 里的完整 SN |
|------------------------|-----------------|---------------------|
| `3209A93PBL` | `VRWE` | `PBLVRWE` |
| `5536RE5R85` | `PRX4` | `R85PRX4` |

- **数字开头** = Blancco 里的 **型号**（如 `3209A93`）
- **P / R 开头**（完整或片段）= **序列号 SN**

合并脚本会先拼回完整 SN 再对 `reports.csv`。笔记本行（`20NYS4CP00` + `PC1…`）不受影响。

多个扫描文件先合并：

```bat
py merge_scanned_stock.py
```

## 3. 运行

1. 放入最新 `reports.csv`
2. 双击 `run_merge.bat`
3. 确认看到：`Merge logic version: 20260708-thinkcentre-sn`
4. 看 Analysis 页统计

每次运行会从 git 仓库 **自动覆盖** 最新的 `merge_receipt_blancco.py`。

## 4. 三个输出文件 — 上传哪一个？

| 文件 | 上传 Odoo？ |
|------|-------------|
| **`MERGED import-all <日期>.csv`** | **要 — 上传这个** |
| `MERGED import-ready` | 不要（只有 Pass，没有 CMOS Fail） |
| `MERGED import-not-ready` | 不要（Blancco 失败 + 已售） |

**not-ready 里正常应有：**

- Blancco 找不到 SN
- 已售 SN（exclude 列表）

**不正常：** 大量 `Status=SUCCESS` + 原因 `CMOS Fail` → **脚本太旧**，请同步后重跑；这些应在 **import-all** 里（`-CMOSFL`）。

## 5. 导入 Odoo

1. （一次性）备份 → archive 旧 SKU → 上传 **import-all**
2. 日常：**Inventory → Upload inventory CSV** → 选 **import-all**
3. CMOS Fail 机器在 `*-CMOSFL`，修好后再改 CMOS / 转 CMOSP
4. 每卖出一台，更新 `sold_serials_exclude.txt` 再 merge

## 6. 常见问题

| 现象 | 处理 |
|------|------|
| 没有 import-all 文件 | 旧脚本，从 repo 复制 |
| CMOS Fail 全在 not-ready | 同上，重跑 merge |
| 传错 not-ready / import-ready | 只传 **import-all** |

---

*Last updated: 2026-07-08*
