# Integration Services

If your WMS doesn't already speak Cool Agristock's documented REST API, connecting it is
custom integration work — a [paid professional service](PROFESSIONAL_SERVICES.md), not something
the free module does automatically. This page explains the process and what to include in a
request.

**Security note:** never include real API keys, passwords, database credentials, or other secrets
anywhere, including by email. Describe authentication methods generically (e.g. "API key in a
header," "username/password over HTTPS") rather than pasting real values — even in a private email,
there's no reason to send the actual secret itself.

## The process

1. **Customer submits an integration request** — by email (see
   [How to request](#how-to-request) below) using the questionnaire in this document.
2. **Cool Agristock reviews the customer's WMS** — based on the questionnaire answers and any
   public documentation the customer can point to for their WMS's own API or integration points.
3. **Technical compatibility is assessed** — whether the WMS can call Cool Agristock's REST API
   directly, or needs a translation layer (adapter) in between. **No integration is promised until
   this assessment is complete** — compatibility depends entirely on the specific WMS's own API or
   lack of one, so it cannot be judged from the questionnaire alone before this step.
4. **Required API adaptations are identified** — on the WMS side (most common, since Cool Agristock
   Connector's API itself isn't modified per customer — see
   [Known limitations](API.md#known-limitations) for what the API does and doesn't support today).
5. **Project scope is agreed** — what's being built, by when, and any constraints, agreed directly
   with the customer before work starts. (No pricing or SLA is published; this is discussed per
   request.)
6. **Integration is developed** — against the documented API in [API.md](API.md), on the agreed
   scope.
7. **Integration is tested** — using disposable test data, never real production inventory.
8. **Customer validates the integration** — the customer's own acceptance testing against their
   real workflows (see [CUSTOMER_ONBOARDING.md, step 8](CUSTOMER_ONBOARDING.md#step-8--test-supported-inventory-workflows)).
9. **Deployment is completed** — rolled out to the customer's production environment once
   validated.
10. **Optional support is provided** — ongoing maintenance/support after deployment is itself an
    optional, separate service (see [PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md)).

## Customer requirements questionnaire

Include this information in your integration request issue:

```markdown
**WMS name and version**


**Hosting environment** (your WMS's hosting, and your Odoo hosting: self-hosted / Odoo.sh)


**Available API documentation for your WMS**
(link to it, or attach/describe it — don't paste proprietary docs you're not allowed to share
publicly)

**Your WMS's authentication method**
(describe generically, e.g. "API key in header," "OAuth2" — no real credentials)

**Required inventory workflows**
(e.g. receiving, dispatching, stock lookups, product sync — which of Cool Agristock's
documented operations you need: see [Supported REST endpoints](WMS_INTEGRATION.md#supported-rest-endpoints))

**Number of warehouses**


**Estimated transaction volume**
(e.g. receipts/dispatches per day — helps assess whether current limitations like the 100-record
list cap or lack of pagination, see [Known limitations](API.md#known-limitations), would matter)

**Customization requirements**
(anything beyond the documented API's existing behavior — e.g. workflow mapping, data
transformation, partial-quantity handling)

**Testing requirements**
(how you plan to validate the integration before go-live — e.g. a staging Odoo database, specific
workflows that must be demonstrated, who signs off)

**Deployment requirements**
(target go-live timing if any, who performs the production cutover, and any downtime constraints)
```

## How to request

Email the questionnaire above, filled in, to **Cool Agristock** (the team behind Cool Agristock
Connector):

<team@agricarecentres.com>

Use subject line `Integration request: <your WMS name>`. Email, rather than a public GitHub issue,
keeps your hosting details, authentication method, and transaction volume out of a public forum.

This is reviewed as a professional services request, not a bug report — see
[PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md) for what "paid" does and doesn't mean here.
