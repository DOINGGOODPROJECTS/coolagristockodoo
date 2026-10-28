# Installation Guide

This guide is for a business that wants to connect its existing Warehouse Management System (WMS)
to Odoo 19 using Cool Agristock. It assumes **no prior Odoo development experience** — only
that you (or someone at your organization) has administrator access to your Odoo 19 instance.

If you only need the short version, see [QUICK_START.md](QUICK_START.md). For the full REST API
reference, see [API.md](API.md). For the integration narrative aimed at the developer configuring
your WMS side, see [WMS_INTEGRATION.md](WMS_INTEGRATION.md).

## Before you start: how is your Odoo hosted?

How you get Cool Agristock onto your instance depends on your hosting:

| Hosting | Supported? |
|---|---|
| Self-hosted / on-premise Odoo 19 | Yes — verified below. You (or your IT provider) have full access to the server's addons path. |
| Odoo.sh | The marketplace listing offers a "Deploy on Odoo.sh" option, which requires signing in with your Odoo.com account and authorizing via GitHub. We have not independently verified this deployment path end-to-end — if you use Odoo.sh, follow Odoo.sh's own documentation for adding a third-party module to your branch, or see [Free software and paid services](../README.md#free-software-and-paid-services) for paid installation help. |
| Odoo Online (odoo.com SaaS) | **Not supported.** Odoo Online does not support installing custom third-party modules with external dependencies. If this is your only hosting option, this guide does not apply to you — contact Odoo or an Odoo partner about moving to Odoo.sh or a self-hosted instance. |

The remaining steps are verified for a self-hosted Odoo 19 environment where a technical contact
can place files on the server. If that isn't you, forward this guide to whoever manages your Odoo
hosting.

## 1. Download Cool Agristock from Odoo Apps

Open the marketplace listing:

<https://apps.odoo.com/apps/modules/19.0/cool_agristock>

Click **Download for v 19.0**. This downloads a single zip file
(`cool_agristock-19.0.1.0.0.zip`) containing everything the module needs.

## 2. Extract the package and place it in your Odoo addons path

Cool Agristock depends on four Odoo Community Association (OCA) modules — `component`,
`component_event`, `connector`, `queue_job`. **You do not need to download or clone these
separately.** The marketplace zip you downloaded in step 1 already bundles all four, at exactly
the versions Cool Agristock requires (`component` 19.0.1.0.1, `component_event` 19.0.1.0.0,
`connector` 19.0.1.0.0, `queue_job` 19.0.2.1.6). This was verified directly: installing straight
from this zip's contents, with no other files added, succeeded cleanly in a from-scratch Odoo 19
test environment.

1. Extract the zip. You'll see five top-level folders: `cool_agristock`, `component`,
   `component_event`, `connector`, `queue_job`.
2. Copy **all five folders** into your Odoo addons directory (the folder your `odoo.conf`'s
   `addons_path` already includes, or a new folder you add to it). Keep every folder — removing
   any of the four dependency folders will make Cool Agristock refuse to install with a
   missing-dependency error.
3. Restart the Odoo service so it picks up the new addons path contents.

## 3. Install Cool Agristock in Odoo 19

1. Log in to Odoo as an administrator.
2. Enable developer mode (**Settings → General Settings**, scroll to the bottom, **Activate the
   developer mode**).
3. Go to the **Apps** menu.
4. Click **Update Apps List** (top-left), then **Update**.
5. Search for **Cool Agristock**.
6. Click **Install**. Odoo installs Cool Agristock together with the bundled `component`,
   `component_event`, `connector`, and `queue_job` modules in one step — no separate dependency
   installation step is needed.

If the module does not appear in the search results, one or more of the five folders from step 2
was not placed in a path Odoo scans, or the service was not restarted after step 2 — recheck those
before continuing.

## 4. Assign the appropriate user permissions

Installing the module does **not** by itself give anyone access to it. An administrator with
Odoo's own **Settings** access must grant the right group to the right people:

1. Go to **Settings → Users & Companies → Users**.
2. Open the user who should manage API keys (commonly, you — the business owner or IT contact).
3. Under **Access Rights**, find **Cool Agristock** and set it to **Administrator**.
4. Click **Save**.

This grants the **Cool Agristock Administrator** group, which is required to generate, revoke, or replace
API keys. (The separate **Cool Agristock API User** group is assigned automatically to a dedicated
integration account the first time you generate a key — see step 6 — you do not assign it to a
human yourself.)

## 5. Open API Management

In the main Odoo app switcher (top-left, the grid icon, or the app menu bar), open
**Cool Agristock → API Management**. You should see two entries:

- **API Keys** — the list of keys you've generated, with their status.
- **Generate API Key** — the form to create a new one.

If you don't see **Cool Agristock** in your app list at all, your user is missing the
Administrator access right from step 4.

## 6. Generate an API key

1. Go to **Cool Agristock → API Management → Generate API Key**.
2. Enter an **Integration Name** that identifies this connection (e.g. "Main Warehouse WMS").
3. If you work with more than one company in this Odoo database, choose the **Company** this key
   belongs to.
4. Continue to step 7 to set when the key expires.

## 7. Select an expiration date or Never Expires

- To set an expiration date: leave **Never Expires** unchecked, and fill in **Expiration Date**
  with a date in the future.
- To create a key that never expires on its own: check **Never Expires**.

A date-based key stops authenticating automatically once that date passes. A **Never Expires** key
remains valid until you explicitly revoke it. Prefer an expiration date unless your integration
genuinely needs a long-lived credential.

Click **Generate**.

## 8. Copy the generated API key

Odoo immediately shows the raw key in an **API Key Ready** dialog. **Copy it now and store it in
your WMS's secret/credential storage.** This is the only time the raw key is ever shown — Odoo
stores only a salted hash afterward, and the key cannot be retrieved again. If you lose it, revoke
it from the **API Keys** list and generate a replacement.

## 9. Configure your existing WMS

In your WMS's integration settings, enter:

- **API base URL** — your Odoo instance's address followed by `/cool_agristock/api/v1`, for example
  `https://your-odoo-instance.example.com/cool_agristock/api/v1`.
- **API key** — the value you copied in step 8.
- **Authentication method** — Bearer token: every request must carry an
  `Authorization: Bearer <your-api-key>` header.

How you enter these two values depends entirely on your WMS's own settings screen — this part is
specific to your WMS software. See [WMS_INTEGRATION.md](WMS_INTEGRATION.md) for what your WMS (or
its developer) needs to implement on its side.

## 10. Test the connection using the REST API

With a terminal (or your WMS's "test connection" feature, if it has one), check the health
endpoint first — it needs no API key:

```bash
curl -s https://your-odoo-instance.example.com/cool_agristock/api/v1/health
```

Expected response:

```json
{"status": "success", "service": "Cool Agristock", "api_version": "1.0", "message": "Cool Agristock API is running"}
```

Then confirm your API key works against a real, protected endpoint:

```bash
curl -s https://your-odoo-instance.example.com/cool_agristock/api/v1/products \
  -H "Authorization: Bearer YOUR_API_KEY"
```

A successful response looks like:

```json
{"status": "success", "count": 2, "products": [ ... ]}
```

If you instead get a `401 Unauthorized` HTML page, the Bearer token is missing, mistyped, expired,
or revoked. If you get `{"status": "error", "message": "Access denied: Cool Agristock API User role
required"}`, the key's underlying integration user is missing the required group — this should not
happen with a key generated through the wizard in step 6, so contact support if it does.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Cool Agristock doesn't appear after Update Apps List | One or more of the five extracted folders isn't in the addons path, or Odoo wasn't restarted after adding them. |
| Install fails citing a missing dependency | One of the bundled `component`, `component_event`, `connector`, `queue_job` folders was skipped during extraction or copying — re-extract the zip and copy all five folders together. |
| **Cool Agristock** menu is missing after install | Your user doesn't have the Cool Agristock Administrator access right (step 4). |
| `401 Unauthorized` (HTML, not JSON) | Bad, missing, expired, or revoked API key. |
| `403` JSON error | Authenticated, but the key's integration user lacks the Cool Agristock API User group — shouldn't occur with wizard-generated keys. |

## Getting help

Cool Agristock itself is free and open-source — see
[Free software and paid services](../README.md#free-software-and-paid-services) for what's
included at no cost, and what optional paid services (custom WMS integration, installation help,
support) are available. The project's GitHub Issues page is the current contact channel:

<https://github.com/DOINGGOODPROJECTS/coolagristockodoo/issues>
