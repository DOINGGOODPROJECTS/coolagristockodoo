# Cool Agristock — Commercial Strategy

**Status:** Draft for management review. Not yet published or acted upon.

**A note on evidence.** This document distinguishes three kinds of statements throughout:
*verified facts* (checked against the live repository, the GitHub API, or public web sources, with
sources cited), *reasoned assumptions* (explicitly labeled as planning assumptions, not measured
data), and *illustrative figures* (financial/pricing numbers built from a single-source benchmark
or simple arithmetic, explicitly not validated market rates). No customer demand, existing
customer, or market-size statistic is asserted as confirmed anywhere in this document.

## 1. Executive Summary

Cool Agristock is a free, open-source Odoo 19 module (LGPL-3.0) that lets a compatible external
Warehouse Management System (WMS) exchange product, warehouse, and inventory data with Odoo
Inventory over a documented REST API. The software itself will never carry a license fee. This
strategy's only proposed revenue source is **optional professional services** — installation help,
custom WMS integration, adapter development, workflow customization, training, and support — sold
separately from the free software, consistent with every prior documentation task in this project
(see [PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md)).

The plan below targets agribusiness-adjacent sectors in Côte d'Ivoire first — where a real, Odoo
Apps Marketplace, public listing, and a prior clean-install test confirm this project exists and
works — and evaluates (without assuming) expansion into Ghana, Senegal, Nigeria, and other West
African markets. It proposes five service packages, ranks ten acquisition channels against five
criteria, lays out a six-month action plan sized for a small team, and models three financial
scenarios. Every price, cost, and projection in this document is explicitly an illustrative
planning estimate, not a validated market rate or a committed forecast.

## Phase 1 verification (prerequisite check)

Before building this strategy, the following was confirmed directly against the project:

- `docs/SUPPORT.md`, `docs/PROFESSIONAL_SERVICES.md`, `docs/CUSTOMER_ONBOARDING.md`, and
  `docs/INTEGRATION_SERVICES.md` all exist, and are committed and pushed to both `main` and `19.0`
  on GitHub as of commit `c2a9a18` (verified via `git log` and `git diff origin/main origin/19.0`
  returning empty).
- There is no record anywhere in this repository, its commit history, or its documentation of a
  task or milestone labeled "Step 113." If that label refers to tracking kept outside this
  repository, I have no visibility into it and cannot confirm or deny its completion from here.
- **What is not yet true:** these docs being on GitHub does not mean they are live on the
  `apps.odoo.com` marketplace listing — that listing is a separate, manually-published artifact
  (confirmed in earlier work this session) and still needs you to resubmit it through Odoo's
  publisher portal.

## 2. Target Customers

Ranked in the order given, for the primary market (Côte d'Ivoire) first, with expansion markets
evaluated separately below. "Difficulty of acquisition" is a reasoned assumption based on how
discoverable and reachable each segment is, not a measured conversion rate.

| Segment | Main warehouse challenge | Why Odoo integration helps | Likely integration requirements | Professional-services demand potential | Acquisition difficulty |
|---|---|---|---|---|---|
| **1. Agricultural cooperatives** | Often track stock on paper or spreadsheets across scattered collection points; poor visibility into aggregate inventory | Odoo Inventory + Cool Agristock gives a single system of record if they already run or adopt a WMS at collection points | Usually need a WMS selected/implemented first — likely a **Package 2 or 3** candidate | High for installation + WMS selection guidance | **Hard** — fragmented, often low digital maturity, requires in-person trust-building |
| **2. Agricultural produce distributors** | Manage inbound receipts from many small suppliers and outbound dispatches to retail/export; reconciliation errors | REST API enables near-real-time stock sync if they already use a WMS for the warehouse floor | Typically already have barcode/WMS software — needs a **custom adapter (Package 3)** unless it happens to speak the documented API | High — adapter work is the most labor-intensive, highest-value package | **Medium** — identifiable via trade associations and distribution hubs |
| **3. Food processing businesses** | Input/output inventory (raw produce in, processed goods out) often tracked in separate systems from ERP | Odoo's stock workflow plus Cool Agristock's receipt/dispatch model fits raw-material-in, product-out flows | May need workflow customization for processing-specific steps (not currently a documented Cool Agristock feature — see Known Limitations) | High for **Package 4** (workflow customization) | **Medium** — more formalized businesses, easier to find decision-makers |
| **4. Cold-storage operators** | Need accurate, timely inventory to avoid spoilage; often run specialized cold-chain WMS | Could use Cool Agristock as the Odoo-side bridge if their cold-chain WMS can be adapted | Cold-chain WMS software is usually proprietary/vertical-specific — high likelihood of needing **Package 3** | High, if WMS compatibility is confirmed | **Hard** — small number of operators, highly specialized software, may not have REST capability at all |
| **5. Agricultural warehouses (generic)** | General stock visibility, manual counts | Lowest-friction segment if they already have any REST-capable WMS | Depends entirely on existing WMS — could be **Package 2** (basic) if compatible | Medium | **Medium** |
| **6. Exporters and importers** | Need accurate stock for compliance/customs documentation and to avoid overselling | Odoo Inventory already commonly used for trade documentation; Cool Agristock bridges to warehouse-floor WMS | Integration requirements vary widely by existing software stack | Medium-High | **Medium** — identifiable via trade/export associations |
| **7. Agribusinesses already using Odoo** | Already have Odoo but their WMS isn't connected — manual double-entry | Lowest-friction segment: they already run Odoo, so only the WMS side needs work | Narrowest requirement — likely **Package 2** | Medium-High, and fastest to close | **Easiest** — existing Odoo users are reachable through Odoo partners (see Acquisition Channels) and don't need an Odoo sales pitch, only a WMS-integration one |
| **8. Companies using separate WMS and ERP (any ERP, not just Odoo)** | Classic double-entry/reconciliation pain | Requires them to also adopt Odoo Inventory, or at minimum evaluate it — a bigger ask | Both an ERP decision and a WMS-integration decision | High total contract value, but long sales cycle | **Hard** — two decisions bundled into one sale |

**Recommended initial focus:** segment 7 (agribusinesses already using Odoo) for fastest time-to-
first-customer, and segment 2 (distributors) for the clearest, highest-value integration work —
both reachable through the Odoo partner channel verified below.

### Geographic evaluation

**Primary market — Côte d'Ivoire:** A real Odoo partner ecosystem exists in Abidjan. All five
partners named in the original research pass (ConsulTech, Progistack, VEONE, ADG, Qanthom) have
since been individually confirmed directly on Odoo's own official partner directory
(odoo.com/partners), not just the third-party directory used initially — see
[Verified Odoo Partners](#verified-odoo-partners-côte-divoire) below for the full record. This
confirms Odoo has genuine market presence in Côte d'Ivoire; it does **not** confirm demand for
Cool Agristock specifically, which has not been tested with any real customer yet.

**Expansion markets — important currency/language caveat:** Côte d'Ivoire and Senegal both use the
West African CFA franc (XOF) and are primarily Francophone. **Ghana uses the Ghanaian cedi (GHS)
and Nigeria uses the naira (NGN) — neither is in the CFA zone**, and both are primarily Anglophone,
with different legal/business norms and a different (and in Nigeria's case, much larger) Odoo
partner landscape. Treating all four expansion markets as a single uniform "West Africa" plan would
be a planning error. Recommendation: validate Côte d'Ivoire first; if expanding, evaluate Senegal
next (closest market: same currency zone, same language, similar agribusiness structure) before
Ghana/Nigeria, which would need separate pricing, currency handling, and likely separate local
partnerships.

### Verified Odoo Partners (Côte d'Ivoire)

Verification method: each company was looked up directly on Odoo's own official partner directory
(`odoo.com/partners`), not the third-party directory (ERPResearch) used in the initial research
pass — that directory's listings are now only a secondary cross-reference. No company below is
marked UNVERIFIED; all five were found and confirmed as real, currently-listed Odoo partners.

| Company | Website | Country | Verified Odoo relationship | Public contact channel | Source of verification |
|---|---|---|---|---|---|
| ConsulTech | [consultech.ci](https://consultech.ci/) | Côte d'Ivoire (Abidjan) | Confirmed — official Odoo partner profile (tier label on the page reads "Ready"; 1 certified expert each for v17-v19) | +225 27 2243 4537 / odoo@consultech.ci | [odoo.com/partners/consultech-773923](https://www.odoo.com/partners/consultech-773923) |
| Progistack | [progistack.com](https://progistack.com/) | Côte d'Ivoire (Abidjan) | Confirmed — **Gold** partner | +225 2722231696 / info@progistack.com | [odoo.com/partners/progistack-6648660](https://www.odoo.com/partners/progistack-6648660) |
| VEONE | [veone.net](http://www.veone.net/) | Côte d'Ivoire (Abidjan, Cocody) | Confirmed — **Gold** partner | +225 20 0 04640 / sales@veone.net | [odoo.com/partners/veone-5100](https://www.odoo.com/partners/veone-5100) |
| ADG (Africa Digital Genius) | [adg.ci](https://adg.ci/) | Côte d'Ivoire (Abidjan, Cocody) | Confirmed — **Silver** partner | +225 07 08 20 5986 / mkone@adg.ci | [odoo.com/partners/adg-africa-digital-genius-7575930](https://www.odoo.com/partners/adg-africa-digital-genius-7575930) |
| Qanthom Technologies | [qanthom-tech.odoo.com](https://qanthom-tech.odoo.com) | Côte d'Ivoire (Abidjan, Port Bouët) | Confirmed — **Silver** partner | +225 07 08 39 0290 / am@qanthom-tech.com | [odoo.com/partners/qanthom-technologies-30707709](https://www.odoo.com/partners/qanthom-technologies-30707709) |

**What this does and doesn't establish:** this confirms each company is a real, currently-active
Odoo partner with a public contact channel. It does **not** confirm any of them has agreed to a
referral relationship, has agribusiness clients needing WMS integration, or has any awareness of
Cool Agristock — those are still Month 1-2 actions (Section 8), not completed outreach. **No
company listed here has been contacted** as part of this verification pass.

## 3. Value Proposition

**Core message** (unchanged from existing documentation, restated here as the commercial
positioning anchor):

> Cool Agristock is a free, open-source Odoo 19 application that enables compatible external
> warehouse management systems to exchange warehouse and inventory information with Odoo through a
> REST API.

**What to highlight**, all verified against the current implementation (`docs/API.md`):

- Free and open-source (LGPL-3.0) — no license fee, ever.
- Self-service API key management — generate, name, expire, revoke, replace, without contacting
  Cool Agristock.
- Product information retrieval.
- Warehouse information retrieval.
- Inventory visibility (on-hand quantities).
- Receipt creation and validation (incoming deliveries).
- Dispatch creation and validation (outgoing deliveries).
- Secure Bearer-token API authentication, built on Odoo's own API key infrastructure.

**What to say about compatibility, every time:** some WMS applications will not speak this REST API
natively and require custom integration development — this is not a defect, it's explicitly how the
product is designed (WMS-initiated, generic REST API; see
[Known limitations](API.md#known-limitations)). Oversell here is the single easiest way to damage
credibility with a technical buyer; every piece of outward-facing material should repeat this
caveat rather than bury it.

**Do not advertise:** pagination, partial receipts/dispatches, scheduled sync, or bidirectional sync
— none of these exist (see `docs/API.md`'s Known Limitations). Any sales material implying
otherwise would be a false claim about a currently free product that could also undermine trust in
the paid services built on top of it.

**Correction, Phase F:** lot/serial support **does** now exist — product/warehouse/supplier/UOM
synchronization, lot/serial tracking, staged inventory import, and receipt/dispatch
synchronization (including lot-aware receipts/dispatches) are all implemented and tested as of
Phases A–G. This list, and the website copy it was describing, predate that work. **Verify every
claim against `docs/API_ROADMAP.md`'s Development Roadmap section before publishing or updating
any outward-facing material** — each phase there is explicitly marked "Implemented" or "Proposed —
not implemented," so this strategy document never has to be the single source of truth for what's
actually shipped.

## 4. Revenue Model

Revenue comes exclusively from time-based or project-based professional services. No tier of the
module itself is paywalled, no feature is held back from the free version, and no subscription is
required to use the documented API. This is a deliberate choice consistent with every prior
decision in this project (see `docs/PROFESSIONAL_SERVICES.md`'s "What's never for sale" section) —
changing it would require an explicit, separate decision and is not recommended here.

**Illustrative currency conversion used throughout this document:** 1 USD ≈ 575–600 XOF (FCFA) in
2026, per multiple currency-data sources (see Sources); this document uses a rounded **1 USD = 600
FCFA** for simple arithmetic only. **Verify the live rate before quoting any customer** — the XOF is
pegged to the euro, so it moves with EUR/USD, not independently.

## 5. Professional Service Packages

Pricing below is built from a single third-party vendor blog's cited day rate for Abidjan-based
developers (100,000–200,000 FCFA/day, per Kolonell — see Sources) and the same source's cited
custom-module cost range (2.5–6M FCFA). **This is one vendor's publicly stated pricing, not
validated market research, not a benchmark survey, and not a confirmed rate Cool Agristock/Cool Agristock
has ever charged.** Treat every figure below as a starting planning assumption to be replaced with
real data after the first 2-3 engagements.

### Package 1 — Odoo Installation and Configuration

- **Target customers:** Segment 7 (already-Odoo businesses needing Cool Agristock installed) and any
  segment choosing self-hosted/Odoo.sh deployment without in-house Odoo expertise.
- **Services included:** Installing Cool Agristock and its bundled OCA dependencies, assigning
  user permissions, generating the first API key, confirming the health-check endpoint responds.
- **Expected deliverables:** A working, tested Cool Agristock install with documented
  credentials handoff (never the raw key itself in a deliverable document).
- **Estimated implementation effort:** 0.5–2 days, depending on hosting complexity.
- **Required technical resources:** One person familiar with Odoo deployment (Docker/on-premise or
  Odoo.sh).
- **Suggested pricing model:** Fixed fee per installation.
- **Indicative price:** 100,000–400,000 FCFA (≈ USD 170–670), planning estimate only.
- **Potential recurring revenue:** None directly; this is typically a one-time engagement, though
  it's a natural entry point to Package 5.

### Package 2 — Basic WMS Integration

- **Target customers:** Segments 5 and 7 — any customer whose WMS already speaks a REST API
  compatible (or near-compatible) with Cool Agristock's documented contract.
- **Services included:** Configuring the customer's existing WMS against Cool Agristock's REST
  API, testing the connection, validating one receipt and one dispatch end-to-end against test
  data, handing off to the customer's own acceptance testing (per `CUSTOMER_ONBOARDING.md`).
- **Expected deliverables:** A documented, tested connection; a short runbook for the customer's
  own team.
- **Estimated implementation effort:** 2–5 days.
- **Required technical resources:** One integration developer familiar with both REST APIs and the
  customer's WMS basics.
- **Suggested pricing model:** Fixed fee per integration, scoped after a short technical discovery
  call.
- **Indicative price:** 500,000–1,500,000 FCFA (≈ USD 830–2,500), planning estimate only.
- **Potential recurring revenue:** Natural lead-in to Package 5 (ongoing support).

### Package 3 — Custom WMS Adapter Development

- **Target customers:** Segments 2 and 4 (distributors, cold-storage) and any customer whose WMS
  cannot speak the documented API without a translation layer.
- **Services included:** Building a custom adapter between the customer's WMS's native protocol and
  Cool Agristock's REST API; this is new code, developed against the customer's specific WMS,
  not a change to Cool Agristock itself (see `docs/INTEGRATION_SERVICES.md`'s process).
- **Expected deliverables:** A working adapter, test results against disposable data, documentation
  of the adapter's own configuration.
- **Estimated implementation effort:** 2–6 weeks, highly variable — this is the package most
  dependent on the specific WMS's own API quality and documentation.
- **Required technical resources:** A developer comfortable with both REST integration and
  whatever protocol the target WMS uses (could be SOAP, a proprietary file format, a different
  REST dialect, etc.).
- **Suggested pricing model:** Scoped project fee after a paid or free discovery phase (recommend a
  small paid discovery fee to filter unserious inquiries, applied against the project fee if it
  proceeds).
- **Indicative price:** 2,500,000–8,000,000 FCFA (≈ USD 4,200–13,300), planning estimate only —
  wide range reflects genuinely wide variance in adapter complexity.
- **Potential recurring revenue:** Strong lead-in to Package 5; adapters typically need maintenance
  as either system updates.

### Package 4 — Advanced Inventory Workflow Customization

- **Target customers:** Segment 3 (food processors) and any customer whose operational workflow
  doesn't map cleanly onto Cool Agristock's current receipt/dispatch model.
- **Services included:** Customization work on top of (not a change to) the documented API —
  e.g. orchestration scripts, Odoo-side automation, or process documentation adapting the
  customer's workflow to what the API supports today.
- **Expected deliverables:** Documented workflow mapping, any custom Odoo-side automation built,
  user training on the adapted process.
- **Estimated implementation effort:** 1–4 weeks.
- **Required technical resources:** An Odoo developer with inventory/stock-module experience.
- **Suggested pricing model:** Scoped project fee.
- **Indicative price:** 1,500,000–5,000,000 FCFA (≈ USD 2,500–8,300), planning estimate only.
- **Potential recurring revenue:** Moderate — workflow changes tend to be more one-off than ongoing.

### Package 5 — Ongoing Technical Support and Maintenance

- **Target customers:** Any customer who has completed Package 1, 2, 3, or 4 and wants continuity
  beyond best-effort community GitHub support.
- **Services included:** Priority response to issues, monitoring the integration's health,
  applying OCA dependency or Odoo version updates, minor adjustments as the customer's operations
  change.
- **Expected deliverables:** A defined response-time commitment (to be set per contract — **do not
  publish a blanket SLA without the capacity to honor it**), periodic check-ins.
- **Estimated implementation effort:** Ongoing, typically a few hours per month per customer once
  stable.
- **Required technical resources:** Whoever did the original Package 2/3/4 work, ideally, for
  continuity.
- **Suggested pricing model:** Monthly retainer.
- **Indicative price:** 150,000–500,000 FCFA/month (≈ USD 250–830/month), planning estimate only.
- **Potential recurring revenue:** This is the only genuinely recurring line in the model — the
  one most worth protecting and growing once a handful of Package 2/3 customers exist.

## 6. Customer Acquisition Channels

Ranked using reasoned assumptions (not measured data, since there is no existing customer pipeline
to draw conversion data from). Scale: Low / Medium / High for each criterion.

| Channel | Acquisition cost | Ease of implementation | Lead quality | Revenue potential | Time to acquire |
|---|---|---|---|---|---|
| 1. Odoo Apps Marketplace | Low (already live) | Already done | Medium — self-selected, already Odoo-curious | Medium | Slow (passive) |
| 2. GitHub | Low | Already done | Low-Medium — mostly developers, not buyers | Low-Medium | Slow (passive) |
| 3. LinkedIn | Low-Medium (time cost) | Easy to start | Medium | Medium | Medium |
| 4. Direct agribusiness outreach | Medium-High (time-intensive) | Hard — requires local presence/contacts | High if targeted well | High | Slow |
| 5. Odoo implementation partners | Low-Medium | Medium — requires relationship-building | **High** — partners already have Odoo-using agribusiness clients needing exactly this kind of add-on | **High** | Medium |
| 6. Agricultural cooperatives | Medium-High | Hard | Medium (long sales cycles, segment 1 above) | Medium | Slow |
| 7. ERP consultants (non-Odoo) | Medium | Medium | Medium — only relevant for segment 8 (dual ERP/WMS decision) | Medium | Slow |
| 8. Technology integrators | Medium | Medium | Medium | Medium | Medium |
| 9. Agribusiness associations | Low-Medium | Medium (often one application/sponsorship to join) | Medium-High if association is active | Medium | Medium-Slow |
| 10. Referrals | Very low (no cost until a sale exists) | N/A until first customers exist | **Highest** once available | High | N/A initially — only works after Package 1-4 customers exist |

**Recommended five channels for the first six months**, in priority order:

1. **Odoo implementation partners** (channel 5) — verified real partners exist in Abidjan
   (ConsulTech, Progistack, VEONE, ADG, Qanthom — see Sources); they already have Odoo-using
   agribusiness clients and a direct incentive to recommend an add-on that doesn't compete with
   their own core Odoo work.
2. **Odoo Apps Marketplace** (channel 1) — zero additional cost, already live; optimize the listing
   (already done this session) and let it work passively.
3. **LinkedIn** (channel 3) — lowest-cost active channel; target agribusiness operations managers
   and Odoo consultants in Côte d'Ivoire specifically.
4. **Agribusiness associations** (channel 9) — higher trust than cold outreach, moderate effort.
5. **Direct agribusiness outreach** (channel 4) — highest effort but highest-quality leads for
   segments 2 and 3, worth the time investment once channels 1-4 are running.

**Deprioritized for the first six months:** referrals (no base yet to generate them from),
agricultural cooperatives (segment 1's acquisition difficulty is high — revisit once a reference
customer exists), ERP consultants and technology integrators (relevant mainly for segment 8, the
hardest and slowest segment).

## 7. Customer Sales Funnel

```text
CUSTOMER DISCOVERS COOL_AGRISTOCK
           |
           v
VISITS MARKETPLACE OR GITHUB
           |
           v
DOWNLOADS FREE APPLICATION
           |
           v
INSTALLS AND TESTS
           |
           v
REQUESTS OPTIONAL ASSISTANCE
           |
           v
TECHNICAL DISCOVERY
           |
           v
INTEGRATION PROPOSAL
           |
           v
PAID IMPLEMENTATION
           |
           v
OPTIONAL SUPPORT CONTRACT
```

**Managing leads at each stage** (assuming no existing customer data — this is a from-zero design):

- **Discovers / Visits:** No individual lead exists yet — this stage is only measurable in
  aggregate (marketplace views, GitHub stars/traffic). Nothing to manage per-lead here.
- **Downloads / Installs and tests:** Still anonymous unless the customer self-identifies (e.g. by
  filing a GitHub issue, which is already the documented support channel). Don't assume visibility
  into who downloaded — the marketplace does not currently expose per-download contact info.
  Treat any self-identification (an issue, an email) as the actual top of the trackable funnel.
- **Requests optional assistance:** This is the first real lead — log it immediately (see CRM
  recommendation below) with source channel, date, and a one-line description of what they asked.
- **Technical discovery:** A short call or email exchange using the `INTEGRATION_SERVICES.md`
  questionnaire. Log the questionnaire answers against the lead record.
- **Integration proposal:** A written scope + price (from the Package ranges above, adjusted per
  discovery). Log the proposal date and value.
- **Paid implementation → Optional support contract:** Log the won/lost outcome and, if won,
  whether a Package 5 retainer was attached.

**Recommended simple CRM workflow:** for a team this size, a full CRM platform is overkill at
launch. Recommend a single shared spreadsheet (or, since the product itself runs on Odoo, Odoo's
own free CRM app, which has the side benefit of being a live demo of Odoo to prospects) with one
row per lead: `Date | Source channel | Segment | Contact | Stage | Questionnaire done? (Y/N) |
Proposal value | Outcome | Support contract? (Y/N)`. Upgrade to a dedicated CRM only once lead
volume makes a spreadsheet unwieldy (a threshold to set once real volume is observed, not predicted
here).

## 8. Six-Month Action Plan

Sized for a small team: assumed **one technical founder/lead (full-time)** plus **occasional
part-time commercial/outreach support**, consistent with this being an early-stage, bootstrapped
services business layered on an existing free product. Costs below are additive planning estimates
in FCFA (rounded), not committed budget.

| Month | Activities | Deliverables | Responsible role | Est. cost (FCFA) | Success indicators |
|---|---|---|---|---|---|
| **1 — Commercial preparation and positioning** | Finalize this strategy; prepare LinkedIn presence; identify and list specific Abidjan Odoo partners to approach; prepare a one-page service overview (derived from `PROFESSIONAL_SERVICES.md`, not a new document) | LinkedIn company/profile presence; partner contact list; one-page overview | Founder | 0–50,000 (mostly time cost) | Strategy approved; outreach list of ≥10 named partners/contacts exists |
| **2 — Customer prospecting and outreach** | Contact the Odoo partners identified in Month 1; publish 2-3 LinkedIn posts; join 1-2 relevant agribusiness associations if low/no-cost options exist | First partner conversations held; association membership status known | Founder (+ part-time outreach help if available) | 50,000–200,000 (association fees, travel) | ≥3 partner conversations held; ≥1 inbound inquiry via any channel |
| **3 — Pilot customer integrations** | Convert the best lead(s) from Month 2 into a discovery call and, ideally, one pilot engagement (Package 1 or 2, priced conservatively or discounted explicitly as a pilot) | One pilot engagement scoped and started | Founder | 0 (pilot revenue may partially offset time cost) | ≥1 signed pilot engagement |
| **4 — Customer feedback and improvements** | Complete the pilot; gather structured feedback; update `docs/` and package definitions based on what the pilot actually revealed (real effort vs. estimated, real objections, real questions asked) | Pilot completed and documented internally; package pricing/scope revised with real data | Founder | 0 | Pilot delivered; at least one package's effort/price estimate replaced with real data |
| **5 — Partnership development** | Formalize a referral or co-selling arrangement with at least one Odoo partner from Month 1-2; revisit agribusiness association engagement with the pilot as a reference (with the pilot customer's permission) | A documented (even informal) partner arrangement | Founder | 0–50,000 | ≥1 partner agrees to refer or co-sell |
| **6 — Commercial evaluation and expansion planning** | Review actual results against this plan; decide whether to continue as-is, adjust packages/pricing, or begin Senegal evaluation (not Ghana/Nigeria yet, per the currency/language caveat in Section 2) | A short internal review memo; go/no-go decision on expansion | Founder | 0 | Documented decision made with real data, not projections |

**Note on team size:** if commercial/outreach capacity is actually zero (solo founder, no part-time
help), Months 2 and 5 will take proportionally longer — this plan assumes *some* non-founder time
for outreach; if that assumption is wrong, the plan should be re-timed, not just pushed through
unchanged.

## 9. Financial Projections

**These are hypothetical planning scenarios, not forecasts of confirmed business performance.**
They exist to stress-test whether the package pricing in Section 5 could plausibly sustain the
effort in Section 8 — not to predict actual results, which depend entirely on real market response
this document cannot measure in advance.

All figures in FCFA, rounded; 1 USD = 600 FCFA for reference only.

| Assumption | Conservative | Base case | Optimistic |
|---|---|---|---|
| Paying customers (6 months) | 1 | 3 | 6 |
| Average project value (Packages 1-4 blended) | 800,000 FCFA | 1,200,000 FCFA | 1,800,000 FCFA |
| Customers also on a Package 5 retainer | 0 | 1 | 3 |
| Monthly retainer value | — | 250,000 FCFA | 300,000 FCFA |
| **Integration + installation revenue (6 mo. total)** | 800,000 | 3,600,000 | 10,800,000 |
| **Support/retainer revenue (6 mo. total, avg. 2 months active)** | 0 | 500,000 | 1,800,000 |
| **Total revenue (6 months)** | **800,000** | **4,100,000** | **12,600,000** |
| Operating costs (travel, association fees, tools, misc., 6 mo.) | 300,000 | 500,000 | 800,000 |
| **Gross profit** | 500,000 | 3,600,000 | 11,800,000 |
| Founder time cost (not cash — opportunity cost, illustrative at 150,000/day × ~40 days over 6 mo.) | 6,000,000 | 6,000,000 | 6,000,000 |
| **Net operating contribution (cash, excl. founder time)** | **500,000** | **3,600,000** | **11,800,000** |
| **Net including founder opportunity cost** | **(5,500,000)** | **(2,400,000)** | **5,800,000** |

**Reading this table honestly:** in the Conservative and Base scenarios, cash contribution is
positive but does not cover a full-time founder's opportunity cost at the illustrative day rate
used elsewhere in this document — meaning, on these assumptions, the first six months likely
function as a paid validation phase (better than unpaid, worse than sustaining) rather than a
standalone living. Only the Optimistic scenario clears that bar. This is a reason to keep Month 1's
costs near zero and treat Months 1-6 as a deliberately low-overhead pilot, not a reason to inflate
the other two scenarios to look better.

## 10. Success Metrics

| Metric | Measurable now? | How |
|---|---|---|
| Marketplace downloads | **Yes** | Visible directly on the `apps.odoo.com` listing page (shown as a download count) |
| GitHub activity (stars, clones, traffic) | **Yes** | GitHub's own repo Insights/Traffic page (clone/view counts are time-limited to 14 days by GitHub, so needs periodic manual recording to build history) |
| Open/closed GitHub issues | **Yes** | Verified via the GitHub API this session (`has_issues: true`, currently 0 open) |
| Customer inquiries (any channel) | **No — needs new tracking** | Start the spreadsheet/CRM from Section 7 on day one |
| Qualified leads (discovery call completed) | **No — needs new tracking** | Same spreadsheet; define "qualified" as questionnaire completed |
| Integration projects started/completed | **No — needs new tracking** | Same spreadsheet |
| Paying customers | **No — needs new tracking** | Same spreadsheet |
| Average project revenue | **No — needs new tracking** | Derived from the spreadsheet once ≥3 projects exist (1 data point isn't an average) |
| Monthly recurring support revenue | **No — needs new tracking** | Same spreadsheet, Package 5 rows |
| Customer satisfaction | **No — needs new tracking, and a method** | Needs an explicit decision: even a simple post-engagement 1-5 rating is better than nothing, but there is no mechanism for this today |
| Support response times | **No — needs new tracking** | GitHub issue timestamps are measurable retroactively; email response times are not tracked anywhere today |

## 11. Risks and Mitigation

| Risk | Likelihood/impact (reasoned, not measured) | Mitigation |
|---|---|---|
| **Low brand awareness / unproven track record** | High likelihood, medium impact | Lead with the Odoo-partner channel (Section 6) rather than cold outreach — borrowed credibility matters more than ads for an unproven product |
| **Local Odoo partners build competing in-house integrations instead of referring** | Medium likelihood, medium impact | Position Cool Agristock explicitly as complementary (open-source, they can inspect/extend it) rather than as a competitor to their implementation services — most partners make money on implementation/support, not on building REST connectors from scratch |
| **Documentation is English-only in a primarily Francophone target market** | **Confirmed fact, not a projection** — every doc in this repo is English-only; Côte d'Ivoire and Senegal are Francophone | Translate at minimum `QUICK_START.md` and `CUSTOMER_ONBOARDING.md` to French before scaling outreach in Month 2-3; do not wait until a French-speaking customer asks and then scramble |
| **Currency/economic volatility (XOF pegged to EUR, moves with EUR/USD)** | Medium likelihood, low-medium impact | Quote in FCFA to local customers (removes their FX risk), re-verify the live rate before every quote rather than relying on this document's rounded figure |
| **Reliance on unmodified OCA dependencies (component/connector/queue_job)** | Low likelihood (pinned versions, verified compatible), low impact today | Already mitigated by pinning exact commits (see `README.md`); re-verify compatibility before any future Odoo version bump |
| **No existing support capacity for a published SLA** | Medium likelihood if oversold, high impact if promised and missed | `docs/PROFESSIONAL_SERVICES.md` already correctly avoids publishing an SLA — keep it that way until real response-time data exists from actual Package 5 customers |
| **Single-founder dependency (bus factor)** | Confirmed structural fact for a small team | Document institutional knowledge (already underway via this `docs/` set); this is a long-term risk to flag to management, not one this document can solve |
| **Financial projections treated as commitments by stakeholders** | Medium likelihood if this document is read superficially | This document labels every financial figure as illustrative in three separate places (header note, Section 9 intro, Section 9 closing paragraph) — management reviewing this should treat Section 9 as a stress-test, not a budget |

## 12. Recommended Next Actions

1. **Decide on this document's status** — review and either approve, request changes, or reject
   before any part of it is acted on publicly (per the task's explicit instruction to wait for
   approval).
2. **Resubmit the `apps.odoo.com` marketplace listing** (manual step on your end — not something
   previously completed; the live listing still shows the pre-rebrand author name as of last
   check) so the public-facing material matches what's in this repository.
3. **Translate `QUICK_START.md` at minimum into French** before beginning Month 2 outreach to
   Francophone prospects — this is a concrete, low-cost gap identified above, not a hypothetical
   one.
4. **Build the lead-tracking spreadsheet from Section 7** before the first outreach message is
   sent, so Month 1 data isn't lost to memory.
5. **Contact the specific, named Odoo partners verified in this document** (ConsulTech, Progistack,
   VEONE, ADG, Qanthom — see [Verified Odoo Partners](#verified-odoo-partners-côte-divoire) for
   confirmed contact details) as the first concrete Month 1/2 action. Contact details were pulled
   directly from each company's official Odoo partner profile; reconfirm they're still current
   immediately before outreach, since profiles can change.
6. **Do not quote any price from Section 5 as final** — re-derive pricing after the first real
   discovery call, since the entire pricing section is built from a single external benchmark, not
   this business's own validated costs.

---

### Sources

- [usd to xof — OFX](https://www.ofx.com/en-sg/exchange-rates/usd-to-xof/)
- [USD/XOF Exchange Rate — Pound Sterling Live](https://www.poundsterlinglive.com/data/currencies/usd-pairs/USDXOF-exchange-rate)
- [Ivory Coast currency — Trading Economics](https://tradingeconomics.com/ivory-coast/currency)
- [USD to XOF converter — exchange-rates.org](https://www.exchange-rates.org/converter/usd-xof)
- [CFA BCEAO Franc to US Dollar, 2026-07-31 — ValutaFX](https://www.valutafx.com/history/xof-usd-2026-07-31)
- [USD to XOF Forecast — CoinCodex](https://coincodex.com/forex/usd-xof/forecast)
- [ConsulTech — official Odoo partner profile](https://www.odoo.com/partners/consultech-773923)
- [Progistack — official Odoo partner profile](https://www.odoo.com/partners/progistack-6648660)
- [VEONE — official Odoo partner profile](https://www.odoo.com/partners/veone-5100)
- [ADG Africa Digital Genius — official Odoo partner profile](https://www.odoo.com/partners/adg-africa-digital-genius-7575930)
- [Qanthom Technologies — official Odoo partner profile](https://www.odoo.com/partners/qanthom-technologies-30707709)
- [Progistack — ERPResearch (secondary, cross-referenced only)](https://www.erpresearch.com/odoo-partners/progistack)
- [ADG Africa Digital Genius — ERPResearch (secondary, cross-referenced only)](https://erpresearch.com/odoo-partners/adg-africa-digital-genius)
- [Qanthom Technologies — ERPResearch (secondary, cross-referenced only)](https://erpresearch.com/odoo-partners/qanthom-technologies)
- [VEONE — ERPResearch (secondary, cross-referenced only)](https://erpresearch.com/odoo-partners/veone)
- [Custom software development in Ivory Coast 2026 — Kolonell](https://kolonell.com/en/blog/custom-software-development-ivory-coast-2026)
- [ERP programmer salary info, Ivory Coast — Paylab](https://www.paylab.com/ci/salaryinfo/information-technology/erp-programmer)
