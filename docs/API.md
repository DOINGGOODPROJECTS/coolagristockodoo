# Cool Agristock API Reference

Complete technical reference for external WMS developers integrating with Cool Agristock.

## Contents

1. [API overview](#api-overview)
2. [Base URL](#base-url)
3. [API versioning](#api-versioning)
4. [Authentication](#authentication)
5. [Generating API keys](#generating-api-keys)
6. [API key expiration](#api-key-expiration)
7. [Never-expiring keys](#never-expiring-keys)
8. [API key revocation](#api-key-revocation)
9. [API key replacement](#api-key-replacement)
10. [API key permissions](#api-key-permissions)
11. [Company access restrictions](#company-access-restrictions)
12. [HTTP headers](#http-headers)
13. [JSON request formats](#json-request-formats)
14. [JSON response formats](#json-response-formats)
15. [Error handling](#error-handling)
16. [HTTP status codes](#http-status-codes)
17. [Duplicate transaction protection](#duplicate-transaction-protection)
18. [Integration examples](#integration-examples)
19. [Security best practices](#security-best-practices)
20. [Known limitations](#known-limitations)
21. [Endpoints](#endpoints)

## API overview

Cool Agristock exposes a REST API on top of Odoo 19's Inventory app. An external WMS calls
this API to read product, warehouse, and inventory data, and to create and validate incoming
receipts and outgoing dispatches. Every request is initiated by the external WMS — Odoo never
calls out to the WMS (there is no webhook or callback mechanism in either direction beyond the
WMS's own requests and Odoo's responses to them).

```text
External WMS  --(HTTPS + API key)-->  Cool Agristock  --(Odoo ORM)-->  Odoo 19  -->  PostgreSQL
```

The connector translates WMS actions into standard Odoo stock operations (`stock.picking` /
`stock.move`): an incoming delivery becomes a **receipt**, an outgoing delivery becomes a
**dispatch**. Both follow a two-step lifecycle — **create** (draft) then **validate** (confirms the
operation in Odoo's stock workflow).

## Base URL

All endpoints are rooted at `/cool_agristock/api/v1`. In local development this is
`http://localhost:8069/cool_agristock/api/v1`. In this document, `YOUR_ODOO_URL` stands in for your
instance's actual base URL.

## API versioning

The API is versioned via the URL path segment `v1`. The health check endpoint's response also
reports the version explicitly (`"api_version": "1.0"`). There is currently only one version;
no deprecation or version-negotiation mechanism exists yet.

## Authentication

| Endpoint type | `auth` mode | Requirement |
|---|---|---|
| Health check | `public` | None |
| All other endpoints | `bearer` | `Authorization: Bearer <odoo-api-key>` header |

The Bearer token is a real **Odoo API key** — not a separate Cool Agristock-specific credential format.
Odoo's HTTP layer validates the key *before* any Cool Agristock controller code runs. If the header is
missing, malformed, or the key is invalid/revoked/expired, Odoo itself returns a **plain-text HTML
401 response** (not JSON):

```http
HTTP/1.1 401 UNAUTHORIZED
Content-Type: text/html

<!doctype html>
<html lang=en>
<title>401 Unauthorized</title>
<h1>Unauthorized</h1>
<p>User not authenticated, use an API Key with a Bearer Authorization header.</p>
```

Clients must therefore check the HTTP status code first and only attempt to parse the body as JSON
when the status code indicates a controller-level response.

## Generating API keys

Keys are generated inside Odoo's UI, not via a REST call — there is no "create API key" HTTP
endpoint. A user in the **Cool Agristock Administrator** group opens **Cool Agristock → API
Management → Generate API Key**, supplies an integration name, and chooses an expiration date or
**Never Expires**. The raw key is shown exactly once, immediately, in a dialog; it cannot be
retrieved again afterward, and only a salted hash is ever stored (matching how Odoo stores all API
keys). Store it in the external system's secret manager, never in source control.

This is a narrower requirement than Odoo's own built-in self-service key management (which is
normally limited to managing your own keys, and reserves "never expires" for Odoo System
Administrators): Cool Agristock's generate/revoke/replace actions run with elevated privileges
internally, but only after verifying the caller holds **Cool Agristock Administrator** for the specific
company the key belongs to.

## API key expiration

If an expiration date is set, Odoo's own API key infrastructure rejects the key at authentication
time once that date passes — this check happens in the database query that validates the Bearer
token, before any Cool Agristock code runs, so it cannot be bypassed by this module's own logic. No
separate expiry check exists or is needed in the controllers.

## Never-expiring keys

A key created with no expiration date remains valid until someone explicitly revokes it. There is
no automatic expiry for such keys.

## API key revocation

**Cool Agristock → API Management → API Keys**, then **Revoke** on the relevant row. Revocation
deletes the underlying Odoo API key record immediately; the very next request using that key fails
authentication, with no propagation delay or caching involved.

## API key replacement

Clicking **Create New** on an expired or revoked key's row opens the generate wizard pre-filled
with that key's integration name and expiration policy (date-based or Never Expires), so issuing a
replacement doesn't require re-entering those details. The old and new keys are entirely
independent credentials; the old one stays revoked/expired even after a replacement is issued.

## API key permissions

A generated key authenticates as a dedicated, password-less Odoo user (one per company), which
Odoo creates automatically the first time a key is generated for that company. That user belongs to
the **Cool Agristock API User** group and nothing else — it has exactly the permissions documented in
[Authorization](#authorization) below, no more. It cannot log in interactively (it has no usable
password), so the key is the only way to act as that identity.

## Authorization

Once authenticated, every non-public endpoint additionally requires the authenticated user to
belong to the **Cool Agristock API User** group (`cool_agristock.group_cool_agristock_api_user`), or a
group that implies it (**Cool Agristock Administrator**). This check happens inside the controller, so a
valid API key alone is **not** sufficient — the key's owning user must also carry the group.
Requests from an authenticated user lacking the group receive a JSON 403 response:

```json
{"status": "error", "message": "Access denied: Cool Agristock API User role required"}
```

## Company access restrictions

Record-level access is scoped to the warehouses/companies the authenticated user has access to
(`warehouse.company_id in env.companies.ids`); product/partner lookups are similarly company-scoped
where relevant. Separately, the `cool_agristock.api.key` records themselves are protected by a
PostgreSQL-level record rule restricting each company's administrators to their own company's keys
— one company's Cool Agristock Administrators can never view, generate for, or revoke another company's
keys. There is currently no per-warehouse allow-list within a company; see
[Known limitations](#known-limitations).

## HTTP headers

| Header | Direction | Notes |
|---|---|---|
| `Authorization: Bearer <key>` | Request | Required on every endpoint except the health check |
| `Content-Type: application/json` | Request | Required on `POST` endpoints with a JSON body |
| `Content-Type: application/json` | Response | All controller-level responses; the framework-level 401 is `text/html` instead |

## JSON request formats

`POST` endpoints expect a single JSON object as the request body (not an array, and not
form-encoded data). Malformed JSON, or a JSON value that isn't an object, is rejected with `400`.
Field-level constraints are documented per endpoint below.

## JSON response formats

All controller-level JSON responses (everything except the framework-level 401) share the shape:

```json
{"status": "success", ...}
```
or
```json
{"status": "error", "message": "..."}
```

## Error handling

Clients should treat `status: "error"` responses as authoritative and surface `message` to an
operator; they should not attempt to infer the cause from the HTTP status code alone, since several
conditions can share a code (e.g. `409` covers duplicate references, state mismatches, and quantity
mismatches, each with a different `message`). On `5xx`-free success (`200`/`201`), the controller's
database transaction has already committed by the time the response is returned.

## HTTP status codes

| Code | Meaning | Produced by |
|---|---|---|
| 200 | Success (read, or validate) | Controller |
| 201 | Resource created | Controller (`POST /receipts`, `POST /dispatches`) |
| 400 | Malformed JSON or invalid/missing field | Controller |
| 401 | Missing, malformed, invalid, expired, or revoked API key | Odoo framework (before controller runs) |
| 403 | Authenticated but not authorized, or action out of scope for this API | Controller |
| 404 | Referenced record (warehouse, partner, product, receipt, dispatch) not found | Controller |
| 409 | Conflict — duplicate reference, state mismatch, quantity mismatch, concurrent lock | Controller |
| 500 | Unexpected server-side error (logged, transaction rolled back) | Controller |

## Duplicate transaction protection

`external_reference` is the idempotency key the WMS assigns to a receipt or dispatch (stored as the
Odoo picking's `origin`). Concurrent requests for the same `external_reference` are serialized with
a PostgreSQL transaction-scoped advisory lock, so only one receipt (or dispatch) is ever created
even if two identical requests arrive at the same time; the second resolves to a `409` response
that includes the existing record's id. To validate a receipt or dispatch, its `external_reference`
**must** use the matching prefix:

| Operation | Required prefix |
|---|---|
| Receipt | `COOL_AGRISTOCK-RCPT-` |
| Dispatch | `COOL_AGRISTOCK-DISP-` |

This prevents the API from being used to validate draft stock operations that were not created by
Cool Agristock (e.g. pickings created manually in the Odoo UI). A validate call against a reference
without the correct prefix returns `403` with `"<Receipt|Dispatch> is not managed by Cool Agristock"`.

## Integration examples

A minimal end-to-end flow, using `YOUR_ODOO_URL` and `YOUR_API_KEY` as placeholders for your real
instance URL and a key generated per [Generating API keys](#generating-api-keys). **Never commit
real values for these placeholders.**

**1. Check the API is reachable (no authentication needed):**

```bash
curl -s YOUR_ODOO_URL/cool_agristock/api/v1/health
```
```json
{"status": "success", "service": "Cool Agristock", "api_version": "1.0", "message": "Cool Agristock API is running"}
```

**2. Look up a product to receive:**

```bash
curl -s YOUR_ODOO_URL/cool_agristock/api/v1/products \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**3. Create a receipt for that product:**

```bash
curl -s -X POST YOUR_ODOO_URL/cool_agristock/api/v1/receipts \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "external_reference": "COOL_AGRISTOCK-RCPT-00042",
        "warehouse_id": 1,
        "supplier_id": 37,
        "products": [{"product_id": 14, "quantity": 500}]
      }'
```
```json
{"status": "success", "receipt_id": 102, "receipt_reference": "WH/IN/00042", "external_reference": "COOL_AGRISTOCK-RCPT-00042", "state": "draft"}
```

**4. Once the goods are physically counted, validate the receipt:**

```bash
curl -s -X POST YOUR_ODOO_URL/cool_agristock/api/v1/receipts/102/validate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "external_reference": "COOL_AGRISTOCK-RCPT-00042",
        "received_quantities": [{"product_id": 14, "quantity": 500}]
      }'
```
```json
{"status": "success", "receipt_id": 102, "receipt_reference": "WH/IN/00042", "external_reference": "COOL_AGRISTOCK-RCPT-00042", "state": "done"}
```

Dispatches follow the same create-then-validate pattern; see
[`POST /dispatches`](#7-post-cool_agristockapiv1dispatches) and
[`POST /dispatches/{id}/validate`](#8-post-cool_agristockapiv1dispatchesdispatch_idvalidate) below. Some
WMS platforms will need custom integration development to speak this API natively — see the
project [README](../README.md#free-software-and-paid-services).

## Security best practices

- Store generated keys in the external system's secret manager; never in source control, logs, or
  plaintext configuration.
- Prefer an expiration date over Never Expires unless the integration genuinely needs a long-lived
  credential.
- Revoke a key immediately if you suspect it has leaked, then issue a replacement.
- Run Cool Agristock behind HTTPS in any environment beyond local development — Bearer tokens
  sent over plain HTTP are visible on the network path.
- Grant the **Cool Agristock Administrator** group only to business users who should be trusted to
  generate and revoke API credentials.
- Choose `external_reference` values with the correct `COOL_AGRISTOCK-RCPT-`/`COOL_AGRISTOCK-DISP-` prefix
  from the start if you intend to validate that record later.

## Known limitations

- No pagination: list endpoints (`products`, `warehouses`, `inventory`) hard-cap at 100 records,
  with no offset/cursor parameter.
- No per-warehouse access control: any user in the Cool Agristock API User group can act on any warehouse
  within their allowed companies — there is no way to restrict one integration identity to a
  specific warehouse subset.
- Partial receipts and partial dispatches are not supported; quantities must match exactly.
- **Lot/serial-tracked products are supported as of Phase F.** `POST`/`GET`/`PATCH
  /cool_agristock/api/v1/lots` creates and resolves native `stock.lot` records, and both receipt and
  dispatch validation accept an optional `lot_external_id` per line — see
  [LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md) for the full reference. A tracked
  product with **no** `lot_external_id` on its line is still rejected with `409`
  (`"Lot or serial tracking is not supported yet"`) — that message is historical wording for an
  unchanged case, not evidence the feature is missing.
- Multiple move lines for the same product on one receipt are not supported.
- No automatic or scheduled synchronization: every request is initiated by the external WMS; there
  is no polling, cron job, or background task in this module.
- No bidirectional synchronization: Cool Agristock never calls out to the WMS.
- No built-in WMS-specific adapters: this is one generic REST API, not a library of per-WMS
  connectors.

## Endpoints

### 1. `GET /cool_agristock/api/v1/health`

Public health check. No authentication required.

**Response 200**
```json
{
  "status": "success",
  "service": "Cool Agristock",
  "api_version": "1.0",
  "message": "Cool Agristock API is running"
}
```

---

### 2. `GET /cool_agristock/api/v1/products`

Returns up to 100 products, ordered by id.

**Auth:** Bearer API key + Cool Agristock API User group.

**Response 200**
```json
{
  "status": "success",
  "count": 2,
  "products": [
    {"id": 14, "name": "Urea 50kg Bag", "default_code": "FERT-UREA-50", "barcode": "6161100000012", "active": true},
    {"id": 15, "name": "Maize Seed 25kg Bag", "default_code": "SEED-MAIZE-25", "barcode": "", "active": true}
  ]
}
```

**Errors:** `403` (not authorized), `500` (unexpected failure).

---

### 3. `GET /cool_agristock/api/v1/warehouses`

Returns up to 100 warehouses, ordered by id.

**Auth:** Bearer API key + Cool Agristock API User group.

**Response 200**
```json
{
  "status": "success",
  "count": 1,
  "warehouses": [
    {"id": 1, "name": "Main Warehouse", "code": "WH", "company_id": 1, "company_name": "My Company"}
  ]
}
```

**Errors:** `403`, `500`.

---

### 4. `GET /cool_agristock/api/v1/inventory`

Returns up to 100 non-zero stock quants in internal locations, ordered by id.

**Auth:** Bearer API key + Cool Agristock API User group.

**Response 200**
```json
{
  "status": "success",
  "count": 1,
  "inventory": [
    {
      "product_id": 14,
      "product_name": "Urea 50kg Bag",
      "location_id": 8,
      "location_name": "Main Warehouse/Stock",
      "quantity": 420.0,
      "reserved_quantity": 0.0,
      "unit": "kg"
    }
  ]
}
```

**Errors:** `403`, `500`.

---

### 5. `POST /cool_agristock/api/v1/receipts`

Creates a draft incoming stock receipt (`stock.picking` of the warehouse's incoming type).

**Auth:** Bearer API key + Cool Agristock API User group + `create` rights on `stock.picking`/`stock.move`.

**Request body**
```json
{
  "external_reference": "COOL_AGRISTOCK-RCPT-00042",
  "warehouse_id": 1,
  "supplier_id": 37,
  "products": [
    {"product_id": 14, "quantity": 500}
  ]
}
```

| Field | Type | Constraints |
|---|---|---|
| `external_reference` | string | Required, 1–128 chars, must use the `COOL_AGRISTOCK-RCPT-` prefix if it will later be validated |
| `warehouse_id` | integer | Required, > 0, must resolve to a warehouse in the caller's companies |
| `supplier_id` | integer | Required, > 0, must resolve to an existing partner |
| `products` | array | Required, 1–100 entries |
| `products[].product_id` | integer | Required, > 0, must be a stock-tracked (`consu` + storable) product |
| `products[].quantity` | number | Required, `0 < quantity <= 1,000,000,000` |

**Response 201**
```json
{
  "status": "success",
  "receipt_id": 102,
  "receipt_reference": "WH/IN/00042",
  "external_reference": "COOL_AGRISTOCK-RCPT-00042",
  "state": "draft"
}
```

**Errors**

| Code | Condition |
|---|---|
| 400 | Invalid JSON / not an object / invalid `external_reference`, `warehouse_id`, `supplier_id`, `products`, or a product line / product not stock-tracked |
| 403 | Not authorized, or insufficient Odoo create rights |
| 404 | Warehouse, supplier, or product not found |
| 409 | `external_reference` already used for this warehouse's incoming operations — response includes the existing `receipt_id` |
| 500 | Unexpected failure (transaction rolled back) |

Concurrent requests for the same `external_reference` are serialized with a PostgreSQL
transaction-scoped advisory lock, so only one receipt is ever created even if two identical
requests arrive at the same time; the second resolves to the `409` duplicate response.

---

### 6. `POST /cool_agristock/api/v1/receipts/{receipt_id}/validate`

Confirms a draft receipt and records received quantities, then validates it in Odoo.

**Auth:** Bearer API key + Cool Agristock API User group + `read`/`write` rights on `stock.picking`, `write` on `stock.move`.

**Request body**
```json
{
  "external_reference": "COOL_AGRISTOCK-RCPT-00042",
  "received_quantities": [
    {"product_id": 14, "quantity": 500}
  ]
}
```

| Field | Type | Constraints |
|---|---|---|
| `external_reference` | string | Required, must match the receipt's stored origin exactly, must use `COOL_AGRISTOCK-RCPT-` prefix |
| `received_quantities` | array | Required, 1–100 entries, no duplicate `product_id` |
| `received_quantities[].product_id` | integer | Required, > 0 |
| `received_quantities[].quantity` | number | Required, finite, `0 < quantity <= 1,000,000,000` |
| `received_quantities[].lot_external_id` | string | Optional (Phase F). Required if the product is lot/serial-tracked — resolved via the same external-ID mapping as `POST /lots`. |

The set of products in `received_quantities` must exactly match the receipt's move lines, and each
quantity must exactly match the expected quantity (partial receipts are not yet supported). A
lot/serial-tracked product line is accepted when it names the exact lot via `lot_external_id`
(Phase F); a tracked product with no `lot_external_id` is rejected with `409`.

**Response 200**
```json
{
  "status": "success",
  "receipt_id": 102,
  "receipt_reference": "WH/IN/00042",
  "external_reference": "COOL_AGRISTOCK-RCPT-00042",
  "state": "done"
}
```

**Errors**

| Code | Condition |
|---|---|
| 400 | Invalid JSON / invalid fields / receipt has no active lines / products don't match receipt |
| 403 | Not authorized / insufficient rights / `external_reference` lacks the `COOL_AGRISTOCK-RCPT-` prefix |
| 404 | Receipt not found (or not an incoming operation in the caller's companies); or unknown `lot_external_id` |
| 409 | `external_reference` mismatch, receipt already validated/cancelled/not in draft, quantity mismatch, tracked product with no `lot_external_id`, or Odoo rejects the validation |
| 422 | `lot_external_id` resolves to a lot belonging to a different product |
| 500 | Unexpected failure (transaction rolled back) |

The receipt row is locked (`SELECT ... FOR UPDATE NOWAIT`) for the duration of validation, so two
concurrent validate calls on the same receipt cannot both succeed.

---

### 7. `POST /cool_agristock/api/v1/dispatches`

Creates a draft outgoing stock dispatch (`stock.picking` of the warehouse's outgoing type).

**Auth:** Bearer API key + Cool Agristock API User group + `create` rights on `stock.picking`/`stock.move`.

**Request body**
```json
{
  "external_reference": "COOL_AGRISTOCK-DISP-00017",
  "warehouse_id": 1,
  "customer_id": 52,
  "products": [
    {"product_id": 14, "quantity": 120}
  ]
}
```

| Field | Type | Constraints |
|---|---|---|
| `external_reference` | string | Required, 1–128 chars, must use `COOL_AGRISTOCK-DISP-` prefix if it will later be validated |
| `warehouse_id` | integer | Required, > 0, must resolve to a warehouse in the caller's companies |
| `customer_id` | integer | Required, > 0, must resolve to an existing partner |
| `products` | array | Required, 1–100 entries, no duplicate `product_id` |
| `products[].product_id` | integer | Required, > 0, must be a stock-tracked product visible to the warehouse's company |
| `products[].quantity` | number | Required, finite, `0 < quantity <= 1,000,000,000` |

**Response 201**
```json
{
  "status": "success",
  "dispatch_id": 58,
  "dispatch_reference": "WH/OUT/00017",
  "external_reference": "COOL_AGRISTOCK-DISP-00017",
  "state": "draft"
}
```

**Errors:** same pattern as receipts creation (400 / 403 / 404 / 409 / 500), using `"dispatch_id"`
instead of `"receipt_id"` in the 409 duplicate payload. Duplicate creation is protected by the same
transaction-scoped advisory lock.

---

### 8. `POST /cool_agristock/api/v1/dispatches/{dispatch_id}/validate`

Confirms a draft dispatch, reserves stock, records picked quantities, and validates it.

**Auth:** Bearer API key + Cool Agristock API User group + `read`/`write` rights on `stock.picking` and `stock.move`.

**Request body**
```json
{
  "external_reference": "COOL_AGRISTOCK-DISP-00017",
  "dispatched_quantities": [
    {"product_id": 14, "quantity": 120}
  ]
}
```

| Field | Type | Constraints |
|---|---|---|
| `external_reference` | string | Required, must match the dispatch's stored origin exactly, must use `COOL_AGRISTOCK-DISP-` prefix |
| `dispatched_quantities` | array | Required, 1–100 entries, no duplicate `product_id` |
| `dispatched_quantities[].product_id` | integer | Required, > 0 |
| `dispatched_quantities[].quantity` | number | Required, finite, `0 < quantity <= 1,000,000,000` |
| `dispatched_quantities[].lot_external_id` | string | Optional (Phase F). Required if the product is lot/serial-tracked. The named lot is reserved specifically — never a different lot of the same product, even if Odoo's own removal strategy would otherwise have picked one. |

Constraints: exact quantity match only (no partial dispatch); a lot/serial-tracked product line is
accepted when it names the exact lot via `lot_external_id` (Phase F), otherwise rejected; the
dispatch must be fully reserved before Odoo will validate it.

**Response 200**
```json
{
  "status": "success",
  "dispatch_id": 58,
  "dispatch_reference": "WH/OUT/00017",
  "external_reference": "COOL_AGRISTOCK-DISP-00017",
  "state": "done"
}
```

**Errors**

| Code | Condition |
|---|---|
| 400 | Invalid JSON / invalid fields / no active move lines |
| 403 | Not authorized / insufficient rights / `external_reference` lacks the `COOL_AGRISTOCK-DISP-` prefix |
| 404 | Dispatch not found (or not an outgoing operation in the caller's companies); or unknown `lot_external_id` |
| 409 | Lock unavailable (concurrent validation in progress), reference mismatch, state mismatch, product/quantity mismatch, tracked product with no `lot_external_id`, insufficient stock in the named lot, or Odoo rejects the validation |
| 422 | `lot_external_id` resolves to a lot belonging to a different product |
| 500 | Unexpected failure (transaction rolled back) |
