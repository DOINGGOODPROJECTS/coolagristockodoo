# WMS-First Integration Plan

**Status: mostly PROPOSED DESIGN, NOT YET IMPLEMENTED — except the "External ID mapping design"
section immediately below, which shipped as Phase A** (branch `feature/wms-external-id-mapping`,
not yet merged — see [EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md) for the authoritative,
as-built reference). Every other section in this document (master data integration, initial
inventory import, lot and batch support, and the rest) remains design-only; nothing in those
sections exists in the codebase yet. See [ARCHITECTURE.md](ARCHITECTURE.md) for the target
architecture this design implements, and [API_ROADMAP.md](API_ROADMAP.md) for the phased build plan
and endpoint schemas.

## External ID mapping design

**This section's design shipped largely as described below** — the
`cool_agristock.external.id.mapping` model, its two database-level unique constraints, and the
resolve/create/update/remove service all exist and are tested. One refinement made during
implementation, not anticipated here: external systems are now their own explicit model
(`cool_agristock.external.system`), not a bare `external_system` string field, giving them company
scoping, an active flag, and an admin UI — see
[EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md#external-system-identity) for why and exactly what
exists today, rather than re-reading this section as current.

### The problem

Every existing endpoint (`receipts.py`, `dispatches.py`, confirmed by reading the code) requires
the caller to already know Odoo's internal integer ID for a product, warehouse, or partner. A
WMS-first integration needs the opposite: the WMS should be able to refer to its *own* identifiers
(`WMS-PRODUCT-001`) and have Cool Agristock resolve or create the corresponding Odoo record
transparently.

### Proposed model: `cool_agristock.external.id.mapping`

A single, generic mapping model — not a bespoke mapping table per record type — so the same
mechanism covers products, warehouses, suppliers, and lots without new infrastructure per phase.

| Field | Type | Notes |
|---|---|---|
| `company_id` | Many2one `res.company`, required | Scopes the mapping to one company, matching the existing isolation pattern. |
| `external_system` | Char, required | A short identifier for *which* external integration this mapping belongs to (e.g. `"primary_wms"`). Deliberately **not** a reference to `cool_agristock.api.key` — a mapping must survive key rotation/replacement; tying it to a specific key's lifecycle would orphan every mapping when a business rotates its credentials. |
| `res_model` | Char, required | e.g. `"product.product"`, `"stock.warehouse"`, `"res.partner"`, `"stock.lot"`. |
| `res_id` | Integer, required | The Odoo record's own database ID. Not a formal `Many2one` (the target model varies), consistent with Odoo's own generic-reference conventions. |
| `external_id` | Char, required | The WMS's own identifier string, e.g. `"WMS-PRODUCT-001"`. |

**Database constraints (both required, both enforced at the SQL level, not just in Python):**

- `unique(company_id, external_system, res_model, external_id)` — the same external ID cannot map
  to two different Odoo records (prevents duplicate creation on retry).
- `unique(company_id, external_system, res_model, res_id)` — one Odoo record cannot be mapped to
  two different external IDs for the same WMS (prevents split-identity confusion).

### Lookup and idempotency rule

Every proposed `POST` (create) endpoint follows the same algorithm:

1. Look up `cool_agristock.external.id.mapping` for `(company, external_system, res_model, external_id)`.
2. **If found:** reject with `409 Conflict`, same pattern as the existing receipt/dispatch
   duplicate-reference check — the existing record's Odoo ID is included in the response.
3. **If not found:** create the Odoo record (via the allow-listed fields only — see
   [ARCHITECTURE.md's ownership matrix](ARCHITECTURE.md#data-ownership-matrix)), create the mapping
   row in the same database transaction, return both the new Odoo ID and the external ID.

Every proposed `PATCH` (update) endpoint:

1. Look up the mapping by `(company, external_system, res_model, external_id)` from the URL path.
2. **If not found:** `404 Not Found` — a `PATCH` never creates a record; that's what `POST` is for.
3. **If found:** update only the allow-listed fields present in the request body; fields not sent
   are left untouched (partial update, standard `PATCH` semantics).

This mirrors the existing create-vs-validate split already used for receipts/dispatches (`POST`
creates once, a second call is a `409`; a separate call acts on the existing record) rather than
introducing a new, inconsistent "upsert" idiom.

### Why external IDs, not Odoo IDs, in the URL path

**Decision: proposed new `PATCH` routes are keyed by `external_id`, not by Odoo's internal integer
ID.** Rationale: the entire point of this plan is that the WMS should never need to learn or store
Odoo's internal IDs for records it owns. A path like `PATCH /products/{external_id}` lets the WMS
operate entirely in terms of its own identifiers. The Odoo ID is still returned in every response
body for debugging/support purposes, but it is not required as an input anywhere in the new
endpoints. **This is called out as an open decision for approval** in the final report, since it's
a genuine design choice, not the only possible one (the alternative — keying by Odoo ID and adding
a separate `GET /products/by-external-id/{id}` lookup endpoint — was considered and rejected as
more round-trips for no real benefit).

## Master data integration

### 1–2. Product creation and updates

**Status: IMPLEMENTED** (Phase B, branch `feature/wms-product-sync`) — see
[PRODUCT_SYNCHRONIZATION.md](PRODUCT_SYNCHRONIZATION.md) for the authoritative, as-built reference;
the sketch below is preserved for history but the shipped allow-list differs slightly (no
`is_storable` as a request field — it's fixed server-side; `description` was added).

- `POST /cool_agristock/api/v1/products` creates a `product.product` (consistent with the existing
  `GET /products` endpoint, which also operates on `product.product`, not `product.template`).
- Allow-listed fields (WMS-owned): `name`, `default_code`, `barcode`, `is_storable` (fixed `true`
  for anything synced this way — non-storable products aren't a warehouse-operations concept),
  `uom_id` (resolved via the UOM mapping below, not a raw Odoo UOM ID).
- **Not exposed, by design:** `list_price`, `standard_price`, tax fields, accounting category
  fields, supplier pricelists — all Odoo-owned per the ownership matrix.
- `PATCH /cool_agristock/api/v1/products/{external_id}` updates only the fields above, when present in
  the request body.

### 3. Warehouse creation and mapping

**Status: IMPLEMENTED** (Phase C, branch `feature/wms-warehouse-sync`) — see
[WAREHOUSE_SYNCHRONIZATION.md](WAREHOUSE_SYNCHRONIZATION.md) for the authoritative, as-built
reference. One refinement over this sketch: `PATCH` excludes `code`, not just the
routes/resupply/valuation fields anticipated here — changing a warehouse's code after its
locations and sequences are already named from it was identified as unsafe during design, not
merely out of scope.

- `POST /cool_agristock/api/v1/warehouses` creates a `stock.warehouse`.
- Allow-listed fields: `name`, `code`.
- **Not exposed:** anything related to multi-step routes, resupply rules, or accounting valuation
  settings tied to the warehouse — those remain Odoo/operations-team-configured, since they affect
  how Odoo's own stock engine behaves internally, not just data mirroring.
- `PATCH /cool_agristock/api/v1/warehouses/{external_id}` — same pattern as products, minus `code`.

### 4. Supplier creation and updates

- `POST /cool_agristock/api/v1/suppliers` creates a `res.partner` with `supplier_rank` set so it behaves
  as a vendor in Odoo's own logic.
- Allow-listed fields: `name`, `email`, `phone`, `street`, `city`, `country_id` (resolved from an
  ISO country code, not a raw Odoo ID — same external-identifier principle applied to a
  well-known reference list).
- **Not exposed:** payment terms, fiscal position, accounting-related partner fields.
- `PATCH /cool_agristock/api/v1/suppliers/{external_id}` — same pattern.

**Customers, not just suppliers:** the existing `dispatches.py` already accepts a `customer_id`
the same way `receipts.py` accepts `supplier_id` — both are `res.partner` records. The supplier
endpoints above are written generically enough (`res.partner`, `supplier_rank` vs. a parallel
`customer_rank` flag) that the same design covers customer creation too; the roadmap phases this in
alongside supplier work rather than as a separate phase, since it's the same model and the same
code path with one flag's value different.

### 5. Unit-of-measure mapping

UOM is a smaller, bounded problem: Odoo ships a fixed, well-known set of base UOMs (kg, units,
liters, etc.). Rather than letting a WMS create arbitrary new UOM records (high risk of duplicate
or inconsistent units — "kg" vs "Kg" vs "kilogram" all meaning the same thing), the proposed design
is a **mapping-only** endpoint: the WMS supplies its own UOM code/name, and Cool Agristock
resolves it to an existing Odoo `uom.uom` record via a small, explicit lookup table (seeded with
common agricultural units: kg, ton, liter, unit/piece, bag). No `POST /uom` creation endpoint is
proposed — if a WMS uses a unit with no sensible Odoo equivalent, that's a conflict to surface
loudly (`400`, with a clear message), not silently invent a new unit.

### 6. External WMS identifier mapping

Covered above by the `cool_agristock.external.id.mapping` model — applies uniformly to products,
warehouses, suppliers, and (Phase F) lots.

### Conflict-handling rules (summary)

| Situation | Rule |
|---|---|
| `POST` with an `external_id` that's already mapped | `409`, existing Odoo ID returned, no changes made |
| `PATCH` with an `external_id` that has no mapping | `404` — `PATCH` never creates |
| `PATCH` body includes a field outside the allow-list | That field is silently ignored, not an error — treat unknown/disallowed fields the same way REST APIs commonly ignore unrecognized body fields, so a WMS sending its *entire* local record (including fields it has no business sending) doesn't break |
| Two concurrent `POST`s for the same new `external_id` | Serialized via a PostgreSQL advisory lock keyed on `(company_id, external_system, res_model, external_id)`, exactly the same pattern already used for receipt/dispatch `external_reference` locking |

## Initial inventory import

### Two distinct flows — not one

1. **Initial inventory import** (one-time, bulk, per warehouse/product — migrating a WMS's existing
   stock levels into Odoo for the first time).
2. **Ongoing stock reconciliation** (recurring, periodic physical-count corrections after go-live).

**Day-to-day stock changes are not inventory adjustments.** Routine stock movements continue to
flow through the existing `POST /receipts` and `POST /dispatches` endpoints, unchanged. The
proposed `inventory-adjustments` endpoint exists only for the two flows above — it is explicitly
*not* a third way to move stock, by design, because receipts/dispatches already carry a proper
audit trail (`external_reference`, supplier/customer, a `stock.picking` record) that a generic
"set the count" adjustment does not.

### The mechanism: Odoo's own inventory-adjustment process, not a quantity overwrite

**Hard constraint, carried over verbatim from the task:** never directly overwrite
`stock.quant.quantity`. The proposed design uses the same mechanism Odoo's own "Inventory
Adjustments" UI feature uses internally, and the same mechanism already verified working in this
project's own clean-environment REST testing earlier this project (seeding 1,000 units of test
stock used exactly this call):

```python
env["stock.quant"].with_context(inventory_mode=True).create({
    "product_id": product.id,
    "location_id": location.id,
    "inventory_quantity": counted_quantity,   # the WMS's physical count
})
# NOTE: action_apply_inventory() is deliberately NOT called by the API.
```

Setting `inventory_quantity` (the "counted" value) creates a visible **difference** against the
current `quantity` (the "on hand" value) inside Odoo's native Inventory Adjustments screen — this
is standard, unmodified Odoo behavior, not new code. The proposed API call stops there. **A human
in Odoo reviews the difference and clicks Apply** (`action_apply_inventory()`) themselves, inside
Odoo's own UI. This is what satisfies the "inventory adjustment approval" requirement using a real,
existing Odoo mechanism rather than inventing an approval workflow from scratch.

### Design elements

- **Duplicate prevention:** each import/reconciliation batch carries its own idempotency key (an
  `external_reference`-style field), checked the same way receipts/dispatches already are, so a
  retried batch doesn't double-count a pending (not-yet-applied) adjustment.
- **Error handling:** a batch is validated line-by-line before any `stock.quant` row is touched —
  same "validate everything, then write" pattern `receipts.py` already uses for its product lines.
  An invalid product/warehouse reference in one line fails the whole batch with a clear line-level
  error, rather than partially applying a bulk import.
- **Audit logging:** proposed new model `cool_agristock.inventory.import.log` — one row per batch,
  recording the external batch reference, company, line count, submission timestamp, submitting
  integration (`external_system`), and whether it was later applied (and by whom, which Odoo
  already tracks natively on the resulting `stock.quant` write). This exists because a 500-line
  import batch needs batch-level traceability that per-quant `create_date`/`write_uid` alone
  doesn't give an operator trying to answer "what did last Tuesday's import actually contain?"

### Correction (Phase E, as-built): the mechanism above does not do what this plan assumed

**The code example above is wrong, and was corrected by reading Odoo 19's actual
`stock/models/stock_quant.py` before implementing Phase E, not by assuming this plan's earlier
"already verified working" note still held.** `stock.quant`'s `inventory_quantity` field has an
inverse method, `_set_inventory_quantity()`, whose own docstring says plainly: "Inverse method to
create stock move when `inventory_quantity` is set." Tracing it directly: setting that field while
`inventory_mode` context is active calls `action_apply_inventory()` **synchronously, in the same
write** — there is no intermediate "counted, not yet applied" persisted state to stop at. The
`# NOTE: action_apply_inventory() is deliberately NOT called by the API` comment above describes
code that would still apply the adjustment anyway, just from inside a method this module never
calls directly — the application happens inside Odoo's own field-write plumbing instead, which is
not actually safer.

**What Phase E shipped instead:** `cool_agristock.inventory.import`/`cool_agristock.inventory.import.line` (not
`cool_agristock.inventory.import.log`, and not touching `stock.quant` at all until a human later works
inside Odoo's own Physical Inventory screen by hand) — a plain staging area that only ever *reads*
`stock.quant.quantity`, never writes `inventory_quantity` or any other quant field. See
[INITIAL_INVENTORY_IMPORT.md's Native adjustment handoff](INITIAL_INVENTORY_IMPORT.md#native-adjustment-handoff-phase-11--deferred-by-design-not-by-oversight)
for the full reasoning and the resulting Known limitation (the apply step is manual, not automated,
in this phase). The duplicate-prevention and validate-before-write design elements above carried
over to the as-built version unchanged; the audit-logging and mechanism paragraphs above are
superseded by the correction in this section.

## Lot and batch support

**The current, explicit rejection of lot/serial-tracked products stays exactly as it is until this
phase is built and tested** — this is a direct requirement from the task, not a suggestion. No
change to that behavior is proposed for earlier phases.

### Design, once built

- Odoo 19's existing `product.product.tracking` field (`none` / `lot` / `serial`) and existing
  `stock.lot` model are reused as-is — no new tracking mechanism, no bypass of Odoo's own
  lot-validity rules (e.g. Odoo already prevents moving more of a lot than exists).
- **External lot identifiers:** the same generic `cool_agristock.external.id.mapping` model handles
  `stock.lot` the same way it handles products/warehouses — no bespoke lot-mapping table.
- `POST /cool_agristock/api/v1/lots` creates a `stock.lot` tied to a product (resolved via that product's
  own external ID, not a raw Odoo product ID — consistent with the rest of this design).
- `GET /cool_agristock/api/v1/lots` lists lots, filterable by product, scoped by company — read access
  only, matching the existing read-endpoint pattern.
- **Product relationship:** a lot belongs to exactly one product, enforced by Odoo's own model
  already (`stock.lot.product_id`) — nothing new to build here beyond passing it through correctly.
- **Duplicate prevention:** the same mapping-table unique constraint as every other record type.
- **Lot-specific stock movements:** receipts/dispatches gain an *additive, optional* field per
  product line — `lot_external_id` — resolved via the mapping table to a real `stock.lot`. Existing
  callers that never send this field see **no behavior change at all**; this is what makes the
  change backward-compatible (see [API_ROADMAP.md](API_ROADMAP.md#api-compatibility--versioning)).
- **Validation rules:** the lot must belong to the product referenced on the same line (Odoo
  enforces this already, but the controller should surface it as a clear `400`/`409` rather than a
  raw ORM exception); a lot cannot be referenced on a quantity that would exceed what's recorded
  against it, reusing Odoo's own stock-move validation rather than re-implementing quantity checks.

### Correction (Phase F, as-built): what actually shipped, and one real technical finding

Mostly built as sketched above, with small, worth-recording corrections:

- **Error codes:** "lot belongs to a different product" surfaces as `422` (not `400`/`409` as
  guessed above) — consistent with how every other "well-formed request, semantically rejected"
  case in this module is coded (e.g. Phase E's incompatible-UOM rejection).
- **`GET /lots` has no product filter** — it lists everything visible to the caller's company,
  capped at 100, exactly like every other `GET` endpoint already does; a filter wasn't needed and
  wasn't built, keeping this endpoint identical in shape to `GET /products`/`GET /warehouses`.
- **Receiving a lot was exactly as simple as sketched** — set `move.move_line_ids.lot_id` after the
  existing `move.quantity = ...` assignment, relying entirely on Odoo's own `_check_lot_product`
  constraint.
- **Dispatching from a specific lot was not as simple as sketched, and required reading Odoo 19's
  actual reservation code before writing anything.** The generic `action_assign()` call this plan
  assumed would "just work" picks whichever lot Odoo's own removal strategy prefers — not
  necessarily the one the WMS named. The as-built controller instead calls
  `stock.move._update_reserved_quantity(need, location_id, lot_id=..., strict=True)` — a real,
  public Odoo primitive for reserving an exact quantity from an exact lot, confirmed by reading
  `stock/models/stock_move.py` directly — before the normal reservation pass runs. See
  [LOT_BATCH_SYNCHRONIZATION.md's Dispatches section](LOT_BATCH_SYNCHRONIZATION.md#dispatches-outgoing--the-one-place-this-phase-had-to-go-past-just-set-a-field)
  for the full reasoning. This is still "the exact same `stock.move` creation path that exists
  today," as this plan promised — just invoked with an extra, explicit step for the lot-pinning
  case, not a parallel mechanism.
- **Resolving a lot requires a bound API key**, exactly like every other mapping-touching
  capability in this module — not mentioned explicitly in the original sketch above, but a direct
  consequence of reusing `cool_agristock.external.id.mapping`, which is itself always
  `(company, external_system)`-scoped. A legacy caller that never sends `lot_external_id` never
  triggers that requirement, preserving the backward compatibility this plan promised.

## Transaction review — receipts and dispatches

Reviewed directly against `receipts.py`, `dispatches.py`, `receipt_validation.py`,
`dispatch_validation.py`: the current `external_reference`-keyed advisory-lock duplicate protection
is sound and **is not being changed**. What changes is purely additive:

- `warehouse_id`/`supplier_id`/`customer_id`/`product_id` may optionally be supplied as
  `warehouse_external_id`/`supplier_external_id`/`customer_external_id`/`product_external_id`
  instead of the raw Odoo integer — resolved server-side via the mapping table. **Existing clients
  that send the numeric fields today are entirely unaffected** — both forms are accepted, numeric
  takes precedence if a request somehow sent both (treated as caller error otherwise, surfaced as
  `400` for sending conflicting identifiers rather than silently picking one).
- **Idempotency rule, stated explicitly:** `external_reference` remains the one and only
  idempotency key for receipts and dispatches, exactly as today. External-ID resolution for
  product/warehouse/partner references does not introduce a second idempotency concept — it only
  changes *how a reference is looked up*, not *how a duplicate submission is detected*.
- No new duplicate stock movements are introduced by any part of this plan: lot-specific moves and
  external-ID-resolved moves still go through the exact same `stock.move` creation path that
  exists today, just with an extra resolution step before it.

### Correction (Phase G, as-built)

Mostly built as sketched above, with two corrections:

- **Not field-level substitution on the existing `products[]` array** — the shipped schema is a
  second, parallel `lines[]` array on the same route, since it also needed `unit` and
  `lot_external_id` per line, which `products[]` had no place for. "Numeric takes precedence if
  both are sent" was replaced with a simpler, equally-safe rule: sending both `products` and
  `lines` at the top level is rejected outright (`400`) rather than given an implicit precedence
  order.
- **Idempotency did gain a second concept, deliberately, for the new path only**: the legacy
  `products[]` schema's advisory-lock/`origin`-match mechanism is untouched, exactly as promised
  above. The new `lines[]` schema uses a real `cool_agristock.wms.transaction` row with a database unique
  constraint instead, because it also needed to support `GET` status retrieval by
  `(company, external_system, external_reference)` — a lookup the legacy mechanism was never
  designed to serve. See
  [WMS_TRANSACTION_SYNCHRONIZATION.md's Transaction identity](WMS_TRANSACTION_SYNCHRONIZATION.md#transaction-identity).

## Security and multi-company design

Every new model and endpoint follows the existing, verified pattern rather than inventing a new
one:

- **`cool_agristock.external.id.mapping`, `cool_agristock.inventory.import.log`, and any new models:** row-level
  `ir.rule` scoped by `company_id`, mirroring `rule_cool_agristock_api_key_company` exactly.
- **`ir.model.access.csv`:** new rows grant the **Cool Agristock Administrator** group read/write access
  (matching the existing pattern for `cool_agristock.api.key`); the **Cool Agristock API User** group gets
  **no direct model access** — exactly like today, all access to these models is mediated through
  controller code calling `sudo()` only after the controller's own permission checks pass (the same
  architecture `api_key.py`'s `generate_key()` already uses). This means a compromised or
  misconfigured API key's underlying user can never query the mapping table directly via a generic
  Odoo RPC call — only through the specific, validated REST endpoints.
- **Every new write endpoint checks `has_access('create'/'write')`** on the real underlying model
  (`product.product`, `stock.warehouse`, `res.partner`, `stock.lot`) before writing — the same check
  `receipts.py` already performs for `stock.picking`/`stock.move`.
- **Company isolation:** every lookup (mapping table, product/warehouse/supplier resolution) is
  filtered by `company_id in env.companies.ids`, identically to how `receipts.py` already scopes
  its warehouse lookup today. One company's integration can never see, create against, or modify
  another company's products, warehouses, suppliers, lots, or mappings.
- **Least privilege, open decision:** today there is one API-calling role (Cool Agristock API User) with
  one fixed permission set. A finer-grained split (e.g., "can sync inventory counts" vs. "can
  create new products") is a legitimate future enhancement, flagged in the final report as an open
  decision, and deliberately **not** part of the initial roadmap phases — introducing it prematurely
  would add configuration surface before any real customer has asked for that granularity.
