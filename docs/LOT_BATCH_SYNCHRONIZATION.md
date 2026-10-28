# Lot, Batch, and Serial Number Synchronization — Reference

**Status: IMPLEMENTED.** Branch `feature/wms-lot-batch-sync`, based on Phase E
(`feature/wms-inventory-import` @ `2690067`), not yet merged into `main`/`19.0`. This is Phase F of
the WMS-first roadmap — see
[API_ROADMAP.md](API_ROADMAP.md#phase-f--lot-and-batch-integration) for where it fits.

## What this is

Native Odoo `stock.lot` records, created and resolved through the same external-ID mapping service
every other phase uses (`res_model = "stock.lot"` was already present in Phase A's allow-list,
anticipating this phase). No new lot/batch model of this module's own — Odoo's own traceability
engine is reused directly, never duplicated.

## Endpoints

### `POST /cool_agristock/api/v1/lots`

```json
{"external_id": "LOT-001", "product_external_id": "AGRI-001", "name": "COCOA-2026-001"}
```

Response `201`:
```json
{"status": "success", "lot_id": 42, "external_id": "LOT-001", "name": "COCOA-2026-001", "product_external_id": "AGRI-001"}
```

### `GET /cool_agristock/api/v1/lots`

Read-only, same pattern as every other `GET` — no external-system binding required, capped at 100,
company-scoped.

### `PATCH /cool_agristock/api/v1/lots/{external_id}`

```json
{"name": "COCOA-2026-001-R2"}
```

## Supported lot fields

**Create:** `product_external_id` and `name` required. **Update allow-list (identical to create,
minus product):** `name`, `ref` (internal reference), `note` (free text). Verified directly against
this installation's `stock.lot` field metadata — `company_id`, `product_id` (immutable after
creation, by design), `location_id` (a *computed* field on real Odoo 19 lots that, if written to
directly, triggers `move_quants()` — a real stock relocation — so it is never exposed to this API
at all), `quant_ids`, and `lot_properties` are all deliberately not exposed.

## Why `location_id` is never exposed — a real finding, not a cautious guess

Read directly from `stock/models/stock_lot.py` before writing any code: `stock.lot.location_id` is
`compute='_compute_single_location', inverse='_set_single_location'`. Writing to it calls
`move_quants()` on the lot's own quants — i.e., setting it isn't just descriptive metadata, it
**physically relocates stock**. Exposing it on this API would have been a silent way for a WMS to
trigger a stock movement through what looks like an ordinary metadata field. It is excluded
entirely, and this is the reason why.

## Lot identity, uniqueness, and duplicate/conflict handling

Identity is `(company, external_system, "stock.lot", external_id)` — the same Phase A mapping
schema as every other model, no separate lot-specific table. **Any** repeat `POST` of an
already-mapped `external_id` is rejected with `409` (matching the products/warehouses/suppliers
precedent exactly) — this is a stricter rule than Phase E's inventory-import idempotency (which
tolerates an identical retry): a lot's identity should never be silently re-confirmed or
re-interpreted once assigned.

Odoo's own `stock.lot._check_unique_lot()` constraint (unique per company + product + name) is
reused as-is, not reimplemented — a second `POST` naming an already-used lot name for the same
product/company, under a *different* `external_id`, surfaces as a clean `409` by catching that
constraint's `ValidationError`, not a raw database error.

## Serial number safety

**A serial number identifies exactly one physical unit — never a batch.** This is enforced
structurally at the one place quantities actually enter the system for a serial-tracked product:
Phase E's inventory import and the receipt/dispatch `/validate` endpoints both reject a
serial-tracked line whose *normalized* quantity (in the product's own unit) is not exactly `1`,
regardless of what the WMS's raw unit/quantity said before normalization. Lot creation itself
(`POST /lots`) does not carry a quantity at all, so there is nothing to aggregate at that step —
the restriction applies where it actually matters.

## Expiration and best-before metadata — not available, and why

**Checked directly, not assumed:** this installation does not have the `product_expiry` module
installed (confirmed via `ir_module_module`), which is what adds `expiration_date`/`use_date`/
`removal_date`/`alert_date` to `stock.lot`/`product.template` in Odoo. The base `stock` module's own
`stock.lot` has no expiration-related field at all. Per "do not invent Odoo fields or dependencies,"
this phase does **not** install `product_expiry` and ships **no** expiration-related fields or
behavior. An `expiration_date` sent in a request body is rejected the same way any other
unsupported field is — `400`, via the ordinary allow-list check, not a special case.

**A note on `lot_properties`:** `stock.lot` does have a generic `lot_properties` (Properties-type)
field in the base `stock` module itself, which *could* in principle hold an administrator-defined
"expiration"-like property without installing `product_expiry`. This phase deliberately does not
wire anything into it — doing so would mean this module inventing an informal convention on top of
a generic field, which is exactly the kind of invented-field risk the task asked to avoid. If a
real deployment needs genuine expiration tracking, installing `product_expiry` and extending this
API with its real fields is a better-scoped future phase.

## Lot-level inventory import integration (extends Phase E)

`POST /cool_agristock/api/v1/inventory-adjustments` lines gained an optional `lot_external_id`:

```json
{
  "external_reference": "INITIAL-LOT-STOCK-001",
  "warehouse_external_id": "WH-001",
  "lines": [{"product_external_id": "AGRI-001", "lot_external_id": "LOT-001", "quantity": 2500, "unit": "kg"}]
}
```

- **Tracked product, no `lot_external_id`:** still rejected with `422`, byte-for-byte the same
  message as Phase E shipped — zero behavior change for a caller that has never heard of lots.
- **Tracked product, `lot_external_id` given:** the lot is resolved (`404` if unknown), checked
  against the resolved product (`422` if it belongs to a different product), and checked for
  company ownership. Reconciliation for that line is scoped to the exact
  `(product_id, location_id, lot_id)` triple — **verified directly**: two lots of the same product
  in the same location, holding different quantities, each reconcile against only their own lot's
  stock, never the other's or their sum.
- **Serial-tracked:** the line's normalized quantity must equal exactly `1`, enforced the same way
  as receipts/dispatches below.
- **Untracked product with a `lot_external_id`:** rejected with `422` — a lot reference is never
  silently ignored.
- Still only ever `warehouse.lot_stock_id`, exactly as Phase E — this phase does not introduce any
  location-mapping extension, per the task's own explicit instruction.
- Stale-data detection, human review, and idempotency are entirely unchanged and apply identically
  to lot-tracked lines — **verified directly** with a lot-tracked import that goes stale after its
  lot's stock changes before review.
- **No invented UOM-category assumptions:** this phase reuses Phase D/E's verified
  `relative_uom_id`/`parent_path`-based compatibility check as-is — see
  [INITIAL_INVENTORY_IMPORT.md's UOM validation](INITIAL_INVENTORY_IMPORT.md#uom-validation-phase-8)
  for the original finding; nothing about lots changes that mechanism.

## Receipt and dispatch integration

Both `/validate` endpoints gained an optional `lot_external_id` per line, alongside the existing
`product_id`/`quantity`:

```json
{"product_id": 42, "quantity": 300, "lot_external_id": "LOT-001"}
```

**Resolving a lot requires a bound API key** (`resolve_authorized_external_system()`, the same
check every other lot/mapping-touching endpoint uses) — but **only when at least one line actually
uses `lot_external_id`.** A legacy caller that never sends it never triggers that resolution at
all, even if its own key happens to be unbound — confirmed directly with a test using the
pre-Phase-F unbound-style key fixture against an untracked product.

### Receipts (incoming)

After the existing `move.quantity = ...` assignment (which already creates exactly one move line
per move, per Phase 8's one-move-per-product invariant), the resolved lot is assigned directly to
`move.move_line_ids.lot_id` — Odoo's own `_check_lot_product` constraint is the real guarantee that
this can never end up inconsistent with the move's product, not any check this module adds.

### Dispatches (outgoing) — the one place this phase had to go past "just set a field"

A dispatch has to *reserve* stock before validating, and Odoo's standard `action_assign()` picks
whichever lot its removal strategy prefers — not necessarily the one the WMS named. Investigated
directly in `stock/models/stock_move.py` before writing any code: `stock.move._update_reserved_quantity(need, location_id, lot_id=..., strict=True)` is Odoo's own public primitive for reserving
an exact quantity from an exact lot, and it reports back how much it actually found. This module
calls it explicitly, for the named lot only, **before** the normal `_action_assign()` pass runs;
`_action_assign()` then recognizes that move as already fully reserved (confirmed directly by
reading its own reserved-quantity check) and leaves it alone, reserving every other, non-lot move
exactly as it always has. If the named lot doesn't have enough stock, `_update_reserved_quantity`
reports a shortfall and the whole validation is rejected with `409` — never falling back to
reserving from a different lot.

**Nothing here is a parallel/duplicate reservation path** — it's the same native method Odoo's own
`_action_assign()` calls internally for lot-specific reservation, called directly instead of
indirectly, so this module can pin the lot the WMS actually asked for.

## Security

Identical pattern to every other phase: Bearer token → Cool Agristock API User group →
`resolve_authorized_external_system()`, server-derived. **A real, favorable finding, not assumed:**
`stock.group_stock_user` (already implied by the Cool Agristock API User group since Phase B) already has
full native `create`/`read`/`write`/`unlink` access to `stock.lot` in this Odoo 19 installation —
checked directly against `ir.model.access`, the same way every prior phase's ACL gaps were found.
Unlike suppliers/warehouses/inventory-import, **no gated `sudo()` pattern and no new
`ir.model.access.csv` row were needed at all** for the lot endpoints themselves — `controllers/lots.py`
calls `stock.lot.create()`/`.write()` directly under the authenticated API user's own permissions.

## Error responses

| Code | Condition |
|---|---|
| 400 | Invalid JSON, missing/invalid field, unsupported field (including any expiration-related field), empty name |
| 401 | Missing/invalid/revoked/expired API key |
| 403 | Not a Cool Agristock API User; key not bound to an active external system; inactive external system |
| 404 | Unknown `external_id` (lot or product); unknown `lot_external_id` on import/receipt/dispatch |
| 409 | Duplicate `external_id`; conflicting lot name for the same product/company; lot name change after stock history; insufficient stock in the named lot (dispatch) |
| 422 | Product not lot/serial-tracked but a lot was given (or vice versa); lot belongs to a different product; serial quantity != 1 |
| 500 | Unexpected server-side error (transaction rolled back) |

## Known limitations

- **No expiration/best-before support** — `product_expiry` isn't installed; see above.
- **`lot_properties` not exposed** — reserved for a future phase if a real need for arbitrary
  admin-defined lot metadata emerges.
- **No bulk lot creation** — one lot per `POST`, matching every other create endpoint in this
  module.
- **Lot-level inventory import is still warehouse-level-location only** — no shelf/bin granularity,
  carried over unchanged from Phase E.

## Verification performed

- **All 270 tests in the module pass** against a fresh database (236 pre-existing + 34 new across
  `test_lot_sync.py` and the now-properly-registered `test_inventory_import.py` — see the Phase F
  final report for the full accounting of what that count actually includes).
- **Real HTTP + direct PostgreSQL verification** on a disposable live-server database: a tracked
  product's lot was created via the API (`lot_id=1`, confirmed as a real `stock_lot` row with the
  correct `product_id=1`/`company_id=1`), a repeat `POST` confirmed `409` with no duplicate row, a
  cross-system `PATCH` attempt confirmed `404`, a lot-scoped inventory import was staged
  (`reported_quantity=2500`, `current_odoo_quantity=0`) and confirmed via direct SQL to leave
  `stock_quant` with zero rows, a receipt against that lot was validated and confirmed via SQL to
  set `stock_move_line.lot_id=1` and bring on-hand quantity to `300`, and a dispatch of `120` units
  against that same lot was validated and confirmed to decrease the warehouse location's quantity
  to exactly `180` (not an unrelated amount), with a repeated validation attempt correctly rejected
  (`409`, no duplicate stock move) rather than silently re-applied.
- **A real, load-bearing bug was found and fixed by this verification, not just confirmed-clean:**
  `stock.picking.action_confirm()` can itself auto-reserve a move against whatever lot is available
  (confirmed directly) *before* this module's own explicit per-lot reservation runs.
  `stock.move._update_reserved_quantity()`'s `need` argument is additive on top of whatever is
  already reserved, not an absolute target, so calling it without first clearing any existing
  reservation silently double-reserved (and the test suite initially caught exactly this: a
  dispatch of 400 units against 1000 in stock left 200 remaining instead of 600). The fix —
  `move.move_line_ids.unlink()` immediately before the explicit lot-pinned reservation — makes the
  final reservation state deterministic regardless of what Odoo's own confirm-time reservation
  already did, and is covered by `test_dispatch_with_valid_lot`.
