# WMS Integration Guide

This guide is for the developer configuring or building the connection between an existing
Warehouse Management System (WMS) and Odoo 19, via Cool Agristock. It explains the integration
model and walks through each supported operation with real request/response examples.

For the complete field-by-field API reference (every parameter, every error condition), see
[API.md](API.md). For the non-developer steps to install the module and generate a key inside
Odoo, see [INSTALLATION.md](INSTALLATION.md).

## Integration architecture

```text
+----------------+        HTTPS + Bearer token         +----------------------+
|  External WMS  |  ------------------------------->    |  Cool Agristock  |
|  (your system) |  <-------------------------------    |  (Odoo 19 module)    |
+----------------+     JSON request / JSON response      +----------------------+
                                                                    |
                                                              Odoo ORM
                                                                    v
                                                          +-------------------+
                                                          |  Odoo 19 Inventory |
                                                          |  (stock.picking,   |
                                                          |   stock.move, ...) |
                                                          +-------------------+
                                                                    |
                                                                    v
                                                           +---------------+
                                                           |  PostgreSQL   |
                                                           +---------------+
```

**Every request in this integration is initiated by your WMS.** Cool Agristock exposes a REST
API that your system calls — it never calls out to your WMS. There is no webhook, callback, or
scheduled push of data in either direction. If your WMS needs up-to-date product, warehouse, or
inventory data, your WMS must call the relevant `GET` endpoint again whenever it needs fresh data
(see [Product synchronization](#product-synchronization) below) — Cool Agristock does not run
any polling, cron job, or background task of its own.

## API base URL

All endpoints are rooted at:

```text
https://YOUR_ODOO_URL/cool_agristock/api/v1
```

Replace `YOUR_ODOO_URL` with your actual Odoo instance's address (e.g.
`https://your-company.odoo.com` or your self-hosted domain).

## API versioning

The version is part of the URL path (`v1`). There is currently only one version; no
deprecation/negotiation mechanism exists. The health check endpoint also reports the version
explicitly in its response body (`"api_version": "1.0"`).

## Authentication

Every endpoint except the health check requires an `Authorization: Bearer <key>` header, where
`<key>` is a real Odoo API key generated through **Cool Agristock → API Management → Generate
API Key** inside Odoo (see [INSTALLATION.md](INSTALLATION.md)). There is no separate
Cool Agristock-specific credential or OAuth flow — it is Odoo's own API key mechanism.

Odoo validates the key **before** any Cool Agristock code runs. An invalid, missing, expired, or revoked
key gets a plain-text HTML `401` response, not JSON:

```http
HTTP/1.1 401 UNAUTHORIZED
Content-Type: text/html

<!doctype html>
<html lang=en>
<title>401 Unauthorized</title>
<h1>Unauthorized</h1>
<p>User not authenticated, use an API Key with a Bearer Authorization header.</p>
```

Your integration code must check the HTTP status code before attempting to parse the response body
as JSON.

Beyond a valid key, the key's underlying account must also carry the **Cool Agristock API User** role.
Keys generated through the wizard already have this; if you ever see
`{"status": "error", "message": "Access denied: Cool Agristock API User role required"}`, the key or its
account was altered outside the normal generation flow.

## Required HTTP headers

| Header | Applies to | Value |
|---|---|---|
| `Authorization` | Every endpoint except `/health` | `Bearer <your-api-key>` |
| `Content-Type` | Every `POST` request | `application/json` |

## Supported REST endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/cool_agristock/api/v1/health` | Confirm the API is reachable (no auth) |
| GET | `/cool_agristock/api/v1/products` | Retrieve products |
| GET | `/cool_agristock/api/v1/warehouses` | Retrieve warehouses |
| GET | `/cool_agristock/api/v1/inventory` | Retrieve on-hand inventory |
| POST | `/cool_agristock/api/v1/receipts` | Create a draft incoming receipt |
| POST | `/cool_agristock/api/v1/receipts/{id}/validate` | Confirm a receipt |
| POST | `/cool_agristock/api/v1/dispatches` | Create a draft outgoing dispatch |
| POST | `/cool_agristock/api/v1/dispatches/{id}/validate` | Confirm a dispatch |

All list endpoints (`products`, `warehouses`, `inventory`) return at most 100 records per call —
there is currently no pagination parameter (see [Known limitations](#known-limitations)).

## Product synchronization

Call `GET /cool_agristock/api/v1/products` whenever your WMS needs an up-to-date product list — on
startup, on a schedule your WMS controls, or on demand before creating a receipt/dispatch. There is
no change-notification mechanism, so "synchronization" here means **your WMS polling this endpoint
on its own schedule**, not Cool Agristock pushing updates.

```bash
curl -s https://YOUR_ODOO_URL/cool_agristock/api/v1/products \
  -H "Authorization: Bearer YOUR_API_KEY"
```

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

Use `id` as the stable key when referencing a product in later receipt/dispatch calls.

## Warehouse information retrieval

```bash
curl -s https://YOUR_ODOO_URL/cool_agristock/api/v1/warehouses \
  -H "Authorization: Bearer YOUR_API_KEY"
```

```json
{
  "status": "success",
  "count": 1,
  "warehouses": [
    {"id": 1, "name": "Main Warehouse", "code": "WH", "company_id": 1, "company_name": "My Company"}
  ]
}
```

`warehouse_id` from this response is required when creating receipts and dispatches.

## Inventory retrieval

```bash
curl -s https://YOUR_ODOO_URL/cool_agristock/api/v1/inventory \
  -H "Authorization: Bearer YOUR_API_KEY"
```

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

Only non-zero quants in internal locations are returned.

## Receipt creation and validation

An incoming delivery is a **receipt**, modeled as an inbound `stock.picking`. It follows a
two-step **create, then validate** flow — create it in draft as soon as you know what's arriving,
then validate it once goods are physically counted in.

**1. Create the draft receipt:**

```bash
curl -s -X POST https://YOUR_ODOO_URL/cool_agristock/api/v1/receipts \
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

`external_reference` is a string **you** choose (1–128 chars); it must start with
`COOL_AGRISTOCK-RCPT-` if you intend to validate this receipt later (see
[Duplicate transaction protection](#duplicate-transaction-protection--idempotency)).

**2. Validate the receipt once goods are counted:**

```bash
curl -s -X POST https://YOUR_ODOO_URL/cool_agristock/api/v1/receipts/102/validate \
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

`received_quantities` must list exactly the same products as the draft receipt, with exactly
matching quantities — partial receipts are not yet supported (see
[Known limitations](#known-limitations)). **Lot/serial-tracked products are supported as of
Phase F** via an optional `lot_external_id` per line (resolved through the same external-ID
mapping `POST /lots` uses) — see
[LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md). A tracked product with no
`lot_external_id` on its line is still rejected with `409`.

## Dispatch creation and validation

An outgoing delivery is a **dispatch**, modeled as an outbound `stock.picking`, following the same
create-then-validate pattern.

**1. Create the draft dispatch:**

```bash
curl -s -X POST https://YOUR_ODOO_URL/cool_agristock/api/v1/dispatches \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "external_reference": "COOL_AGRISTOCK-DISP-00017",
        "warehouse_id": 1,
        "customer_id": 52,
        "products": [{"product_id": 14, "quantity": 120}]
      }'
```

```json
{"status": "success", "dispatch_id": 58, "dispatch_reference": "WH/OUT/00017", "external_reference": "COOL_AGRISTOCK-DISP-00017", "state": "draft"}
```

**2. Validate the dispatch once the goods are picked:**

```bash
curl -s -X POST https://YOUR_ODOO_URL/cool_agristock/api/v1/dispatches/58/validate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "external_reference": "COOL_AGRISTOCK-DISP-00017",
        "dispatched_quantities": [{"product_id": 14, "quantity": 120}]
      }'
```

```json
{"status": "success", "dispatch_id": 58, "dispatch_reference": "WH/OUT/00017", "external_reference": "COOL_AGRISTOCK-DISP-00017", "state": "done"}
```

Dispatch validation additionally requires the stock to be available/reservable; an under-stocked
dispatch resolves to a `409` rather than succeeding partially.

## Duplicate transaction protection / idempotency

`external_reference` is the idempotency key your WMS assigns. If two requests for the same
`external_reference` arrive concurrently (e.g. a retried request after a network timeout), Odoo
serializes them with a transaction-scoped PostgreSQL advisory lock — only one receipt or dispatch
is ever created. The second request receives a `409` response that includes the already-created
record's id, so your WMS can detect "this was already processed" instead of creating a duplicate:

```json
{"status": "error", "message": "A receipt with this external_reference already exists", "receipt_id": 102}
```

To validate a receipt or dispatch later, its `external_reference` **must** use the matching
prefix — `COOL_AGRISTOCK-RCPT-` for receipts, `COOL_AGRISTOCK-DISP-` for dispatches — or validation is rejected
with `403`. Choose your reference scheme with this in mind from the start.

## API error handling

Every controller-level JSON response has one of two shapes:

```json
{"status": "success", ...}
```
```json
{"status": "error", "message": "..."}
```

Your WMS should branch on `status`, and on error, surface `message` — don't try to infer the exact
cause purely from the HTTP status code, since one code can mean several things (e.g. `409` covers
duplicate references, state mismatches, and quantity mismatches, each with a different message).

| Code | Meaning |
|---|---|
| 200 | Success (read, or validate) |
| 201 | Resource created (`POST /receipts`, `POST /dispatches`) |
| 400 | Malformed JSON or an invalid/missing field |
| 401 | Missing, malformed, invalid, expired, or revoked API key (plain HTML, not JSON) |
| 403 | Authenticated but not authorized for this action |
| 404 | Referenced warehouse, partner, product, receipt, or dispatch not found |
| 409 | Conflict — duplicate reference, state mismatch, quantity mismatch, or concurrent lock |
| 500 | Unexpected server-side error (transaction rolled back) |

## Security recommendations

- Run your Odoo instance behind HTTPS for any environment beyond local development — a Bearer
  token sent over plain HTTP is visible to anyone on the network path.
- Store the API key in your WMS's own secret/credential manager, never in source control, logs, or
  a plaintext config file.
- Prefer a key with an expiration date over **Never Expires**, unless your integration genuinely
  needs a long-lived credential.
- Rotate (revoke + regenerate) the key immediately if you suspect it has leaked.
- Choose `external_reference` values with the correct prefix from the start if you'll need to
  validate that record later — see [Duplicate transaction protection](#duplicate-transaction-protection--idempotency).

## Known limitations

- No pagination on `products`, `warehouses`, or `inventory` — each hard-caps at 100 records.
- No per-warehouse access restriction within a company — any authorized key can act on any
  warehouse the caller's company owns.
- Partial receipts and partial dispatches are not supported; quantities must match exactly.
- **Lot/serial-tracked products are supported as of Phase F** — `POST`/`GET`/`PATCH /lots`, plus an
  optional `lot_external_id` on receipt/dispatch validation lines and on inventory-import lines.
  A tracked product with no `lot_external_id` is still rejected with `409`. See
  [LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md).
- Multiple move lines for the same product on one receipt are not supported.
- No automatic or scheduled synchronization — every request is initiated by your WMS; there is no
  polling, cron job, or push notification from Cool Agristock.
- No bidirectional synchronization — Cool Agristock never calls out to your WMS.
- No built-in, WMS-specific adapters — this is one generic REST API; translating it to your WMS's
  native protocol, if needed, is integration work on your side (optionally available as a paid
  service — see the [README](../README.md#free-software-and-paid-services)).

For the complete, field-by-field specification (every request/response field, every validation
rule, every error condition per endpoint), see [API.md](API.md).
