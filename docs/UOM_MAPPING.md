# UOM Mapping — Reference

**Status: IMPLEMENTED.** Branch `feature/wms-supplier-uom-sync`, not yet merged into `main`/`19.0`.
This is the other half of Phase D — see
[SUPPLIER_SYNCHRONIZATION.md](SUPPLIER_SYNCHRONIZATION.md) for the supplier half, and
[API_ROADMAP.md](API_ROADMAP.md#phase-d--supplier-integration-and-uom-mapping) for where this fits
in the overall roadmap. This document **supersedes** the small hardcoded unit set originally
shipped in Phase B ([PRODUCT_SYNCHRONIZATION.md's Supported units](PRODUCT_SYNCHRONIZATION.md#supported-units))
— that set still works, unchanged, as a fallback; this is the richer mechanism layered on top of
it, exactly as that document said would happen "in Phase D."

## The model: `cool_agristock.uom.mapping`

| Field | Type | Notes |
|---|---|---|
| `company_id` | Many2one `res.company`, required | Defaults to the current company. |
| `external_system_id` | Many2one `cool_agristock.external.system`, required | Scopes the mapping, same pattern as every other model in this project. |
| `external_unit_code` | Char, required | The WMS's own unit code, e.g. `bag_50kg`. Free text — not restricted to a fixed list, since different WMS systems name units differently. |
| `uom_id` | Many2one `uom.uom`, required | An **existing** Odoo unit of measure. Never created or guessed by this module — see [No invented conversion factors](#no-invented-conversion-factors) below. |
| `active` | Boolean, default `True` | Standard archive pattern. |
| `description` | Text | Free-text notes — e.g. "this WMS's 50kg bag, fertilizer products only." |

**Uniqueness:** `unique(company_id, external_system_id, external_unit_code)` — a real database
constraint, confirmed present via `\d cool_agristock_uom_mapping` against a live install, not just
declared in code. Two different companies (or two different external systems within the same
company) may use the identical code with no conflict.

## No invented conversion factors

**This is the central design constraint, and it's enforced structurally, not by convention.**
`cool_agristock.uom.mapping` has no conversion-factor field of its own at all — it only has `uom_id`, a
reference to a real, already-existing `uom.uom` record. Whatever conversion factor that Odoo UOM
carries (set through Odoo's own Settings → Technical → Units of Measure, or by Odoo core/OCA
modules) is what applies — this module never calculates, stores, or overrides one.

**Practical consequence, directly addressing "do not assume every bag weighs 50kg":** if an
administrator maps the code `bag_50kg` to Odoo's `kg` unit, every product using that mapping is
being told "this quantity is already expressed in kilograms, after whatever conversion the
administrator decided." The module has no opinion on what a "bag" weighs — the administrator's
choice of `uom_id`, and the `description` field explaining that choice, are the only place that
decision lives. **This is why `description` is a free-text field on every mapping row, not
cosmetic** — a bag means whatever the administrator documents it to mean here, for whichever
products they've verified it applies to.

## Supported agricultural units — what's actually possible out of the box

Reviewed directly against this Odoo 19 installation's actual `uom.uom` records (not assumed):

| Requested unit | Native Odoo 19 UOM available? | What this means |
|---|---|---|
| Kilograms | **Yes** (`kg`) | Mappable immediately. |
| Grams | **Yes** (`g`) | Mappable immediately. |
| Tonnes | **Yes** (`Ton`) | Mappable immediately. |
| Bags | **No native UOM** | Cannot be mapped until an administrator first creates a custom `uom.uom` record in Odoo itself (Settings → Technical → Units of Measure) representing whatever a "bag" means for their products — this module does not, and will not, auto-create one. |
| Cartons | **No native UOM** | Same as bags. |
| Crates | **No native UOM** | Same as bags. |

**"Only enable mappings that are valid in the installed Odoo configuration" is enforced by
`uom_id` being a required reference to an existing record** — there is no code path that creates a
new `uom.uom` row from an external unit code. If no suitable Odoo unit exists yet, the mapping
simply cannot be created (the admin form will show an empty/invalid selection), which is the
correct, safe outcome rather than fabricating one.

## Administrator interface

A new **UOM Mappings** menu (under **Cool Agristock → External Systems**, Administrator-only,
same access pattern as External Systems and ID Mappings) lets an administrator register, edit, and
deactivate mappings. Full CRUD for Administrators; **no access at all** for the Cool Agristock API User
group — mappings are read only through the `resolve_unit()` service, server-side, during product
synchronization, never editable by an API caller.

## Integration with product synchronization

`controllers/products.py`'s unit resolution now checks, in order:

1. **`cool_agristock.uom.mapping.resolve_unit(company, external_system, unit_code)`** — an
   administrator-configured mapping, scoped to the caller's company and external system.
2. **The Phase B hardcoded set** (`kg`, `g`, `ton`/`t`, `l`/`liter`/`litre`, `unit`/`units`/`pcs`) —
   consulted only if step 1 found nothing, for full backward compatibility.
3. **Rejected with `400`** if neither resolves — never silently guessed or defaulted.

**Verified directly, not just by design:** an admin-configured mapping for the code `kg` that
points at a *different* UOM than the hardcoded default is confirmed to take precedence — proving
step 1 is genuinely consulted first, not merely a fallback for codes the hardcoded set doesn't
already cover. Separately, a product-creation request using `unit: "kg"` with **no mapping
configured at all** for that company still succeeds via the hardcoded set, confirming zero
behavior change for any integration that has never configured a mapping.

**Backward compatibility, and what's deliberately unchanged:** `PATCH /products/{external_id}`
still excludes `unit` from its allow-list entirely (per Phase B's original, still-valid reasoning —
changing a product's UOM after it may have stock history is unsafe without a check this phase
doesn't add). This phase only extends what `unit` can *resolve to* at creation time; it does not
touch the existing-product UOM-change restriction at all.

## Error responses

| Code | Condition |
|---|---|
| 400 (on `POST /products`) | `unit` matches neither a configured mapping nor the hardcoded set |
| 403 (model-level, admin UI) | A non-Administrator attempting to manage mappings directly |

## Known limitations

- **No bulk/CSV import of mappings** — each is created one at a time through the admin UI.
- **No automatic suggestion of likely mappings** — an administrator must know which Odoo UOM a
  given external code should resolve to; this module never guesses based on the code's name.
- **Product-specific packaging (e.g. "this product's bag is 25kg, that one's is 50kg") isn't
  modeled** — a mapping is scoped to `(company, external_system, code)`, not to an individual
  product. If a WMS genuinely needs two different "bag" weights for different products, it needs
  two different external unit codes (e.g. `bag_25kg`, `bag_50kg`), each mapped separately — this is
  a real constraint of the current design, not an oversight, and is documented here so it's an
  explicit decision rather than a surprise.

## Verification performed

- **Database constraint confirmed present** via `\d cool_agristock_uom_mapping` against a live install —
  not just declared in code.
- **Admin-only access confirmed**: both the Cool Agristock API User group and a plain internal user
  without the Administrator group are rejected (`AccessError`) attempting direct model access.
- **`resolve_unit()` confirmed correct** for the found, not-found, and inactive-mapping cases.
- **Full product-sync integration demonstrated live over real HTTP**, with direct PostgreSQL
  verification: an administrator configured `bag_50kg` → Odoo's `kg` unit; a WMS then created a
  product with `"unit": "bag_50kg"`; the resulting product's `uom_id` was confirmed, via direct SQL
  join from `product_product` through `product_template` to `uom_uom`, to be the exact `kg` record
  the mapping specified.
- All 178 tests in the module pass (149 pre-existing + 29 new).
