# Customer Support Guide

How to get help with AgriWare Connector, and what to include so your report can actually be acted
on.

**The public channel for all non-sensitive technical issues is GitHub Issues:**

<https://github.com/DOINGGOODPROJECTS/coolagristockodoo/issues>

There is no service-level agreement (SLA) or guaranteed response time on GitHub Issues; community
and maintainer responses are best-effort.

For **paid professional services** specifically (not general technical support), contact
**Cool Agristock**, the team behind AgriWare Connector, by email: <team@agricarecentres.com>. See
[PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md) and [INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md).

**Never paste a real API key, password, or other credential into a GitHub issue.** Issues are
public. If a report needs to show an API call, redact the key (e.g. `Authorization: Bearer
[REDACTED]`) and redact any real customer/business data in logs or screenshots before posting.

Before filing anything, check whether your question is already answered:

- Installation steps and common install errors: [INSTALLATION.md](INSTALLATION.md#troubleshooting)
- The full REST API contract (request/response formats, every error code): [API.md](API.md)
- Integration architecture and error-handling guidance: [WMS_INTEGRATION.md](WMS_INTEGRATION.md#api-error-handling)
- Documented gaps that are not bugs: [API.md's Known Limitations](API.md#known-limitations)

## 1. Reporting installation problems

Open an issue titled `[Install] <short description>`. Include:

- Your Odoo version (should be 19.x) and hosting type (self-hosted, Odoo.sh, Odoo Online).
- Whether you installed from the Odoo Apps Marketplace zip or from source.
- The exact error message from the Odoo **Apps** screen or server log.
- Which step of [INSTALLATION.md](INSTALLATION.md) you were on.

## 2. Reporting API errors

Open an issue titled `[API] <short description>`. Include:

- The endpoint and HTTP method (e.g. `POST /agriware/api/v1/receipts`).
- The HTTP status code and the full JSON response body (`status`/`message`).
- The request body you sent, with `external_reference` kept but any real product/partner
  identifiers replaced with placeholders if they reveal business data you don't want public.
- What you expected to happen, per [API.md](API.md) or [WMS_INTEGRATION.md](WMS_INTEGRATION.md).

## 3. Requesting technical assistance

Community-level questions (e.g. "how do I configure X") belong as a regular GitHub issue titled
`[Question] <short description>`.

Paid, hands-on technical assistance (someone working directly on your instance or your WMS
integration) is a professional service, not covered by community support — see
[PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md).

## 4. Submitting bug reports

Open an issue titled `[Bug] <short description>` using this template:

```markdown
**Environment**
- AgriWare Connector version (see Apps > AgriWare Connector):
- Odoo version:
- Hosting (self-hosted / Odoo.sh / Odoo Online):
- Installed from (Marketplace zip / Git source):

**Steps to reproduce**
1.
2.
3.

**Expected behavior**


**Actual behavior**


**Logs / error output (redact any API keys, passwords, or real business data)**
```

## 5. Requesting new features

Open an issue titled `[Feature request] <short description>`. Include:

- The workflow you're trying to accomplish.
- Which documented [limitation](API.md#known-limitations), if any, is blocking you.
- What the ideal behavior would look like from your WMS's perspective.

Feature requests are not guaranteed to be implemented or to have a timeline. If you need a feature
built on a specific schedule, that's a paid engagement — see
[PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md).

## 6. Requesting custom WMS integrations

If your WMS doesn't natively speak the documented REST API, building an adapter or custom
integration is a paid professional service. Don't file this as a bug — see
[INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md) for the process and the requirements
questionnaire to include in your request.

## Contributing code

If you want to fix a bug or add a feature yourself: fork the repository, open a pull request
against `main`, and run the automated test suite against a throwaway database first (see the
[README](../README.md#development-and-testing)).
