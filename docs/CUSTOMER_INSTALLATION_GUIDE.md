# Customer Installation Guide

**Status:** covers Cool Agristock as implemented through Phase G (branch
`feature/wms-transaction-sync` @ `8b88d50`), verified live on a disposable Odoo 19 database as part
of the Phase H production-readiness assessment. Every step below was actually performed, not
assumed — see [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) for the full
verification record.

## 1. Supported Odoo environments

- **Odoo 19**, Community edition. No Enterprise-only feature is used anywhere in this module —
  confirmed by reading every model/controller: nothing depends on `web_enterprise`, Studio, or any
  Enterprise-only addon.
- Verified on a fresh database, and on a database that already had `stock` (and its own demo data)
  installed before this module was added (see
  [PRODUCTION_READINESS_REPORT.md's Fresh installation and upgrade results](PRODUCTION_READINESS_REPORT.md#i-fresh-installation-results)).

## 2. Required dependencies

Declared in the manifest: `base`, `connector`, `stock`. The `connector` module itself pulls in
`component`, `component_event`, and `queue_job` (all from the Odoo Community Association's
`connector` suite). **These three OCA modules are bundled with a marketplace install already and
need no separate step** — but it's worth knowing, as a customer evaluating this module, that
**nothing in the current implementation actually uses them yet** (confirmed: no `@job`,
`Component`, or queue_job pattern appears anywhere in this module's code). They are a forward
dependency for possible future asynchronous/queued processing, not something this version relies on
— installing them costs nothing functionally today, but it's not free complexity either; see
[PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) for the full architecture audit
note on this.

## 3. Installation procedure

1. Place `cool_agristock` (and, if not already present in your Odoo addons environment, the
   `connector`/`component`/`component_event`/`queue_job` OCA modules it depends on) on your Odoo
   19 instance's addons path.
2. From **Apps**, search for "Cool Agristock" and click **Install** — or, from the command
   line: `odoo -d <your_database> -i cool_agristock`.
3. No configuration file changes, no environment variables, and no post-install script are
   required — everything from here on is done through the Odoo web interface.

## 4. External system registration

1. As an Administrator, go to **Inventory → Configuration → External Systems** (or search
   "External Systems" in the top search bar).
2. Click **New**, give it a name (e.g. "AGRI-WMS-TEST") and a short `code` — this is how the
   system is identified internally; it does not need to match anything on the WMS side.
3. Save. **One external system per WMS integration** is the expected pattern — if you have two
   separate WMS deployments (e.g. one per subsidiary), register two external systems.

## 5. API-key creation

1. Go to **Settings → Users & Companies → API Keys** (Cool Agristock's own API Keys menu, visible to
   Administrators).
2. Click **New**, give the key a name, and — this is the important part — select the **External
   System** you just created in the key's own binding field.
3. Click **Generate**. The raw key is shown **exactly once** — copy it immediately and store it
   securely (a password manager or secrets vault, not a chat message or a plain-text file). It
   cannot be retrieved again; if lost, revoke it and generate a new one.
4. **What happens automatically, with no developer involvement:** generating a *bound* key (one
   tied to an external system) silently creates a dedicated, single-purpose integration user behind
   the scenes (named something like `cool_agristock-api-service-<company>-<random>@cool_agristock.local`). This
   is the security mechanism that keeps two different WMS integrations on the same company from
   ever being able to act as each other — verified directly as part of this guide's own preparation
   (confirmed a fresh dedicated user is created per bound key, not shared).

**No step in this process requires a developer or a database shell** — everything above is ordinary
Odoo administrator UI work.

## 6. WMS connection setup

Configure your WMS (or integration middleware) with:
- **Base URL:** your Odoo instance's URL, e.g. `https://your-odoo-instance.example.com`
- **Authorization header:** `Authorization: Bearer <the raw key from step 5>`
- **Health check:** `GET /cool_agristock/api/v1/health` — call this first to confirm connectivity before
  anything else; it requires no authentication at all.

Verify the key works before building anything further:
```bash
curl -H "Authorization: Bearer <your-key>" https://your-odoo-instance.example.com/cool_agristock/api/v1/products
```
A `200` with `{"status": "success", ...}` confirms the key is valid and bound correctly. A `401`
means the key itself is wrong; a `403` means it's valid but not a Cool Agristock API User, or not bound
to an active external system (depending on the endpoint).

## 7. Product synchronization

```bash
POST /cool_agristock/api/v1/products
{"external_id": "CASSAVA-001", "name": "Cassava", "unit": "kg"}
```

- `external_id` is **your own** product code — Odoo never sees or cares what scheme you use.
- `unit` accepts `kg`, `g`, `ton`/`t`, `l`/`liter`/`litre`, `unit`/`units`/`pcs` out of the box, or
  any unit an Administrator has configured in **UOM Mappings** (see step 10's note on packaging
  units like bags).
- Repeating the same `external_id` is safe — it returns `409` with the existing product's id, never
  a duplicate.
- `PATCH /cool_agristock/api/v1/products/{external_id}` updates `name`/`default_code`/`barcode`/
  `description` only — pricing, accounting, and tax fields are never exposed to this endpoint, by
  design (an allow-list, not a block-list — there is no field this module could accidentally expose
  by forgetting to block it).

## 8. Warehouse synchronization

```bash
POST /cool_agristock/api/v1/warehouses
{"external_id": "WH-ANYAMA", "name": "Anyama Warehouse", "code": "ANY"}
```

Creates a real Odoo warehouse with its full native structure (stock locations, incoming/outgoing
picking types, routes) — verified directly against the database, not just the API response.
`code` cannot be changed after creation (it names the warehouse's own auto-generated location/
sequence structure internally) — plan your codes before your first sync, not after.

## 9. Supplier synchronization

```bash
POST /cool_agristock/api/v1/suppliers
{"external_id": "SUP-001", "name": "Cooperative Agricole Anyama", "country_code": "CI"}
```

Allow-listed fields only: `name`, `email`, `phone`, `street`, `city`, `country_code`. Every supplier
your WMS creates is scoped to your own company — it can never create or modify a partner shared
across companies.

## 10. Lot synchronization

```bash
POST /cool_agristock/api/v1/lots
{"external_id": "MAIZE-LOT-001", "product_external_id": "MAIZE-001", "name": "MAIZE-2026-H1"}
```

**The product must already be configured for lot or serial tracking in Odoo** (Inventory →
Products → *your product* → Traceability tab) before a lot can be created against it — this
module never flips a product into tracked mode on your behalf, since that's a decision with real
consequences for existing stock.

**A note on packaging units (bags, cartons, crates):** Odoo has no native "bag" unit out of the
box. If your products are counted in bags rather than kilograms, an Administrator must first
create that unit in **Settings → Technical → Units of Measure**, then map your WMS's own code for
it (e.g. `bag_50kg`) to that unit in **UOM Mappings**. This module will never guess that a bag
weighs 50kg on its own — an unmapped unit is rejected, not assumed.

**Expiration dates are not supported in this version** — the Odoo module that adds them
(`product_expiry`) isn't a dependency of this one; see
[LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md) if your products need genuine
expiration tracking.

## 11. Initial inventory import

```bash
POST /cool_agristock/api/v1/inventory-adjustments
{
  "external_reference": "INITIAL-2026-001",
  "warehouse_external_id": "WH-ANYAMA",
  "lines": [{"product_external_id": "CASSAVA-001", "quantity": 2500, "unit": "kg"}]
}
```

**This never changes your actual Odoo stock by itself.** It stages what your WMS believes is on
hand, compares it against what Odoo currently has, and waits for a human — an Inventory Manager —
to review it under **Inventory → Operations → Inventory Imports**. Approving it is a recorded
decision, not a stock change; actually applying the counted quantity still requires one manual step
in Odoo's own native **Physical Inventory** screen, by design (see
[INITIAL_INVENTORY_IMPORT.md](INITIAL_INVENTORY_IMPORT.md#native-adjustment-handoff-phase-11--deferred-by-design-not-by-oversight)
for exactly why).

## 12. Receipt synchronization

```bash
POST /cool_agristock/api/v1/receipts
{
  "external_reference": "WMS-REC-001",
  "warehouse_external_id": "WH-ANYAMA",
  "supplier_external_id": "SUP-001",
  "lines": [{"product_external_id": "MAIZE-001", "quantity": 3000, "unit": "kg", "lot_external_id": "MAIZE-LOT-001"}]
}
```

This only **creates a draft** incoming stock movement — it does not add stock yet. Validate it
separately (same as before this schema existed):
```bash
POST /cool_agristock/api/v1/receipts/{receipt_id}/validate
{"external_reference": "WMS-REC-001", "received_quantities": [{"product_id": 2, "quantity": 3000, "lot_external_id": "MAIZE-LOT-001"}]}
```
`product_id` here is the **numeric** id the creation call returned in its own `lines[].product_id`
— save it from the creation response, since `/validate` wasn't rewritten to accept external IDs
(see [WMS_TRANSACTION_SYNCHRONIZATION.md](WMS_TRANSACTION_SYNCHRONIZATION.md) for why). Only after
this second call does Odoo's actual on-hand quantity increase.

Check status anytime with `GET /cool_agristock/api/v1/receipts/WMS-REC-001`.

## 13. Dispatch synchronization

Same two-step pattern as receipts (`POST /dispatches` then `POST /dispatches/{id}/validate`), with
`customer_external_id` not required in this version's creation schema. **Partial receipts and
partial dispatches are not supported** — the quantity you validate must match the quantity you
created the line with, exactly; a mismatch is rejected rather than partially applied or backordered.

## 14. Common errors

| What you'll see | What it means |
|---|---|
| `401` | The API key itself is invalid, expired, or revoked. |
| `403`, "not bound to an active external system" | The key works, but either it was never bound to an external system at creation, or that system has since been deactivated. Generate a new bound key, or reactivate the system. |
| `404`, "X not found" | The `external_id`/`external_reference` you referenced hasn't been created yet, or belongs to a different company/external system than your key is bound to (these look identical on purpose — see Security in any of the phase reference docs). |
| `409`, "already mapped" / "already used with different content" | You're reusing an `external_id`/`external_reference` either exactly as before (safe — you'll get the existing record back) or with different content (a real conflict your integration needs to resolve). |
| `422` | The request was well-formed but semantically invalid — e.g. a unit that's not compatible with the product's own unit, or a lot that belongs to a different product. |

## 15. Troubleshooting

- **"It worked in testing but now returns 403"** — check whether the external system was
  deactivated, or whether the key was revoked/regenerated. A revoked key's dedicated integration
  user loses all authorization immediately; a fresh key must be generated.
- **"A receipt was created but validate always fails"** — confirm you're sending the numeric
  `product_id` the creation response gave you, not the `product_external_id` string.
- **"A lot-tracked product's receipt keeps rejecting"** — tracked products require
  `lot_external_id` on every line referencing them, both at creation (where it's validated) and at
  `/validate` (where it's actually applied) — see step 12.
- **Still stuck?** Every phase of this module has its own detailed reference document in `docs/`
  (`PRODUCT_SYNCHRONIZATION.md`, `WAREHOUSE_SYNCHRONIZATION.md`, `SUPPLIER_SYNCHRONIZATION.md`,
  `UOM_MAPPING.md`, `INITIAL_INVENTORY_IMPORT.md`, `LOT_BATCH_SYNCHRONIZATION.md`,
  `WMS_TRANSACTION_SYNCHRONIZATION.md`) with a full list of error codes and known limitations for
  that specific capability.
