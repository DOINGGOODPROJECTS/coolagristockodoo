# Professional Services

Cool Agristock's software is, and always will be, free and open-source — there is no license
fee, subscription, or paid tier of the module itself. This page covers the **separate, optional**
paid services available to businesses that want hands-on help beyond what's in the docs.

## Free: the software and its documented functionality

Included at no cost, forever (LGPL-3.0):

- The Cool Agristock source code itself.
- Every documented REST API capability — see [API.md](API.md).
- Self-service API key management (generate, name, expire, revoke, replace) — no Cool Agristock
  involvement needed.
- Self-service integration: if your WMS already speaks the documented API, you can connect it
  yourself using [INSTALLATION.md](INSTALLATION.md) and [WMS_INTEGRATION.md](WMS_INTEGRATION.md).
- Community support via GitHub Issues — see [SUPPORT.md](SUPPORT.md).

## Optional paid services

These are professional services performed by people, not software features you unlock by paying.
No prices are listed here — pricing is discussed per request, since scope varies per engagement.

1. **Odoo installation and configuration** — setting up Cool Agristock (and its OCA
   dependencies) on your Odoo 19 instance, for businesses without in-house Odoo expertise.
2. **External WMS integration** — connecting your specific WMS to Cool Agristock's REST API
   end-to-end, including your own configuration on the WMS side.
3. **Custom WMS adapter development** — if your WMS can't be configured to speak the documented
   API directly, building a translation layer between its native protocol and this API.
4. **Inventory workflow customization** — adapting how receipts/dispatches map to your specific
   operational process, within what Odoo's stock workflow supports.
5. **API integration troubleshooting** — hands-on debugging of a specific integration that isn't
   behaving as expected, beyond what's answerable in a public GitHub issue.
6. **Technical training** — walking your team through API key management, the REST API, and
   day-to-day operation.
7. **Maintenance and technical support** — ongoing, dedicated support beyond best-effort community
   responses on GitHub Issues.

## What's never for sale

- The Cool Agristock module itself, or any license to use it — it's LGPL-3.0, always free.
- Any documented REST API functionality — see [Known limitations](API.md#known-limitations) for
  what genuinely isn't implemented yet; paid work can extend functionality but doesn't unlock
  anything already built and gated behind payment.
- Guaranteed compatibility with a WMS that hasn't been assessed — see
  [INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md) for how compatibility is actually evaluated.

## How to request a paid service

These services are provided by **Cool Agristock**, the team behind Cool Agristock. Email:

<team@agricarecentres.com>

Describe which service above you're interested in, and your Odoo/WMS setup. For WMS integration
specifically, use the structured request process and requirements questionnaire in
[INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md) instead, and include it in your email — it
collects what's actually needed to scope that kind of work, and keeps integration-specific details
(hosting, authentication method, workflows) out of public GitHub issues.

Free, community-level bugs, questions, and feature requests still go through GitHub Issues — see
[SUPPORT.md](SUPPORT.md). Email is for paid service requests specifically.

There is no published price list or service-level agreement; terms are discussed per request.
