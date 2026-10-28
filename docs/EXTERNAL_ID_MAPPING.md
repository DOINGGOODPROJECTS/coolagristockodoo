# External ID Mapping — Reference

**Status: IMPLEMENTED.** Everything in this document exists in the code today, on branch
`feature/wms-external-id-mapping` (not yet merged into `main`/`19.0`). This is Phase A of the
WMS-first roadmap — see [API_ROADMAP.md](API_ROADMAP.md#phase-a--external-id-mapping-and-data-ownership)
for where it fits, and [ARCHITECTURE.md](ARCHITECTURE.md) for why it exists at all.

**What this phase does *not* include, explicitly:** no REST endpoint exposes any of this yet. There
is no `POST /products`, no `POST /warehouses`, nothing a WMS can call today to use this
infrastructure. This document describes internal plumbing — models and a Python service layer —
not a new customer-facing feature. Product/warehouse/supplier/lot synchronization (Phases B-F) are
still design-only; see [WMS_FIRST_INTEGRATION_PLAN.md](WMS_FIRST_INTEGRATION_PLAN.md).

## External system identity

**Model: `cool_agristock.external.system`**

| Field | Type | Notes |
|---|---|---|
| `name` | Char, required | Human-readable, e.g. "Main Warehouse WMS". |
| `code` | Char, required | Short, stable identifier, e.g. `primary_wms`. Non-empty enforced (rejects whitespace-only values too, not just blank). |
| `company_id` | Many2one `res.company`, required | Defaults to the current company. |
| `active` | Boolean, default `True` | Standard Odoo archive pattern — "deactivate" means setting this to `False`, not deleting the record. |
| `description` | Text | Free text, admin-facing only. |

**Why this is its own model, not a bare string field on the mapping table (a refinement made
during implementation, not in the original design sketch):** an external system represents a
real, ongoing integration relationship — a specific WMS a specific company talks to — independent
of any one API key. A business can rotate or replace its API key at any time (already supported,
pre-existing behavior) without that affecting which external system its mappings belong to. Tying
mappings to a key directly, instead, would silently orphan every mapping the moment a key is
rotated — reviewed and explicitly rejected; see [ARCHITECTURE.md's open decision](ARCHITECTURE.md#approved-decisions)
on API-key binding below.

**Uniqueness:** `code` is unique per `company_id` — enforced as a real Postgres constraint
(`unique(company_id, code)`), not just a Python-level check. Two different companies may use the
identical code (e.g. both call their system `primary_wms`) with no conflict, since the constraint
includes `company_id`.

### API-key binding: reviewed, not implemented

The approval task asked whether an existing `cool_agristock.api.key` should be associated with a
specific external system. **Reviewed and deferred, not implemented:**

- `cool_agristock.api.key` was **not modified** in this phase — zero changes to an existing, already-
  shipped, already-tested model. Authentication behavior is unchanged, confirmed by the full
  existing test suite passing unmodified (see [Verification](#verification-performed) below).
- Rationale for deferring rather than building it now: there is no current call site that would
  consume such a binding (no REST endpoint uses `cool_agristock.external.system` yet), and building it
  speculatively would mean touching authentication-adjacent code for a feature nothing calls —
  exactly the kind of premature complexity this project avoids elsewhere.
- **Compatibility implication, documented in case this is revisited:** if a future phase does add
  an optional `external_system_id` field to `cool_agristock.api.key`, it should be **nullable**, with
  existing keys defaulting to no binding — this is non-breaking by construction as long as nothing
  is made to *require* the field. Any design that makes it required, or that changes how an
  existing key authenticates based on this field, would need its own explicit compatibility review
  before implementation, not be bundled into a routine addition.

## Mapping schema

**Model: `cool_agristock.external.id.mapping`**

| Field | Type | Notes |
|---|---|---|
| `company_id` | Many2one `res.company`, required | Defaults to the current company. |
| `external_system_id` | Many2one `cool_agristock.external.system`, required | `ondelete="restrict"` — an external system in active use cannot be deleted out from under its mappings. |
| `res_model` | Char, required | Restricted to an explicit allow-list — see below. |
| `external_id` | Char, required | The external system's own identifier string, e.g. `WMS-PRODUCT-001`. Non-empty enforced. |
| `res_id` | Integer, required | The id of the record in `res_model` this `external_id` refers to. |

### Allowed models (explicit allow-list, enforced in Python)

```python
ALLOWED_MODELS = (
    "product.product",
    "stock.warehouse",
    "res.partner",
    "stock.lot",
)
```

No API client, and no direct caller of the mapping service, can register a mapping against any
other model — attempting to do so raises `ValidationError` immediately, both from the model's own
`@api.constrains` (so it's enforced even for a direct `create()` call, not just through the service
methods) and, redundantly, as an early guard inside `create_mapping()` itself.

**`product.template` was reviewed and deliberately excluded.** Every existing and planned
product-facing endpoint (today's `GET /products`, and the proposed `POST`/`PATCH /products` in
Phase B) operates on `product.product` — the sellable/stockable variant — not the shared template.
Including `product.template` here would introduce a second, inconsistent product identity concept
with no current or planned caller.

## Uniqueness constraints

Two real Postgres unique constraints (confirmed present via `\d cool_agristock_external_id_mapping`
against a live Odoo 19 install, not just declared in code):

```sql
UNIQUE (company_id, external_system_id, res_model, external_id)  -- "external_id_uniq"
UNIQUE (company_id, external_system_id, res_model, res_id)       -- "res_id_uniq"
```

- The first prevents the same external identifier being mapped to two different Odoo records
  within the same company/system/model namespace (no duplicate identity creation).
- The second prevents one Odoo record being claimed by two different external identifiers within
  that same namespace (no split identity).

**Different external systems, or different companies, may use the identical `external_id` string**
with no conflict — both are part of the uniqueness key, by design, and this is directly tested (see
[Verification](#verification-performed)).

Built using Odoo 19's current `models.Constraint(...)` class-attribute mechanism — **verified
against the actual installed Odoo version** before use, since this Odoo build has moved away from
the older `_sql_constraints = [...]` list syntax (only one legacy usage of the old syntax remains
anywhere in Odoo core itself, in an unrelated module).

## Security model

- **Row-level isolation:** both models carry a company-scoped `ir.rule`
  (`[('company_id', 'in', company_ids)]`), identical in form to the existing
  `rule_cool_agristock_api_key_company` rule. One company's integration can never see or act on another
  company's external systems or mappings — tested directly, including an attempt to force it via
  direct ORM search.
- **Direct model access (`ir.model.access.csv`):**

  | Model | Cool Agristock Administrator | Cool Agristock API User |
  |---|---|---|
  | `cool_agristock.external.system` | Full CRUD | **No access at all** |
  | `cool_agristock.external.id.mapping` | **Read-only** (no write/create/unlink) | **No access at all** |

  Administrators manage external systems through the admin UI (below). Nobody — not even an
  Administrator — can hand-edit a mapping row directly; mappings are written only through the
  service methods, which apply their own validation and conflict handling. The API User group has
  no direct grant on either model at all: every write happens through the service layer's own
  `sudo()` calls, made only after that layer's own authorization check passes.
- **Service-layer authorization (`_check_mapping_access`):** every write operation
  (`create_mapping`, `update_mapping`, `remove_mapping`) independently re-verifies that the calling
  user holds the **Cool Agristock API User** group and that the target company is one of their allowed
  companies — the same two checks a REST controller would perform at the HTTP layer, duplicated
  here so the service itself never silently trusts a caller that reached it through some other
  path. `resolve_mapping` (read-only) checks company membership only, not the group, matching the
  more permissive nature of a lookup versus a write.
- **A real bug this review caught:** the first implementation named this authorization helper
  `_check_access`, which collided with — and silently replaced — Odoo's own internal
  `BaseModel._check_access(operation)` hook that every `search()`/`write()` call relies on for
  standard access control. Caught by the automated test suite, not by inspection; renamed to
  `_check_mapping_access`. Documented here as a concrete example of why Phase 10's "test against
  the actual Odoo installation" requirement mattered — this would not have been caught by static
  analysis alone.

## Mapping lifecycle

```python
Mapping = env["cool_agristock.external.id.mapping"]

# Create (or discover it already exists)
record, created = Mapping.create_mapping(
    company, external_system, "product.product", "WMS-PRODUCT-001", product.id,
)
# created is False if this external_id was already mapped -- record is the
# *existing* row in that case, not a new one. This is the service-layer
# equivalent of the 409-with-existing-id pattern receipts/dispatches already
# use at the HTTP layer.

# Look up
mapping = Mapping.resolve_mapping(
    company, external_system, "product.product", "WMS-PRODUCT-001",
)
# Empty recordset if not found -- never raises for a simple not-found lookup.

# Update (re-point at a different Odoo record)
Mapping.update_mapping(
    company, external_system, "product.product", "WMS-PRODUCT-001", new_product.id,
)
# Raises ValidationError if no mapping exists yet -- update never creates one.

# Remove
removed = Mapping.remove_mapping(
    company, external_system, "product.product", "WMS-PRODUCT-001",
)
# Returns True/False, never raises for a mapping that's already gone
# (idempotent) -- and only ever deletes the mapping row, never the
# underlying Odoo record it pointed to.
```

## Concurrency behavior

**The database constraints are the actual enforcement mechanism — not the application-level
pre-check.** `create_mapping()` does check for an existing mapping first (cheap, avoids a failed
insert in the common case), but if two requests race for the same new `external_id` at the same
moment, the pre-check in both can pass before either has committed. What actually prevents both
from succeeding is the Postgres unique constraint: the losing request's `INSERT` is wrapped in
`self.env.cr.savepoint()`, so when it fails with `psycopg2.IntegrityError`, the savepoint rolls back
cleanly (the surrounding transaction stays healthy — this is the standard, Odoo-core-verified
idiom for "try an operation that might violate a constraint"), and the method then re-resolves the
mapping and returns the winner's row with `created=False`, rather than raising.

This is directly tested by bypassing the service's own pre-check entirely — calling `.create()`
twice directly against the model — to prove the database constraint itself is what rejects the
second attempt, independent of any Python-level logic (see `test_concurrent_mapping_creation_enforced_by_database`
in `tests/test_external_id_mapping.py`).

## Error handling

| Situation | Behavior |
|---|---|
| `create_mapping()` for an identity that already exists | Returns `(existing_record, False)` — no exception. |
| Two concurrent `create_mapping()` calls for the same new identity | Both return successfully; one gets `created=True`, the other `created=False` with the same record. |
| `create_mapping()`/`update_mapping()` with a `res_model` outside the allow-list | `ValidationError`, raised before any database write is attempted. |
| `update_mapping()`/`remove_mapping()` for an identity with no existing mapping | `update_mapping` raises `ValidationError`; `remove_mapping` returns `False` (idempotent, not an error). |
| A mapping's target record doesn't exist, or belongs to a different company | `ValidationError`, enforced by an `@api.constrains` check that runs on every create/write, not just through the service layer. |
| Caller lacks the Cool Agristock API User group, or the target company isn't theirs | `AccessError`, from the service layer's own authorization check. |
| Direct ORM access to either model by a non-Administrator | `AccessError`, from `ir.model.access.csv` — enforced before any of the above logic even runs. |

## Future API integration

**Update: Phase B now consumes this service layer**, confirming the design worked as intended —
`controllers/products.py` calls `resolve_mapping()`/`create_mapping()` exactly as sketched below,
with no changes needed to this phase's schema or constraints. See
[PRODUCT_SYNCHRONIZATION.md](PRODUCT_SYNCHRONIZATION.md) for the full reference. `update_mapping()`
and `remove_mapping()` remain uncalled by any controller so far — Phase B's `PATCH` endpoint
updates the underlying product record directly, since the mapping itself (which external_id points
to which product) never changes during a product update.

Still not built — warehouse, supplier, and lot sync (Phases C-F), and the additive
`*_external_id` fields on `POST /receipts`/`/dispatches` (Phase G):

- Warehouse/supplier/lot controllers will call `resolve_mapping()`/`create_mapping()` the same way
  Phase B's product controller does, exactly as designed in
  [WMS_FIRST_INTEGRATION_PLAN.md](WMS_FIRST_INTEGRATION_PLAN.md).
- An optional `*_external_id` alternative to the existing numeric `product_id`/`warehouse_id`/
  `supplier_id`/`customer_id` fields on `POST /receipts` and `POST /dispatches`, resolved via
  `resolve_mapping()` — purely additive, existing numeric-ID callers unaffected (Phase G).

This document will be updated again as each further phase starts consuming this service layer.

## Verification performed

- **Module installs cleanly** into a fresh, disposable Odoo 19 database (`cool_agristock_feature_test`,
  dropped after use — the persistent dev database was never touched), confirmed via direct
  `ir_module_module` query (`state = 'installed'`, version `19.0.1.1.0`).
- **Module upgrades cleanly** from the prior installed state (`-u cool_agristock` against the
  same throwaway database), zero errors.
- **Both new tables and both SQL constraints exist exactly as designed**, confirmed via `\d` against
  the live Postgres schema, not just by reading the Python source.
- **Both new menus and both new views render through Odoo's real view-resolution path**
  (`get_views()`), not just parsed as valid XML.
- **The pre-existing REST health endpoint still responds `200`**, confirmed live against the
  throwaway database with this phase's code installed.
- **All 84 tests in the module pass** against a fresh database: all 61 pre-existing tests
  (authentication, authorization, catalog endpoints, receipts, dispatches, API keys, menu
  visibility) at their original counts, plus 23 new tests for this phase, with zero failures and
  zero errors.
- **One real bug was found and fixed during this verification** — the `_check_access` naming
  collision described above — directly demonstrating why testing against the real, installed Odoo
  version (not static analysis alone) was required by this phase's own instructions.
