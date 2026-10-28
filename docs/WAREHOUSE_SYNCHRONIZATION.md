# Warehouse Synchronization — Reference

**Status: IMPLEMENTED** (POST/PATCH creation and update), **DESIGNED BUT NOT IMPLEMENTED**
(existing-warehouse adoption — see [Existing warehouse adoption](#existing-warehouse-adoption)).
Branch `feature/wms-warehouse-sync`, based on Phase B's `feature/wms-product-sync`, not yet merged
into `main`/`19.0`. This is Phase C of the WMS-first roadmap — see
[API_ROADMAP.md](API_ROADMAP.md#phase-c--warehouse-creation-and-mapping) for where it fits, and
[PRODUCT_SYNCHRONIZATION.md](PRODUCT_SYNCHRONIZATION.md) for Phase B, which this phase mirrors
closely.

**Not included, explicitly:** supplier, lot, and inventory-adjustment endpoints remain design-only.

## How Odoo actually creates a warehouse (verified, not assumed)

Read directly from the installed Odoo 19 source
(`odoo/addons/stock/models/stock_warehouse.py`) before writing any code:

- `name` and `code` are both **required**, and both are **unique per company** — two separate
  database constraints (`unique(name, company_id)`, `unique(code, company_id)`), not one.
- `code` is a `Char` with a hard `size=5` limit — a longer code is a database-level error if not
  caught first.
- `company_id` is `readonly=True` — Odoo itself never lets a warehouse change company after
  creation, through any code path.
- `stock.warehouse.create()` is heavily overridden: given just `name`/`code`/`company_id`, it
  internally creates a view location, every operational sub-location (`lot_stock_id`, and
  input/output/quality/packing locations depending on `reception_steps`/`delivery_steps`, which
  default to the simplest one-step configuration), picking types and their sequences, routes, and
  push/stock rules — touching `stock.location`, `stock.picking.type`, `stock.route`, `stock.rule`,
  and `ir.sequence` along the way. **None of this is reimplemented here** — every endpoint below
  calls `stock.warehouse.create()` exactly as Odoo's own UI would, and lets it do all of this
  itself.

## Endpoints

### `POST /cool_agristock/api/v1/warehouses`

Request:
```json
{"external_id": "WH-001", "name": "Anyama Warehouse", "code": "ANY"}
```

Response `201`:
```json
{"status": "success", "warehouse_id": 23, "external_id": "WH-001", "name": "Anyama Warehouse", "code": "ANY"}
```

Response `409` (duplicate `external_id`, name, or code):
```json
{"status": "error", "message": "external_id already mapped", "warehouse_id": 23}
```

### `PATCH /cool_agristock/api/v1/warehouses/{external_id}`

Request:
```json
{"name": "Anyama Agricultural Warehouse"}
```

Response `200`:
```json
{"status": "success", "warehouse_id": 23, "external_id": "WH-001", "name": "Anyama Agricultural Warehouse", "code": "ANY"}
```

Response `404` (no warehouse mapped under this external_id):
```json
{"status": "error", "message": "No warehouse mapped for this external_id"}
```

Response `400` (attempting to change `code`):
```json
{"status": "error", "message": "code cannot be changed once a warehouse is created (its locations and sequences are already named from it) -- create a new warehouse instead if the code must change"}
```

### `GET /cool_agristock/api/v1/warehouses` — unchanged

Confirmed byte-for-byte unchanged by the full pre-existing test suite passing at its original
count. No binding is required to call it — exactly like `GET /products`.

## Supported warehouse fields

**Create (`POST`) allow-list:** `name`, `code` only. Both required.

**Update (`PATCH`) allow-list:** `name` only.

**`code` is excluded from `PATCH` entirely, on purpose** (per the task's own instruction: "if
changing a code could affect existing operations or integrations, reject the change rather than
risk data corruption"). `code` is used once, at creation time, to name the warehouse's
auto-generated view location and feeds into its other naming — nothing re-propagates a later code
change into those already-named child records, so allowing it would desynchronize the warehouse's
displayed code from its real internal structure. Rather than build and test that propagation
safely, it's simply not exposed — attempting to `PATCH` it returns a `400` with an explanation, not
a silent no-op or a confusing partial update.

**Verified never exposed, by construction:** `route_ids`, `reception_steps`/`delivery_steps`,
every picking-type field (`pick_type_id`, `in_type_id`, `out_type_id`, …), `resupply_wh_ids`/
`resupply_route_ids`, `mto_pull_id`, and every location field (`view_location_id`, `lot_stock_id`,
…) — none of these can be set by any request body, regardless of what it contains. `company_id` is
additionally enforced read-only by Odoo itself, independent of this module's own allow-list.

## External ID mapping

Reuses Phase A's `cool_agristock.external.id.mapping` exactly as designed — no separate
warehouse-specific mapping table. `res_model = "stock.warehouse"`:

```text
External System:        WMS-ANYAMA
External Warehouse ID:  WH-001
Odoo Warehouse ID:      23
```

Phase A's existing guarantees apply unchanged: no duplicate `external_id` within
(company, external system, model); no duplicate mapping to the same Odoo warehouse within that
same scope; full cross-company and cross-system isolation; the database's own unique constraints
are the final concurrency safety net, not just the application-level pre-check — confirmed directly
by forcing a duplicate insert and watching the database constraint reject it.

## Duplicate behavior

Two separate conflicts are possible for warehouses, unlike products — `name` and `code` are *each*
unique per company in Odoo itself, independent of the `external_id` mapping:

1. **Duplicate `external_id`** — checked first, before any warehouse is created; `409` with the
   existing `warehouse_id`.
2. **Duplicate `name` or `code`** within the same company — pre-checked before calling
   `stock.warehouse.create()`, so the conflict surfaces as a clean `409` rather than a raw database
   constraint violation. (`code`'s conflict is checked only on create — `PATCH` can't set a new
   code at all, so a code conflict can't arise through this endpoint after creation.)

**Atomicity:** warehouse creation (and everything Odoo's `create()` override does on its behalf —
the location tree, picking types, routes) and mapping creation share one request-level transaction.
If a race loses the mapping-creation step after the warehouse already exists, the entire
transaction — warehouse, its auto-created locations, picking types, everything — is explicitly
rolled back, not left as an orphaned structure. Verified directly, mirroring the identical proof
used for Phase B's products.

## Existing warehouse adoption

**Reviewed, and deliberately not implemented in this phase** — the task's own instructions allow
documenting a safe design rather than shipping an unsafe shortcut, and that's the choice made here.

**Why this needs its own workflow, not a quick addition to `POST`:** most real Odoo installations
already have warehouses, created by a human through the normal UI, long before any WMS integration
exists. A WMS's very first sync attempt for an existing warehouse would otherwise either (a) fail
confusingly on `POST`'s name/code uniqueness check (since the warehouse already exists), or
(b) if "helpfully" auto-matched by name, silently attach external data to a warehouse nobody
explicitly confirmed is the right one — exactly the "silently overwrite" and "automatically merge"
outcomes the task explicitly forbids.

**Proposed design (not built):**

1. A new, **Administrator-only** action — not reachable by any API key, ever — e.g. "Adopt
   External Warehouse Mapping," presented from the existing warehouse's own form view.
2. The administrator explicitly selects: the target Odoo warehouse (already on screen, so
   unambiguous), the external system, and types in the external system's own ID for it.
3. Server-side validation before anything is written: the warehouse exists (trivially true — it's
   selected from a real record) and belongs to the administrator's own company (enforced by the
   same `ir.rule` pattern already applied everywhere else); no existing mapping already claims that
   external ID, or that warehouse, for that external system (Phase A's own unique constraints would
   catch this anyway, but a clean pre-check gives a better error message).
4. Only on confirmation does it call `cool_agristock.external.id.mapping.create_mapping()` — the exact
   same service method `POST /warehouses` uses, so adopted and natively-created mappings are
   indistinguishable afterward; this is a second path to the same well-tested write operation, not
   a separate, less-tested one.
5. **No bulk/automatic matching by name or code is proposed.** Each adoption is one explicit,
   human-reviewed action per warehouse — deliberately not scalable to "adopt all warehouses at
   once," since that's exactly the kind of unsupervised bulk operation this design exists to avoid.

**Why not implemented now:** this is a genuinely separate feature (an admin UI workflow, not a REST
endpoint) with its own view/action/testing surface, and the task's own Phase 9 explicitly permits
documenting rather than building a shortcut. Building it properly deserves to be its own scoped
piece of work, not squeezed into this phase alongside the two REST endpoints.

## Security

- Authentication and external-system resolution are identical to Phase B: Bearer token → Cool Agristock
  API User group → `resolve_authorized_external_system()`, server-derived, never trusted from the
  request body. See [PRODUCT_SYNCHRONIZATION.md's API key binding](PRODUCT_SYNCHRONIZATION.md#api-key-binding)
  for the authorization-isolation fix (each bound key gets its own dedicated integration user,
  found necessary by a pre-Phase-D security review) — confirmed to apply identically to warehouse
  endpoints by `tests/test_api_key_isolation_security.py`'s dedicated warehouse-side assertions.
- **Deliberate security design difference from Phase B:** Phase B granted the Cool Agristock API User
  group explicit, auditable `ir.model.access.csv` rows on `product.product`/`product.template`.
  This phase does **not** grant any new `ir.model.access` rows at all. Warehouse creation cascades
  into `stock.location`, `stock.picking.type`, `stock.route`, `stock.rule`, and `ir.sequence` —
  models whose direct, standing write access Phase 7 explicitly says a WMS must never have (routes,
  picking types, operational configuration). Granting broad native access across all of them to
  reach parity with Phase B's pattern would have meant giving the API User group a standing
  capability well beyond "create a warehouse." Instead, the controller performs its own explicit
  authentication/authorization check first (identical to Phase B's), and only then calls
  `stock.warehouse.sudo().create(...)` — a narrow, already-gated use of `sudo()`, not a general
  bypass exposed to callers. This satisfies "do not expose *unrestricted* sudo() operations to API
  callers": the operation is singular, fixed, and reachable only after the same authorization gate
  every other write endpoint already requires.
- Company isolation: every lookup and every created/updated record is scoped to the resolved
  external system's own company — verified directly, including a cross-company update attempt
  (returns `404`, not `403` — a mapping outside your company's scope is indistinguishable from one
  that doesn't exist, matching Phase B's identical behavior for products).

## Error responses

| Code | Condition |
|---|---|
| 400 | Invalid JSON, missing/empty `name` or `code`, unsupported field, attempting to `PATCH` `code` |
| 401 | Missing, malformed, invalid, expired, or revoked API key |
| 403 | Not a Cool Agristock API User; key not bound to an active external system; identity ambiguously bound to more than one |
| 404 | (`PATCH` only) No warehouse mapped for this `external_id` |
| 409 | `external_id`, warehouse `name`, or warehouse `code` already in use |
| 422 | `code` longer than 5 characters (Odoo's own hard limit) |
| 500 | Unexpected server-side error (transaction rolled back; no stack trace in the response) |

## Known limitations

- **Existing-warehouse adoption is designed, not built** — see above.
- **No code change after creation** — by design, for data-integrity reasons, not an oversight.
- **No operational configuration (routing, picking steps) is configurable via the API** — every
  warehouse created this way gets Odoo's simplest default (one-step receiving, one-step delivery).
  Customizing this remains a manual, Odoo-side configuration task.
- **Resupply routes between warehouses aren't configurable here** — `resupply_wh_ids` is Odoo-UI-
  only for warehouses created through this API.

## Verification performed

- **Module installs cleanly** into a fresh, disposable Odoo 19 database, and **upgrades cleanly**
  from the Phase B state.
- **All 132 tests pass**, with zero failures on the first full run (unlike Phase B, where two real
  bugs needed fixing): all 106 pre-existing tests (Phases A and B) at their original counts, plus
  26 new tests for this phase.
- **The full demo scenario was run against real HTTP requests and verified against actual
  PostgreSQL rows:** a WMS created "Anyama Warehouse" (`POST`, `201`) → updated its name to "Anyama
  Agricultural Warehouse" (`PATCH`, `200`) → repeated the original creation request (`409`, same
  warehouse id) → confirmed via direct SQL that exactly one `stock_warehouse` row with code `ANY`
  exists, its name reflects the update, the mapping row correctly points `WH-001` → that warehouse,
  and — the part unique to this phase — that Odoo's own `create()` override genuinely ran: real
  `stock_location` rows exist for the view location (named "ANY", `usage='view'`) and the internal
  stock location (named "Stock", `usage='internal'`), and real picking types are assigned
  (`in_type_id`, `out_type_id` both set).
- The pre-existing `/cool_agristock/api/v1/health`, `GET /warehouses`, product-sync, and receipt/dispatch
  endpoints were confirmed still responding correctly with this phase's code installed.
