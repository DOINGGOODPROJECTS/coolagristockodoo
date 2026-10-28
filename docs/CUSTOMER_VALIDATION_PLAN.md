# Customer Validation Plan — First 30 Days

**Status:** Draft, pending approval. This plan sits inside Month 2-3 of
[docs/COMMERCIAL_STRATEGY.md](COMMERCIAL_STRATEGY.md)'s six-month plan — it is the detailed,
week-by-week execution of that plan's early customer-facing activity, not a separate strategy.

**The numbers below are targets to test the plan against, not confirmed outcomes, projections, or
promises.** No prospect has been contacted as of this writing (see
[docs/COMMERCIAL_STRATEGY.md's Phase 6 verification](COMMERCIAL_STRATEGY.md#verified-odoo-partners-côte-divoire)
— five Odoo partners were verified to exist, none were contacted).

## Funnel targets for the 30-day window

| Stage | Target | What it means here |
|---|---|---|
| Qualified prospects (list) | 20 | Companies matching the target-segment criteria below, added to `commercial/LEAD_TRACKER.csv` with status `NEW` — not yet contacted. This is a *list-qualification*, distinct from a lead reaching `QUALIFIED` status in the tracker (see Terminology note). |
| Discovery conversations | 10 | A real conversation (call, video, or substantive email exchange) using the questionnaire in [INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md#customer-requirements-questionnaire) or its [French version](PROSPECTION_CLIENTS_FR.md#d-questionnaire-de-découverte-client). |
| Technical compatibility assessments | 5 | Of the 10 discovery conversations, the subset where enough information exists to judge whether the prospect's WMS can speak Cool Agristock's documented API, or would need Package 3 (custom adapter). |
| Commercial proposals | 2 | A written scope + indicative price (from `COMMERCIAL_STRATEGY.md` section 5, re-derived per the real discovery, not quoted verbatim) sent to a prospect. |
| Potential paid pilot | 1 | One prospect agrees to a paid engagement (any package). This is the actual validation signal the whole 30 days is designed to produce. |

**Terminology note:** "qualified prospect" in this plan's funnel table means *list-level
qualification* (fits the target segment — see criteria below). The `LEAD_TRACKER.csv` status
`QUALIFIED` means something narrower — *discovery is complete and a real need was confirmed*. Don't
conflate the two when reading the tracker against this plan's targets.

## Target-segment qualification criteria (for the 20-prospect list)

A company qualifies for the list if it meets **all** of the following, drawn directly from
`COMMERCIAL_STRATEGY.md` section 2:

1. Based in Côte d'Ivoire (this 30-day plan does not cover expansion markets).
2. Falls into one of the eight segments in `COMMERCIAL_STRATEGY.md` section 2 — prioritize segment
   7 (already using Odoo) and segment 2 (distributors) per that document's recommendation.
3. Has, or is actively evaluating, Odoo 19 (confirmed by inquiry, public case study, or an Odoo
   partner's reference list — not assumed from the sector alone).
4. Has some separate warehouse-management software or process worth connecting — a company with no
   WMS at all and no warehouse operation isn't a fit for this product regardless of sector.

A company that cannot be confirmed against criterion 3 (Odoo usage) goes on the list as **lower
priority** rather than being excluded — it may still be worth a conversation, but shouldn't count
toward the "20 qualified prospects" target until confirmed.

## Weekly plan

| Week | Activities | Responsible role | Success indicator |
|---|---|---|---|
| **Week 1** | Build the 20-prospect list against the criteria above, prioritizing the five verified Odoo partners' likely client base (ask the partners directly, where a conversation happens, rather than guessing); populate `LEAD_TRACKER.csv` with status `NEW` for each. | Founder | List reaches 20 named companies (not 20 generic "agribusiness" entries) |
| **Week 2** | Begin outreach using the templates in [PROSPECTION_CLIENTS_FR.md](PROSPECTION_CLIENTS_FR.md) (French) or their English equivalents; move contacted leads to `CONTACTED`; follow up on non-responses once, not repeatedly. | Founder (+ part-time outreach help if available, per `COMMERCIAL_STRATEGY.md` section 8) | ≥10 of the 20 moved to `CONTACTED`; ≥3 responses of any kind |
| **Week 3** | Run discovery conversations with everyone who responded positively; complete the questionnaire for each; move completed leads to `DISCOVERY` then `QUALIFIED` as appropriate. | Founder | Progress toward the 10-conversation target is visible in the tracker, even if not yet complete |
| **Week 4** | Finish remaining discovery conversations; complete technical compatibility assessments for qualified leads; draft and send proposals for the strongest 1-2 candidates; move leads to `PROPOSAL`. | Founder | The 5-assessment and 2-proposal targets are evaluated against actual numbers, not assumed met |

**If a pilot is agreed during Week 4,** it starts immediately per `COMMERCIAL_STRATEGY.md`'s Month
3 ("Pilot customer integrations") — this plan's 30 days end at the proposal stage; closing a deal
can reasonably take longer than 30 days and shouldn't be forced to fit the window artificially.

## Decision criteria at day 30

Compare actual tracker numbers against the targets table, honestly, and choose one:

- **Continue as planned** — if discovery-conversation and proposal numbers are within roughly
  half of target (e.g. ≥5 conversations, ≥1 proposal) and no systemic blocker was found (e.g.
  every prospect says their WMS can't do REST at all), continue into Month 3 of the main strategy
  unchanged.
- **Revise the channel mix** — if the prospect list (Week 1) was hard to build to 20 real
  companies, or outreach (Week 2) produced few responses, revisit `COMMERCIAL_STRATEGY.md` section
  6's channel ranking — the issue is likely channel choice, not the product or pricing.
- **Revise the offer or positioning** — if conversations happen but few pass technical
  compatibility, or proposals don't lead to interest, the issue is more likely product-fit or
  pricing than outreach — revisit sections 3 and 5 of the main strategy, not just the channels.
- **Pause and reassess** — if the 20-prospect list itself cannot be built (i.e., Côte d'Ivoire
  Odoo-using agribusinesses needing WMS integration turn out to be rarer than assumed), this is the
  honest signal the strategy was built to surface — report it plainly rather than lowering the
  targets retroactively to claim success.

None of these outcomes is predicted here — this section defines how to read the result, not what
the result will be.
