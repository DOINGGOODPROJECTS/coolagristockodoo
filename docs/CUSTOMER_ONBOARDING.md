# Customer Onboarding

A simple, high-level checklist for a business taking Cool Agristock from "never heard of it"
to "connected to our WMS in production." Each step links to the detailed how-to guide — this page
is the checklist, not a restatement of those steps.

**Before you start:** Cool Agristock does not connect to just any WMS automatically. Your WMS
must either already speak the documented REST API, or be adapted to do so (self-built, or via
[professional integration services](INTEGRATION_SERVICES.md)). Installing the module does not, by
itself, establish a connection to anything.

## Step 1 — Download Cool Agristock

From the Odoo Apps Marketplace. See [INSTALLATION.md, step 1](INSTALLATION.md#1-download-cool_agristock-connector-from-odoo-apps).

*Done when:* you have the zip file, and you've confirmed your hosting type supports installing it
(self-hosted and Odoo.sh — not Odoo Online; see [INSTALLATION.md](INSTALLATION.md#before-you-start-how-is-your-odoo-hosted)).

## Step 2 — Install the application in a supported Odoo 19 environment

See [INSTALLATION.md, steps 2-3](INSTALLATION.md#2-extract-the-package-and-place-it-in-your-odoo-addons-path).

*Done when:* Cool Agristock shows as installed in **Apps**, and the **Cool Agristock** menu
appears for an administrator.

## Step 3 — Assign the appropriate permissions

See [INSTALLATION.md, step 4](INSTALLATION.md#4-assign-the-appropriate-user-permissions).

*Done when:* the person who will manage API keys has the **Cool Agristock Administrator** access right,
and can see **Cool Agristock → API Management**.

## Step 4 — Generate an API key

See [INSTALLATION.md, steps 5-8](INSTALLATION.md#6-generate-an-api-key).

*Done when:* you've copied the raw key somewhere safe (your WMS's own secret storage). Remember:
Odoo shows it exactly once.

## Step 5 — Review the API documentation

Read [API.md](API.md) (complete reference) or [WMS_INTEGRATION.md](WMS_INTEGRATION.md)
(integration-focused narrative) before writing any integration code — this tells you (or your WMS
vendor) exactly what the WMS side needs to implement: authentication, headers, endpoints, and error
handling.

*Done when:* you (or your WMS's developer) understand the request/response contract for every
endpoint you plan to use.

## Step 6 — Configure your external WMS

Enter your Odoo instance's API base URL and the generated key into your WMS's integration
settings. See [INSTALLATION.md, step 9](INSTALLATION.md#9-configure-your-existing-wms) and
[WMS_INTEGRATION.md](WMS_INTEGRATION.md#api-base-url).

*Done when:* your WMS is configured to send an `Authorization: Bearer <key>` header to your Odoo
instance's `/cool_agristock/api/v1` base URL.

## Step 7 — Test API connectivity

See [INSTALLATION.md, step 10](INSTALLATION.md#10-test-the-connection-using-the-rest-api) for the
health-check and authenticated-request examples.

*Done when:* `/cool_agristock/api/v1/health` returns `200`, and an authenticated call (e.g.
`/cool_agristock/api/v1/products`) returns your real data, not a `401`/`403`.

## Step 8 — Test supported inventory workflows

Using disposable/test data, exercise the actual workflows your business needs:

- Retrieve products, warehouses, and inventory.
- Create and validate a receipt (see [WMS_INTEGRATION.md](WMS_INTEGRATION.md#receipt-creation-and-validation)).
- Create and validate a dispatch (see [WMS_INTEGRATION.md](WMS_INTEGRATION.md#dispatch-creation-and-validation)).
- Confirm the resulting stock movements in Odoo's Inventory app match what you expect.

*Done when:* a full receipt and a full dispatch have gone end-to-end against test data, with stock
quantities changing as expected in Odoo.

## Step 9 — Begin operational use

Only after your own acceptance testing (step 8) passes against your real workflows. Cool Agristock
Connector and its maintainers do not perform this acceptance testing for you — it's your
business's own sign-off that the integration behaves the way your operations need.

## Troubleshooting

See [INSTALLATION.md's troubleshooting table](INSTALLATION.md#troubleshooting) for installation
and permission issues, and [WMS_INTEGRATION.md's error handling section](WMS_INTEGRATION.md#api-error-handling)
for REST API errors during steps 7-8.

If you're stuck beyond what those cover, see [SUPPORT.md](SUPPORT.md) for how to report the
problem. If the blocker is that your WMS doesn't speak the documented API at all, that's not a bug
— see [INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md).
