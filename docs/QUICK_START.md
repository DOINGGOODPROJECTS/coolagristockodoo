# Quick Start Guide

The fastest path to understanding how Cool Agristock fits together. For full detail, see
[INSTALLATION.md](INSTALLATION.md) (step-by-step setup) and [WMS_INTEGRATION.md](WMS_INTEGRATION.md)
(full developer integration guide).

## The basic workflow

```text
INSTALL COOL_AGRISTOCK CONNECTOR
          |
          v
ASSIGN USER PERMISSIONS
          |
          v
GENERATE API KEY
          |
          v
CONFIGURE EXTERNAL WMS
          |
          v
TEST API CONNECTION
          |
          v
EXCHANGE WAREHOUSE DATA
```

1. **Install Cool Agristock** — from the Odoo Apps marketplace, into your Odoo 19 instance. The
   download bundles its own required OCA dependencies, so there's nothing extra to fetch. See
   [INSTALLATION.md](INSTALLATION.md#1-download-cool_agristock-connector-from-odoo-apps).
2. **Assign user permissions** — grant the **Cool Agristock Administrator** access right to whoever will
   manage API keys. See [INSTALLATION.md](INSTALLATION.md#4-assign-the-appropriate-user-permissions).
3. **Generate an API key** — from **Cool Agristock → API Management → Generate API Key**,
   choosing an expiration date or **Never Expires**. See
   [INSTALLATION.md](INSTALLATION.md#6-generate-an-api-key).
4. **Configure your external WMS** — with your Odoo instance's base URL
   (`https://YOUR_ODOO_URL/cool_agristock/api/v1`) and the API key, using Bearer-token authentication.
5. **Test the API connection** — confirm both the health check and an authenticated call succeed
   (example below).
6. **Exchange warehouse data** — your WMS calls the REST API to read products/warehouses/inventory
   and to create and validate receipts and dispatches. See
   [WMS_INTEGRATION.md](WMS_INTEGRATION.md) for the full set of operations.

## A minimal example: authenticating against the products endpoint

Using placeholder values — replace them with your own instance URL and a real generated key (never
commit real values for these):

```bash
export ODOO_URL="https://YOUR_ODOO_URL"
export API_KEY="YOUR_API_KEY"

curl -s "$ODOO_URL/cool_agristock/api/v1/products" \
  -H "Authorization: Bearer $API_KEY"
```

Expected response:

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

If you get a `401` HTML page instead of this JSON, double-check the Bearer token — see
[INSTALLATION.md's Troubleshooting section](INSTALLATION.md#troubleshooting).

## What Cool Agristock is not

- It is not a WMS itself — it's the integration layer between your existing WMS and Odoo Inventory.
- It does not push data to your WMS on a schedule — every exchange is initiated by your WMS calling
  the REST API.
- It does not auto-resolve partial receipts/dispatches — quantities must match exactly. (Lot/serial
  tracking **is** supported, as of Phase F — see
  [LOT_BATCH_SYNCHRONIZATION.md](LOT_BATCH_SYNCHRONIZATION.md).) See
  [WMS_INTEGRATION.md's Known limitations](WMS_INTEGRATION.md#known-limitations) for the full list.

## Next steps

- Full installation walkthrough: [INSTALLATION.md](INSTALLATION.md)
- Full developer integration guide: [WMS_INTEGRATION.md](WMS_INTEGRATION.md)
- Complete API reference: [API.md](API.md)
