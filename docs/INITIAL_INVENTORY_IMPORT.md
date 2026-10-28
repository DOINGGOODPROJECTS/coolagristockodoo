# Initial Inventory Import — Reference

**Status: IMPLEMENTED.** Branch `feature/wms-inventory-import`, based on Phase D
(`feature/wms-supplier-uom-sync`), not yet merged into `main`/`19.0`. This is Phase E of the
WMS-first roadmap — see
[API_ROADMAP.md](API_ROADMAP.md#phase-e--initial-inventory-import-and-reconciliation) for where
this fits.

**Update (Phase F):** `lines[].lot_external_id` (optional) was added on top of everything below —
see [LOT_BATCH_SYNCHRONIZATION.md's Lot-level inventory import integration](LOT_BATCH_SYNCHRONIZATION.md#lot-level-inventory-import-integration-extends-phase-e).
Everything in this document remains accurate for lines that don't use it.

## What this is, and what it deliberately is not

A WMS can submit its own count of what it believes is on hand for a product at a warehouse.
Cool Agristock stages that observation, reconciles it against Odoo's actual on-hand quantity,
and surfaces the difference to a human. **It never writes to `stock.quant.quantity`, never calls
`action_apply_inventory()`, and never creates a `stock.move`.** Applying an approved import to real
stock remains a separate, manual action in Odoo's own native Inventory Adjustment screen — see
[Native adjustment handoff](#native-adjustment-handoff) below for exactly why, backed by reading
Odoo 19's actual source rather than assuming older-version behavior carries over.

## The models

### `cool_agristock.inventory.import`

| Field | Type | Notes |
|---|---|---|
| `company_id` | Many2one `res.company`, required | |
| `external_system_id` | Many2one `cool_agristock.external.system`, required | |
| `external_reference` | Char, required | The WMS's own batch identifier, e.g. `INITIAL-2026-001`. |
| `warehouse_id` | Many2one `stock.warehouse`, required | Resolved at submission time. |
| `location_id` | Many2one `stock.location`, required | Always `warehouse_id.lot_stock_id` — see [Location mapping](#location-mapping). |
| `request_hash` | Char, required | SHA-256 of the normalized request body — see [Idempotency](#idempotency). |
| `state` | Selection | `pending_review` / `stale` / `approved` / `rejected`. |
| `submitted_at`, `submitted_by` | Datetime, Many2one `res.users` | |
| `reviewed_by`, `reviewed_at` | Many2one `res.users`, Datetime | Set by `action_approve()`/`action_reject()`. |
| `notes` | Text | |
| `line_ids` | One2many | See below. |

**Unique constraint:** `(company_id, external_system_id, external_reference)` — a real database
constraint, the import's identity (Phase 13).

### `cool_agristock.inventory.import.line`

| Field | Type | Notes |
|---|---|---|
| `product_id`, `location_id` | Many2one | |
| `lot_id` | Many2one `stock.lot`, optional | Set only for a lot/serial-tracked product line (Phase F). Reconciliation is then scoped to the exact `(product, location, lot)` triple. |
| `uom_id` | Many2one `uom.uom` | The **product's own** unit — both quantity fields below are expressed in it, never in the WMS's raw unit. |
| `external_unit_code` | Char | The WMS's raw unit code, preserved verbatim for audit. |
| `original_reported_quantity` | Float | The quantity exactly as submitted, in `external_unit_code`, before normalization — preserved for audit (Phase 8) even though it is `reported_quantity` below that reconciliation actually uses. |
| `reported_quantity` | Float | `original_reported_quantity` converted into `uom_id`. |
| `current_odoo_quantity` | Float | Live on-hand quantity (`stock.quant.quantity`, summed, read-only) as of the last (re)computation. |
| `proposed_difference` | Float | `reported_quantity - current_odoo_quantity`, as of the last (re)computation. Never applied automatically. |
| `validation_status` | Selection | `ok` / `stale`. |
| `error_message` | Char | Reserved for a future partial-validation mode — always empty today, since an import is validated atomically, all-or-nothing, before any line is ever stored (see [Validation is all-or-nothing](#validation-is-all-or-nothing)). |

## Endpoint

### `POST /cool_agristock/api/v1/inventory-adjustments`

```json
{
  "external_reference": "INITIAL-2026-001",
  "warehouse_external_id": "WH-001",
  "lines": [
    {"product_external_id": "AGRI-001", "quantity": 5000, "unit": "kg"},
    {"product_external_id": "AGRI-002", "quantity": 3000, "unit": "kg"}
  ]
}
```

Quantities are treated as **absolute stock observations** ("this is what's here right now"), never
as movement deltas.

Response `201`:
```json
{
  "status": "success",
  "import_id": 7,
  "external_reference": "INITIAL-2026-001",
  "state": "pending_review",
  "lines": [
    {"product_external_id": "AGRI-001", "reported_quantity": 5000.0, "current_odoo_quantity": 2000.0, "proposed_difference": 3000.0}
  ]
}
```

There is deliberately no `GET`/`PATCH` on this endpoint — human review happens in Odoo's own
backend (see [Human review](#human-review) below), not through the WMS-facing API, matching the
precedent set by UOM Mappings in Phase D (an admin-only Odoo interface, not a REST surface).

### Validation is all-or-nothing

The entire request is resolved and validated — warehouse, every product, every unit, every
conversion — **before any `cool_agristock.inventory.import` row is created.** A single invalid line
rejects the whole batch with no partial import left behind. This is why `error_message` on the
line model is always empty: there is currently no code path that stores a line in an error state.

## Resolution and rejection rules (Phase 6)

Reuses `cool_agristock.external.id.mapping.resolve_mapping()`, exactly as products/warehouses/suppliers
do. Because that service is already scoped to `(company, external_system)`, cross-company and
cross-system isolation fall out for free, with no special-case code: a product or warehouse mapped
under a different company or a different external system (even within the same company) simply
isn't found, and the request is rejected with `404` — **confirmed directly** with a second external
system registered against the *same* company as the first.

| Condition | Response |
|---|---|
| Unknown `warehouse_external_id` | `404` |
| Unknown `product_external_id` | `404` |
| Product requires lot/serial tracking | `422` — see [Lot and serial safety](#lot-and-serial-safety) |
| Inactive external system | `403` (identical to every other endpoint — enforced by `resolve_authorized_external_system()`, not new code) |
| Unknown/incompatible unit | `400` / `422` — see [UOM validation](#uom-validation) |
| Negative `quantity` | `400` |
| Unsupported top-level or line field | `400` |

Products and warehouses are never created by this endpoint — an unresolved reference is always a
hard rejection, never an implicit creation.

## Location mapping (Phase 7)

**Only `warehouse_id.lot_stock_id` is ever used or compared against — never a child location, and
never an arbitrary split across several.** A warehouse's `lot_stock_id` is Odoo's own single,
unambiguous "the" internal stock location for that warehouse (confirmed directly by reading
`stock.warehouse`'s own model code, not assumed); this module does not attempt to resolve any more
specific shelf/bin location, matching the request schema itself, which only ever names a warehouse,
never a location. **Verified directly:** a test creates a second internal location under the same
warehouse with a large quantity of stock in it, and confirms the import's `current_odoo_quantity`
is computed from `lot_stock_id` alone (`0`, not including the other location's stock) — proving no
arbitrary distribution or summation across locations happens. If a future WMS genuinely needs
shelf-level granularity, that is explicitly out of scope for this phase — see
[Known limitations](#known-limitations).

## UOM validation (Phase 8)

Reuses Phase D's `cool_agristock.uom.mapping.resolve_unit()` with the same hardcoded fallback as product
synchronization — identical precedence rule, same two-step resolution already documented in
[UOM_MAPPING.md](UOM_MAPPING.md#integration-with-product-synchronization).

**Compatibility checking required discovering, not assuming, Odoo 19's actual UOM design.** Odoo
19 has no `uom.category` model and no `category_id` field any more (verified directly by reading
`uom/models/uom_uom.py`) — older-version knowledge of "same category_id" does not apply. UOMs
instead form a self-referencing tree via `relative_uom_id`/`parent_path`; two units are convertible
iff they share the same root ancestor (confirmed directly against real data: `kg` and `g` both root
at `g`'s own id; `L` roots at a completely different id, `ml`). This module computes each unit's
root from `parent_path` and rejects the request with `422` if the resolved unit's root differs from
the product's own unit's root — **this check is load-bearing, not defensive boilerplate**: Odoo's
own `uom.uom._compute_quantity()` does not itself refuse a cross-category conversion (verified
directly in the same file) — it will happily compute a number using mismatched factors if asked to.
Without this explicit check, "reject incompatible conversions" would not actually hold.

Normalization uses `_compute_quantity(quantity, product_uom, round=True)` — Odoo's own conversion
arithmetic, never a conversion factor invented by this module.

## Reconciliation (Phase 9)

For each line: `current_odoo_quantity` is read, read-only, as `sum(stock.quant.quantity)` for the
exact `(product_id, location_id)` pair — never `inventory_quantity`, never anything that could
trigger a write-side effect (see [Native adjustment handoff](#native-adjustment-handoff) for why
that distinction matters). `proposed_difference = reported_quantity - current_odoo_quantity` is
computed and stored, never applied.

## Human review (Phase 10)

A new **Inventory Imports** menu (Inventory → Operations, visible to `stock.group_stock_user`)
lists every staged import. The form view shows every line's reported/current/difference values
side by side, with stale lines highlighted.

- **Approve** and **Reject** are restricted to Odoo's own native **Inventory Manager** group
  (`stock.group_stock_manager`) — reused deliberately rather than inventing a parallel
  Cool Agristock-specific authorization concept for a decision that is already an inventory-management
  action in Odoo's own terms.
- **Recalculate** (read-level, any `stock.group_stock_user`) refreshes every line against current
  stock without changing the approve/reject decision.
- Approving **only records that a reviewer has decided to act on this import** — it is explicitly
  documented, in the form view itself, that approval does not change Odoo's actual stock.

## Stale data detection (Phase 12)

`action_approve()` always re-reads every line's live on-hand quantity **before** approving.
If anything changed since the import's numbers were last computed (outside the product's own UOM
rounding), the import is flipped to `stale` instead of `approved` — its `current_odoo_quantity` and
`proposed_difference` are refreshed to the new live values, but the state change to `approved` does
not happen. The reviewer must look at the now-current numbers and click **Approve** again
deliberately — a second, informed decision, not an automatic retry. **Verified directly:** an
import is submitted against `0` on-hand stock, the stock is then changed to `2500` before review,
and the first `action_approve()` call is confirmed to move the import to `stale` (not `approved`)
with the line's numbers refreshed to `2500`; a second call then succeeds.

## Idempotency (Phase 13)

Identity is `(company_id, external_system_id, external_reference)`, enforced by a real database
unique constraint. A retried `POST` with **identical** content (compared via a SHA-256 hash of the
normalized request body) returns the existing import with `200`, not a new row and not an error. A
retried `POST` reusing the same `external_reference` with **different** content returns `409`.
Concurrent submissions are handled the same way every other phase's creation race is: an
application-level pre-check for the common case, with `env.cr.savepoint()` plus the database
constraint as the actual concurrency safety net — **verified directly** with a forced-race test at
the model level (mirrors
[test_external_id_mapping.py's `test_concurrent_mapping_creation_enforced_by_database`](../cool_agristock/tests/test_external_id_mapping.py)).

## Lot and serial safety (Phase 14)

Any line whose product has `tracking != 'none'` rejects the **entire** import with `422` — lot-level
inventory import is explicitly Phase F's work, not this phase's. This deliberately does not attempt
to silently aggregate lot-level stock into one number, and does not discard traceability
information, since no lot-tracked line is ever persisted here at all.

## Native adjustment handoff (Phase 11) — deferred, by design, not by oversight

**Investigated directly against this Odoo 19 installation's actual `stock.quant` source before
making this decision** (`odoo/addons/stock/models/stock_quant.py`): writing `inventory_quantity` on
a quant, under the `inventory_mode` context that Odoo's own Physical Inventory screen uses, does
**not** stage a value for later separate application — its inverse method
(`_set_inventory_quantity`) calls `action_apply_inventory()` **synchronously, in the same write**,
the moment the context says inventory mode is active. There is no native "count entered, not yet
applied" persisted state outside of that same mechanism to safely hook into. Programmatically
pre-populating `inventory_quantity` from this module would therefore either do nothing (outside
inventory-mode context) or apply the count immediately (inside it) — neither is "human-controlled
execution, no automatic stock changes," which this phase requires.

**Per the task's own explicit permission** ("if native handoff cannot be implemented safely within
this phase: keep the import in staging models, document the limitation, do not substitute unsafe
direct SQL writes") — this phase keeps every import in `cool_agristock.inventory.import`/`.line` only.

**Instructions for the inventory manager, to actually apply an approved import:** open
**Inventory → Operations → Physical Inventory**, filter to the product and location shown on the
approved import, enter the `reported_quantity` value shown there as the counted quantity, and click
**Apply** — Odoo's own screen, Odoo's own `is_outdated` staleness guard (the same native mechanism
this module's own stale-detection was modeled on), Odoo's own `stock.move` creation. This module
never substitutes a shortcut for that screen.

## Security

Identical authentication/authorization pattern to every other write endpoint: Bearer token →
Cool Agristock API User group → `resolve_authorized_external_system()`, server-derived, never trusting a
client-supplied `external_system_id`. `res_model`/`sudo()` usage for `cool_agristock.inventory.import`
creation mirrors Phase C/D's gated pattern (the controller performs the full auth + resolution
chain itself, then a single already-authorized `sudo()` create) rather than a standing
`ir.model.access.csv` grant to the API User group for a model whose approval workflow is an
internal Odoo decision, not something a WMS should ever directly manipulate.

## Error responses

| Code | Condition |
|---|---|
| 400 | Invalid JSON, missing/invalid top-level or line field, unsupported field, negative quantity, unsupported unit |
| 401 | Missing/invalid/revoked/expired API key |
| 403 | Not a Cool Agristock API User; key not bound to an active external system; inactive external system |
| 404 | Unknown `warehouse_external_id`; unknown `product_external_id` |
| 409 | `external_reference` reused with different content |
| 422 | Lot/serial-tracked product; incompatible unit conversion; warehouse has no resolvable stock location |
| 500 | Unexpected server-side error (transaction rolled back) |

## Known limitations

- **Shelf/bin-level granularity isn't modeled** — only `warehouse_id.lot_stock_id` is supported;
  a WMS that tracks stock at a finer location granularity than "the warehouse's main stock
  location" cannot be reconciled more precisely in this phase.
- **Native adjustment handoff is manual, by design** — see above; a future phase could revisit this
  if a genuinely safe automated path is found (none was, after directly reading the relevant Odoo
  19 source).
- **`error_message` is unused today** — reserved for a future partial-validation mode; this phase's
  validation is strictly all-or-nothing per batch.
- **No bulk/CSV review tooling** — each import is reviewed individually in the form view.

## Verification performed

- **All tests in the module pass** against a fresh database, clean install and clean upgrade from
  the prior Phase D state — see the Phase E final report for the exact count.
- **Real HTTP + direct PostgreSQL verification**, on a disposable database: a product and warehouse
  were created and mapped, an initial stock balance was established through an authorized Odoo
  workflow (not this module), an inventory import was submitted and confirmed staged with the
  correct computed difference, the underlying `stock.quant.quantity` was confirmed unchanged both
  immediately after submission and after approval, the live stock was then changed and the import
  was confirmed to move to `stale` with refreshed numbers on the next approval attempt, and a second,
  informed approval was confirmed to succeed.
