# Release Checklist — WMS-First AgriWare Connector

Tracks the release-preparation work done on `release/agriware-19.0-wms-first` (based on `eab9642`,
Phase H) against the conditions `docs/PRODUCTION_READINESS_REPORT.md` set for GO. Checked items
were verified in this pass, not assumed.

## Documentation corrections

- [x] `docs/API.md` — "lot/serial not supported" corrected to reflect Phase F, with the
  `lot_external_id` field documented in both receipt and dispatch validation tables.
- [x] `docs/QUICK_START.md` — corrected.
- [x] `docs/WMS_INTEGRATION.md` — corrected in both places it appeared.
- [x] `docs/COMMERCIAL_STRATEGY.md` — the root-cause instruction ("do not advertise... lot/serial
  support") corrected; this is what the stale website copy was following.
- [x] `agriware_connector/static/description/ICON_REQUIREMENTS.md` — "not yet created" corrected;
  `icon.png` confirmed to exist and match spec.
- [x] **Website local source** — corrected English and French text applied directly to
  `website/src/content/en.ts`/`fr.ts` in the Step 131 public-release pass (explicit authorization
  given for local edits only), extending `docs/WEBSITE_CONTENT_CORRECTIONS.md` to cover sections
  found independently stale (homepage "Key Features"/"How It Works", `operations.items`).
  Committed (`8c29d51`); `npm run build` verified clean. **Not deployed** — a maintainer with
  deploy access must still push this to the live site.

## New documentation

- [x] `CHANGELOG.md` — created, covering `19.0.1.0.0` → `19.0.1.7.0`.
- [x] `docs/ARCHITECTURE.md` — multi-company behavior section added (what's shared, what's
  isolated, shared-hosting implications).
- [x] `docs/RELEASE_NOTES_WMS_FIRST.md` — created.
- [x] `docs/RELEASE_APPROVAL_REPORT.md` — created.
- [x] `docs/WEBSITE_CONTENT_CORRECTIONS.md` — created.

## Installation guide

- [x] `docs/CUSTOMER_INSTALLATION_GUIDE.md` reviewed against this task's own 12-item list
  (supported environments, dependencies, installation, external system registration, API-key
  configuration, product/warehouse/supplier/lot sync, inventory import, receipt/dispatch sync) —
  already complete from Phase H; **no changes needed**.

## Dependency and maintainability review

- [x] `connector`/`component`/`component_event`/`queue_job` investigated — confirmed functionally
  unused (no `@job`, `Component`, or queue_job pattern anywhere in the codebase). **Recommendation:
  keep**, not remove — see `docs/RELEASE_APPROVAL_REPORT.md`'s Outstanding risks section for the
  full reasoning. Not removed in this pass.
- [x] `controllers/receipts.py`/`dispatches.py` duplication reviewed. **No refactor performed**, per
  this task's own instruction — documented as technical debt in
  `docs/RELEASE_APPROVAL_REPORT.md`.

## Package verification

- [x] Manifest: valid Python literal, all referenced `data` files exist, dependencies
  (`base`/`connector`/`stock`) correct, `license: "LGPL-3"` matches the repository `LICENSE` file.
- [x] All module XML files parse without error (`lxml` validation on every file).
- [x] `ir.model.access.csv` structurally consistent (8 columns throughout).
- [x] No secret, password, or real API key anywhere in git history (full-history search) — only a
  placeholder value in `.env.example`.
- [x] No unnecessary files **in the actual package**: `__pycache__/` and one stray
  `controllers/receipts.py.bak` exist in the local working tree but are **not tracked by git**
  (excluded by `.gitignore`) and would not be included in any archive built from this repository.
  Flagged for manual working-tree cleanup; not deleted by this pass since it wasn't created by this
  session's own work.
- [x] **Module version** — bumped to `19.0.2.0.0` in the Step 130 release-candidate pass, per that
  step's explicit instruction (left at `19.0.1.7.0` during Step 129 on purpose — see
  `docs/RELEASE_APPROVAL_REPORT.md`).

## Final testing

- [x] Full `agriware_connector` test suite re-run against this exact release-preparation commit:
  **271 passed, 0 failed, 0 errors** — the authoritative count from Phase H, not 307.
- [x] Fresh installation re-confirmed clean.
- [x] Upgrade path (published `19.0.1.0.0` → current code) re-confirmed clean, with pre-existing
  data intact, in Phase H; not re-run a third time in this pass since no application code changed.
- [x] Existing (legacy, numeric-ID) API behavior re-confirmed unaffected.

## Remaining before an actual release

1. ~~Decide and apply the actual release version number~~ — **done**: `19.0.2.0.0`, applied in
   Step 130, re-verified in Step 131.
2. ~~Apply the website copy corrections~~ — **done locally** in Step 131 (`8c29d51`); deploying
   them to the live site still requires access this session does not have.
3. Explicit approval to push/merge/publish — none of this has been done.

## Step 131 publication checklist — exactly what requires your explicit approval

Everything below is **prepared, not executed**. Each item requires a separate, explicit go-ahead
from you (or whoever holds the relevant access) before anyone carries it out — see
`docs/PUBLICATION_PACKAGE.md` for the full prepared content behind each one.

- [ ] **Confirm branch protection rules** on `main`/`19.0` (this session could not query GitHub's
  API — no `gh` CLI, no admin-scoped access). Needed before choosing Option A vs. Option B in
  `docs/PUBLICATION_PACKAGE.md` Section 3.
- [ ] **Push `release/agriware-19.0-wms-first`** to `origin` and open the pull request(s)
  (or perform the direct merge, if protection rules allow it) into `19.0`, then `main`.
- [ ] **Merge** that pull request (or direct merge) once reviewed.
- [ ] **Create and push the Git tag** `v19.0.2.0.0`.
- [ ] **Publish the GitHub release** using the draft title/body in
  `docs/PUBLICATION_PACKAGE.md` Section 6, with the release ZIP attached.
- [x] **Build the separate marketplace package** — done
  (`agriware_connector-19.0.2.0.0-marketplace.zip`, SHA-256 `b54e8b5e...`, bundling the four pinned
  OCA modules; see `docs/PUBLICATION_PACKAGE.md` Section 5), fresh-install/upgrade/271-test
  re-verified. **[ ] Upload it** to the Odoo Apps Marketplace, updating the listing's version —
  still requires your approval and marketplace seller-account access this session does not have.
- [ ] **Deploy the corrected website copy** (English and French) — already applied to the local
  source (`8c29d51`); per `docs/PUBLICATION_PACKAGE.md` Section 8, still needs an actual deploy.
- [ ] **Take a production database backup** immediately before any real customer upgrades to this
  version (tooling verified present and functional in Step 131; command in
  `docs/PUBLICATION_PACKAGE.md` Section 9).

**None of the above has been done by this session.** This checklist exists so you can approve each
step individually rather than as one bundled "yes."


---

## 19.0.2.0.1 — Connector navigation, dashboard, location sync, supplier classification

Extends the `19.0.2.0.0` checklist above. All code and test work is done.

### Completed in this session

- [x] **Navigation** — five-area menu tree replacing flat legacy layout; all XML IDs preserved
  for upgrade compatibility; redundant intermediate WMS category deactivated.
- [x] **Overview dashboard** — `agriware.dashboard` TransientModel; live company-scoped counts;
  eight quick-access buttons tested as ordinary inventory user and connector administrator.
- [x] **History views** — list/search/form for `agriware.wms.transaction`; picking-status badge;
  "Cancelled WMS Operations" domain-filtered action (distinguishes from API failures).
- [x] **Supplier classification** — `agriware_is_supplier` on `res.partner`; native contact form
  reused; upgrade migration for existing mapped partners.
- [x] **Location sync API** — `GET`/`POST`/`PATCH /agriware/api/v1/locations`; company-scoped;
  internal-location-only write restriction.
- [x] **Automatic inventory adjustments** — apply route with per-WMS opt-in and variance limit;
  native Odoo stock moves; pending-count and ambiguous-quant protection.
- [x] **Tests** — 290 total (up from 271), 0 failures, 0 errors on a fresh-install database.
- [x] **Release artifacts** built:
  - `agriware_connector-19.0.2.0.1.zip` (SHA-256 `1c2867aa...`)
  - `agriware_connector-19.0.2.0.1-marketplace.zip` (SHA-256 `6a4dfde3...`)
- [x] **Pre-Task-4 database backup** — `backups/agriwareodoo_before_task4_20261026.dump`
- [x] **`docs/CONNECTOR_NAVIGATION.md`** — navigation reference added.
- [x] **`docs/PUBLICATION_PACKAGE_19.0.2.0.1.md`** — publication guide for this version.

### Requires explicit approval before execution

- [ ] **Commit working-tree changes** — git index read-only in the dev session; commit must be
  done manually (command in `docs/PUBLICATION_PACKAGE_19.0.2.0.1.md` Section 3).
- [ ] **Push, PR, merge, tag** `v19.0.2.0.1`.
- [ ] **Publish GitHub release** with `agriware_connector-19.0.2.0.1.zip`.
- [ ] **Upload marketplace zip** `agriware_connector-19.0.2.0.1-marketplace.zip` to Odoo Apps.
- [ ] **Production database backup** before any customer upgrade.
