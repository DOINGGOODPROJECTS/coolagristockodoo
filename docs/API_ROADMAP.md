# API Roadmap

**Status: PROPOSED. NOT YET IMPLEMENTED.** This document specifies request/response schemas for
endpoints that do not exist yet, and a phased plan for building them. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why, and
[WMS_FIRST_INTEGRATION_PLAN.md](WMS_FIRST_INTEGRATION_PLAN.md) for the detailed functional design
each schema below implements.

All proposed endpoints keep the existing prefix, `/cool_agristock/api/v1/` — **no new version segment is
introduced**; see [API compatibility & versioning](#api-compatibility--versioning) for why.

## Proposed endpoint schemas

### `POST /cool_agristock/api/v1/products`

Request:
```json
{
  "external_system": "primary_wms",
  "external_id": "WMS-PRODUCT-001",
  "name": "Cassava 50kg Bag",
  "default_code": "CASS-50",
  "barcode": "6161100000099",
  "uom_code": "kg"
}
```
Response `201`:
```json
{
  "status": "success",
  "product_id": 101,
  "external_id": "WMS-PRODUCT-001",
  "name": "Cassava 50kg Bag"
}
```
Response `409` (external_id already mapped):
```json
{"status": "error", "message": "external_id already mapped", "product_id": 101}
```

### `PATCH /cool_agristock/api/v1/products/{external_id}`

Request (partial — only fields to change):
```json
{"name": "Cassava 50kg Bag (updated)", "barcode": "6161100000100"}
```
Response `200`:
```json
{"status": "success", "product_id": 101, "external_id": "WMS-PRODUCT-001"}
```
Response `404` (no such external_id mapped for this company/system):
```json
{"status": "error", "message": "No product mapped for this external_id"}
```

### `POST /cool_agristock/api/v1/warehouses`

Request:
```json
{"external_system": "primary_wms", "external_id": "WMS-WH-ANYAMA", "name": "Anyama Depot", "code": "ANY"}
```
Response `201`:
```json
{"status": "success", "warehouse_id": 3, "external_id": "WMS-WH-ANYAMA", "name": "Anyama Depot"}
```

### `PATCH /cool_agristock/api/v1/warehouses/{external_id}`

Same shape as the product `PATCH` — partial body, allow-listed fields only (`name`, `code`).

### `POST /cool_agristock/api/v1/suppliers`

Request:
```json
{
  "external_system": "primary_wms",
  "external_id": "WMS-SUPPLIER-014",
  "name": "Cooperative Agricole d'Anyama",
  "email": "contact@example.ci",
  "phone": "+225 07 00 00 0000",
  "country_code": "CI"
}
```
Response `201`:
```json
{"status": "success", "supplier_id": 37, "external_id": "WMS-SUPPLIER-014", "name": "Cooperative Agricole d'Anyama"}
```

### `PATCH /cool_agristock/api/v1/suppliers/{external_id}`

Same partial-update shape as products/warehouses, allow-listed fields only.

### `POST /cool_agristock/api/v1/lots`

**Status: IMPLEMENTED** as sketched below, with two corrections to match what actually shipped —
see [LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md) for the full as-built reference.
First, there is no `external_system` field in the request body at all: like every other write
endpoint in this module, the external system is derived server-side from the authenticated API
key's own binding (`resolve_authorized_external_system()`), never trusted from the client — the
original sketch's `external_system` field would have let a caller claim a system it wasn't actually
authorized for. Second, `GET` takes no query parameters in this phase (no `product_external_id`
filter) — it lists everything visible to the caller's company, capped at 100, matching every other
`GET` endpoint's existing pattern exactly.

Request:
```json
{
  "external_id": "LOT-001",
  "product_external_id": "AGRI-001",
  "name": "COCOA-2026-001"
}
```
Response `201`:
```json
{"status": "success", "lot_id": 42, "external_id": "LOT-001", "name": "COCOA-2026-001", "product_external_id": "AGRI-001"}
```
Response `404` (product external_id not found):
```json
{"status": "error", "message": "Product not found"}
```

### `GET /cool_agristock/api/v1/lots`

Response `200`:
```json
{
  "status": "success",
  "count": 1,
  "lots": [{"id": 42, "name": "COCOA-2026-001", "product_id": 101, "ref": ""}]
}
```

### `POST /cool_agristock/api/v1/inventory-adjustments`

**Status: IMPLEMENTED** as sketched below, with field names corrected to match what actually
shipped — see [INITIAL_INVENTORY_IMPORT.md](INITIAL_INVENTORY_IMPORT.md) for the full as-built
reference (the sketch originally in this section used `counted_quantity` and a
`cool_agristock.inventory.import.log` model name; the shipped implementation uses `quantity`/`unit` and
`cool_agristock.inventory.import` — documented here as the correction it is, not silently).

Request:
```json
{
  "external_reference": "INITIAL-2026-001",
  "warehouse_external_id": "WH-001",
  "lines": [
    {"product_external_id": "AGRI-001", "quantity": 5000, "unit": "kg"}
  ]
}
```
Response `201` (import staged, **not yet applied** — see
[INITIAL_INVENTORY_IMPORT.md's Native adjustment handoff](INITIAL_INVENTORY_IMPORT.md#native-adjustment-handoff-phase-11--deferred-by-design-not-by-oversight)):
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
Response `409` (duplicate `external_reference` with different content):
```json
{"status": "error", "message": "external_reference already used with different content", "import_id": 7}
```
An identical retry of the same `external_reference` returns `200` with the existing import
(idempotent), not `409` — see [Idempotency](INITIAL_INVENTORY_IMPORT.md#idempotency-phase-13).

### Additive fields on existing endpoints (no new routes)

`POST /receipts`, `POST /dispatches`, and their `/validate` counterparts were proposed to gain
**optional** alternative identifier fields, used only if the corresponding numeric field is absent:

| Existing numeric field | New optional alternative | Status |
|---|---|---|
| `warehouse_id` | `warehouse_external_id` | Proposed — not implemented |
| `supplier_id` | `supplier_external_id` | Proposed — not implemented |
| `customer_id` | `customer_external_id` | Proposed — not implemented |
| `products[].product_id` | `products[].product_external_id` | Proposed — not implemented |
| `received_quantities[].product_id` / `dispatched_quantities[].product_id` (on `/validate` only) | `lot_external_id` | **Implemented** (Phase F — see [LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md#receipt-and-dispatch-integration)) |

**Correction:** Phase F shipped `lot_external_id` only on the `/validate` endpoints' line items
(`received_quantities`/`dispatched_quantities`), matching where quantities and lot assignment
actually happen in the existing flow — not on the `products[]` array of the initial `POST`
`/receipts`/`/dispatches` (which only ever carries the expected quantity, not what lot it arrived
in). The rest of this table's external-ID-everywhere proposal for receipts/dispatches'
*creation* endpoints remains unimplemented, as before.

Sending both the numeric and external-ID form for the same field is a caller error (`400`), not a
silent precedence rule.

## Development roadmap

### Phase A — External ID mapping and data ownership

**Status: IMPLEMENTED** (branch `feature/wms-external-id-mapping`, not yet merged). See
[EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md) for full documentation of what shipped.

- **Technical tasks:** ~~create the generic mapping model~~ done, plus an explicit
  `cool_agristock.external.system` model (not originally scoped this precisely, but needed so mappings
  can be scoped independently of any one API key's lifecycle — see
  [EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md#external-system-identity)); the
  resolve/create/update/remove service as model methods on
  `cool_agristock.external.id.mapping`, not a separate mixin.
- **Files changed:** `models/external_system.py`, `models/external_id_mapping.py` (new);
  `models/__init__.py`; `security/cool_agristock_security.xml`, `security/ir.model.access.csv`;
  `views/external_system_views.xml` (new); `tests/test_external_systems.py`,
  `tests/test_external_id_mapping.py` (new); `tests/__init__.py`; `__manifest__.py` (data entry +
  version bump).
- **Database models:** `cool_agristock.external.system`, `cool_agristock.external.id.mapping` (both new).
- **API endpoints:** none — confirmed, this phase shipped no REST routes, exactly as scoped.
- **Security requirements:** implemented as designed — company-scoped `ir.rule` on both new models;
  `ir.model.access.csv` grants the Administrator group full access to `external.system` and
  **read-only** access to `external.id.mapping`; the API User group has no direct grant on either
  model (service-mediated only, via `sudo()` after an explicit group+company check).
- **Automated tests:** 23 new tests (7 for `external.system`, 16 for the mapping service and
  model), covering every scenario originally listed for this phase plus the full approval-task
  checklist (duplicate codes, duplicate external IDs, duplicate Odoo-record mappings, different
  systems/companies sharing an ID, invalid targets, unsupported models, cross-company access,
  concurrent creation via the DB constraint, and the admin/API-User access boundary). All 84 tests
  in the module (61 pre-existing + 23 new) pass against a fresh throwaway database.
- **Dependencies:** none beyond what's already installed — confirmed.
- **Risks, as anticipated:** none materialized against the schema itself. One real implementation
  bug was caught by testing against the actual installed Odoo 19 build, not assumed: this Odoo
  version's `models.BaseModel` defines its own internal `_check_access(operation)` hook used by
  every `search()`/`write()` call; naming the mapping model's own authorization helper the same
  thing silently overrode Odoo's own access-control dispatch for that model. Renamed to
  `_check_mapping_access` once the test suite caught it. This is exactly the kind of thing "verify
  against the installed Odoo version" was meant to surface.
- **Acceptance criteria:** met — verified directly: a mapping can be created, retrieved, and a
  duplicate is handled without creating a second row; company A cannot see or create against
  company B's mappings (tested, not assumed); the database constraints — not just the
  application-level pre-check — are what actually stop a forced duplicate insert.

### Phase B — Product creation and updates

**Status: IMPLEMENTED** (branch `feature/wms-product-sync`, based on Phase A, not yet merged). See
[PRODUCT_SYNCHRONIZATION.md](PRODUCT_SYNCHRONIZATION.md) for the full as-built reference.

- **Technical tasks:** done, plus one addition not originally scoped here: binding an
  `cool_agristock.api.key` to an `cool_agristock.external.system` (Phase 3 of the implementation task), since
  "resolve external system from the authenticated key" required it and nothing had built that
  binding yet. UOM resolution shipped as a small hardcoded set now (not the Phase D table) — the
  sequencing question is resolved: Phase B shipped first, Phase D's richer table remains future
  work, exactly as flagged as an open decision.
- **Files changed:** `controllers/products.py` (new); `controllers/__init__.py`,
  `controllers/api_security.py` (added `resolve_authorized_external_system()`); `models/api_key.py`
  (added `external_system_id`, its company constraint, and
  `resolve_authorized_external_system()`); `wizards/api_key_generate_wizard.py` and
  `views/api_key_views.xml` (expose the binding at generation time); `security/ir.model.access.csv`
  (two new grants — see Risks); `tests/test_product_sync.py` (new); `tests/__init__.py`;
  `__manifest__.py` (version bump).
- **Database models:** none new — reuses `product.product` and Phase A's mapping model, as planned.
- **API endpoints:** `POST /products`, `PATCH /products/{external_id}`, exactly as planned.
- **Security requirements:** implemented as **explicit, auditable `ir.model.access.csv` grants**
  (not a `sudo()` bypass) — see Risks for why both `product.product` and `product.template` needed
  a grant, not just the former.
- **Automated tests:** 22 new tests — create, duplicate rejection (including a forced-race
  variant), update, 404 on unknown external_id, allow-list enforcement, **explicit rejection**
  (not silent ignoring — a deliberate refinement, see
  [PRODUCT_SYNCHRONIZATION.md](PRODUCT_SYNCHRONIZATION.md#supported-product-fields)), plus the full
  API-key-binding security matrix (valid/missing/invalid/revoked/expired/unbound keys, inactive
  external system, cross-company, cross-system). All 106 tests in the module pass (84 pre-existing
  + 22 new).
- **Dependencies:** Phase A — confirmed sufficient, nothing else was needed.
- **Risks, as anticipated vs. actual:** anticipated "low, closely mirrors existing patterns" — not
  quite true in practice. Two real issues surfaced only by testing against the installed Odoo 19,
  not by code review: (1) `stock.group_stock_user` (implied by Cool Agristock API User) has **no**
  `product.product` create/write access at all, unlike `stock.picking`/`stock.move` — had to be
  granted explicitly; (2) granting `product.product` access alone wasn't sufficient either —
  creating a `product.product` without an existing template also needs `create` access to the
  underlying `product.template` (delegation inheritance), only discovered when every product-
  creation test failed with an ACL error naming `product.template`, not `product.product`.
- **Acceptance criteria:** met, and demonstrated live — see
  [PRODUCT_SYNCHRONIZATION.md's Verification performed](PRODUCT_SYNCHRONIZATION.md#verification-performed)
  for the real HTTP request/response sequence (create Cassava → update it → repeat the create →
  `409`, no duplicate) with direct PostgreSQL row verification, not just API response trust.

### Phase C — Warehouse creation and mapping

**Status: IMPLEMENTED** (branch `feature/wms-warehouse-sync`, based on Phase B, not yet merged).
See [WAREHOUSE_SYNCHRONIZATION.md](WAREHOUSE_SYNCHRONIZATION.md) for the full as-built reference.

- **Technical tasks:** done, plus one addition not originally scoped: existing-warehouse adoption
  (reviewed per the task's own Phase 9, designed in detail, deliberately **not** implemented — the
  task explicitly permits documenting rather than shipping an unsafe shortcut).
- **Files changed:** `controllers/warehouses.py` (new); `controllers/__init__.py`;
  `tests/test_warehouse_sync.py` (new); `tests/__init__.py`; `__manifest__.py` (version bump). No
  `security/ir.model.access.csv` changes — see Security requirements below for why this phase
  deliberately diverged from Phase B's pattern there.
- **Database models:** none new — reuses `stock.warehouse` and Phase A's mapping model, as planned.
- **API endpoints:** `POST /warehouses`, `PATCH /warehouses/{external_id}`, exactly as planned.
  `code` ended up excluded from `PATCH` (see Risks).
- **Security requirements:** **not** `has_access()` as originally sketched. `stock.warehouse`
  creation cascades into `stock.location`, `stock.picking.type`, `stock.route`, `stock.rule`, and
  `ir.sequence` — confirmed by reading `stock.warehouse.create()` directly — and none of those
  models has any native create access for the Cool Agristock API User group (verified empirically,
  the same way the Phase B product.template gap was found). Granting broad access across all of
  them to match Phase B's pattern would hand the API User group standing write access to routing/
  picking-type configuration, which Phase 7 explicitly forbids. Instead: the controller performs
  the same explicit auth + resolved-external-system check as every other write endpoint, then calls
  `stock.warehouse.sudo().create(...)` — a single, narrow, already-gated operation, not a general
  capability. See [WAREHOUSE_SYNCHRONIZATION.md's Security section](WAREHOUSE_SYNCHRONIZATION.md#security)
  for the full reasoning.
- **Automated tests:** 26 new tests — creation, native location/picking-type generation, update,
  duplicate name/code/external_id handling (three distinct conflict sources, not one), the
  `code`-immutability rejection, the full API-key-binding security matrix, cross-company isolation,
  and confirmation that Phase A/B's existing endpoints and tests are entirely unaffected. All 132
  tests in the module pass (106 pre-existing + 26 new) — notably, **zero failures on the first full
  run**, unlike Phase B, because the product.template-style ACL lesson was checked for up front
  before writing the controller rather than discovered by a failing test.
- **Dependencies:** Phase A — confirmed sufficient.
- **Risks, as anticipated vs. actual:** anticipated "needs explicit testing that auto-created
  records don't produce surprises" — confirmed true and tested directly (real `stock_location` and
  picking-type rows verified via SQL, not just trusted from the API response). One risk not
  anticipated in the original sketch: `code` changes after creation turned out to be a genuine
  data-integrity hazard (a warehouse's auto-generated locations are named from its code at creation
  time, with no re-propagation on a later change) — resolved by excluding `code` from `PATCH`
  entirely, per the task's own "reject the change rather than risk data corruption" instruction.
- **Acceptance criteria:** met, and demonstrated live — see
  [WAREHOUSE_SYNCHRONIZATION.md's Verification performed](WAREHOUSE_SYNCHRONIZATION.md#verification-performed)
  for the real HTTP sequence (create Anyama Warehouse → update it → repeat the create → `409`) with
  direct PostgreSQL verification that the native location tree and picking types genuinely exist,
  not just that the warehouse row does.

### Phase D — Supplier integration and UOM mapping

**Status: IMPLEMENTED** (branch `feature/wms-supplier-uom-sync`, based on the API-key isolation
security fix, not yet merged). See [SUPPLIER_SYNCHRONIZATION.md](SUPPLIER_SYNCHRONIZATION.md) and
[UOM_MAPPING.md](UOM_MAPPING.md) for the full as-built reference.

- **Technical tasks:** done. The `customer_rank`/`supplier_rank` variant mentioned in the original
  plan was dropped: both fields were checked directly against this installation and found not to
  exist (no `account`/`sale`/`purchase` module installed) — not referenced anywhere in the shipped
  code. Country lookup resolution shipped as planned.
- **Files changed:** `controllers/suppliers.py`, `models/uom_mapping.py`,
  `views/uom_mapping_views.xml` (new); `controllers/__init__.py`, `models/__init__.py`,
  `security/ir.model.access.csv`, `security/cool_agristock_security.xml`, `__manifest__.py` (version
  bump); `controllers/products.py` (UOM-mapping integration); `tests/test_supplier_sync.py`,
  `tests/test_uom_mapping.py` (new); `tests/__init__.py`. No seed data file — mappings are
  administrator-created from scratch, not pre-populated, since the whole point is that this
  module never assumes what a "bag" weighs.
- **Database models:** `cool_agristock.uom.mapping` (new) — shipped as a **database-backed model**, as
  approved (see [ARCHITECTURE.md's Approved decisions](ARCHITECTURE.md#approved-decisions), item 7).
- **API endpoints:** `POST /suppliers`, `PATCH /suppliers/{external_id}`, plus a `GET /suppliers`
  not originally itemized in this roadmap's Phase D row but present in the implementation task and
  shipped, matching the read-endpoint pattern already established for products/warehouses.
- **Security requirements:** **not** `has_access()` as originally sketched — checked empirically
  (the same way the Phase B/C ACL gaps were found) and confirmed `res.partner` has no native
  create/write access for the Cool Agristock API User group either. Rather than grant a standing
  `ir.model.access.csv` row — which would hand the API User group broad write access to the
  *entire* contacts/partner directory, arguably Odoo's single most widely-shared model — the
  controller uses the same gated `sudo()` pattern as Phase C's warehouses. This directly resolves
  the risk flagged below.
- **Automated tests:** 29 new tests across both files — supplier creation/update/duplicate/
  shared-partner-protection/security matrix, and UOM mapping creation/duplicate/admin-only-access/
  `resolve_unit()` correctness/product-sync integration (including proof that a configured mapping
  takes precedence over the hardcoded fallback, not merely supplements it). All 178 tests in the
  module pass (149 pre-existing + 29 new).
- **Dependencies:** Phase A — confirmed sufficient.
- **Risks, as anticipated vs. actual:** the anticipated risk ("`res.partner` is widely-shared,
  needs careful review") is exactly what drove the `sudo()`-over-native-ACL decision above, and is
  additionally addressed by always creating WMS-sourced suppliers company-scoped
  (`company_id` set, never `False`) and refusing to `PATCH` a shared (`company_id = False`) target
  even if one is ever mapped through another path. See
  [SUPPLIER_SYNCHRONIZATION.md's Shared partner protection](SUPPLIER_SYNCHRONIZATION.md#shared-partner-protection).
- **Acceptance criteria:** the originally sketched criterion ("appears as a vendor option on a
  purchase order") could not be verified as written, since this installation has no `purchase`
  module — the equivalent, verified check instead: a supplier created via the API is a real,
  well-formed `res.partner` row (confirmed via direct SQL, not just the API response), correctly
  company-scoped, with its country resolved to the matching `res.country` record.

### Phase E — Initial inventory import and reconciliation

**Status: IMPLEMENTED** (branch `feature/wms-inventory-import`, based on Phase D, not yet merged).
See [INITIAL_INVENTORY_IMPORT.md](INITIAL_INVENTORY_IMPORT.md) for the full as-built reference.

- **Technical tasks:** done, with one real correction to this roadmap's own original sketch: the
  sketch assumed the `inventory_mode` quant-creation path (setting `inventory_quantity` on a quant)
  would *stage* a count for later separate application. Reading Odoo 19's actual
  `stock/models/stock_quant.py` directly shows this is wrong — that field's inverse method calls
  `action_apply_inventory()` **synchronously, in the same write**, whenever `inventory_mode` context
  is active; there is no native "staged but not applied" state to hook into at all. The native
  handoff is therefore fully manual in this phase — see
  [INITIAL_INVENTORY_IMPORT.md's Native adjustment handoff](INITIAL_INVENTORY_IMPORT.md#native-adjustment-handoff-phase-11--deferred-by-design-not-by-oversight)
  for the complete reasoning, confirmed against source rather than assumed.
- **Files changed:** `models/inventory_import.py` (new — `cool_agristock.inventory.import` +
  `cool_agristock.inventory.import.line`, not `cool_agristock.inventory.import.log` as originally sketched);
  `controllers/inventory_import.py` (new); `models/__init__.py`, `controllers/__init__.py`;
  `security/ir.model.access.csv`, `security/cool_agristock_security.xml`; `views/inventory_import_views.xml`
  (new — an Odoo-native review screen under Inventory → Operations, not a REST `GET`/`PATCH`);
  `__manifest__.py` (version bump); `tests/test_inventory_import.py` (new); `tests/__init__.py`.
- **Database models:** `cool_agristock.inventory.import`, `cool_agristock.inventory.import.line` (both new).
- **API endpoints:** `POST /inventory-adjustments` only — deliberately no `GET`/`PATCH`; review
  happens in Odoo's own backend, matching the UOM Mappings precedent from Phase D.
- **Security requirements:** not `has_access('create')` on `stock.quant` as originally sketched —
  `stock.quant` is far too broad/sensitive a model for a standing grant (same reasoning as Phase
  C/D). The controller uses the same gated `sudo()` pattern instead; approving/rejecting a staged
  import is restricted to Odoo's own native `stock.group_stock_manager` (Inventory Manager), reused
  rather than inventing a parallel authorization concept.
- **Automated tests:** 27 new tests — valid import, multiple lines, unknown product/warehouse,
  invalid/incompatible unit, negative quantity, idempotent duplicate vs. conflicting duplicate, a
  forced-race test at the model level, cross-company/cross-system isolation, the full API-key
  security matrix, lot/serial rejection, location-ambiguity (proving only `lot_stock_id` is ever
  used), reconciliation arithmetic (existing stock, zero stock), stale-data detection across a real
  state transition, unauthorized approval, rejection, a direct assertion that `stock.quant.quantity`
  is bit-for-bit unchanged after both creation and approval, and existing-endpoint compatibility.
  All tests in the module pass against a fresh database — see the Phase E final report for the
  exact total.
- **Dependencies:** Phases A, B (products), C (warehouses), D (UOM mapping) — confirmed sufficient.
- **Risks, as anticipated vs. actual:** the anticipated risk ("highest-risk phase... a bug here
  risks corrupting real inventory counts") is exactly why the native-handoff investigation above
  was done *before* writing any quant-touching code, not after — and it's exactly what led to
  **not** shipping any automated handoff at all this phase, per the task's own explicit permission
  to defer rather than ship an unsafe shortcut. The no-auto-apply recommendation is met by
  construction: there is no code path in this phase that can apply an adjustment, automatically or
  otherwise.
- **Acceptance criteria:** the originally sketched criterion (apply via Odoo's native screen, stock
  matches exactly) could not be demonstrated as a single automated test, since the apply step is
  manual by design — instead, verified directly: a batch is submitted, staged with the correct
  computed difference, confirmed to leave `stock.quant.quantity` completely unchanged, and a
  deliberate real-stock change before review is confirmed to move the import to `stale` rather than
  let it be approved against outdated numbers. See
  [INITIAL_INVENTORY_IMPORT.md's Verification performed](INITIAL_INVENTORY_IMPORT.md#verification-performed).

### Phase F — Lot and batch integration

- **Technical tasks:** `POST`/`GET /lots`; the additive `lot_external_id` field on receipt/dispatch
  product lines; **removal of the current blanket lot/serial rejection, replaced with real
  handling** — this is the one place existing behavior intentionally changes, and only for
  lot-tracked products specifically (non-tracked products are entirely unaffected).
- **Files likely to change:** new `controllers/lots.py`; `controllers/receipts.py`,
  `controllers/dispatches.py`, `controllers/receipt_validation.py`,
  `controllers/dispatch_validation.py` (the four files containing today's rejection logic).
- **Database models:** none new (reuses `stock.lot` + Phase A's mapping model).
- **API endpoints:** `POST /lots`, `GET /lots`; additive fields on the four existing transaction
  endpoints.
- **Security requirements:** `has_access()` on `stock.lot`.
- **Automated tests:** everything in the *existing* lot-rejection test suite must still pass
  unchanged for non-lot-tracked products; new tests for the lot-tracked path end-to-end; a test
  confirming a lot cannot be over-allocated beyond its recorded quantity.
- **Dependencies:** Phases A, B (lots belong to products).
- **Risks:** this phase touches the most existing, already-shipped code (the four transaction
  controllers) — regression risk is real. The existing rejection tests must be run and pass before
  and after every change in this phase, not just at the end.
- **Acceptance criteria:** a lot-tracked product can now be received and dispatched by external lot
  ID end-to-end; a non-lot-tracked product's behavior is byte-for-byte unchanged, confirmed by the
  existing test suite passing with zero modifications to those specific test assertions.

### Phase G — Transaction integration enhancements

**Status: IMPLEMENTED** (branch `feature/wms-transaction-sync`, based on Phase F, not yet merged).
See [WMS_TRANSACTION_SYNCHRONIZATION.md](WMS_TRANSACTION_SYNCHRONIZATION.md) for the full as-built
reference.

- **Technical tasks:** done, shaped differently than this sketch assumed — not additive
  `*_external_id` fields alongside the existing `products[]` array, but a second, parallel request
  shape (`lines[]` instead of `products[]`) on the same route, since the new schema also needed
  `unit` and `lot_external_id` per line that the original array had no place for. Both shapes are
  accepted on the same `POST`, discriminated by which top-level key is present.
- **Files changed:** `controllers/receipts.py`, `controllers/dispatches.py` (both substantially
  extended, legacy code path preserved verbatim inside its own method); `controllers/receipt_validation.py`,
  `controllers/dispatch_validation.py` (one small fix — see Risks); `models/wms_transaction.py`
  (new); `models/__init__.py`, `security/ir.model.access.csv`, `security/cool_agristock_security.xml`,
  `__manifest__.py` (version bump); `tests/test_transaction_sync.py` (new); `tests/__init__.py`.
- **Database models:** `cool_agristock.wms.transaction` (new) — not originally scoped in this sketch
  ("none new"), added because the existing advisory-lock/`origin`-match duplicate protection has no
  real database-level uniqueness and no `external_system_id` dimension; see
  [WMS_TRANSACTION_SYNCHRONIZATION.md's Transaction identity](WMS_TRANSACTION_SYNCHRONIZATION.md#transaction-identity)
  for the full reasoning.
- **API endpoints:** no new routes for creation (confirmed, as sketched) — but two new routes were
  added beyond this sketch's scope: `GET /receipts/{external_reference}` and
  `GET /dispatches/{external_reference}` (Phase G's own task specification, section 7).
- **Security requirements:** as sketched — the new path reuses the exact same mapping-lookup
  resolution as Phases A-F; the legacy path requires no external-system binding at all, unchanged.
- **Automated tests:** 32 new tests — the "numeric only / external-ID only / both provided" matrix
  this sketch anticipated, plus idempotency, conflict, a forced-race test, the full security matrix,
  status retrieval, lot/serial-tracked transactions, partial-transaction rejection (confirmed not to
  create a backorder), and existing-endpoint compatibility. All tests in the module pass against a
  fresh database — see the Phase G final report for the exact total.
- **Dependencies:** Phases A-D — confirmed sufficient, plus Phase F for lot resolution.
- **Risks, as anticipated vs. actual:** anticipated "low... mostly wiring" — mostly true, but one
  real compatibility bug surfaced only by testing, not by code review: `/validate`'s existing guard
  checked only for the legacy `COOL_AGRISTOCK-RCPT-`/`COOL_AGRISTOCK-DISP-` prefix, which a Phase G
  `external_reference` would never match — a WMS-first receipt could be created but never
  validated. Fixed by also recognizing a real `cool_agristock.wms.transaction` row as proof of
  Cool Agristock ownership.
- **Acceptance criteria:** met, and demonstrated live — see
  [WMS_TRANSACTION_SYNCHRONIZATION.md's Verification performed](WMS_TRANSACTION_SYNCHRONIZATION.md#verification-performed):
  an existing numeric-ID integration (the full pre-Phase-G test suite) continues to pass unchanged;
  a new WMS-first integration created, retrieved, and validated a receipt and a dispatch using only
  external IDs, confirmed via direct SQL.

### Phase H — ERP workflow integration testing

- **Technical tasks:** no new code — this phase is validation that everything built in A-G
  interacts correctly with Odoo's own ERP functions (the parts explicitly **not** touched by any
  phase): a product created via the API can be invoiced normally; a supplier created via the API
  can receive a normal Odoo-created purchase order; accounting entries post correctly from
  API-created stock moves exactly as they do from manually-created ones.
- **Files likely to change:** none (test files only).
- **Database models:** none new.
- **API endpoints:** none new.
- **Security requirements:** none new — this phase verifies the ownership-matrix boundary actually
  holds (nothing WMS-created ever touches accounting config).
- **Automated tests:** end-to-end scenarios spanning a product/supplier created via the API through
  to a real Odoo invoice, run against a throwaway database per the project's existing test
  conventions.
- **Dependencies:** Phases A-G complete.
- **Risks:** this is where a subtle ownership-matrix violation would surface (e.g., a field
  accidentally left writable that shouldn't be) — treat any finding here as a blocker, not a
  follow-up item.
- **Acceptance criteria:** a full customer scenario — WMS creates products/warehouse/supplier,
  imports initial stock, receives and dispatches goods including a lot-tracked one — produces
  correct, auditable Odoo accounting entries with no manual data entry required on the Odoo side
  beyond the initial inventory-adjustment approval clicks.

## API compatibility & versioning

- **Every existing route's request/response shape is unchanged** across all eight phases. Confirmed
  by design, not just intention: Phases A-E and most of F/G add only new routes or strictly
  *optional, additive* fields on existing ones; the only phase that touches existing controller
  files in a way that changes behavior (Phase F, the lot-rejection removal) only changes behavior
  for the specific product-tracking case that previously always failed — a client that never sends
  a lot-tracked product sees no change at all.
- **No existing route is renamed or removed.** The `/cool_agristock/api/v1/` prefix is unchanged
  throughout; **no `v2` is introduced** by this roadmap, because nothing in it breaks an existing
  request/response contract.
- **Recommended module version bump:** Odoo module versions follow
  `odoo_major.odoo_minor.module_major.module_minor.module_patch` (the current manifest version is
  `19.0.1.0.0`). Since every phase is additive, each phase should bump the **module_minor** segment
  (e.g. Phase A → `19.0.1.1.0`, Phase B → `19.0.1.2.0`, and so on), reserving a **module_major** bump
  (`19.0.2.0.0`) for if/when a genuinely breaking change is ever needed — which this roadmap does
  not plan to introduce.
- **Existing API clients require zero changes** to keep working through every phase in this
  roadmap — this is treated as a hard constraint, not a best-effort goal, and Phase G's test matrix
  exists specifically to keep proving it with each change.
