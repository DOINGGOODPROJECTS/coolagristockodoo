# Changelog

All notable changes to AgriWare Connector are documented here. Versions follow Odoo's own
`{odoo_series}.{major}.{minor}.{patch}` convention.

This file covers the **WMS-first rearchitecture**: `19.0.1.0.0` (the last published marketplace
release) through `19.0.2.0.1` (the current release). The entries below `19.0.2.0.0` are the
per-phase development history and are kept exactly as originally written, unrewritten, even though
none of those intermediate version numbers (`19.0.1.1.0` through `19.0.1.7.0`) was itself published.

## [19.0.2.0.0] — WMS-first general availability (release candidate)

## [19.0.2.0.1] — Locations, supplier classification, and connector navigation

### Added
- Company-scoped storage-location synchronization through `GET`/`POST`/`PATCH
  /agriware/api/v1/locations`; writes are restricted to internal locations within
  the authorized warehouse.
- Supplier-specific partner classification and a dedicated Supplier Records view.
  Upgrade migration marks existing company-scoped partner mappings as suppliers.
- A per-WMS opt-in automatic inventory adjustment route at
  `POST /agriware/api/v1/inventory-adjustments/apply`. Odoo admins must enable it
  and configure a positive per-line maximum variance. The original staged review
  endpoint remains available.
- AgriWare overview dashboard and navigation to existing Odoo Inventory records,
  connector transaction history, and configuration.
- Five operational navigation areas, a real-data overview with quick links, native
  supplier contact forms, and searchable WMS transaction/import/mapping views.
- Ordinary-user menu/action/view access regressions and company-scoped dashboard checks.

### Fixed
- Fresh-install menu load order and dashboard model access; ordinary users now use
  Odoo's supported action loader for quick links.
- Staged inventory API route registration alongside the new automatic apply route.
- Automatic counts now apply through native Odoo stock moves instead of only staging
  quantities. Pending manual counts and ambiguous stock are preserved; non-finite
  quantities and invalid automatic variance settings are rejected.


The umbrella release bundling everything below: Phases A through H of the WMS-first
rearchitecture, finalized after the Step 129/130 release-preparation and verification passes. See
`docs/RELEASE_NOTES_WMS_FIRST.md` for the customer-facing summary and
`docs/FINAL_RELEASE_VERIFICATION.md` for the complete verification record this version number is
based on.

## [19.0.1.7.0] — Phase G: WMS-first receipt and dispatch synchronization

### Added
- `POST /agriware/api/v1/receipts` and `POST /agriware/api/v1/dispatches` now accept a second,
  parallel request shape (`lines[]`) alongside the original (`products[]`): every reference
  (warehouse, supplier, product, unit, lot) resolved from the caller's own external-ID namespace.
- `agriware.wms.transaction` — real database-level transaction identity and idempotency for the
  new schema, independent of the legacy advisory-lock mechanism.
- `GET /agriware/api/v1/receipts/{external_reference}` and
  `GET /agriware/api/v1/dispatches/{external_reference}` — transaction status retrieval.

### Fixed
- `/validate`'s "is this AgriWare-managed" guard previously recognized only the legacy
  `AGRIWARE-RCPT-`/`AGRIWARE-DISP-` prefix convention, which a Phase G `external_reference` would
  never match — a WMS-first receipt or dispatch could be created but never validated. Now also
  recognizes a real `agriware.wms.transaction` row as proof of ownership.

### Compatibility
- The original `products[]`/numeric-ID schema is unchanged, byte-for-byte, including every error
  message and status code.

## [19.0.1.6.0] — Phase F: lot, batch, and serial number synchronization

### Added
- `POST`/`GET`/`PATCH /agriware/api/v1/lots` over native `stock.lot`, resolved through the same
  external-ID mapping service every other record type uses.
- Optional `lot_external_id` on inventory-import lines, reconciled at the exact
  `(product, location, lot)` level — never aggregated across lots.
- Optional `lot_external_id` on receipt/dispatch `/validate` lines. A serial-tracked line's
  normalized quantity must be exactly `1`, enforced everywhere a quantity is accepted.

### Fixed
- Dispatch lot reservation could double-reserve stock: `action_confirm()` can itself auto-reserve a
  move before this module's own explicit per-lot reservation runs, and
  `stock.move._update_reserved_quantity()`'s `need` argument is additive, not absolute. Fixed by
  clearing any existing reservation immediately before pinning the requested lot.
- `tests/__init__.py` had never actually registered `test_inventory_import.py` (a Phase E
  oversight) — its 26 tests had never run as part of any reported total until this fix.

## [19.0.1.5.0] — Phase E: staged initial inventory import and reconciliation

### Added
- `POST /agriware/api/v1/inventory-adjustments` and `agriware.inventory.import`/`.line` — a pure
  staging area for WMS stock observations. Reconciled read-only against `stock.quant`; **never**
  writes `stock.quant.quantity` or calls `action_apply_inventory()`.
- Human review workflow (Inventory → Operations → Inventory Imports): approve/reject, restricted
  to the native `stock.group_stock_manager` group.
- Stale-data detection: approval re-reads live stock first; if it changed since the import's
  numbers were last computed, the import is flipped to `stale` with refreshed numbers instead of
  being approved, requiring a second, informed approval.

### Documented
- Odoo 19's `stock.quant.inventory_quantity` applies synchronously under `inventory_mode` (traced
  directly in source) — there is no safe "staged but not yet applied" hook to automate the final
  apply-to-stock step. That step remains a deliberate, manual action in Odoo's own Inventory
  Adjustment screen.

## [19.0.1.4.0] — Phase D: supplier synchronization and UOM mapping

### Added
- `POST`/`PATCH`/`GET /agriware/api/v1/suppliers` over `res.partner`, company-scoped, with shared
  (`company_id = False`) partner protection on both creation and update.
- `agriware.uom.mapping` — admin-configurable, database-backed unit-of-measure mapping, layered
  over Phase B's hardcoded kg/g/ton/liter/unit fallback with verified precedence.

### Security
- Reviewed and confirmed: Odoo 19 has no `uom.category` model or `category_id` field — UOM
  compatibility is based on the `relative_uom_id`/`parent_path` tree instead. This finding shaped
  every subsequent phase's unit-compatibility checks.

## [19.0.1.3.0] and earlier — API-key isolation security fix

### Fixed — security
- **A real authorization-isolation vulnerability**, found and fixed before Phase D: an API key
  generated with no external-system binding could inherit authorization from an unrelated *bound*
  key sharing the same company, because every key for a company shared one integration user and
  Odoo's own Bearer-auth layer can't distinguish which key authenticated. Reproduced via real HTTP
  before being fixed. Fixed by giving every *bound* key its own, never-shared dedicated integration
  user (`agriware-api-service-<company>-<random>@agriware.local`); unbound keys are entirely
  unaffected. Covered by two dedicated regression suites (isolation and lifecycle), re-run clean in
  every phase since.

## [19.0.1.3.0] — Phase C: warehouse creation and synchronization

### Added
- `POST`/`PATCH /agriware/api/v1/warehouses` over `stock.warehouse`, including its full native
  structure (locations, picking types, routes, sequences). `code` is immutable after creation (it
  names the warehouse's own auto-generated structure).

## [19.0.1.2.0] — Phase B: product creation and synchronization

### Added
- `POST`/`PATCH /agriware/api/v1/products` over `product.product`, with a strict allow-list
  (`name`, `default_code`, `barcode`, `description`, `unit`) — no pricing, accounting, or
  valuation field is ever exposed.
- A small hardcoded set of supported units (kg, g, ton, liter, unit) for product creation, later
  superseded (not replaced) by Phase D's database-backed mapping.

## [19.0.1.1.0] — Phase A: external ID mapping infrastructure

### Added
- `agriware.external.system` and `agriware.external.id.mapping` — the generic, reusable mapping
  service every subsequent record type (products, warehouses, suppliers, lots, inventory imports,
  transactions) is built on. Binds an `agriware.api.key` to a specific external system.
- No new REST endpoints in this phase — infrastructure only, as scoped.

## [19.0.1.0.0] — Last published marketplace release (pre-WMS-first baseline)

Read-only catalog endpoints (`GET /products`, `/warehouses`, `/inventory`) and legacy,
numeric-Odoo-ID receipt/dispatch creation and validation. No external-ID resolution, no lot/serial
support, no inventory import, no supplier or UOM synchronization. This is the version currently on
the Odoo Apps marketplace — everything above this entry in the changelog is not yet published.

---

**Backward compatibility, stated once, for the whole range:** every endpoint and behavior present
in `19.0.1.0.0` remains unchanged, byte-for-byte, through `19.0.1.7.0` — confirmed by the complete
pre-Phase-A test suite passing unmodified at every single step above, and by a real upgrade test
(install `19.0.1.0.0`, create real data, upgrade in place to `19.0.1.7.0`) confirming that data's
survival. See `docs/PRODUCTION_READINESS_REPORT.md` for the full verification record.
