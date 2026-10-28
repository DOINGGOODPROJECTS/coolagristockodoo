# Product Synchronization — Reference

**Status: IMPLEMENTED.** Everything in this document exists in the code today, on branch
`feature/wms-product-sync` (based on Phase A's `feature/wms-external-id-mapping`, not yet merged
into `main`/`19.0`). This is Phase B of the WMS-first roadmap — see
[API_ROADMAP.md](API_ROADMAP.md#phase-b--product-creation-and-updates) for where it fits, and
[EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md) for the Phase A infrastructure this builds on.

**Not included, explicitly:** warehouse, supplier, lot, and inventory-adjustment endpoints remain
design-only — see [WMS_FIRST_INTEGRATION_PLAN.md](WMS_FIRST_INTEGRATION_PLAN.md). Created products
never get stock quantities from this phase; that's a separate, not-yet-built concern.

## Endpoints

### `POST /cool_agristock/api/v1/products`

Creates a new product, identified going forward by your own `external_id`.

**Authentication:** `Authorization: Bearer <api-key>`, same as every other endpoint — **and** the
key must be bound to an active external system (see [API key binding](#api-key-binding) below).

Request:
```json
{
  "external_id": "AGRI-001",
  "name": "Cassava",
  "default_code": "CASSAVA-001",
  "unit": "kg"
}
```

Response `201`:
```json
{"status": "success", "product_id": 53, "external_id": "AGRI-001", "name": "Cassava"}
```

Response `409` (external_id already mapped — no new product created):
```json
{"status": "error", "message": "external_id already mapped", "product_id": 53}
```

### `PATCH /cool_agristock/api/v1/products/{external_id}`

Partial update — only send the fields you want to change.

Request:
```json
{"name": "Fresh Cassava"}
```

Response `200`:
```json
{"status": "success", "product_id": 53, "external_id": "AGRI-001", "name": "Fresh Cassava"}
```

Response `404` (no product mapped under this external_id, for this company/external system):
```json
{"status": "error", "message": "No product mapped for this external_id"}
```

**`PATCH` never creates a product.** If `external_id` doesn't resolve to an existing mapping, the
request fails — it does not fall back to creating one.

### `GET /cool_agristock/api/v1/products` — unchanged

Still exactly what it was before this phase: read-only, no authentication beyond the existing
Bearer + Cool Agristock API User requirement, no binding to an external system required. A key with no
external-system binding can still call this freely — see
[Backward compatibility](#backward-compatibility).

## API key binding

Product write endpoints require the authenticated key to be bound to an **active**
`cool_agristock.external.system`. Binding happens once, at key-generation time, via the **Generate API
Key** wizard's new **Authorized External System** field (Administrator-only, same screen as
before) — it cannot be changed afterward on an existing key, matching how every other field on a
generated key is already locked once created.

**Security history — a real vulnerability was found and fixed here, not just a documented
limitation.** The first version of this feature resolved authorization from the authenticated
*user*, not the specific key. Odoo's own Bearer-token verification
(`_check_apikey_credentials`) only ever returns *which user* authenticated, never *which specific
key row* — and at the time, every `cool_agristock.api.key` for one company shared **one** integration
user (the pre-existing, unchanged design for unbound keys). The consequence, reproduced directly
via a real HTTP request against a disposable Odoo 19 database: a key generated with **no** binding
authenticated a product-write request and succeeded (`201`), inheriting authorization from an
unrelated bound key that happened to share its company. See
[EXTERNAL_ID_MAPPING.md's API key binding section](EXTERNAL_ID_MAPPING.md#api-key-binding-reviewed-not-implemented)
for Phase A's original deferral decision, which Phase B's first implementation (below) revisited.

**Fixed:** a key that requests a binding now gets its **own, dedicated integration user**, created
fresh at generation time and never shared with any other key —
`cool_agristock.api.key._create_dedicated_integration_user()`. A bearer token now maps to exactly one
user, which maps to exactly one key, which resolves to exactly one external system. Keys generated
with **no** binding are entirely unaffected — they continue sharing the one per-company user
exactly as before, since that path never changed. Re-verified directly after the fix: the same
request that previously returned `201` for an unbound key now correctly returns `403`.

Regression tests proving this isolation live in
`tests/test_api_key_isolation_security.py` — covering both product and warehouse endpoints,
cross-system mapping access, and confirming the unbound-key-sharing behavior is unchanged for keys
that never request a binding.

## Supported product fields

**Create (`POST`) allow-list:**

| Field | Odoo field | Notes |
|---|---|---|
| `external_id` | *(mapping only, not a product field)* | Required, 1-128 chars. |
| `name` | `name` | Required, non-empty. |
| `default_code` | `default_code` | Optional. |
| `barcode` | `barcode` | Optional. |
| `description` | `description` | Optional. |
| `unit` | `uom_id` | Optional — see [Supported units](#supported-units). Defaults to **Units** if omitted. |

**Update (`PATCH`) allow-list:** `name`, `default_code`, `barcode`, `description` — **`unit` is
deliberately not updatable.** Changing a product's unit of measure after it may already have stock
movements is unsafe without checking for existing transactions first, which this phase doesn't
implement — so it's simply not exposed, rather than exposed without that safety check. See
[Known limitations](#known-limitations).

**Any field not on these lists is explicitly rejected with `400`**, not silently ignored — e.g.
sending `list_price` returns `{"status": "error", "message": "Unsupported field(s): list_price"}`.
This is a deliberate refinement over the conflict-handling rule originally sketched in
[WMS_FIRST_INTEGRATION_PLAN.md](WMS_FIRST_INTEGRATION_PLAN.md) (which proposed silently ignoring
unknown fields) — explicit rejection gives the WMS developer an immediate, actionable error instead
of a silently-dropped field discovered later.

**Fields verified never exposed, by construction (not by a block-list check):** sales price, cost,
taxes, accounting properties (income/expense accounts), valuation configuration, product category,
and every other ERP-specific setting. There is no code path in either endpoint that can write any
of these, regardless of what a request body contains.

**`product.template` vs `product.product`:** every endpoint operates on `product.product` (the
variant), matching the pre-existing `GET /products` endpoint — see
[EXTERNAL_ID_MAPPING.md](EXTERNAL_ID_MAPPING.md#allowed-models-explicit-allow-list-enforced-in-python)
for why `product.template` was
excluded from the mapping allow-list entirely.

Every created product is fixed, server-side, as `type="consu"`, `is_storable=True`,
`tracking="none"`, `company_id=False` (shared across companies, matching how `receipts.py` already
treats product lookups as company-independent via `company_id in [False, ...]`) — none of these are
client-controllable.

## Supported units

**Update (Phase D): the database-backed UOM mapping is now implemented** — see
[UOM_MAPPING.md](UOM_MAPPING.md) for the full reference. `unit` resolution now checks, in order:
(1) an administrator-configured `cool_agristock.uom.mapping` row for the caller's company and external
system, then (2) the small hardcoded set below, which remains exactly as it was in Phase B for
full backward compatibility — an integration that has never configured a mapping is entirely
unaffected.

A small, explicit, hardcoded set — verified to exist in this installed Odoo 19 via `env.ref()`
directly before use, not guessed:

| `unit` value(s) | Resolves to |
|---|---|
| `kg` | kg |
| `g` | g |
| `ton`, `t` | Ton |
| `l`, `liter`, `litre` | L |
| `unit`, `units`, `pcs` | Units |

Omitting `unit` defaults to **Units**. Any other value not matching a configured mapping **or**
this hardcoded set — including plausible-looking ones like `bag` or `box`, which this standard
Odoo installation does not ship as a native unit — is rejected with `400`, never silently guessed
or defaulted differently.

## Duplicate behavior

Identity is `(company, external_system, "product.product", external_id)` — reusing Phase A's
mapping schema directly, no separate product-specific identity table. A repeated `POST` with the
same `external_id`:

1. Is checked **before** any product is created (the common case) — returns `409` immediately, no
   new product, no mapping change.
2. Is also safe in the rarer **concurrent** case: if two requests for the same new `external_id`
   race, the database's unique constraint (not just the pre-check) is what actually prevents a
   second mapping; the losing request's product is explicitly rolled back — **never left as an
   orphaned, unmapped product.id** — and that request also returns `409` with the winning
   request's `product_id`. Verified directly: product creation and mapping creation share one
   request-level transaction, so any failure after the product is created discards the product
   too, not just the mapping attempt.

## Error responses

| Code | Condition |
|---|---|
| 400 | Invalid JSON, missing/empty `name`, missing/invalid `external_id`, unsupported field, unsupported unit |
| 401 | Missing, malformed, invalid, expired, or revoked API key (same as every existing endpoint) |
| 403 | Authenticated but not a Cool Agristock API User; or authenticated but the key isn't bound to an active external system; or the identity is ambiguously bound to more than one external system |
| 404 | (`PATCH` only) No product mapped for this `external_id` |
| 409 | `external_id` already mapped (create), with the existing `product_id` included |
| 500 | Unexpected server-side error (transaction rolled back; no stack trace in the response body) |

## Security restrictions

- Every write re-derives the authorized external system **from the authenticated key**, server-
  side — **never** from anything in the request body. There is no `external_system_id` field a
  client can send; it would be ignored even if sent, since the controller never reads it from the
  payload at all.
- Requires real, auditable ORM access: the Cool Agristock API User group was granted explicit `create`/
  `write` access to `product.product` **and** `product.template` (the latter discovered necessary
  only by testing against the real installation — see [Known limitations](#known-limitations)) —
  no `sudo()` bypass of ordinary access control for these writes.
- Company isolation is enforced the same way as every other write endpoint: the resolved external
  system's own `company_id` scopes every lookup and every created record.
- Cross-company: a key bound to one company's external system cannot create, read, or update
  another company's products through these endpoints — verified directly, including an attempt
  to `PATCH` another company's mapped product by its external_id (returns `404`, not `403` — the
  mapping simply isn't visible in that company's scope, so it looks the same as "doesn't exist").

## Backward compatibility

Every existing endpoint's behavior is unchanged, confirmed by the full pre-existing test suite
(84 tests) passing at its original count, unmodified:

- `GET /products`, `GET /warehouses`, `GET /inventory`, and the receipt/dispatch endpoints require
  no external-system binding and are entirely unaffected by this phase.
- A key generated with no `external_system_id` (the default — this field is optional) continues to
  work for every endpoint it already worked with; it's rejected only by the two new product-write
  endpoints.
- `cool_agristock.api.key`'s existing fields, `generate_key()`'s existing call signature (the new
  `external_system` parameter is optional, defaulting to `None`), and `action_revoke()`/
  `action_create_replacement()` are all unchanged in behavior for callers that don't pass the new
  parameter.

## Known limitations

- **No UOM change after creation** — `unit` is create-only; changing it later isn't implemented.
- **No stock quantities created** — a product created here starts with zero stock everywhere; Phase
  E (initial inventory import) is the planned, not-yet-built mechanism for that.
- **No product category / classification field** — reviewed per the original task's "candidate"
  list and deliberately excluded from this phase: there's no specified scheme for a WMS to
  reference a valid Odoo product category, and guessing one would mean inventing an underspecified
  resolution mechanism rather than a reviewed, documented one.
- **Existing-product adoption isn't supported here** — there's no way to retroactively map an
  `external_id` onto a product that already existed in Odoo before this phase; every `POST`
  creates a genuinely new product. An admin-approved adoption workflow, analogous to the one
  designed for warehouses in a later phase, would need its own separate design if this is ever
  needed for products too.

## Verification performed

- **Module installs cleanly** into a fresh, disposable Odoo 19 database, and **upgrades cleanly**
  from the Phase A state.
- **All 106 tests pass** against a fresh database: all 84 from Phase A at their original counts,
  plus 22 new tests covering the full security/behavior matrix for this phase.
- **A real bug was found and fixed by testing against the installed Odoo 19, not by inspection:**
  granting `product.product` create/write access to the Cool Agristock API User group was not sufficient
  — creating a `product.product` without an existing template also requires `create` access to the
  underlying `product.template` record (delegation inheritance). The first test run failed with
  `Access Denied by ACLs for operation: create ... model: product.template` on every product-
  creation attempt; fixed by granting the same explicit access to `product.template`.
- **A real test-fixture bug was also caught and fixed**, not hidden: an early test for "an unbound
  key is rejected" initially generated the unbound key for the *same company* as an already-bound
  key, which (per the API-key-binding finding above) made it inherit authorization — the test
  passed for the wrong reason until this was caught, then fixed by using a dedicated company with
  no bound key anywhere.
- **The full demo scenario was run against real HTTP requests and verified against actual
  PostgreSQL rows, not just API responses:** a WMS created "Cassava" (`POST`, `201`, product id
  recorded) → updated it to "Fresh Cassava" (`PATCH`, `200`) → repeated the original creation
  request (`409`, same product id returned) → confirmed via direct SQL that exactly one
  `product_product` row with that `default_code` exists, its name is "Fresh Cassava", and the
  `cool_agristock_external_id_mapping` row correctly points `AGRI-001` → that one product id.
- The pre-existing `/cool_agristock/api/v1/health` and `GET /products` endpoints were confirmed still
  responding correctly with this phase's code installed.
