# Supplier Synchronization — Reference

**Status: IMPLEMENTED.** Branch `feature/wms-supplier-uom-sync`, based on the API-key isolation
security fix (`bff5dd0`) and its lifecycle hardening (`f1972cb`), not yet merged into `main`/`19.0`.
This is part of Phase D of the WMS-first roadmap — see
[API_ROADMAP.md](API_ROADMAP.md#phase-d--supplier-integration-and-uom-mapping) for where it fits,
and [UOM_MAPPING.md](UOM_MAPPING.md) for the other half of Phase D.

## Endpoints

### `POST /cool_agristock/api/v1/suppliers`

Request:
```json
{
  "external_id": "SUP-014",
  "name": "Cooperative Agricole d'Anyama",
  "email": "contact@example.ci",
  "phone": "+225 07 00 00 0000",
  "country_code": "CI"
}
```

Response `201`:
```json
{"status": "success", "supplier_id": 138, "external_id": "SUP-014", "name": "Cooperative Agricole d'Anyama"}
```

Response `409` (duplicate `external_id`):
```json
{"status": "error", "message": "external_id already mapped", "supplier_id": 138}
```

### `PATCH /cool_agristock/api/v1/suppliers/{external_id}`

Partial update. Request:
```json
{"phone": "+225 07 00 00 0001"}
```

Response `200`: same shape as creation. Response `404` if `external_id` isn't mapped. Response
`409` if the mapped record is a **shared** partner (see
[Shared partner protection](#shared-partner-protection) below) — refused, not silently applied.

### `GET /cool_agristock/api/v1/suppliers`

Read-only, same authentication requirement (Bearer + Cool Agristock API User) as every other `GET`
endpoint — **no external-system binding required**, matching `GET /products`/`GET /warehouses`.
Lists partners visible to the caller's company (`company_id` in `[False, company_id]`), capped at
100, ordered by id.

## Supported supplier fields

**Create and update allow-list (identical for both):** `name` (required on create), `email`,
`phone`, `street`, `city`, `country_code` (resolved to an existing `res.country` by ISO
alpha-2 code — an unrecognized code is rejected with `400`, never guessed).

**Verified never exposed, by construction — not by a block-list check:** this installation has no
`account`, `sale`, or `purchase` module installed, so fields like `property_account_payable_id`,
`property_payment_term_id`, or `credit_limit` don't even exist here. The protection holds
regardless: the allow-list approach means nothing outside the six fields above is ever read from a
request body, whether or not a real deployment has those modules installed alongside this one.
`supplier_rank`/`customer_rank` were reviewed and found not to exist in this installation either
(they come from fuller CRM/Sales-enabled setups) — not referenced anywhere in this module.

## Shared partner protection

**The real risk, verified directly against Odoo 19's `res.partner`:** a partner with
`company_id = False` is visible and usable from *every* company in the database — modifying one
through a single company's WMS binding could silently affect other companies' data.

**How this is prevented:**

- `POST /suppliers` **always** creates company-scoped records (`company_id` set to the resolving
  company) — confirmed directly in the live demo: a supplier created this way has
  `company_id = 1`, never `False`. A WMS integration can never create a shared partner through this
  API, by construction.
- `PATCH /suppliers/{external_id}` additionally checks the *target* record before writing: if the
  mapped partner's `company_id` is falsy, the request is refused with `409`, regardless of how that
  mapping came to exist. Since `POST` never produces a shared target, this guards specifically
  against a shared partner having been mapped through some other path (see
  [Existing partner adoption](#existing-partner-adoption-not-implemented) below) — confirmed
  directly by a test that manually creates such a mapping and verifies the `PATCH` is still
  refused.

## Existing partner adoption (not implemented)

Reviewed per the task's Phase 5, and **deliberately not implemented** — the same reasoning as
[WAREHOUSE_SYNCHRONIZATION.md's existing-warehouse adoption](WAREHOUSE_SYNCHRONIZATION.md#existing-warehouse-adoption)
applies here, with one addition specific to partners: **a genuinely shared (`company_id = False`)
partner should never be adopted directly.** If an administrator wants to map a WMS supplier onto an
existing Odoo partner that happens to be shared across companies, the safe design is to first
duplicate it into a company-scoped copy (a standard Odoo `copy()` with `company_id` explicitly set),
then adopt the mapping onto *that* copy — never onto the shared original. Building the actual
admin-only adoption UI (analogous to the warehouse one) remains future work; this document records
the safe design so it isn't skipped when that work happens.

## Duplicate behavior

Identity is `(company, external_system, "res.partner", external_id)` — the same Phase A mapping
schema, no separate supplier-specific table. Checked before any partner is created (common case,
`409` immediately) and protected by the database's own unique constraints for the concurrent case
(forced-race tested the same way as products and warehouses) — a losing race's partner is rolled
back, never left orphaned.

## Security

- Authentication and external-system resolution: identical to Phases B/C — Bearer token →
  Cool Agristock API User group → `resolve_authorized_external_system()`, server-derived.
- **Security design choice, verified empirically before writing any code:** the Cool Agristock API User
  group has no native `create`/`write` access to `res.partner` (checked the same way the
  Phase B product.template gap and Phase C warehouse-model gaps were found). Rather than grant a
  standing `ir.model.access.csv` row — which would hand the API User group broad write access to
  the *entire* contacts/partner directory, arguably the most widely-shared, most sensitive model in
  all of Odoo (contacts, invoicing, portal users, messaging) — the controller uses the same gated
  `sudo()` pattern as Phase C's warehouse endpoints: explicit auth + resolved-external-system check
  first, then a single, narrow, already-authorized `res.partner.sudo()` operation. This is an even
  stronger case for that pattern than warehouses was.
- Company isolation and cross-system isolation: verified directly, including a cross-company
  `PATCH` attempt (`404`, indistinguishable from "doesn't exist," matching every other endpoint's
  behavior).

## Error responses

| Code | Condition |
|---|---|
| 400 | Invalid JSON, missing/empty `name`, unsupported field, unrecognized `country_code` |
| 401 | Missing, malformed, invalid, expired, or revoked API key |
| 403 | Not a Cool Agristock API User; key not bound to an active external system; ambiguous binding |
| 404 | (`PATCH` only) No supplier mapped for this `external_id` |
| 409 | `external_id` already mapped (create); mapped target is a shared partner (update) |
| 500 | Unexpected server-side error (transaction rolled back) |

## Known limitations

- **Existing-partner adoption is designed, not built** — see above.
- **No `supplier_rank`/`customer_rank` tagging** — this installation doesn't have those fields;
  a fuller deployment with CRM/Sales installed would need separate review before relying on them.
- **No company/organization-specific fields beyond the six listed** — e.g. no VAT/tax ID, no
  company registration number. Reviewed and excluded for this phase to keep the allow-list tight;
  can be added later with its own explicit review if genuinely needed.

## Verification performed

- **All 178 tests pass** against a fresh database (149 pre-existing + 29 new across supplier and
  UOM mapping tests), clean install and clean upgrade from the prior state.
- **The full demo scenario was run over real HTTP and verified against actual PostgreSQL rows:** a
  WMS created a supplier with a real country code → updated its phone number → repeated the
  original creation request (`409`, same supplier id) → confirmed via direct SQL that the partner
  is company-scoped (`company_id = 1`, not `False`), its country resolved correctly, and exactly one
  mapping row exists for that external_id.
