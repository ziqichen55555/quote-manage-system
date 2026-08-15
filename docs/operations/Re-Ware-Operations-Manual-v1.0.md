# Re-Ware Operations Manual v1.0

**Status:** Working standard  
**Audience:** All Re-Ware staff  
**Scope:** Sales, Inventory, Returns, Warehouse areas  
**Version:** 1.0 · 2026-08-15

---

## 0. Purpose of this manual

This document defines Re-Ware’s standard operating processes for sales, inventory, returns, and warehouse areas.

It is based on:

| Source | Role in this manual |
|--------|---------------------|
| [ISO 9001 — Quality management systems](https://www.iso.org/standard/62085.html) | Purpose, trigger, steps, responsibility, control, definition of done |
| [ISO 10013 — Guidance for documented information](https://www.iso.org/standard/75792.html) | Keep documentation practical and proportionate |
| [Lean Enterprise Institute — Standardized Work](https://www.lean.org/lexicon-terms/standardized-work/) | Document the current best-known way of working |
| [PDCA (Plan–Do–Check–Act)](https://www.lean.org/lexicon-terms/pdca/) | Improve the standard over time (v1.0 → v1.1 → …) |
| [Kanban Guide](https://kanbanguides.org/) | Make work visible through physical warehouse areas |
| [Odoo 17 — Warehouses](https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/warehouses.html) | Warehouse concepts |
| [Odoo 17 — Serial numbers](https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/inventory/product_management/product_tracking/serial_numbers.html) | Serial tracking on receipts / deliveries |
| [Odoo 17 — Returns and refunds](https://www.odoo.com/documentation/17.0/applications/sales/sales/products_prices/returns.html) | Customer returns and credit notes |

This is **not** an ISO certification project. The frameworks above support how we design and write processes. Odoo is the system of record for sellable stock and sales transactions.

### When Odoo is used (current Re-Ware practice)

| Stage | Odoo? |
|-------|-------|
| Physical moves between warehouse areas | **No** |
| After wipe succeeds — upload / receive stock with serial | **Yes** |
| Sales / delivery / invoice | **Yes** |
| Customer return validate | **Yes** |
| Faulty return that cannot stay in sellable stock (no Repair stock in Odoo yet) | **Yes** — validate return, then remove from stock |

---

## 1. Three things that must stay separate

| Concept | Meaning | Example |
|---------|---------|---------|
| **Physical location** | Where is the laptop sitting? | Area: Pending Install |
| **Processing status** | What still needs to happen? | Needs installation |
| **Odoo On Hand** | System quantity in sellable stock | On Hand = 1 |

**Critical rules**

- Wiped ≠ Ready for sale.
- Odoo On Hand ≠ Ready to sell to a customer.
- Do **not** label a pending-installation area as **Available**. That name implies the device can be sold.

---

## 2. Warehouse areas

Areas are **physical** zones (labels, shelves, or bays). They do not all need separate rooms. Combine areas if space is limited, but keep names clear.

Re-Ware does **not** currently mirror every area as a separate stock location in Odoo. Odoo holds sellable / received stock after a successful wipe. **Repair** is a physical area only for now.

### Required areas

| Area | Meaning | Sell from here? | In Odoo today? |
|------|---------|-----------------|----------------|
| **Incoming** | Newly received, not processed | No | No |
| **Wipe** | Waiting for / in data wipe | No | No |
| **Pending Install** | Wiped, waiting OS / drivers / setup | No | No (stock already uploaded after wipe) |
| **QC / Testing** | Installed, waiting test | No | No |
| **Ready for Sale** | Fully processed, OK to sell | **Yes** | Sell from Odoo on-hand stock |
| **Repair** | Failed QC or known fault | No | **No Repair stock location yet** |
| **Returns** | Customer returns waiting processing | No | Via return transfer only |
| **Sold / Dispatch** | Sold, waiting pickup or courier | No | Delivery validated |

### If space is limited

- Incoming + Returns → one Intake bay with separate labelled bins
- Wipe + Pending Install → one bench with two labelled ends
- QC may share the Install bench if only one person works there

### Sales rule

Only sell devices that are physically in **Ready for Sale** and exist in Odoo with the correct serial.

---

## 3. Workflow diagrams

See the HTML / PDF version for box-and-arrow diagrams.

### 3.1 Device processing flow (intake → sale)

1. **Incoming** → **Wipe** (or skip wipe if not required)
2. **Wipe succeeds** → upload stock into Odoo (serial) → move physically to **Pending Install**
3. **Install** → **QC / Testing**
4. Pass → **Ready for Sale** → sell → **Sold / Dispatch**
5. Fail → physical **Repair** (not held as Odoo Repair stock yet)

### 3.2 Customer return flow

1. Customer returns device → place in **Returns**
2. Record serial + reason
3. **Odoo:** create Return from Delivery → **Validate** when device is back
4. Inspect

**If OK to reprocess**

5. Physical path: Wipe → Pending Install → Install → QC → **Ready for Sale**
6. Keep / correct Odoo stock so the serial remains sellable only when Ready rules are met

**If problems (cannot stay in sellable stock)**

5. Return is already validated in Odoo
6. **Odoo:** remove from stock (inventory adjustment / scrap)
7. Move physically to **Repair**
8. Do not sell until repaired and stock is handled correctly again

**If refund is required (after invoice)**

- Issue **Credit Note** in Odoo (in parallel with the stock path above)

### Ready for Sale — minimum checklist

- Wipe done (if required)
- Stock uploaded to Odoo with serial (after successful wipe)
- OS / software installed to Re-Ware standard
- Basic QC passed (power, screen, keyboard, battery, ports as applicable)
- Condition / grade noted
- Photos / listing ready if selling online
- Device placed in the **Ready for Sale** area

---

## 4. Process: Sales (in-store / phone / counter)

**Purpose:** Sell the correct device, at the correct price, with the correct serial, and update stock.

**Trigger:** Customer wants to buy / order is agreed.

**Responsibility:** Sales staff. For high-value sales, a second person should check price and serial where practical.

### 4.1 Process steps

1. Confirm the device is in **Ready for Sale**.
2. Confirm product, price, and serial with the customer.
3. Create and confirm the Sales Order in Odoo.
4. On delivery, assign the correct serial number.
5. Validate delivery when the device is handed over or collected by courier.
6. Complete invoice and payment per Re-Ware finance rules.
7. Move the unit out of Ready for Sale (or via Dispatch if used).

### 4.2 Odoo steps (Sales + Delivery)

1. Open **Sales**.
2. Click **New**.
3. Select **Customer**.
4. Add product line(s).
5. Check unit price (and tax if shown).
6. Click **Confirm**.
7. Open the **Delivery** smart button.
8. Open detailed operations for the product line.
9. Select the correct **Lot/Serial Number** (use an existing serial; do not create a new one on delivery).
10. Set **Done** quantity.
11. Click **Validate**.
12. Create / confirm **Invoice** and register payment as required.

### Common mistakes

- Selling from Wipe, Pending Install, or Repair
- Validating delivery without checking the serial
- Leaving an incorrect price from an old quotation
- Handing over the device without validating delivery (stock becomes wrong)

### Definition of done

- Customer has the device (or courier has collected it)
- Delivery validated with the correct serial
- Payment / invoice completed per rules
- Physical area updated

**Record:** Sales Order + Delivery + Invoice in Odoo

---

## 5. Process: Intake and wipe (when stock enters Odoo)

**Purpose:** Receive devices physically, wipe them, then upload stock to Odoo only after wipe succeeds.

**Trigger:** Goods arrive from supplier, trade-in, or other intake.

### 5.1 Process steps (physical first)

1. Place the device in **Incoming**.
2. Identify and label the serial number.
3. Move to **Wipe** (or skip wipe if not required).
4. Complete wipe / data clear.

### 5.2 When wipe succeeds — upload to Odoo

Only after wipe succeeds (or wipe is not required):

1. Receive / upload the device into Odoo with the correct **Serial Number**.
2. Move the device physically to **Pending Install**.

Do **not** upload stock to Odoo for devices that failed wipe or are not yet wiped.

### 5.3 After upload (physical only — no Odoo area moves)

1. Install OS / software.
2. Move to **QC / Testing**.
3. Pass → move to **Ready for Sale**.
4. Fail → move to physical **Repair** (do not create Repair stock in Odoo until that location exists).

### Definition of done (upload point)

- Wipe complete (if required)
- Serial in Odoo
- Device in **Pending Install** (or next correct physical area)

### Control

No device is sold without an Odoo record and serial created after successful wipe.

---

## 6. Process: Moves between areas (physical only)

**Purpose:** Keep devices in the correct labelled physical area as work progresses.

**Trigger:** A device finishes a stage (for example, wipe complete, install complete, QC complete).

**Odoo:** There is **no Odoo step** for moving between areas. Re-Ware does not update Odoo locations for Incoming / Wipe / Pending Install / QC / Repair moves. Stock is uploaded once after wipe succeeds (see Section 5).

### Steps

1. Complete the physical work for that stage.
2. Move the device to the next labelled area.
3. After wipe succeeds: upload stock to Odoo (Section 5.2), then move to **Pending Install**.
4. For all other stage moves: physical move only — no Odoo action.

After wipe, the next area is **Pending Install**, not “Available”.

---

## 7. Process: Customer returns

**Purpose:** Receive the returned device safely, update Odoo, then decide wipe / restock / repair handling.

**Trigger:** Customer returns a product.

**Note:** Re-Ware does **not** have a Repair stock location in Odoo yet. Faulty returns must not remain as sellable on-hand stock.

### 7.1 Process steps

1. Place the device in **Returns** immediately.
2. Record serial and reason.
3. Process the return in Odoo and **Validate** when the device is physically back (this brings stock back into Odoo).
4. Inspect the device.

**If the device is OK to reprocess / resell later**

5. Move physically to Wipe / Pending Install / QC as needed.
6. Only treat as sellable again when it meets Ready for Sale rules (and stock in Odoo is correct).

**If the device has problems (cannot stay in sellable stock)**

5. Still **Validate** the return in Odoo first (so the delivery / return history is correct).
6. Then **remove it from Odoo stock** (inventory adjustment / scrap — so it is not sellable on hand).
7. Move the device physically to **Repair**.
8. Do not put it in Ready for Sale until repaired, re-wiped if required, and stock is correctly handled again.

9. If a refund is required after invoicing, issue a Credit Note.

### 7.2 Odoo — return before invoice

Reference: [Odoo 17 — Returns and refunds](https://www.odoo.com/documentation/17.0/applications/sales/sales/products_prices/returns.html)

1. Open the **Sales Order**.
2. Open **Delivery**.
3. On the validated delivery, click **Return**.
4. Adjust quantities if it is a partial return.
5. Confirm **Return** (creates the incoming return operation).
6. When the device is back, click **Validate**.

Delivered quantity on the sales order updates. Invoice later only for what the customer keeps.

### 7.3 Odoo — return after invoice

1. Complete the reverse transfer as above (Delivery → Return → Validate when received).
2. Open **Invoices** from the Sales Order.
3. Click **Credit Note**.
4. Enter reason, journal, and date.
5. Choose **Reverse** (or Reverse and Create Invoice).
6. Confirm the credit note.

### Common mistakes

- Putting a return on Ready for Sale without validating the Odoo return
- Leaving a faulty return in Odoo on-hand stock (looks sellable)
- Refunding without validating the return transfer
- Skipping wipe / QC before reselling a return

### Definition of done

- Device in Returns, then moved to the correct next physical area
- Return transfer validated
- Faulty units removed from Odoo stock and placed in physical Repair
- Credit note completed if money must be refunded

---

## 8. Operating standards

| Check | Standard |
|-------|----------|
| Ready for Sale area | Only sellable, QC-passed devices |
| Odoo vs Ready shelf | Devices sold from Ready exist in Odoo with the correct serial |
| Returns | No unlabelled devices left in Returns |
| Faulty returns | Validated in Odoo, then removed from sellable stock |
| Sales | Every handed-over laptop has a validated delivery and serial |

### Simple measures (for review)

- Devices in Incoming or Returns older than 3 days
- Handed-over devices without validated delivery (target: 0)
- Ready for Sale devices missing an Odoo serial (target: 0)
- Faulty returns still showing as on-hand sellable stock (target: 0)

---

## 9. Continuous improvement

```
PLAN  → update the SOP
DO    → operate to the SOP
CHECK → find gaps and failures
ACT   → publish the next version
```

Version history:

| Version | Date | Notes |
|---------|------|--------|
| v1.0 | 2026-08-15 | First published standard: areas, sales, wipe-then-Odoo upload, returns, physical-only area moves |

---

## 10. Planned for later versions

- Match area names to labels already used in the office
- Merge existing Odoo click guides into each process
- Add Repair stock handling in Odoo when ready
- Purchasing
- eBay / website pack and ship
- Stocktake
