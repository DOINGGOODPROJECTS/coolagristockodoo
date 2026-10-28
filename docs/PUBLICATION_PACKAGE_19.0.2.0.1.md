# Publication Package — AgriWare Connector `19.0.2.0.1`

**Everything in this document is prepared content, not executed action.** Nothing here has been
run against the real GitHub remote, the Odoo Apps Marketplace, or the live website. Items that
require explicit approval before execution are marked clearly.

This document extends `docs/PUBLICATION_PACKAGE.md` (which covers `19.0.2.0.0`) with the
incremental changes for `19.0.2.0.1`.

---

## 1. What changed from 19.0.2.0.0

`19.0.2.0.1` is a post-GA increment that adds:

- **Navigation** — five-area menu tree; `stock.group_stock_user` sees all operational screens,
  admin-only items gated at menu and model-ACL level. Removes the redundant intermediate WMS
  category level.
- **Overview dashboard** (`agriware.dashboard`) — live counts for active WMS systems, API keys,
  receipt/dispatch/completed/cancelled transactions, pending/rejected inventory imports, catalog
  mappings. Eight quick-access buttons. Admins see 5 most recent completed transactions inline.
- **WMS transaction history views** — list/search/form for `agriware.wms.transaction`; status
  badge; searchable by reference, system, transfer; filter completed/cancelled/in-progress;
  group by WMS or type. Separate "Cancelled WMS Operations" action (domain-filtered, not a new
  model) distinguishes warehouse-level cancellations from API failures (never stored).
- **Supplier classification** — `agriware_is_supplier` Boolean on `res.partner`; Supplier Records
  view reuses Odoo's native contact form. Supplier Synchronization Mappings submenu (admin only).
- **Location sync API** — `GET`/`POST`/`PATCH /agriware/api/v1/locations`; company-scoped;
  writes restricted to internal locations within the authorized warehouse.
- **Automatic inventory adjustments** — `POST /agriware/api/v1/inventory-adjustments/apply`;
  per-WMS opt-in with a configurable maximum variance per line; native Odoo stock moves;
  rejects ambiguous quants and pending manual counts.
- **Upgrade migration** — `migrations/19.0.2.0.1/post-migration.py` marks existing company-scoped
  partner mappings as `agriware_is_supplier = True`.
- **Test regressions** — 290 tests total (up from 271), 0 failures, on a fresh-install database.

No existing API behavior was changed. The original numeric-ID receipt/dispatch schema is
unchanged byte-for-byte.

---

## 2. Release artifacts

| File | SHA-256 |
|---|---|
| `agriware_connector-19.0.2.0.1.zip` | `1c2867aa49b4d0e77aad99b3249e5440fbce4bc27201e6007a20d8b9da479bca` |
| `agriware_connector-19.0.2.0.1-marketplace.zip` | `6a4dfde3ff7fbbb1f451d7285a400f959ef27bcc0bf84d5095d2a334786ca318` |

Both artifacts are in `release_artifacts/`. The marketplace zip bundles the same four pinned OCA
dependencies as the `19.0.2.0.0` marketplace zip (identical OCA commits, see
`docs/PUBLICATION_PACKAGE.md` Section 5).

The source-only zip (70 files) is the GitHub-release asset.
The marketplace zip (327 files, including all four OCA modules) is the Odoo Apps Marketplace upload.

---

## 3. Git state

All Task 4 changes are in the working tree on `release/agriware-19.0-wms-first`. The `.git`
index is on a read-only filesystem in this session, preventing `git add`/`git commit`. The
working-tree files are complete and all pass syntax and XML validation. Before publishing:

1. Commit all modified and new files as a single commit on `release/agriware-19.0-wms-first`:
   ```
   git add -A agriware_connector/ CHANGELOG.md README.md \
       docs/CONNECTOR_NAVIGATION.md \
       docs/API_INTEGRATION_REPORT_COOL_AGRISTOCK.md \
       docs/PUBLICATION_PACKAGE_19.0.2.0.1.md
   git commit -m "Add 19.0.2.0.1: navigation, dashboard, history, location sync, supplier classification, auto-adjustments"
   ```
2. Follow the same merge/tag/release-draft process as `19.0.2.0.0` (see
   `docs/PUBLICATION_PACKAGE.md` Sections 3 and 6), updating version references to `19.0.2.0.1`.

---

## 4. Odoo Apps Marketplace update

- **Package to upload:** `agriware_connector-19.0.2.0.1-marketplace.zip` (from Section 2 above).
- **Version field:** `19.0.2.0.1`.
- **Description changes:** The dashboard, five-area navigation, and supplier/location sync are
  new capabilities. Consider updating `agriware_connector/static/description/index.html` to
  mention the Overview dashboard and the navigation restructure before uploading.
- **Not done:** no package uploaded, no listing edited.

---

## 5. Pre-publication checklist

- [ ] Commit working-tree changes (git index currently read-only in dev session — see Section 3).
- [ ] Push `release/agriware-19.0-wms-first` and open PR(s) into `19.0` and `main`.
- [ ] Merge and create Git tag `v19.0.2.0.1`.
- [ ] Publish GitHub release with `agriware_connector-19.0.2.0.1.zip` attached.
- [ ] Upload `agriware_connector-19.0.2.0.1-marketplace.zip` to Odoo Apps Marketplace.
- [ ] Take a production database backup before upgrading any customer database.

**None of the above has been done by this session.**

