# AgriWare Connector — API Integration Report for COOL AGRISTOCK

**Status: read-only investigation. No code was modified. Nothing was pushed, merged, published,
or deployed. No credential values are included anywhere in this document.**

Based strictly on the actual source in `agriware_connector/controllers/` and
`agriware_connector/models/` at commit `de9ea4e` (branch `release/agriware-19.0-wms-first`,
module version `19.0.2.0.0`). Every endpoint, field, and behavior below was read directly from
that source, not inferred or assumed.

---

## A. Authentication mechanism

### HTTP layer

- **Transport:** plain HTTP/HTTPS, JSON request/response bodies, `Content-Type: application/json`.
- **Auth type:** Odoo's built-in `auth="bearer"` route authentication (all endpoints except
  `/health`, which is `auth="public"`).
- **Required header:**
  ```
  Authorization: Bearer <raw_api_key>
  ```
  The raw key is the one shown **once**, at generation time, in the Odoo UI (API Management
  screen). It is never stored anywhere in retrievable form afterward — Odoo stores only a hash,
  and `agriware.api.key.generate_key()`'s own docstring is explicit that "the raw key is returned
  exactly once and is never stored anywhere." If it's lost, there is no way to retrieve it again;
  a new key must be generated.
- **Database selection:** this Odoo instance has **no `dbfilter` configured** and hosts multiple
  databases. Every request must also carry:
  ```
  X-Odoo-Database: <database_name>
  ```
  Confirmed directly: a request without this header returns `404 Not Found` with the body "No
  database is selected ... Please verify the hostname ... Alternatively, use the X-Odoo-Database
  header." Adding the header resolves it. (See Section F / Section on local server below.)

### Authorization layers (checked in this order, in code)

1. **Bearer token validity** — Odoo's own `res.users.apikeys` mechanism authenticates the token to
   exactly one `res.users` row (a dedicated, password-less "integration user" — never a human
   login). An invalid, expired, or revoked key fails here with Odoo's own `401`.
2. **`AgriWare API User` group membership** — every endpoint (except `/health`) calls
   `require_agriware_api_user()`, which checks `request.env.user.has_group(
   "agriware_connector.group_agriware_api_user")`. Fails → `403 "Access denied: AgriWare API User
   role required"`.
3. **External system binding** (write endpoints, and the two transaction-status GET endpoints
   only — see the per-endpoint table below) — `resolve_authorized_external_system()` looks up
   which `agriware.external.system` record the authenticated integration user's API key is bound
   to. This binding is set **once**, at key-generation time, via the "Generate API Key" wizard in
   Odoo, and is never editable afterward. An unbound key (or one whose external system has been
   deactivated) fails with `403` and an endpoint-specific message, e.g. *"This API key is not
   authorized for product synchronization: it is not bound to an active external system."*

   **Important nuance:** the plain read-only list endpoints (`GET /products`, `GET /warehouses`,
   `GET /inventory`, `GET /suppliers`, `GET /lots`) only require step 2 (API User group) — **not**
   an external-system binding. Only the write endpoints (POST/PATCH everywhere) and the two
   transaction-status lookups (`GET /receipts/{ref}`, `GET /dispatches/{ref}`) require step 3.

4. **Odoo's own `ir.model.access` / record rules** — the API User group is granted
   `stock.group_stock_user` (read/write on Inventory models) plus explicit
   `product.product`/`product.template` create+write access. Multi-company `ir.rule`s scope every
   AgriWare-specific model (API keys, external systems, mappings, UOM mappings, inventory imports,
   WMS transactions) to `company_id in company_ids`.

### What "the authorized external system" actually means in practice

A bearer token maps to one Odoo user → that user maps to **exactly one** `agriware.api.key` record
(enforced by a model constraint, `_check_dedicated_identity_for_bound_keys`) → that key resolves to
at most one active `agriware.external.system`. This binding is what every write endpoint uses to
scope `external_id` mappings (so two different WMS integrations against the same Odoo company can
never collide on the same external ID namespace).

---

## B. Available endpoints

All paths are rooted at `/agriware/api/v1`. 21 routes total.

| # | Method | Path | Auth level | Purpose |
|---|---|---|---|---|
| 1 | GET | `/health` | public | Liveness check |
| 2 | GET | `/products` | API User | List products (max 100) |
| 3 | POST | `/products` | API User + external system | Create product |
| 4 | PATCH | `/products/{external_id}` | API User + external system | Update product |
| 5 | GET | `/warehouses` | API User | List warehouses (max 100) |
| 6 | POST | `/warehouses` | API User + external system | Create warehouse |
| 7 | PATCH | `/warehouses/{external_id}` | API User + external system | Update warehouse (name only) |
| 8 | GET | `/inventory` | API User | List on-hand stock quants (max 100) |
| 9 | GET | `/suppliers` | API User | List suppliers/partners (max 100) |
| 10 | POST | `/suppliers` | API User + external system | Create supplier |
| 11 | PATCH | `/suppliers/{external_id}` | API User + external system | Update supplier |
| 12 | GET | `/lots` | API User | List lots/serials (max 100) |
| 13 | POST | `/lots` | API User + external system | Create lot/serial |
| 14 | PATCH | `/lots/{external_id}` | API User + external system | Update lot/serial |
| 15 | POST | `/inventory-adjustments` | API User + external system | Stage initial inventory count (never auto-applied) |
| 16 | GET | `/receipts/{external_reference}` | API User + external system | Receipt status lookup |
| 17 | POST | `/receipts` | API User (+ external system for the `lines[]` form) | Create receipt (two schemas — see below) |
| 18 | POST | `/receipts/{receipt_id}/validate` | API User | Validate/confirm a draft receipt |
| 19 | GET | `/dispatches/{external_reference}` | API User + external system | Dispatch status lookup |
| 20 | POST | `/dispatches` | API User (+ external system for the `lines[]` form) | Create dispatch (two schemas) |
| 21 | POST | `/dispatches/{dispatch_id}/validate` | API User | Validate/confirm a draft dispatch |

**Two request schemas for receipts/dispatches, both still live (backward compatible):**
- **Legacy** (`products: [...]`): raw Odoo integer IDs (`warehouse_id`, `supplier_id`/`customer_id`,
  `product_id`), no lot/UOM support, no external-system resolution required for creation itself.
- **WMS-first** (`lines: [...]`): every reference (warehouse, supplier, product, unit, lot)
  addressed by the caller's own external IDs; requires a bound external system.
  A request body must use exactly one of `products` or `lines`, never both (`400` otherwise).

---

## C. Request and response formats

All responses share the shape `{"status": "success"|"error", ...}`. All error responses are
`{"status": "error", "message": "..."}` with an appropriate HTTP status code.

### 1. `GET /health`
No auth. Response `200`:
```json
{"status": "success", "service": "AgriWare Connector", "api_version": "1.0", "message": "AgriWare API is running"}
```

### 2. `GET /products`
Response `200`:
```json
{"status": "success", "count": 3, "products": [
  {"id": 12, "name": "Urea Fertilizer 50kg", "default_code": "UREA-50", "barcode": "", "active": true}
]}
```

### 3. `POST /products`
Request body — allowed fields: `name` (required), `default_code`, `barcode`, `description`,
`unit`, plus `external_id` (required, ≤128 chars):
```json
{"external_id": "WMS-PRD-001", "name": "Urea Fertilizer 50kg", "default_code": "UREA-50", "unit": "kg"}
```
- `unit` resolves via an admin-configured `agriware.uom.mapping` first, falling back to a small
  hardcoded set: `kg, g, ton/t, l/liter/litre, unit/units/pcs`. Omitted → defaults to `unit`.
- Response `201`:
```json
{"status": "success", "product_id": 45, "external_id": "WMS-PRD-001", "name": "Urea Fertilizer 50kg"}
```
- `409` if `external_id` already mapped (returns the existing `product_id`).

### 4. `PATCH /products/{external_id}`
Allowed fields: `name`, `default_code`, `barcode`, `description` (not `unit` — changing a
product's UOM after creation is not exposed at all). `404` if no product is mapped for that
external_id.

### 5. `GET /warehouses`
```json
{"status": "success", "count": 1, "warehouses": [
  {"id": 2, "name": "Main Warehouse", "code": "WH1", "company_id": 1, "company_name": "My Company"}
]}
```

### 6. `POST /warehouses`
Allowed fields: `name` (required), `code` (required, ≤5 chars — Odoo core's own
`stock.warehouse.code` is `Char(size=5)`), `external_id` (required). `422` if code too long, `409`
if name or code already in use for the company.

### 7. `PATCH /warehouses/{external_id}`
Allowed field: `name` only. Sending `code` is explicitly rejected with `400` ("code cannot be
changed once a warehouse is created").

### 8. `GET /inventory`
```json
{"status": "success", "count": 2, "inventory": [
  {"product_id": 12, "product_name": "Urea Fertilizer 50kg", "location_id": 8,
   "location_name": "Main Warehouse/Stock", "quantity": 500.0, "reserved_quantity": 0.0, "unit": "kg"}
]}
```
Only internal locations with non-zero quantity are returned.

### 9. `GET /suppliers`
```json
{"status": "success", "count": 1, "suppliers": [
  {"id": 7, "name": "Acme Fertilizer Co", "email": "", "phone": "", "country_code": "CI"}
]}
```

### 10. `POST /suppliers`
Allowed fields: `name` (required), `email`, `phone`, `street`, `city`, `country_code` (ISO
3166-1 alpha-2 — unrecognized code → `400`), `external_id` (required). Created supplier is scoped
to the resolving company (never a shared/global partner).

### 11. `PATCH /suppliers/{external_id}`
Same field list, all optional. Refuses (`409`) to modify a shared (`company_id=False`) partner
record even if one happens to be mapped.

### 12. `GET /lots`
```json
{"status": "success", "count": 1, "lots": [
  {"id": 3, "name": "LOT-2026-001", "product_id": 12, "ref": ""}
]}
```

### 13. `POST /lots`
Allowed fields: `name` (required), `ref`, `note`, plus `external_id` and `product_external_id`
(both required). `422` if the product isn't configured for lot/serial tracking. `404` if the
referenced product external_id doesn't resolve.

### 14. `PATCH /lots/{external_id}`
Allowed fields: `name`, `ref`, `note`. `409` if the lot already has recorded stock movements and
`name` is being changed (traceability protection).

### 15. `POST /inventory-adjustments`
```json
{
  "external_reference": "WMS-INV-2026-001",
  "warehouse_external_id": "WMS-WH-001",
  "lines": [
    {"product_external_id": "WMS-PRD-001", "quantity": 500, "unit": "kg"},
    {"product_external_id": "WMS-PRD-002", "quantity": 1, "unit": "unit", "lot_external_id": "WMS-LOT-001"}
  ]
}
```
- Idempotent: an identical retry (same `external_reference` + same canonical content hash) returns
  the existing import `200`. A retry with the **same reference but different content** → `409`.
- **Never applies anything to real stock.** Response `201` includes, per line, the WMS-reported
  quantity, Odoo's current on-hand quantity, and the computed difference — for human review only:
```json
{"status": "success", "import_id": 9, "external_reference": "WMS-INV-2026-001", "state": "pending",
 "lines": [{"product_external_id": "WMS-PRD-001", "reported_quantity": 500.0,
            "current_odoo_quantity": 480.0, "proposed_difference": 20.0}]}
```
- An authorized `Inventory Manager` must still apply any approved difference manually, inside
  Odoo's own Inventory Adjustment screen. This endpoint never creates a stock move or adjusts a
  quant by itself.

### 16. `GET /receipts/{external_reference}`
```json
{"status": "success", "external_reference": "WMS-REC-001", "receipt_id": 55,
 "transaction_type": "receipt", "state": "done", "warehouse_id": 2,
 "created_at": "2026-10-20T09:00:00", "validated_at": "2026-10-20T09:05:00"}
```
`404` if no matching `agriware.wms.transaction` row exists for the authenticated external system.

### 17. `POST /receipts`

**WMS-first schema** (`lines`):
```json
{
  "external_reference": "WMS-REC-001",
  "warehouse_external_id": "WMS-WH-001",
  "supplier_external_id": "WMS-SUP-001",
  "lines": [{"product_external_id": "WMS-PRD-001", "quantity": 500, "unit": "kg"}]
}
```
Response `201`:
```json
{"status": "success", "receipt_id": 55, "receipt_reference": "WH1/IN/00012",
 "external_reference": "WMS-REC-001", "state": "draft",
 "lines": [{"product_external_id": "WMS-PRD-001", "product_id": 12, "quantity": 500.0, "lot_external_id": null}]}
```

**Legacy schema** (`products`, raw integer IDs):
```json
{"external_reference": "AGRIWARE-RCPT-001", "warehouse_id": 2, "supplier_id": 7,
 "products": [{"product_id": 12, "quantity": 500}]}
```
Both schemas: idempotent on `external_reference` (`200` if identical retry, `409` if conflicting).
A product line requiring lot/serial tracking that omits `lot_external_id` → `422`.

### 18. `POST /receipts/{receipt_id}/validate`
```json
{"external_reference": "WMS-REC-001",
 "received_quantities": [{"product_id": 12, "quantity": 500, "lot_external_id": "WMS-LOT-001"}]}
```
- `receipt_id` is the **integer** id from the create response (not the external reference).
- `received_quantities` must name every product on the receipt exactly once; quantities must
  match the expected quantity exactly (no partial receipts yet).
- `409` if already validated, cancelled, or not in `draft`; `409` on external-reference mismatch.
- Only receipts this module itself created are accepted (recognized by the legacy
  `AGRIWARE-RCPT-` prefix or by having a matching `agriware.wms.transaction` row) — `403`
  otherwise ("Receipt is not managed by AgriWare").
- Response `200`: `{"status": "success", "receipt_id": 55, "receipt_reference": "WH1/IN/00012", "external_reference": "WMS-REC-001", "state": "done"}`

### 19. `GET /dispatches/{external_reference}`
Identical shape to receipt status, with `"transaction_type": "dispatch"` and `dispatch_id`.

### 20. `POST /dispatches`
Same two-schema pattern as receipts. **Key difference: the WMS-first schema has no
customer/partner field at all** — only `external_reference`, `warehouse_external_id`, `lines`.
(The legacy schema still takes `customer_id`.)

### 21. `POST /dispatches/{dispatch_id}/validate`
Same pattern as receipt validation, with `dispatched_quantities` instead of `received_quantities`.

---

## D. External system / permissions summary

| Requirement | Detail |
|---|---|
| Odoo security group | `AgriWare API User` (`agriware_connector.group_agriware_api_user`) |
| Implied access | `stock.group_stock_user` (Inventory read/write) |
| Extra explicit access | `product.product` / `product.template` create + write |
| External-system binding | Set once at key-generation time; required for all POST/PATCH endpoints and both transaction-status GETs; **not** required for the plain list GETs |
| Multi-company isolation | Every AgriWare model is scoped by `ir.rule` to `company_id in company_ids`; a bound key can only ever resolve mappings within its own company |
| Credential storage | Raw API key is shown once at generation and never stored — not by Odoo, not by this module, not recoverable by anyone afterward including an administrator |

---

## E. Recommended connectivity test

**Use `GET /health`** as the first, zero-risk connectivity check from COOL AGRISTOCK:

```
GET http://<host>:8069/agriware/api/v1/health
```
No headers required at all (public route) beyond whatever `X-Odoo-Database` the deployment needs
for routing (see note below) — confirms the Odoo instance is up and this module is loaded, before
ever touching an API key.

**Second step, to validate the actual key once `/health` succeeds:**
```
GET /agriware/api/v1/products
Authorization: Bearer <api_key>
X-Odoo-Database: <database_name>
```
A `200` with a (possibly empty) `products` list confirms the key authenticates and has the API
User role. A `403` with "Access denied" means the key's user lacks the group; a `401` means the
key itself is invalid/expired/revoked.

**Local server status, checked directly in this session:** the Odoo server at
`http://127.0.0.1:8069` is reachable (confirmed via `curl`), but **this Docker environment has no
`dbfilter` configured and hosts 4 databases** (`postgres`, `agriwareodoo`, `agriware_mkt_full`,
`cool_agristock_customer`), so a request with no database hint returns `404 "No database is
selected"`. Adding `X-Odoo-Database: <name>` resolves it — confirmed directly against
`cool_agristock_customer`, which returned `/health`'s success payload once that header was added.

**Already-configured test environment found in this session:** the `cool_agristock_customer`
database already has `agriware_connector` installed at the exact released version `19.0.2.0.0`,
and already has a real, active, non-expiring API key named **"COOL AGRISTOCK Integration"**,
bound to an external system named **"COOL AGRISTOCK"** (code `cool_agristock`). Its integration
user correctly holds the `AgriWare API User` group. This key is therefore valid for every endpoint
in this report, including every write endpoint that requires an external-system binding — this
answers task item 7 directly: **yes**, assuming the Laravel app is given the original raw key
value from whoever generated it (this session cannot retrieve or display it — see Section A).
If that raw value has been lost, a new key must be generated through the Odoo UI's "Generate API
Key" wizard, choosing **"COOL AGRISTOCK"** as the authorized external system so write endpoints
keep working identically.

---

## F. Instructions for implementing the Laravel API client

1. **HTTP client config.** Base URL `http://<odoo-host>:8069/agriware/api/v1`. Every request
   (except `/health`) needs both:
   ```
   Authorization: Bearer <AGRIWARE_API_KEY>
   X-Odoo-Database: <AGRIWARE_DB_NAME>
   Content-Type: application/json
   ```
   Store both as Laravel config/env values (`config/agriware.php`, `.env`:
   `AGRIWARE_BASE_URL`, `AGRIWARE_API_KEY`, `AGRIWARE_DB_NAME`) — never hardcode the key. Laravel's
   `Http::withToken()` facade maps directly onto this.

2. **Keep this entirely separate from the existing JSON-RPC accounting integration.** Nothing in
   AgriWare Connector touches `account.*` models or any JSON-RPC endpoint — it is a pure REST/HTTP
   module living at its own URL prefix. A new, dedicated service class/client (e.g.
   `App\Services\AgriWareClient`) alongside the existing accounting client, sharing no code path,
   is sufficient to guarantee zero interference.

3. **External-ID strategy.** Decide COOL AGRISTOCK's own external-ID scheme up front (e.g. its own
   primary keys, prefixed: `"CA-PRODUCT-123"`). Every create/update endpoint is keyed off this
   `external_id`, not Odoo's internal integer id — store the mapping back in COOL AGRISTOCK's own
   database if you need to reconcile later, since the Odoo-side mapping is scoped to the bound
   external system and isn't exposed as a bulk "list all my mappings" endpoint.

4. **Sync order matters.** Products, warehouses, and suppliers must exist (and be mapped) before a
   lot, receipt, or dispatch referencing them can be created — every endpoint resolves referenced
   external IDs and returns `404` if the referenced mapping doesn't exist yet.

5. **Idempotency.** Build retries around `external_reference`/`external_id`: a network timeout
   followed by a safe retry of the same POST with the same reference and identical body returns
   the original result (`200`/`409` for a true duplicate), never a second record. Don't invent new
   references on retry.

6. **Validation is a separate step.** Creating a receipt/dispatch only ever produces a Draft. A
   second call to `/receipts/{id}/validate` (or `/dispatches/{id}/validate`) is required to confirm
   it — using the **integer** id returned by the create call, not the external reference.

7. **Inventory imports are observational only.** `POST /inventory-adjustments` never changes Odoo
   stock. If COOL AGRISTOCK needs Odoo's stock corrected to match a physical count, that still
   requires a human to review the returned `proposed_difference` and apply it manually inside
   Odoo's Inventory Adjustment screen — do not build any Laravel-side automation that assumes this
   endpoint changes real inventory.

8. **Error handling.** Every error response is `{"status": "error", "message": "..."}`; map HTTP
   status codes directly: `400` client-side validation bug, `401` bad/expired key, `403`
   missing group or unbound external system, `404` referenced external_id doesn't exist yet, `409`
   duplicate/conflict (often recoverable by reading the included id and treating it as success),
   `422` semantically invalid (e.g. wrong UOM, missing required lot), `500` server-side failure
   (log and alert, don't retry blindly).

9. **UOM mapping.** If COOL AGRISTOCK's unit codes don't match AgriWare's small hardcoded set
   (`kg, g, ton/t, l/liter/litre, unit/units/pcs`), an administrator must configure an
   `agriware.uom.mapping` row inside Odoo (Settings) before the Laravel client can use that code —
   this cannot be done through the REST API itself.

10. **Known limitations to design around** (see also Section D of the earlier marketplace
    materials, unchanged): no pagination on list endpoints (hard-capped at 100 records — a larger
    COOL AGRISTOCK catalog needs either multiple scoped syncs or a future paginated endpoint, not
    yet available); no partial receipts/dispatches (quantities must match exactly); no per-warehouse
    access control (access is company-scoped only); no automatic/scheduled sync in either
    direction — Odoo never calls out to COOL AGRISTOCK, every exchange is client-initiated.

---

## Summary of what was and wasn't done in this session

- Read every controller and the authentication/mapping/UOM model files directly; no endpoint or
  field in this report was invented.
- Confirmed local server reachability and the exact database-selection requirement by making real,
  read-only HTTP requests against the running dev server.
- Found and inspected (metadata only — no key value, nothing written) an existing, already-bound,
  active API key in the `cool_agristock_customer` database that is valid for exactly this
  integration.
- **No file was edited. No commit, push, merge, or deploy of any kind was performed.**
