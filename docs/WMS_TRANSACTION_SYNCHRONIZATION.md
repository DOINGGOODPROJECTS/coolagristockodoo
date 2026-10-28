# WMS-First Receipt and Dispatch Synchronization — Reference

**Status: IMPLEMENTED.** Branch `feature/wms-transaction-sync`, based on Phase F
(`feature/wms-lot-batch-sync` @ `cad5357`), not yet merged into `main`/`19.0`. This is Phase G of
the WMS-first roadmap — see [API_ROADMAP.md](API_ROADMAP.md#phase-g--transaction-integration-enhancements)
for where this fits.

## What this is

`POST /cool_agristock/api/v1/receipts` and `POST /cool_agristock/api/v1/dispatches` now accept **two
request shapes in the same route**, distinguished by which top-level key is present:

- **`products`** — the original, Phase-A-era schema: raw Odoo integer IDs, no external-system
  resolution. **Entirely unchanged, byte-for-byte**, including every error message.
- **`lines`** — the new, Phase G schema: every reference (warehouse, supplier, product, unit, lot)
  resolved from the caller's own external-ID namespace, exactly like every other phase's write
  endpoints.

Sending both, or neither, is a `400` caller error. The `/validate` endpoints are **unchanged** —
the same two routes handle both a legacy-created and a Phase-G-created picking identically.

## Endpoints

### `POST /cool_agristock/api/v1/receipts` (WMS-first schema)

```json
{
  "external_reference": "WMS-REC-001",
  "warehouse_external_id": "WH-001",
  "supplier_external_id": "SUP-001",
  "lines": [
    {"product_external_id": "PROD-001", "quantity": 5000, "unit": "kg", "lot_external_id": "LOT-001"}
  ]
}
```

Response `201`:
```json
{
  "status": "success",
  "receipt_id": 12,
  "receipt_reference": "WH/IN/00012",
  "external_reference": "WMS-REC-001",
  "state": "draft",
  "lines": [
    {"product_external_id": "PROD-001", "product_id": 101, "quantity": 5000.0, "lot_external_id": "LOT-001"}
  ]
}
```

**`lines[].product_id` in the response is deliberate, not incidental:** it is the only way a
WMS-first caller can later call the *unchanged* `/validate` endpoint, which still takes a raw
`product_id` per the original Phase A/B schema (see
[Why validation wasn't also rewritten](#why-validation-wasnt-also-rewritten) below).

`POST /cool_agristock/api/v1/dispatches` is the same shape, minus `supplier_external_id` (dispatches
have no required customer reference in this phase — matching the task's own example payload,
which doesn't include one either; `partner_id` is left unset on the picking, which Odoo allows).

### `GET /cool_agristock/api/v1/receipts/{external_reference}` / `GET /cool_agristock/api/v1/dispatches/{external_reference}`

Requires a **bound** API key (unlike the catalog `GET` endpoints) — a bare `external_reference` is
only meaningful within one external system's own namespace, so resolving it requires knowing which
namespace to look in.

```json
{
  "status": "success",
  "external_reference": "WMS-REC-001",
  "receipt_id": 12,
  "transaction_type": "receipt",
  "state": "draft",
  "warehouse_id": 1,
  "created_at": "2026-10-22T19:41:19.551000",
  "validated_at": null
}
```

`404` if nothing was created under that exact `(company, external_system, transaction_type,
external_reference)` — including for a legacy, numeric-ID-created picking, which never gets an
identity row (see [Transaction identity](#transaction-identity) below).

## Transaction identity

New model `cool_agristock.wms.transaction`: `company_id`, `external_system_id`, `transaction_type`
(`receipt`/`dispatch`), `external_reference`, `request_hash`, `picking_id`. Unique constraint on
`(company_id, external_system_id, transaction_type, external_reference)` — a real database
constraint, not just an application-level check.

**Why a new model, when receipts/dispatches already had duplicate protection:** the existing
mechanism (a PostgreSQL advisory lock + a `picking.origin`/`picking_type_id` match, confirmed by
reading `receipts.py`/`dispatches.py` directly) serializes concurrent requests correctly, but has
no real database-level uniqueness and no `external_system_id` dimension at all — it predates this
module's external-system-binding concept entirely. Rather than retrofit that mechanism (and risk
the legacy path's own, already-tested behavior), this phase adds `cool_agristock.wms.transaction`
specifically for the new WMS-first path, leaving the legacy path's original mechanism **completely
untouched** for `products`-schema requests. This also directly serves the new `GET` status
endpoints, which need a reliable `(company, external_system, type, reference) → picking` lookup
that the old mechanism was never designed to provide.

## Idempotency

Identical to Phase E's inventory import pattern: a SHA-256 hash of the normalized request body
(`external_reference` + `warehouse_external_id` + `supplier_external_id` + sorted lines) is stored
alongside the identity. A retried `POST` with **identical** content returns the existing
transaction with `200`. A retried `POST` reusing the same `external_reference` with **different**
content returns `409`. Concurrent creation is handled the same way as every other phase: an
application-level pre-check for the common case, with `env.cr.savepoint()` plus the database
constraint as the actual concurrency safety net (verified directly with a forced-race test at the
model level).

## UOM and lot/serial handling

Reuses Phase D/E's `relative_uom_id`/`parent_path`-based compatibility logic exactly as built — no
reintroduced `category_id` assumptions. A serial-tracked line's normalized quantity must be exactly
`1`, enforced the same way as Phase F's `/validate` endpoints.

**Lot resolution at creation time is validated, not bound.** `lines[].lot_external_id` is resolved
and checked (must exist, must belong to the stated product, must belong to the caller's company) —
an invalid reference is rejected with `404`/`422` at creation, satisfying "do not silently create
missing master data." But the actual assignment of that lot to a `stock.move.line` still only
happens at `/validate` time, via the exact mechanism Phase F already built and tested. A WMS-first
caller must resend `lot_external_id` in its `/validate` call — it is not silently remembered from
creation.

### Why validation wasn't also rewritten

The task's own instruction for this phase was explicit: **"Preserve existing validation
endpoints."** Phase F already extended `/validate` with `lot_external_id` support; adding a second,
parallel `product_external_id`/`lot_external_id`-only validation schema would mean two independent
code paths that could assign stock differently, for no functional gain — the creation response
already hands back the resolved `product_id` for exactly this reason. A future phase could revisit
this if real integrations find round-tripping the numeric id awkward.

## Security

Identical pattern to every other phase: Bearer token → Cool Agristock API User group →
`resolve_authorized_external_system()`, required only for the WMS-first schema and the `GET` status
endpoints — the legacy `products` schema requires no binding at all, exactly as before this phase.
`cool_agristock.wms.transaction` has no `ir.model.access.csv` grant for the API User group at all (same
as `cool_agristock.external.id.mapping`) — every read/write goes through `sudo()` after the controller's
own explicit auth check, never a standing capability.

**A real compatibility bug was found and fixed by this phase's own testing, not just avoided by
design:** `/validate`'s existing guard ("this picking must actually be Cool Agristock-managed") checked
only for the legacy `COOL_AGRISTOCK-RCPT-`/`COOL_AGRISTOCK-DISP-` prefix convention — which a Phase G
`external_reference` like `WMS-REC-001` would never match, meaning a WMS-first receipt could be
created successfully and then **never validated at all**. Fixed by recognizing a picking as
Cool Agristock-managed if *either* the legacy prefix matches *or* a real `cool_agristock.wms.transaction` row
references it — the only way to have gotten one is through this module's own creation path.

## Known limitations

- **Validation payloads are still numeric-ID-based** — see
  [Why validation wasn't also rewritten](#why-validation-wasnt-also-rewritten).
- **Dispatches have no customer/partner reference in the WMS-first schema** — matching the task's
  own example payload; `partner_id` is left unset on the picking.
- **Partial receipts/dispatches remain entirely unsupported** (inherited from Phase 8 — not a new
  limitation), so there is no backorder-handling code path to document beyond "it does not exist":
  a partial quantity at `/validate` is rejected outright, confirmed not to create a
  `stock.picking` backorder record.
- **No bulk/batch creation** — one receipt or dispatch per `POST`, matching every other endpoint.

## Error responses

Identical structure to Phase E/F's endpoints: `400` (invalid/unsupported field, invalid quantity,
both-or-neither schema), `401`/`403` (API key / binding / company problems), `404` (unknown
warehouse/supplier/product/lot, or unknown transaction on `GET`), `409` (conflicting or duplicate
transaction, repeated validation, partial dispatch), `422` (incompatible unit, missing/wrong lot,
non-1 serial quantity), `500` (unexpected error, transaction rolled back).

## Verification performed

- **All tests in the module pass** against a fresh database — see the Phase G final report for the
  exact total.
- **Real HTTP + direct PostgreSQL verification**, on a disposable database: a WMS-first receipt was
  submitted, repeated (idempotent `200`), inspected via `GET`, validated through the unchanged
  `/validate` endpoint, confirmed via SQL to increase on-hand stock; a dispatch followed the same
  sequence and was confirmed to decrease stock; a repeated dispatch validation was confirmed
  rejected with no second `stock.move` created; a cross-system `GET` attempt was confirmed rejected.
