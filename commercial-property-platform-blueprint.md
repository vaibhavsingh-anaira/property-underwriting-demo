# Commercial Property Underwriting Control Platform — Build Blueprint (three products)

**Date:** 26 Sep 2026 · **Basis:** *Insurance Overview* deck (21 slides), *Commercial Property Data Points* catalogue, and a September 2026 competitor teardown · **Scope:** U.S. middle-market and large commercial property, admitted and E&S, including business written through MGAs and coverholders

**Status:** all three products are built as a working showcase on one shared core. Each has the same demo structure: guide, dashboard, pipeline, narrated workflows with client briefs, rule studio and a real-mode sandbox. What is real and what is mocked is set out in §20, §22 and §23.

---

## Platform at a glance (one-pager)

**Know what changed before you renew, and what it's worth.**

---

### The problem

- Property rates are falling (U.S. −13%, cat-exposed −20% in Q2 2026), so there's no cushion left to absorb stale values, weak terms or quiet rate erosion.
- The evidence for each renewal sits in a dozen places: policy system, rater, claims, engineering, cat models, guidelines, broker emails. Underwriters rebuild it by hand, often only once the broker's SOV arrives about 30 days out.
- Leakage goes unseen until a loss: values that never moved, deductibles below today's guidelines, a binder that doesn't match the issued policy, referrals nobody made.

### What the platform does

For every renewing account it compares **what you wrote last year, what you actually issued, and what you hold today**. Then it tells the underwriter what changed, what that's worth in dollars, and what to do. Every number links back to the page, cell or system record it came from.

### Three products, one core

| # | Product | Question it answers | When it acts | Main output |
|---|---|---|---|---|
| 01 | **Renewal Integrity** (launch first) | *Is the renewal what we think it is?* | T-150 → bind → issuance → in-force | One action record per renewing account: exposure, real rate change, terms, contract, authority |
| 02 | **Decision Assurance** | *Is this new-business decision ready, and is the commitment within our rules?* | Submission → intended action → bind | Draft decision pack before review; **Pass / Pass with flags / Refer–Hold** on the intended action |
| 03 | **Delegated Authority Control** | *Is the coverholder writing the business we authorised?* | Every monthly bordereau, during and after writing | Breach register per policy, monthly authority report and scorecard per coverholder |

All three share one evidence ledger (every fact with its source), one rule engine (the carrier's guidelines as tested code), one authority engine and one materiality model. Each new product adds inputs and outputs; the core is not rebuilt.

**Decision Assurance, example case:**

> **Halvorsen Precision · new business · PASS WITH FLAGS**
>
> - **Contradiction:** the application says fully sprinklered, but the inspection shows one site partially sprinklered. Priced by re-rating the risk on both values.
> - **Pricing:** technical $520K, suggested $500–540K. The intended quote is $505K with a $250K deductible: −2.9% against ±5% permitted.
> - **Checks:** evidence, guidelines and authority all pass.
> - **Remaining condition:** roof-replacement schedule before bind. **The decision owner is the underwriter.**

**Delegated Authority, example policy:**

> **Meridian Gulf Underwriting (MGA) · policy BREACH**
>
> - **Class and territory:** approved.
> - **Limit:** written above authority.
> - **Deductible:** below the minimum.
> - **Premium:** below the approved rating range.
> - **Referral:** required, but no approval located.
> - **Commission:** deducted above the contract rate.
> - **Recommended:** carrier review, then premium and commission reconciliation. Each value links to the bordereau cell and the agreement clause.

### What an underwriter sees (example account)

> **ABC Manufacturing · renews 1 Nov 2026 · ACTION REQUIRED**
>
> - **Exposure:** insured values $120M → $151M (+26%), 1 new Tampa location not yet in the cat model
> - **Real price change:** premium looks **+9.8%**, but like-for-like it's **26.8% rate given away** (insured values +26%, modelled risk +66%)
> - **Terms:** wind deductible 2% is below the new 3% guideline. The issued policy grants $15M business interruption; the binder said $10M.
> - **Risk quality:** 2 new water losses, 2 engineering actions overdue
> - **Portfolio:** Tampa accumulation over threshold, so senior referral is needed
> - **Recommended:** reprice, raise the deductible, refer. **Underwriter decides.**

Clean accounts are **fast-tracked** (typically 40–50% of renewals), so work goes only where something changed.

### What the CUO sees

- The whole renewal book in one queue, ranked by dollars at stake and notice deadlines.
- A dollar pipeline: *identified → validated → approved → actually corrected*.
- The book's **real** rate change, calculated rather than self-reported, traceable to every account.
- Exceptions by underwriter, broker and region; accumulation hot spots before they are bound.

### How it works

1. **Reads** your existing systems and documents (policy, claims, rater, engineering, cat, guidelines).
2. **Reconciles** them into one evidence record per location, noting where sources disagree.
3. **Compares** last term against today: exposure, price, terms, risk quality, appetite.
4. **Quantifies** each finding in dollars and checks it against your guidelines and authority matrix.
5. **Routes** actions to the right underwriter, with referral memos pre-filled.

It runs in three passes: 150 days out on data you already hold, when the renewal submission arrives, and again at bind and issuance. It also flags mid-term events such as a vacancy or a large claim.

### What it's not

- It doesn't replace your policy system, rater, cat model or workbench. It sits beside them.
- It doesn't make decisions. Every recommendation is accepted or rejected by an underwriter, with a reason.
- It doesn't send your data anywhere else. It's deployed in your own cloud and never shared across carriers.
- It doesn't replace a bordereau-management service (VIPR, Tide) or an intake product (Cytora). It reads their output and checks it against the contract.

### How we start: no integration needed

| Step | Time | What you provide | What you get |
|---|---|---|---|
| Backtest | 6–8 weeks | 12–24 months of past renewals (extract plus documents) | Dollars you would have caught, shown account by account |
| Shadow | 90 days | Live renewals | Platform findings compared with what your team found |
| Live | 2 quarters | Treated vs control accounts | Measured impact on price adequacy, retention and prep time |

**What we measure:** dollars actually corrected at renewal · real rate change and price adequacy · retention of profitable accounts · renewal prep time · errors caught before issuance.

---

## 0. Strategic recommendation

**What to build:** an **Evidence Ledger and Control Engine** for commercial property. It records, for every account and location:

- what the carrier **believed** it was writing (submission and pricing at the last decision);
- what it actually **contracted** (the quote, binder, and policy plus endorsements);
- what it **holds today** (claims, engineering, external data, the latest SOV).

It then checks, with evidence and a dollar figure, whether price, terms, authority and portfolio position still match what the carrier intended.

**First surface: Renewal Integrity.** It produces one action record per renewing account and an action queue for the book.

**Then, on the same ledger and engine:**
- **Decision Assurance:** new business, before the carrier commits.
- **Delegated Authority Control:** business bound by MGAs and coverholders on the carrier's paper.

The deck's sequence (renewal → decision assurance → delegated authority) holds. It follows MVP difficulty (low → high → medium) and data moat (medium-high → highest → high). Renewal is sold first because its dollars can be proven on a backtest without live integration. All three are built in the showcase (§22–§23), so the sequence is a sales and pilot order, not a technical dependency.

**Why this beats a generic platform.** The competitor research (§2) shows that every well-funded vendor stops before this point:

| Layer | Owned by (2026) | Gap left behind |
|---|---|---|
| Intake / digitisation | Cytora (Applied), Convr, Guidewire UWC, Moody's Risk Data Refinery | These digitise the new submission. None keeps a field-level history across years. |
| Workflow / appetite | Federato (now an "AI-native core"), Kalepa, Send (Duck Creek) | They score appetite and winnability at submission. They don't reconcile quote, binder and policy. |
| Decision support | Sixfold, AIG Assist | They summarise and flag risk. There's no system of record and no dollar reconciliation. |
| Pricing / RARC | hx (Renew + hyperoperator), Akur8, Earnix | They compute technical price. The exposure and terms adjustments inside RARC are still **typed in by the underwriter, so they can't be audited**. |
| Physical change | Nearmap/Betterview, CAPE (Moody's) | Imagery shows roof and site change. It doesn't cover contract, value or pricing change. |
| QA after the fact | Athenium CairnQA | Audits files after they're written. It doesn't stop the renewal. |

**The wedge in one sentence:** *a computed, evidence-linked, auditable split of every renewal into exposure change, terms change, pure rate change and risk-quality change, plus a check of the contract as quoted, bound and issued.* No vendor we found publishes this, and Lloyd's MS3 and carrier CUOs already need it.

**Deliberately out of scope:** intake, rating, policy admin, billing and claims handling. We **read** from those systems and never replace them.

---

## 1. Product boundary

| We are | We are not |
|---|---|
| The system of record for **evidence and risk state over time** | A policy admin system, rater or workbench |
| Deterministic controls plus AI extraction and critique | An autonomous underwriter |
| One action object per account, with dollar impact | Another dashboard of scores |
| Installed next to Guidewire, Duck Creek, hx or Excel raters | A rip-and-replace project |
| Priced on book analysed and leakage corrected | Priced per seat |
| Oversight of delegated business against the contract | A bordereau-processing bureau or a coverholder admin system |

**Design rule:** the rule engine only ever runs on **resolved, source-linked data**, never on raw documents. This follows §35 of the data catalogue.

---

## 2. How competitors actually work, and what to take from each

### 2.1 Flow teardown

| Vendor | Real flow | Worth copying | Where it stops |
|---|---|---|---|
| **Cytora** (Applied, Sep 2025) | Ingest (email, ACORD, Excel, PDF) → classify the request type → one schema per flow → enrich → clearance (duplicates, broker licence, link to in-force) → route by complexity. **Autopilot** (Mar 2026) links information arriving at different times into one risk record and keeps the model's reasoning in the audit trail. | "One risk record assembled across channels and time"; one schema per transaction type; routing proportional to how much the risk changed | The renewal change check is described only as a "degree of change" compared with policy data. There's no field-level diff, pricing or contract check. |
| **Federato** | Log submission → apply appetite rules → winnability score → 2×2 appetite × winnability matrix → prioritised Action Center. Appetite tracks the portfolio (e.g. $46M of a $50M target written, so the class tightens). | **Queue ordered by value, not a dashboard**; portfolio-aware thresholds | Scores at submission only. It's moving into policy admin and claims, so it's becoming a competitor to cores. |
| **Sixfold** | Upload guidelines → configuration generated automatically → per-submission appetite score, signals with explanations, narrative, next action. Isolated environment per carrier. | Guidelines as input, explained signals, isolation per tenant | Decision support only. No state, no history, no contract. |
| **Kalepa** | Ingest → clearance → triage (likelihood to bind × appetite) → risk dashboard → rating → quote/bind → portfolio guardrails; red/yellow/preferred flags | The flag taxonomy; guardrails tied to appetite targets | Casualty-heavy. No renewal or delegated authority. |
| **hx Renew / hyperoperator** | Actuaries build models in Python; submissions priced by API; technical vs achieved price and RARC dashboards; hyperoperator works in 4 modes (straight-through, pause for human, ad-hoc questions, **always-on book monitoring**) | Model versioning, batch what-ifs, RARC reporting | Relies on the underwriter to enter the exposure and T&C adjustments. No wording or contract reconciliation. **Mode 4 is the nearest encroachment on our space, so integrate with hx rather than compete.** |
| **Send** (Duck Creek, Jul 2026) | Risk-centred workspace; delegated authority module ingests bordereaux, maps them to a model and checks them against binder authority as they arrive | Keeping the original file for reconciliation; checking authority as data arrives | Tied to a core system now. Contract reconciliation isn't published. |
| **Guidewire UWC** | Agents for ingestion, triage, clearance and summarisation → PolicyCenter. Still early access. | — | Pre-bind only. Renewals run in PolicyCenter's standard renewal job. |
| **Archipelago** | SOV cleansing in 7 steps: flag blanks and placeholders → map free text to ISO construction/occupancy → flag valuations older than 12 months → verify geocodes → fill hazard fields → cross-check against inspections and permits → **record source and date of every correction**; gaps prioritised by TIV × hazard | Copy these checks directly into the SOV engine (§7.1) | Built for brokers and insureds. No carrier-side diff across years. |
| **Moody's IRP** | Risk Data Refinery (SOV/slip → EDM, about 95% first pass); UnderwriteIQ pricing cascade Technical → Corporate → Offered; Data Quality Toolkit **weights data gaps by their effect on modelled loss** | Pricing cascade; weighting data quality by dollar impact | Exposure and CAT only. |
| **Nearmap/Betterview** | Imagery up to 3× a year → detect change → alert before renewal → automate renewals with no change, inspect only where risk deteriorated | **Fast-track what hasn't changed and create work only on change**. Our unit of work should behave the same way. | Physical condition only. |
| **Athenium CairnQA** | Reviews all files, not a sample → evaluate against carrier standards → findings that each cite a guideline → expert feedback; every workflow component versioned and checked against a control set of files | **Version everything and validate every change against a control set** (§11.5) | After the fact. Doesn't block a bind. |
| **FM** | RiskMark site score (fire, nat hazard, occupancy) from its own engineering; benchmarking against tens of thousands of sites | Engineering-first view of risk quality; benchmarking against peers | FM's in-house model, not available to buy. |

### 2.2 What carriers are signalling

- **AIG** (Anthropic + Palantir): multi-agent pipeline (ingest, evaluate against guidelines, price against portfolio targets, synthesise) with **real-time human monitoring and intervention**.
- **Chubb:** targets about 85% process automation and about 1.5 combined-ratio points.
- **Travelers:** submission registration cut from 2 hours to 2 minutes.

The takeaway: large carriers are building intake and assistants themselves, so our buyer is the **CUO or portfolio head** paying for controlled economics, not operations paying for speed.

### 2.3 Lessons applied to the build

1. Every number carries a source and a date. Archipelago, Athenium and Cytora all make lineage the foundation.
2. Weight data quality and findings by **dollar impact**, following Moody's.
3. Fast-track renewals with no change. Work proportional to change is the ROI engine, following Nearmap and Cytora.
4. Deliver a queue, not a dashboard, following Federato.
5. Version and backtest every rule and model change against a control set, following Athenium and hx.
6. Integrate with hx, Guidewire and Moody's. Don't rebuild pricing or CAT.

---

## 3. How a best-in-class carrier actually runs a property renewal

This is the operating reality the platform has to fit. Brokers now start renewals 120–150 days before expiry.

| Day (to expiry) | Carrier activity | Pain today | Platform hook |
|---|---|---|---|
| **T-150** | Renewal listing produced from the policy admin system | Static list with no priority | **Pass 1: internal drift scan** of the in-force book with no new submission: claims since bind, endorsements, overdue engineering, guideline changes, portfolio shift, technical price rerun on expiring exposure |
| **T-120** | Renewal strategy: grow, maintain, remediate or exit. Order engineering visits. Ask the broker for the SOV. | Strategy set on instinct | Recommended strategy per account; pre-filled list of what to request from the broker (only the missing or stale fields) |
| **T-120 to T-60** | **Conditional renewal and non-renewal notice windows.** Statutory for admitted business; timing varies by state; E&S often exempt. | Missed notice dates mean the carrier must renew on expiring terms | **Latest valid notice date by state and policy**; alert if a remediation action needs a notice |
| **T-90 to T-45** | Renewal SOV, loss runs and engineering reports arrive | SOV rekeyed and compared by eye | **Pass 2: submission delta.** Location-level redline of the SOV; COPE and value changes; valuation adequacy |
| **T-60** | CAT rerun on renewal exposure; technical price rerun | Model inputs don't match the SOV | Check CAT inputs against the resolved risk state (§14.4 of the catalogue) |
| **T-45 to T-15** | Negotiation, restructuring (deductibles, sublimits, layers), referral | RARC figures typed in by hand; referrals missed | **Computed RARC split** (§10.3); authority and referral check on the *intended* terms |
| **T-15 to T-0** | Quote → bind; subjectivities | Quote and binder drift apart | **Pass 3: contract integrity**, a three-way check of quote, binder and policy |
| **T+0 to T+60** | Issuance, endorsements, clearing subjectivities | Policy issued with the wrong BI sublimit, and nobody notices | Binder vs issued policy check; subjectivity ageing; protective safeguards checked against verified status |
| **In-force** | Endorsements, claims, engineering follow-up | Drift isn't seen until renewal or a loss | **Event-driven re-evaluation** (endorsement, material claim, overdue recommendation, hazard or guideline change) |

**Finer detail most platforms miss:** there are *three passes* per renewal, not one. Pass 1 needs no new broker data and delivers value at T-150. Most tools wait for the renewal SOV, which often arrives at T-30.

---

## 4. Platform architecture

```text
┌──────────────────────────── EXPERIENCE ─────────────────────────────┐
│ Book view (CUO) · Renewal queue · Account integrity record ·        │
│ Location redline · Contract diff · Evidence drawer · Rule studio ·  │
│ Data-quality console · Authority admin                              │
├──────────────────────────── ACTION LAYER ───────────────────────────┤
│ Finding → Action object → Referral/approval → Disposition → Outcome │
├──────────────────────────── CONTROL LAYER ──────────────────────────┤
│ Delta engine (7 deltas) · Rule engine (versioned, effective-dated)  │
│ Economic impact & materiality · RARC decomposition · AI critique    │
├──────────────────────────── STATE LAYER ────────────────────────────┤
│ Canonical Risk State snapshots: AS_SUBMITTED · AS_PRICED ·          │
│ AS_QUOTED · AS_BOUND · AS_ISSUED · AS_ENDORSED(t) · CURRENT ·       │
│ RENEWAL_SUBMITTED · RENEWAL_PROPOSED                                │
├──────────────────────────── EVIDENCE LEDGER ────────────────────────┤
│ Observations (C/S/N/V/D/M/R) · bitemporal · provenance · conflicts  │
│ Entity & location resolution · evidence hierarchy per field         │
├──────────────────────────── INGESTION ──────────────────────────────┤
│ Doc classify → extract (SOV, ACORD, loss runs, forms, engineering,  │
│ CAT outputs) → normalize (ISO/CSP/NAICS/CAT codes) → validate       │
├──────────────────────────── CONNECTORS ─────────────────────────────┤
│ PAS · rater · claims · engineering · CAT · doc repo · email ·       │
│ geocode · hazard · imagery · valuation · crime · portfolio          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. The core idea: the Evidence Ledger and risk-state snapshots

### 5.1 Everything is an observation

A field such as `roof_year` for building B-3 is never a single value. It's a set of observations:

| obs_id | field | value | type | source | as_of | confidence |
|---|---|---|---|---|---|---|
| o1 | roof_year | 2011 | C | 2025 SOV, Sheet1!K14 | 2025-09-01 | 0.95 |
| o2 | roof_year | 2011 | C | 2026 SOV, Locs!M9 | 2026-08-20 | 0.95 |
| o3 | roof_condition | Poor | M | Imagery vendor, v4.2 | 2026-06-11 | 0.81 |
| o4 | roof_year | 2019 | V | Engineering survey p.7 | 2024-03-15 | 0.98 |
| r1 | roof_year (resolved) | 2019 | R | Hierarchy policy `roof_year.v3` | — | — |
| r2 | roof_year_conflict | TRUE | R | o2 vs o4 | — | — |

The broker's SOV repeating a stale 2011 roof year while engineering verified 2019 is itself a finding: the SOV is untrustworthy on this field.

### 5.2 Bitemporal storage

This is non-negotiable for renewals. Each observation stores:

- **valid time:** when the fact was true in the world;
- **transaction time:** when we learned it.

Together these answer *"what did we know at bind?"* (the underwriter's defence) separately from *"what was true at bind?"* (the carrier's exposure). Most workbenches overwrite values and lose both.

### 5.3 Named snapshots

A snapshot is a *view* over observations at a point in time with a resolution policy applied. It is not a copy.

| Snapshot | Built from | Used for |
|---|---|---|
| `AS_SUBMITTED(y)` | Broker documents at last new business or renewal | "What were we told" |
| `AS_PRICED(y)` | Rater inputs and outputs, model version | Price baseline |
| `AS_QUOTED(y, v)` | Every quote version | Negotiation trail |
| `AS_BOUND(y)` | Binder plus accepted quote | Intended contract |
| `AS_ISSUED(y)` | Declarations, forms schedule | Actual contract |
| `AS_ENDORSED(t)` | Issued plus endorsements effective ≤ t, in order | Contract today |
| `CURRENT` | Everything known now, resolved | Risk today |
| `RENEWAL_PROPOSED` | Underwriter's intended renewal terms | Assurance target |

**The delta engine only ever compares two snapshots.** That makes every finding reproducible.

---

## 6. Data model (core tables)

```sql
-- identity
account(account_id, legal_name, fein, parent_account_id, segment, ...)
party(party_id, role /*insured|broker|MGA*/, licence_no, ...)
location(location_uid, account_id, std_address, lat, lon, geocode_level,
         parcel_apn, footprint_id, status, first_seen, last_seen)
building(building_uid, location_uid, bldg_no_raw, footprint_id, ...)
location_alias(location_uid, source_doc_id, raw_loc_no, raw_address, match_score, match_method, confirmed_by)

-- evidence
document(doc_id, account_id, doc_type, received_at, source_channel, sha256, version_of)
observation(
  obs_id, subject_type /*account|location|building|policy|coverage|claim|rec*/,
  subject_id, field_code, value_raw, value_norm, unit, currency,
  obs_type CHAR(1) /*C S N V D M R*/, source_family, doc_id, anchor /*page/sheet/cell/bbox*/,
  vendor, model, model_version, confidence, verification_status,
  valid_from, valid_to, recorded_at, superseded_by, human_override, override_reason, actor)
field_catalogue(field_code, domain, datatype, unit, applies_to_occupancy[], required_rule,
                hierarchy_policy_id, staleness_days, materiality_weight)
resolution(subject_id, field_code, snapshot_id, resolved_obs_id, policy_version, conflict_obs_ids[])

-- contract
policy(policy_id, account_id, policy_no, term_start, term_end, carrier_share, layer_attach, layer_limit, admitted_flag, state)
coverage(coverage_id, policy_id, location_scope, coverage_part /*bldg|bpp|BI|EE|...*/, limit, limit_basis /*scheduled|blanket|loss_limit*/, valuation, coinsurance, margin_clause_pct)
peril_term(policy_id, peril, covered, sublimit, aggregate, deductible_amt, deductible_pct, pct_basis, ded_min, ded_max, waiting_hours, form_ref)
form(policy_id, form_no, edition, title, manuscript_flag, text_doc_id)
endorsement(endt_id, policy_id, effective, type, delta_json, premium_delta)
safeguard(policy_id, location_uid, type /*P-1 sprinkler, P-2 alarm, ...*/, form_ref, required)
subjectivity(policy_id, text, due_date, status, cleared_evidence_doc)

-- performance
claim(claim_id, policy_id, location_uid, dol, cause_code_norm, cat_event, paid, reserve, expense, recovery, status)
eng_survey(survey_id, location_uid, date, engineer, scope, doc_id)
recommendation(rec_id, location_uid, raised, category, severity, due, status, verified_closed_at, bind_condition_flag)
pricing_run(run_id, policy_id, snapshot_id, model_name, model_version, tech_premium, cat_load, attritional, expense, profit, schedule_mod, selected, quoted, bound)
cat_run(run_id, snapshot_id, vendor, model_version, perils[], aal, oep_100, oep_250, aep_100, dq_flags_json)

-- control
rule(rule_id, version, family, effective_from, effective_to, scope_json, expr, outcome, severity, authority_level, source_doc, section)
authority_grant(user_id, role, lob, geo[], max_tiv, max_loc_tiv, max_line, max_cat_pml, max_price_dev_pct, overrides[])
finding(finding_id, account_id, subject_id, rule_id, rule_version, snapshot_a, snapshot_b,
        observed, expected, evidence_obs_ids[], impact_usd, impact_method, confidence, materiality,
        status, created_at)
action(action_id, account_id, type /*maintain|reprice|restructure|condition|refer|nonrenew*/, findings[], owner, due, notice_deadline, status)
disposition(finding_id, actor, decision /*accept|reject|defer*/, reason_code, note, at)
outcome(account_id, term, renewed, premium_change, rarc, terms_changed, loss_12m, loss_24m)
```

**Account structure detail that large accounts need:** store `carrier_share`, the layer (`attach`/`limit`) and `limit_basis` (a *loss limit* much smaller than TIV is common on large schedules). Exposure and CAT figures must be **computed on the carrier's participation**, not ground-up. Otherwise large-account findings are wrong by a factor of 4–10.

---

## 7. Ingestion: document-level details

### 7.1 SOV (the hardest document, and the one that pays)

| Problem | Handling |
|---|---|
| Multiple tabs, header rows not in row 1, merged cells, hidden rows and columns, totals and subtotal rows | Parse with the structure intact (openpyxl, keeping merged and hidden state). Detect the header band by density of vocabulary. Drop rows that are arithmetic totals of rows above, and log what was dropped. |
| Varying column names ("Bldg Val", "Building RC", "Real Property") | Synonym dictionary for each canonical field, with an LLM fallback that returns *field + confidence + reason*. Store the mapping per broker template, so next year's SOV from the same broker maps automatically. |
| Is TIV inclusive of BI? Is BI annual or for 12 months? | Recalculate TIV from the components. If reported ≠ recalculated beyond 0.5%, infer which components are included and raise `tiv_definition_ambiguous`. |
| Units and scaling ("$000s", sq m, stories as text) | Detect scale factors from column headers and magnitudes. Normalise to USD and square feet. |
| Free-text construction and occupancy | Map to ISO class 1–6, CSP, NAICS, carrier class, and **CAT model codes (RMS/AIR)**. Keep the raw text. Mark as N-type with confidence. |
| Several buildings behind one address; one building listed under several addresses | Resolve at building level (§8). |
| Placeholder values (0, 1, 9999, "TBD", year built 1900) | Placeholder detector. Treat as *missing*, not as a value (Archipelago step 1). |
| Stale valuations | `value_as_of` older than 12 months → staleness flag (Archipelago step 3). |
| Secondary CAT modifiers missing | Impact-weighted gap list: rank missing fields by TIV × hazard × model sensitivity, following Moody's DQ Toolkit. |

**SOV outputs:** a normalised location/building table; a structural integrity report (TIV arithmetic, impossible values, duplicates); a data-quality score **weighted by modelled-loss impact**; a list of fields to request from the broker.

### 7.2 Policy, forms and endorsements (the contract state)

- Parse the declarations and the **forms schedule** (form number and edition). Examples: CP 00 10 (Building & Personal Property), CP 00 30 (BI), CP 10 30 (Causes of Loss – Special), CP 04 11 (Protective Safeguards), and carrier or manuscript forms.
- Keep a **form library**. For each form and edition, a structured record of what it grants or excludes, so peril coverage is *derived from form references* rather than inferred from prose.
- **Manuscript wording** (large accounts): LLM clause extraction into a `peril_term` / `condition` object, with a clause anchor and a mandatory human confirmation the first time per account.
- **Endorsement roll-forward:** `AS_ENDORSED(t) = AS_ISSUED + Σ endorsements(effective ≤ t)` in effective-date order, with back-dated endorsements re-applied. Reconcile the result against the policy admin system's own current state (`policy_system_integrity_issue`).
- **Deductibles** in structured form: flat, % of what (location TIV, unit of insurance, building value), minimum and maximum, per occurrence or per location. "2% of TIV per unit, $250K min" is not the same as "2% of loss".

### 7.3 Loss runs and claims

- For the carrier's own book: **the claims system beats the PDF loss run**. Use the loss run only for prior carriers.
- Extract claim-level rows. Normalise cause (fire, water non-weather, wind/hail, theft, etc.). Link each claim to a location by address or geocode, and fall back to "account-level" when that fails.
- Split CAT from attritional (using the CAT event code or date and location against the event footprint).
- Track reserve development across successive loss-run valuations (same claim, different valuation dates).

### 7.4 Engineering

- Survey reports: extract as **V** observations with page anchors.
- Recommendation register: severity, due date, status. **"Closed" without evidence of completion is an unverified closure** (R-type).
- Record the engineering-rated construction and protection, for the CAT input check.

### 7.5 CAT and pricing outputs

- Ingest the exposure file sent to the model (not just results). That's what lets you check CAT inputs against the resolved state.
- Store model vendor, model version, run settings and perils. Split CAT change into exposure-driven, model-version-driven and terms-driven (catalogue §14.4).

### 7.6 Extraction quality bar

| Document | Target field accuracy before human review | Human review rule |
|---|---|---|
| SOV numeric values | ≥ 99% (arithmetic checks catch the rest) | Only where the arithmetic fails |
| SOV COPE mapping | ≥ 95% | Confidence < 0.85, or TIV > threshold |
| Loss runs | ≥ 98% (Groundspeed benchmark) | Totals don't match |
| Forms schedule | ≥ 99% | Unknown form or edition |
| Manuscript clauses | ≥ 90% | Always the first time per account |
| Engineering recommendations | ≥ 95% | Severity = critical |

---

## 8. Entity and location resolution across years

This is what makes the "then vs now" comparison work. Get it wrong and every delta is noise.

**Matching cascade** (stop at the first confident match):

1. Carrier location ID carried in the policy admin system or rater (exact)
2. Broker location and building number **plus** address similarity ≥ 0.9
3. Standardised address (USPS CASS) exact match
4. Parcel APN plus footprint ID
5. Geocode within 30 m **and** construction, stories and area similar
6. Fuzzy address plus the same value band. This rung is *proposed only* and needs confirmation.

**Outcomes per location:** `MATCHED`, `NEW`, `DELETED`, `SPLIT` (one to many), `MERGED` (many to one), `AMBIGUOUS`. Keep `location_uid` stable for good and store every alias. Once an underwriter confirms an ambiguous match, reuse that confirmation in later years.

**Traps:**

- The broker renumbers locations every year.
- A campus is listed as one address but contains 12 buildings.
- The carrier exited a location mid-term by endorsement, but it reappears in the renewal SOV.

---

## 9. Evidence resolution (which source wins)

There is a resolution policy **per field**. Each policy is versioned and can be tuned per carrier.

| Field | Ranking (highest first) | Freshness rule |
|---|---|---|
| Construction class | Engineering V > ProMetrix/inspection V > carrier prior-resolved > SOV C > model M | Engineering valid until a renovation is recorded |
| Roof year / condition | Engineering V > roofing permit S > imagery M (condition only) > SOV C | Imagery older than 12 months is downgraded |
| Sprinkler **presence** | Engineering V > certificate C > SOV C | Certificate older than 12 months is stale |
| Sprinkler **adequacy** | Engineering V only | Needs the current commodity and storage height |
| Values (building RC) | Appraisal < 3 years > SOV C, **with a check against the valuation model M** (never overridden by M) | Appraisal older than 3 years is stale |
| Occupancy | Engineering V > SOV/application C (normalised) > business data M | Occupancy drift from last year → re-verify |
| Claims | Claims system S > loss run C | — |
| Contract terms | Issued policy + endorsements S > binder > quote | — |

**Rule:** model data (M) never silently replaces reported data (C). It creates a conflict finding. That keeps disputes with brokers defensible.

---

## 10. The delta engine

### 10.1 Seven deltas (in line with the thesis)

| Delta | Compares | Key computed fields |
|---|---|---|
| **1. Exposure** | `AS_BOUND` vs `CURRENT` / `RENEWAL_SUBMITTED` | TIV change (split into new locations, deleted locations, value change on matched locations, BI change); occupancy drift; COPE change; valuation adequacy ($/sq ft vs model); location concentration |
| **2. Pricing** | `AS_PRICED` vs today's rerun | Technical premium on expiring exposure (under today's model) vs on renewal exposure; **RARC split** (§10.3); adequacy = proposed / technical |
| **3. Terms and contract** | Quote ↔ binder ↔ issued ↔ endorsed; also against current guidelines | Mismatches, e.g. deductible below the floor, a sublimit missing, a safeguard not verified |
| **4. Risk quality** | Since `AS_BOUND` | New claims by cause, repeat causes, overdue or unverified recommendations, imagery deterioration, hazard score changes |
| **5. Appetite and portfolio** | Current rules and accumulation | Class or territory now out of appetite; CAT zone utilisation after renewal; concentration by broker or industry |
| **6. Retention and commercial** | Account economics | Loss ratio over 3–5 years, relationship value, sensitivity to the size of the increase, broker book share |
| **7. Net / reinsurance** (V2) | Treaties | Net PML, facultative need, capital use |

### 10.2 Location-level redline (the screen underwriters will actually use)

| Loc | Status | TIV exp → ren | Δ | COPE change | Valuation vs model | Flags |
|---|---|---|---|---|---|---|
| 1 Dayton OH | MATCHED | $48.0M → $49.4M | +2.9% | — | 71% of model RC | **Under-valued** |
| 2 Tampa FL | MATCHED | $31.0M → $38.5M | +24% | Roof: 2011 (SOV) vs 2019 (eng) | 96% | Tier-1 wind; **deductible 2% < floor 3%** |
| 3 Reno NV | MATCHED | $26.0M → $26.0M | 0% | Occupancy: warehouse → **lithium-ion storage** | 90% | **Occupancy drift → re-verify** |
| 4 Austin TX | MATCHED | $15.0M → $15.1M | +0.7% | — | 88% | 2 water claims; rec #R-114 overdue |
| 5 Tampa FL | **NEW** | — → $22.0M | new | Unknown roof, sprinkler "Y" | n/a | Within 1 km of Loc 2 → **accumulation** |

**Traps that decide whether a TIV change is meaningful:**

- **Flat values across years are a finding.** A zero-change TIV with construction inflation at +4–6% implies creeping under-insurance.
- Values are compared **per matched building**, never just at account totals, because additions and deletions hide each other.

### 10.3 Computed RARC split (the headline capability)

Lloyd's PMDR method: *expected premium = expiring premium adjusted for deductible, breadth-of-cover, and exposure/risk changes; RARC = achieved ÷ expected − 1.* Today the adjustments are typed in by the underwriter. **We compute them by rerunning the carrier's own technical model on controlled snapshots**:

```text
TP(E0,T0) = technical on expiring exposure, expiring terms (today's model)
TP(E1,T0) = technical on renewal exposure, expiring terms
TP(E1,T1) = technical on renewal exposure, proposed terms

exposure_factor = TP(E1,T0) / TP(E0,T0)
terms_factor    = TP(E1,T1) / TP(E1,T0)
expected_prem   = expiring_prem × exposure_factor × terms_factor
RARC            = proposed_prem / expected_prem − 1
adequacy        = proposed_prem / TP(E1,T1)
```

**Worked example (ABC Manufacturing, from the deck):**

| Item | Value |
|---|---|
| Expiring premium | $410,000 on TIV $120M |
| TP(E0,T0) | $395,012 |
| TP(E1,T0), TIV $151M | $657,121 → exposure factor **1.664** (Tampa hurricane exposure nearly doubles; Reno moves to lithium-ion storage) |
| TP(E1,T1), wind deductible 2% → 3%, NS minimum $250K | $591,965 → terms factor **0.901** |
| Expected premium | 410 × 1.664 × 0.901 = **$614,426** |
| Broker counter / proposed | $450,000 |
| Headline premium change | **+9.8%** |
| **RARC** | 450 / 614.4 − 1 = **−26.8%** |
| Adequacy | 450 / 592 = **76.0%** (below the 95% floor) |

**What the underwriter sees:** "The account looks like it's up 9.8%, but on a like-for-like basis you're giving 26.8% of rate — insured values rose 26% but modelled risk rose 66% because the Tampa hurricane exposure nearly doubled. You're at 76% of technical and this needs the CUO." That single line is the product.

*These figures are produced by the showcase engine (mock rater + event-based MockCat) on the demo data, not typed in. The illustrative 1.235 exposure factor in earlier drafts was inconsistent with the account's own facts: a real model cannot let Tampa hurricane exposure double while the technical price rises only in line with TIV.*

**Implementation details:**

- If the rater isn't callable (Excel raters are common), fall back to **exposure elasticity by component**: building and BPP at the expiring rate on line per location, CAT through the AAL ratio. Label the output `method = elasticity_fallback` and assign a lower confidence.
- Hold the **model version fixed** across the three runs. Report model drift separately (`TP_today(E0,T0)` vs `AS_PRICED`).
- Report **gross and net of acquisition cost**. Lloyd's shows a +10% gross RARC turning into −17.5% net when brokerage moves from 20% to 40%.
- Aggregate RARC to the book, weighted by expiring premium. That makes the CUO dashboard auditable, down to each account's three model runs.

### 10.4 Contract integrity check (quote ↔ binder ↔ policy)

Compare field by field on the `peril_term`, `coverage`, `form`, `safeguard` and `subjectivity` objects:

| Field | Quote v3 (accepted) | Binder | Issued policy | Result |
|---|---|---|---|---|
| BI sublimit | $10M | $10M | **$15M** | **Binder ≠ policy** (exposure over-granted) |
| Named storm deductible | 5% per location, $250K min | 5% per location | 5% per location, **no min** | **Minimum lost at issuance** |
| CP 04 11 sprinkler safeguard, Loc 2 | Required | Required | **Missing** | **Safeguard dropped** |
| Subjectivity: roof schedule | Before bind | Outstanding | — | **Bound with an open subjectivity**, now 212 days old |

Where contract integrity breaks is exactly where brokers' policy-checking tools (Patra, CopyCat, Exdion) work. None of the carrier-side vendors publish this.

---

## 11. Rule and control engine

### 11.1 Rule format

Store rules as YAML with CEL expressions (Google Common Expression Language). CEL is sandboxed, fast, deterministic, and non-engineers can read it. Keep rules in git plus the database, with effective dates.

```yaml
id: CAT.WIND.DED_FLOOR
version: 4
family: cat_terms
effective_from: 2026-07-01
scope:
  lob: commercial_property
  states: [FL, TX, LA, SC, NC, GA, AL, MS]
  segment: [middle_market, large]
applies_to: location
inputs: [wind_tier, peril_term.named_storm.deductible_pct, location.tiv_share]
when: loc.wind_tier in ['T1','T2'] && loc.named_storm_ded_pct < 0.03
outcome:
  type: TERM_BREACH          # PASS | FLAG | REFER | BLOCK | CONDITION | PRICE_ADJUST
  severity: high
  expected: "named storm deductible ≥ 3% per location"
  referral_level: senior_uw
  exception_allowed: true
impact:
  method: cat_model_delta     # rerun AAL at 3% vs current
source: "Property UW Guidelines 2026 §7.3, p.41"
tests:
  - fixture: tampa_2pct.json   -> TERM_BREACH
  - fixture: tampa_3pct.json   -> PASS
  - fixture: ohio_2pct.json    -> NOT_APPLICABLE
```

### 11.2 Outcome types

Rules do more than pass or fail:

| Outcome | Effect |
|---|---|
| `PASS` / `NOT_APPLICABLE` | Logged. Counts toward fast-tracking. |
| `FLAG` | Shown on the record; no workflow block |
| `REFER` | Creates a referral task at the authority level |
| `BLOCK` | Renewal can't be marked ready until resolved or an exception is approved |
| `CONDITION` | Proposes a subjectivity or engineering condition |
| `PRICE_ADJUST` | Proposes a debit or credit, with the calculation |
| `DATA_REQUEST` | Adds an item to the broker request list |

### 11.3 Authority check (applied to intended terms, not just facts)

```text
for each proposed action:
  required_level = max(rule.referral_level for triggered rules,
                       authority_needed(limit, loc_tiv, cat_pml, price_dev, overrides))
  if user.level < required_level and no valid approval(referral_id, not expired, same terms):
       AUTHORITY_CONTROL_FAILURE
```

**Detail:** an approval is only valid for the *terms it approved*. If the terms change after approval (a new quote version), the approval is invalidated. Most referral systems miss this.

### 11.4 Rule sources

- **Carrier guidelines PDF → draft rules.** The LLM proposes CEL rules with a citation, following Sixfold's "guidelines as input". A human approves each one. No rule goes live without a test fixture.
- **Standard library shipped with the product:** SOV integrity, contract integrity, authority, staleness and data completeness. These are about 60% of rules and identical across carriers.
- **Occupancy add-on requiredness** (catalogue §38): a restaurant requires cooking suppression, a warehouse requires commodity class, storage height and rack type, and so on.

### 11.5 Rule governance (the Athenium lesson)

- Every rule change is **backtested** on a frozen control set (e.g. 500 historical renewals). The diff in findings is shown before publishing.
- Findings store `rule_id + version`, so historical findings stay explainable after rules change.
- Precision per rule comes from dispositions. Rules with more than 40% rejection get auto-flagged for review.

---

## 12. Economic impact and materiality

A finding without a dollar figure is noise. Every finding carries `impact_usd`, `impact_method` and `confidence`:

| Finding type | Impact method |
|---|---|
| Premium inadequacy | `TP(E1,T1) − proposed` |
| Under-valuation | (model RC − reported) × rate on line, plus **coinsurance/limit shortfall exposure** noted separately |
| Deductible below floor | ΔAAL from the CAT model plus attritional Δ from the deductible credit curve |
| Binder/policy sublimit over-grant | Δ limit × modelled probability of reaching the limit (or flag qualitatively if no model is available) |
| Unmodelled exposure (new location not in the CAT run) | AAL from a proxy location or rate on line |
| Missed referral / authority breach | Premium or limit at stake, reported as *control* exposure, not loss |

**Materiality score** = `impact_usd × confidence`, with thresholds that scale by account premium band (e.g. finding material if ≥ max($5K, 2% of premium)).

**Fast-track criteria:** no material findings, adequacy ≥ floor, no open critical recommendations, no appetite change, and data completeness ≥ threshold. **Aim for 40–50% of renewals fast-tracked.** That's where the handling-time saving comes from.

---

## 13. Where AI is used, and where it is not

| Use AI for | Never use AI for |
|---|---|
| Document classification and field extraction (with anchors) | Arithmetic, TIV sums, RARC, adequacy |
| Header and COPE mapping with confidence | Final rule outcome |
| Manuscript clause → structured term (confirmed by a human) | Creating a fact without a source observation |
| Guidelines → draft rules | Deciding a renewal |
| The account narrative ("why this account needs action") citing finding IDs | Overriding the evidence hierarchy |
| **Critique pass**: a second model tries to refute each material finding and each fast-track decision | — |

**Guardrails:**

- Every generated sentence must cite `obs_id` or `finding_id`. Uncited sentences are removed before display.
- The critique pass follows the deck's arXiv result: base agent vs agent plus critique moved hallucination from 11.3% to 3.8% and traceability from 81% to 96%. Run critique only on material findings and fast-track decisions to control cost.
- Keep a per-carrier **golden set** of about 200 documents and 100 accounts with labelled values. Run it on every model or prompt change. Treat it the same as a rule backtest.
- Deploy LLMs inside the carrier's cloud boundary (for example Claude on Bedrock or Vertex in the carrier's own account). Never train on carrier data across tenants.

---

## 14. Workflow and screens

### 14.1 Screens

The screens below are for Renewal Integrity. Products 02 and 03 have their own screens (§20.1, §20.2). A **product selector** at the top of the sidebar switches between the three; the demo clock, persona, documents viewer, rule studio and evidence drawer are shared.

1. **Book view (CUO / portfolio head)**
   - Renewals by T-minus band.
   - Dollar pipeline: *identified → validated → approved → actually corrected*.
   - Book RARC (computed) vs reported.
   - Adequacy distribution.
   - Exceptions by rule family, underwriter and broker.
   - Concentration interventions.
2. **Renewal queue (underwriter)**
   - Sorted by `materiality × days to notice deadline`.
   - Columns: account, expiry, recommended action, $ at stake, top 3 findings, data gaps, notice deadline.
   - Fast-tracked accounts sit in a separate lane with a single-click confirm.
3. **Account integrity record**
   - Header: integrity score, recommended action, owner, due date, notice deadline.
   - Seven delta cards.
   - Each number clickable into the **evidence drawer**: source document page with a highlighted cell or box, alternative observations, and the resolution policy used.
4. **Location redline:** the §10.2 table with map, filters (new, deleted, changed, flagged) and a side-by-side of prior vs current SOV rows.
5. **Contract diff:** a three-column view of quote, binder and policy, plus endorsements on a timeline.
6. **RARC workbench**
   - The three model runs.
   - A what-if on proposed premium, deductible and sublimits. Live recompute of adequacy, RARC and the required authority level.
7. **Referral / approval**
   - Pre-filled referral memo with cited evidence.
   - Approval tied to a hash of the specific terms.
8. **Finding disposition**
   - Accept, reject or defer, with a **mandatory reason code**:
     - `data_wrong`
     - `already_known`
     - `commercial_override`
     - `immaterial`
     - `rule_outdated`
   - This is the learning signal.
9. **Rule studio:** author, test, backtest, diff, publish; per-rule precision.
10. **Data-quality console**
    - Extraction confidence.
    - Unmatched locations.
    - Stale fields.
    - The broker data request list, exportable as email or broker portal items.

### 14.2 Action taxonomy

`MAINTAIN (fast-track)` · `REPRICE` · `RESTRUCTURE (deductible/sublimit/limit/layer)` · `CONDITION (engineering/subjectivity)` · `DATA_REQUEST` · `REFER` · `CONDITIONAL_RENEWAL_NOTICE` · `NON_RENEW`. An account can carry several actions.

---

## 15. Integrations (build order)

| Priority | System | Pilot method | Production method |
|---|---|---|---|
| 1 | Policy admin (policy, coverage, endorsements) | **Batch extract** (CSV/Parquet from the warehouse) | Guidewire Cloud API / Duck Creek APIs / event stream |
| 1 | Document repository (submissions, SOVs, binders, policies) | Bulk export by policy number | ImageRight/OnBase/SharePoint connectors |
| 1 | Claims | Warehouse extract | ClaimCenter API |
| 2 | Rater / pricing | Excel rater execution in a sandbox, or hx API | hx Connect, or the carrier's rating service |
| 2 | Engineering | Report export + recommendation register CSV | Engineering platform API |
| 2 | Underwriting guidelines + authority matrix | PDF + spreadsheet | Rule studio as the master record |
| 3 | CAT | Exposure file + results export | Moody's IRP APIs / Verisk Synergy Studio |
| 3 | External data | Geocoder (Precisely/HERE), hazard (HazardHub, Verisk), valuation (Verisk 360Value / e2Value), imagery (Nearmap / CAPE) | Same, called per event |
| 4 | Email / broker portal | — | Outbound data requests, inbound renewal submissions |
| 02 | Submission intake (mailbox, broker portal, or Cytora/Convr output) | Folder drop of submission packs | Intake product API / email ingestion |
| 02 | Loss-control inspection vendor | Report PDFs | Vendor order/report API |
| 03 | Binding authority agreements + endorsements | PDF export from the DA registry / binder store | Lloyd's DA registry / carrier contract store |
| 03 | Risk, premium and claims bordereaux | Monthly files as received (any template) | Coverholder portal, VIPR / Tide / bureau output, or DDM feed |
| 03 | Carrier referral system, finance ledger | CSV extract | Referral workflow API; ledger posting (debit notes) |

**Pilot rule:** **no live integrations are needed to prove value.** A 12–24 month historical extract plus documents is enough for backtesting. This removes the biggest sales blocker.

---

## 16. Tech stack (kept deliberately simple)

| Concern | Choice | Why |
|---|---|---|
| Core store | **Postgres + PostGIS** (bitemporal observation tables, JSONB for term objects) | One database; geospatial matching; easy to deploy on the carrier's cloud |
| Files | Object storage (S3/Azure Blob), content-hashed | Unchanging evidence |
| Jobs / orchestration | Postgres-backed queue at first; Temporal only when event-driven in-force volume needs it | Avoid infrastructure you don't need yet |
| Services | Python (FastAPI) for ingestion, delta and rules; CEL evaluator (`cel-python` or Go `cel-go`) | Python suits data and ML work; CEL keeps rules deterministic and sandboxed |
| Documents | Excel parsing that keeps structure; OCR (Textract / Azure Document Intelligence) only for scans; LLM for mapping and clauses | Most SOVs are Excel, so don't OCR them |
| Front end | React / Next.js; the evidence viewer renders PDF and Excel with highlights | The evidence drawer is the trust feature |
| Deployment | **Single tenant in the carrier's own VPC** (AWS/Azure), Terraform | This is how large carriers buy |
| Security | SSO (SAML/OIDC), row-level security by business unit, field-level audit log, SOC 2 Type II, ISO 27001 roadmap | Standard procurement gates |

---

## 17. Governance and compliance

- **NAIC Model Bulletin on the Use of AI Systems by Insurers** (Dec 2023; adopted by a large share of states): requires a written AI programme, governance, documentation of models and third-party vendors. Supply each carrier with a **model card and an audit export**.
- **NYDFS Circular Letter No. 7 (2024):** covers AI and external data in underwriting and pricing. Keep lineage and a record of every external data source.
- **Lloyd's MS3 / Pre-Bind Quality Assurance:** the RARC split and pre-bind assurance map directly onto it. This is the London go-to-market for later.
- **Human-in-the-loop by design:** the platform recommends. The underwriter's disposition is recorded as the decision. No automated non-renewal or adverse action.
- **Statutory notices:** the notice-deadline calculator must be versioned per state and reviewed by legal before use.
- **Delegated authority (product 03):** Lloyd's Coverholder Reporting Standards v5.2 for bordereau fields, the managing agent's obligations for coverholder oversight and audit, and the binding authority agreement as the governing contract. Every breach cites both the agreement clause (page and box) and the bordereau cell.
- **Human final decision (product 02):** the assurance verdict is advice to a named decision owner, who is chosen by the authority matrix. Declines and adverse actions are always taken by a human.

---

## 18. Pilot design and metrics

### 18.1 Three stages

| Stage | Duration | Data | Output | Success gate |
|---|---|---|---|---|
| **A. Backtest** | 6–8 weeks | 500–1,500 renewals from the last 12–24 months, with **known outcomes** (renewed or lost, premium, later losses) | Findings on each account's *pre-renewal* snapshot vs what actually happened | ≥ 70% of material findings accepted by the carrier's underwriter review panel; $ leakage identified ≥ 1% of reviewed premium |
| **B. Shadow** | 90 days | Live renewals, platform output hidden from underwriters | Compare platform findings with what underwriters did | Recall on issues underwriters found ≥ 85%; the platform finds issues they missed |
| **C. Live with control** | 2 renewal quarters | 80% treated / 20% control, **randomised by account** | Treated vs control | See KPIs |

### 18.2 KPIs (in order of importance)

1. **Dollars corrected at renewal**: premium, terms and exposure actually changed (not just identified).
2. RARC and adequacy, treated vs control.
3. **Retention of profitable accounts**, treated vs control. This guards against over-pricing good business.
4. Renewal preparation time (base hypothesis −30–40%; stretch −50%).
5. Share of renewals fast-tracked.
6. Finding precision (acceptance rate) by rule family.
7. Contract integrity defects caught before issuance.
8. Loss ratio, treated vs control (only after 12–24 months, so don't sell on it).

### 18.3 Pilots for products 02 and 03

| Product | Backtest input | Shadow | Primary KPI |
|---|---|---|---|
| 02 Decision Assurance | 300–800 past new-business decisions with documents, the action taken and later losses | Assurance verdicts hidden from underwriters for 90 days; compare with senior-review findings | Material exposure corrected or prevented before commitment ($); errors intercepted; preparation hours saved |
| 03 Delegated Authority | 12 months of bordereaux + BAAs for 3–5 coverholders | Monthly authority reports alongside the existing DA team's review | $ premium written outside authority; missing referrals; commission recovered; correction turnaround |

---

## 19. Build plan

### 19.1 Phases

| Phase | Weeks | Scope |
|---|---|---|
| **0. Data contract** | 0–4 | Field catalogue v1 (from the data-points doc); carrier extract spec; frozen control set; golden labelled set |
| **1. Ledger + exposure + contract** | 4–16 | Observation store, snapshots, SOV ingestion, location matching, policy/forms/endorsement roll-forward, exposure delta, contract integrity, evidence drawer, location redline |
| **2. Pricing + risk quality + rules** | 16–26 | RARC split (rater integration + fallback), claims and engineering ingestion, rule studio with 80–120 standard rules, materiality, action queue, disposition capture. **Run the backtest (Stage A).** |
| **3. Shadow + AI critique** | 26–38 | Critique pass, narratives, notice-deadline calculator, CUO book view, broker data requests |
| **4. Live + in-force events** | 38–52 | Event-driven re-evaluation (endorsement, claim, recommendation, hazard), CAT input check, portfolio accumulation delta |
| **5. Decision Assurance** | 52–68 | Submission pack ingestion (ACORD, SOV, loss runs, inspection, wording), contradiction pricing, tier-1/tier-2 rules, intended-action capture, verdict routing, outcome feedback |
| **6. Delegated Authority Control** | 60–76 | BAA extraction to versioned authority, CRS v5.2 mapper, authority / referral / commission / aggregate / claims rules, breach register, coverholder query loop, monthly report, scorecard, quarterly RARC |

### 19.2 Team (lean)

| Role | Headcount |
|---|---|
| Backend / data engineers | 3 |
| Document/ML engineer | 1 |
| Front-end engineer | 1 |
| Forward-deployed engineer | 1 |
| Former commercial property underwriter (product owner for rules and UX) | 1 |
| Pricing actuary | 0.5 |
| CAT modeller (advisory) | 0.5 |
| PM | 1 |
| **Total** | **About 9 FTE** |

---

## 20. Products 02 and 03 on the same core

What each product reuses, and what it adds:

| Core component | 01 Renewal Integrity | 02 Decision Assurance | 03 Delegated Authority Control |
|---|---|---|---|
| Evidence ledger (C/S/N/V/D/M/R, anchors, resolution policies) | Two terms per location, bitemporal | One submission, many sources that can contradict each other | Authority (BAA as endorsed) vs business written (bordereau rows) |
| Document extraction | SOV, contract PDFs, loss runs, engineering, email | ACORD 125/140 application, SOV, loss runs, inspection, manuscript wording, email | BAA + endorsements (PDF); risk, premium and claims bordereaux (xlsx/csv, any template) |
| Rule engine (YAML + CEL, tests, backtest, publish) | Standard library + carrier guidelines | Tier-1 deterministic + tier-2 critique | Authority, referral, commission, aggregate, claims and data rules |
| Authority engine | Referral level on intended renewal terms; approval tied to a terms hash | New-business matrix (deviation, TIV, premium); approval envelopes | The coverholder's authority *is* the contract, and is versioned by endorsement |
| Materiality ($) | Premium inadequacy, control exposure | Exposure corrected or prevented before commitment | Premium tied to exceptions, commission discrepancy, exposure above authority |
| Output | Action record per account | Decision pack + assurance verdict per case | Breach register per policy + authority report per coverholder |

### 20.1 Product 02: Decision Assurance (new business)

**Promise:** prepare the decision, support the judgement, control the commitment. The human underwriter remains the final decision owner.

**Problem:**
- Expert time goes on assembling the case.
- Evidence is spread across the submission, loss runs, inspection, pricing and guidelines.
- Contradictions and referral triggers get missed.
- The person making the decision is often the one validating it.
- Senior review is too expensive to apply to every material decision.

**Flow (10 stages, as built):**

| # | Stage | Group | What happens | Real / mock |
|---|---|---|---|---|
| 01 | Submission / risk | Prepare the decision | Broker email arrives with ACORD application, SOV, loss runs and inspection attached | Mock mailbox (`MailboxPort`) |
| 02 | Risk & document intelligence | Prepare | Every value extracted with its anchor and normalised to carrier classes; contradictions between sources and missing information detected | **Real** |
| 03 | Carrier context | Prepare | Appetite, guidelines and the authority matrix applied; technical price from the rater; hazard and company data | **Real** rules; mock rater, CAT and vendors |
| 04 | Draft recommendation | Prepare | Decision pack: material factors, pricing range, referral requirements, suggested terms and draft action, all source-linked | **Real** |
| 05 | Underwriter judgement | Support the judgement | Resolve contradictions, request information (the broker returns documents), override flags with a reason, pre-refer | **Real**; mock broker and inspection vendor |
| 06 | Intended action | Support | Quote, bind, refer, decline or override, with premium, deductible, limit, line, terms and rationale | **Real** |
| 07 | Independent assurance | Control the commitment | Tier-1 rules plus tier-2 critique on evidence, pricing, guidelines, appetite and authority | **Real** (tier 2 is a transparent stand-in for the production model) |
| 08 | Pass / flag / refer | Control | Verdict, reasons, remaining conditions and who must decide (tier 3) | **Real** |
| 09 | Human final decision | Control | Decision owner commits, declines or approves with conditions; quote and binder issued and read back | **Real**; mock policy admin |
| 10 | Outcome feedback | Learn | Losses or clean experience months later feed flag precision, override outcomes and tier-2 calibration | **Real**; mock claims feed |

**Stage 1 output: the decision pack.**
- Normalised facts, each with its source.
- Contradictions shown side by side, each priced by re-rating the risk on both values.
- Missing information, with a "request from broker" action.
- Material risk factors.
- Applicable guidelines, with citations.
- Pricing context: technical premium, suggested range, modifiers.
- Authority and referral requirements, suggested terms, draft action, and an evidence count.

**Stage 2 output: the assurance result.**
- Overall verdict (**Pass / Pass with flags / Refer–Hold**), with a result per dimension: evidence, pricing, guidelines, appetite, authority.
- Tier-1, tier-2 and tier-3 checks, each with its reason.
- Remaining conditions, the required decision owner, and the pricing deviation against the permitted band.

**Control model (materiality-based, from the deck):**

| Tier | What it covers | How it runs |
|---|---|---|
| 1 Deterministic | Authority, referral, deductible and limit thresholds, pricing deviation, prohibited classes, required documents | 20 tested YAML rules (`DA.DOC.*`, `DA.APPETITE.PROHIBITED`, `DA.PROT.*`, `DA.ROOF.AGE`, `DA.VAL.RC_RATIO`, `DA.ACCUM.ZONE`, `DA.CAT.*`, `DA.TERMS.*`, `DA.PRICE.*`, `DA.AUTH.*`, `DA.BIND.CONDITIONS_OPEN`) |
| 2 Assurance model | Conflicting evidence, low-confidence extraction, unusual rate against peers, large limit, manuscript wording, overrides not supported by evidence, deviation without rationale | 8 tested rules (`DA.T2.*`). The showcase uses a transparent heuristic, clearly labelled; production swaps in the critique model (§13) behind the same interface |
| 3 Human judgement | Material overrides, unresolved ambiguity, complex coverage, high severity, the final bind or decline | Routed to the named owner from the authority matrix |

**New-business authority matrix (showcase):**

| Level | Role | Pricing deviation vs technical | Max account TIV | Max location TIV | Max premium |
|---|---|---|---|---|---|
| L1 | Property underwriter | ±5% | $750M | $250M | $750K |
| L2 | Senior property underwriter | ±10% | $1.5B | $500M | $2M |
| L3 | Head of property | ±15% | $5B | $1.5B | $7.5M |
| L4 | CUO | ±30% | $10B | $2B | $50M |

Approvals are *envelopes*: minimum premium, minimum deductible, maximum line and wording. A later action outside the envelope loses the approval.

**Deck worked example, reproduced by the engine (case D1, Halvorsen Precision):**
- The application says fully sprinklered; the inspection disagrees. The contradiction is priced by re-rating the risk on both values.
- The roof is 23 years old in a hail zone.
- The engine computes technical at $520,143, with a suggested range of $500–540K.
- The underwriter intends to quote $505K with a $250K deductible. That is −2.9% against the ±5% permitted.
- Verdict: **pass with flags**. Evidence, guidelines and authority pass.
- Remaining condition: roof-replacement schedule before bind. The decision owner is the underwriter.
- The broker later sends the schedule, and bind is re-checked and passes. A hail loss months later confirms the roof flag, which feeds outcome feedback.

**Primary commercial measure:** material underwriting exposure corrected or prevented before commitment ($). It is supported by preparation hours saved, the share of cases auto-prepared, issues surfaced and errors intercepted. Loss ratio is claimed only once a live cohort proves it.

**Where others sit:**

| Vendor | Role |
|---|---|
| Sixfold | Helps underwriters understand risk faster |
| Athenium | Audits quality after the fact |
| Federato | Runs workflow and appetite |
| hyperexponential | Pricing infrastructure |

**Differentiation:** we act on both sides of the human decision (draft decision → human judgement → independent assurance → final decision), with the carrier's own rules and a dollar figure on every flag.

**Screens:**
- **Dashboard:** cases prepared, auto-prepared %, verdict mix, exposure corrected or prevented, errors intercepted, hours saved, time to decision, funnel, results by tier, underwriter and broker, flag precision from outcomes.
- **Case queue.**
- **Case page:** decision pack, intended action with a live verdict, final decision and outcome.
- **Referrals & assurance log**, rule studio, pipeline, Start here guide, and a real-mode sandbox.

### 20.2 Product 03: Delegated Authority Control (MGAs and coverholders)

**Promise:** is the coverholder actually writing the business we authorised? Delegated business is written by someone else, on the carrier's paper, under a contract the carrier rarely re-reads after signing.

**Inputs:**

| A: what the coverholder is allowed to do | B: what the coverholder actually did |
|---|---|
| Binding authority agreement (classes, territories, limits) | Risk bordereaux (policy and risk level) |
| Authority period | Premium bordereaux (written premium, commission) |
| Endorsements and amendments | Claims bordereaux (losses, reserves) |
| Product and rating rules (approved pricing) | Policy documents (actual limits, terms, deductibles) |
| Referral rules | Referral records (requests and approvals) |
| Exclusions (prohibited risks) | Exposure schedules (locations, TIV) |
| Commission terms | Endorsements |
| Aggregate and capacity limits (CAT zone, GPI) | Cancellations |

**Flow (11 stages, as built):**

| # | Stage | Group | What happens | Real / mock |
|---|---|---|---|---|
| 01 | Binding authority onboarded | Authority granted | BAA and endorsements read back from PDF into a **versioned authority contract**; every term keeps its page and box | **Real**; mock DA registry |
| 02 | Bordereau received | Business written | Monthly risk, premium and claims files arrive in the coverholder's own template; lateness against the BAA due date measured | Mock coverholder portal |
| 03 | Mapping & validation | Business written | Header detection and synonym mapping to Lloyd's CRS v5.2 with confidence; type, arithmetic, date and duplicate checks with cell references | **Real** |
| 04 | Risk-level authority checks | Control result | Class, territory, limit, deductibles, pricing range, referral triggers, exclusions, period and zone restrictions. Each line is checked against the **authority in force when it was bound** | **Real** |
| 05 | Referral reconciliation | Control result | Every referral trigger matched to an approval that exists, pre-dates binding and covers the written terms | **Real**; mock referral system |
| 06 | Premium & commission reconciliation | Control result | Risk vs premium bordereau; commission contract vs reported; return premiums; over-deductions posted as debit notes | **Real**; mock finance ledger |
| 07 | Aggregate & capacity monitoring | Control result | In-force TIV by zone vs BAA limits (warning / stop); premium income vs GPI | **Real**; mock CAT aggregate feed |
| 08 | Claims bordereau review | Control result | Claims on out-of-authority risks, late large-loss notification, reserve movements, settlement authority, dates of loss outside the period | **Real** |
| 09 | Breach register & carrier action | Remediation | One entry per policy with the side-by-side authority result; query, ratify or escalate | **Real** |
| 10 | Coverholder query & response | Remediation | Coverholder replies after a few days: corrects, supplies a referral reference, cancels, disputes or agrees. Corrections are re-checked, not trusted | Mock coverholder |
| 11 | Authority report, scorecard & amendment | Remediation | Monthly authority report, coverholder scorecard, quarterly RARC from bordereaux, audit, authority amendments by endorsement | **Real** |

**Rule catalogue (27 tested YAML rules):**

| Area | Rules |
|---|---|
| Class | `DA.CLASS.PERMITTED`, `DA.CLASS.REFERRAL` |
| Exclusion | `DA.EXCLUSION.PROHIBITED` |
| Territory | `DA.TERRITORY.PERMITTED`, `DA.TERRITORY.EXCLUDED` |
| Limit and deductible | `DA.LIMIT.MAX`, `DA.DEDUCTIBLE.MIN_AOP`, `DA.DEDUCTIBLE.MIN_NS` |
| Pricing | `DA.PRICING.BELOW_RANGE` |
| Referral | `DA.REFERRAL.TIV`, `DA.REFERRAL.TIER1_TIV`, `DA.REFERRAL.YEAR_BUILT` |
| Authority period | `DA.PERIOD.AUTHORITY` |
| Zone restriction | `DA.RESTRICTION.REFER`, `DA.RESTRICTION.STOP` |
| Commission and premium | `DA.COMMISSION.CONTRACT`, `DA.CANX.RETURN_PREMIUM` |
| Aggregate and capacity | `DA.AGGREGATE.WARNING`, `DA.AGGREGATE.LIMIT`, `DA.CAPACITY.GPI` |
| Claims | `DA.CLAIM.OUT_OF_AUTHORITY`, `DA.CLAIM.LATE_LARGE_LOSS`, `DA.CLAIM.RESERVE_JUMP`, `DA.CLAIM.SETTLEMENT_AUTHORITY`, `DA.CLAIM.DOL_OUTSIDE_PERIOD` |
| Data | `DA.DATA.LATE_BORDEREAU`, `DA.DATA.MANDATORY_FIELDS` |

**Per-policy authority result (the deck's layout):** class, territory, limit written vs authority, deductible written vs minimum, premium vs expected range, referral required / approval found, commission contract vs reported, and the recommended action. Each value links to the bordereau cell *and* the agreement clause.

**Monthly authority report (per coverholder and book):**
- Policies checked, % within authority, and exceptions by type.
- $ premium tied to exceptions, commission discrepancy and missing referrals.
- Zone aggregates vs thresholds, $ at stake, unauthorised exposure prevented, correction turnaround, and the exception trend by month.

**Coverholder scorecard:**
- Score = 0.35 × within-authority + 0.2 × data quality + 0.15 × timeliness + 0.15 × loss experience + 0.15 × trend.
- Grades: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, otherwise E.

**Quarterly RARC from bordereaux** (required by Lloyd's MS3 but not published by any bordereau platform we found):
- For each renewal line: expected = expiring premium × (renewal TIV ÷ expiring TIV) × (deductible factor now ÷ deductible factor expiring). The factors come from the BAA rating rules.
- RARC = Σ renewal premium ÷ Σ expected − 1. Headline = Σ renewal premium ÷ Σ expiring premium − 1.
- Rate on TIV is reported alongside. Renewals without expiring premium or TIV are excluded and counted.

**Remediation loop:**
1. Query the coverholder.
2. Receive and re-check the response or correction file.
3. Resolve, ratify or escalate.
4. Restrict a zone by endorsement: refer-only or stop.
5. Monitor that the restriction holds on the next bordereau.
6. Post a commission debit note and track settlement.
7. Commission an audit.
8. Amend authority by endorsement; it is effective by date and versioned.

**Core measure:** unauthorised exposure prevented or corrected. It is supported by:
- % of policies within authority
- $ premium written outside authority
- missing referrals
- aggregate breaches
- commission discrepancies
- correction turnaround
- the coverholder quality trend

**Where others sit:**
- Send / Duck Creek DA module: ingests bordereaux against binder authority, but is tied to a core system.
- VIPR, Tide, Pro Global: bordereau processing and data services.

**Differentiation:** the authority is a versioned, clause-anchored contract; referrals are reconciled to approvals; commission is recovered; and a rate change is computed from the coverholder's own data.

**Screens:**
- **Dashboard:** monthly authority report.
- **Coverholders:** list and detail (agreement, scorecard, trend, bordereaux, breaches, aggregates, queries, RARC).
- **Breach register** with a per-policy detail drawer.
- **Bordereaux:** mapping and validation.
- **Aggregates**, rule studio, pipeline, Start here guide, and a real-mode sandbox (upload a bordereau, check it against a demo or uploaded BAA).

### 20.3 Later: portfolio steering

| New input | Reuses | New pieces |
|---|---|---|
| Portfolio targets | Everything above | Appetite that responds to the portfolio (Federato-style), *driven by verified in-force state* from all three products |

---

## 21. What not to build, and the main risks

**Don't build:**

- a submission intake product (Cytora, Convr and Guidewire have it);
- a rater (hx, Earnix, Akur8);
- a CAT model (Moody's, Verisk);
- a generic copilot chat;
- a workflow or task platform beyond the action queue;
- scores without a dollar figure;
- a bordereau-processing bureau or coverholder admin system (VIPR, Tide, Pro Global do this; we check their output against the contract);
- an autonomous decision-maker for new business (product 02 advises the named decision owner, who stays human).

**Risks and mitigations:**

| Risk | Mitigation |
|---|---|
| hx hyperoperator's always-on monitoring or Cytora Autopilot extends into renewals | Go deeper on contract, evidence and the RARC split. Offer integration with both (feed our RARC components into hx). |
| Carrier data is too messy to match locations across years | Phase 0 data contract; confirmed matches reused; the backtest proves feasibility before a contract is signed |
| Underwriters distrust the findings | Evidence drawer on every number; a mandatory reason code on rejection; tune rule precision out in the open |
| The rater isn't callable | Elasticity fallback, labelled with lower confidence |
| Selling on loss ratio before it can be proven | Sell on dollars corrected plus RARC accuracy; loss ratio only after the control cohort matures |
| Scope creep into other lines | Commercial property only until two carriers are live |
| Decision Assurance seen as "second-guessing" underwriters | Verdicts cite evidence and the carrier's own rules; overrides are allowed with a reason and measured against outcomes, not blocked |
| Coverholder bordereaux too inconsistent to check | Mapping confidence and data-quality score are part of the output; missing mandatory fields are themselves a breach that goes back to the coverholder |
| Send / Duck Creek DA module or VIPR adds authority checks | Go deeper on the contract (versioned BAA with clause anchors), referral reconciliation, commission recovery and RARC from bordereaux |

---

## 22. Showcase workspace: end-to-end workflows on dummy data (all three products)

### 22.1 Why it's worth building

The same dummy world, one carrier with three products, serves three purposes, so it's built once:

1. **Sales and demo:** a CUO sees a whole book and realistic workflows for each product in 20 minutes, without supplying any data.
2. **Regression and golden set:** each scenario is a fixture with *expected findings*. Any change to a rule, prompt or model reruns them (§11.5, §13).
3. **Pilot onboarding:** underwriters learn the screens on familiar-looking cases before they see their own book.

**Build it as** a separate `demo` tenant:

- the clock is frozen at **1 Aug 2026**;
- a "reset" button restores the starting state;
- a "fast-forward" control moves the clock through T-150 → T+60 so every pass and in-force event can be shown;
- all entities are fictional, and every document carries a "SAMPLE" watermark.

### 22.2 The dummy carrier and book

| Item | Value |
|---|---|
| Carrier | **Northgate Specialty Insurance Co.** (fictional), U.S. middle-market and large property, admitted + E&S |
| Book | 120 renewing accounts, 640 locations, $9.2B TIV, $48M expiring premium, expiring Sep 2026 – Jan 2027 |
| Users | 4 underwriters (authority levels 1–3), 1 senior underwriter, 1 CUO, 1 risk engineer |
| Reference data | Guidelines PDF (2025 and **2026 versions**, where the 2026 version raises the wind deductible floor to 3%), authority matrix, form library, rater (callable Python stub), CAT results per account, hazard, valuation and imagery vendor stubs |
| Per-account documents | Prior year SOV + renewal SOV (Excel, with real-world messiness), ACORD 125/140, loss runs (PDF), quote versions, binder, dec page + forms schedule, endorsements, engineering report + recommendation register, broker emails |
| New business (product 02) | 6 hero submissions + a simulated book from Nov 2024: ACORD-style application PDF, SOV, loss runs, inspection report, broker email, manuscript wording; new-business authority matrix and classification guide |
| Delegated business (product 03) | 5 coverholders with binding authority agreements (PDF, one endorsement each), monthly risk / premium / claims bordereaux May–Aug 2026 (~3,000 policy rows), referral records, finance ledger |
| Extra persona | Claire Donovan, Head of Delegated Authority (L3) |

**Target distribution** (so the book view looks real):

| Outcome | Accounts |
|---|---|
| Fast-track | 55 (46%) |
| Reprice / restructure | 38 |
| Refer | 17 |
| Condition | 14 |
| Non-renew | 3 |
| Data request only | 12 |

Accounts can carry more than one action, so the rows add up to more than 120.

**Generation approach:**

- A seeded generator produces a consistent *true state* for each account. Broker documents are then rendered from that state with controlled errors injected: stale roof years, renumbered locations, TIV total rows, placeholders, the wrong currency scale.
- Every injected error is recorded in `expected_findings.json`, so the demo is also the test set.

### 22.3 Scenario catalogue

| # | Account (fictional) | Workflow shown | Key dummy facts | Findings the platform must produce | Action |
|---|---|---|---|---|---|
| S1 | **Crestline Office REIT**, 8 offices | Fast-track | TIV +3.8% (in line with cost trend); no claims; recommendations closed and verified; adequacy 104% | None material | `MAINTAIN`, single-click confirm |
| S2 | **ABC Manufacturing**, 5 locations | Full renewal: exposure + RARC + terms + accumulation | §10.2–10.4 figures: TIV $120M → $151M, broker counter $450K, wind deductible 2%, new Tampa location | RARC **−26.8%** despite headline +9.8%; wind deductible below the 3% floor; new location not in the CAT run and 1 km from an existing one; **binder BI $10M vs policy $15M**; Reno occupancy drift | `REPRICE + RESTRUCTURE + REFER` |
| S3 | **Lumen Jewelers**, 14 retail stores | Theft and security | Stock of $1.8–4.2M per store; burglary score in the 92nd percentile at 5 stores; alarm "yes" on the SOV, but certificates show **3 alarms not centrally monitored**; CP 04 11 alarm safeguard in the policy | Security referral (catalogue §40); **protective safeguard breach risk**; theft covered while money and securities exposure has no crime policy → cross-sell / coverage review | `CONDITION` (monitored alarm certificates) + `REFER` |
| S4 | **Redline Logistics**, 3 warehouses | Occupancy drift + sprinkler adequacy | Engineering 2024: general commodities, 20 ft storage. 2026 broker email says "now storing e-bike batteries", and imagery shows new racking. | Occupancy drift (warehouse → lithium-ion storage); **storage height 28 ft > sprinkler design 20 ft** → adequacy FAIL; CAT/pricing class mismatch | `CONDITION` (re-survey before bind) + `REPRICE` |
| S5 | **Harborview Hotels**, 6 hotels | Under-valuation | Building values flat for 3 years; reported $142/sq ft vs model $209/sq ft (68%); last appraisal 2021 | Valuation inadequacy −$38M; stale appraisal; premium leakage on the missing TIV; coinsurance and limit shortfall noted | `DATA_REQUEST` (appraisal) + `REPRICE` on the adjusted TIV |
| S6 | **Ember & Oak Restaurant Group**, 22 sites | Fire / cooking hazard | 4 grease fires in 3 years at 3 sites; hood cleaning certificates missing at 7 sites; cooking suppression listed as a safeguard | Repeat-cause indicator; cooking suppression not verified (catalogue §39); claims linked to an open recommendation | `CONDITION` + deductible restructure on fire |
| S7 | **Pinecrest Plaza**, 1 retail centre (in-force) | **Event-driven, mid-term** | 1 Apr endorsement: anchor tenant leaves, 62% vacant; June imagery shows an empty lot; sprinkler impairment notice | Vacancy beyond the policy threshold → vacancy provision; **vacant + sprinkler impaired → fire referral CRITICAL** (catalogue §41) | `REFER` now, not at renewal |
| S8 | **St. Aurelia Medical Center**, 1 campus, 12 buildings | Contract integrity + authority | Quote v2 approved by the senior UW at a $250K deductible; quote v3 changed it to $100K **after approval**; issued policy is missing the named-storm $250K minimum; subjectivity (generator test) open 212 days | Approval invalid (terms hash changed, §11.3); **minimum lost at issuance**; subjectivity bound while still open | `REFER` (re-approval) + endorsement correction |
| S9 | **Keystone Plastics**, 2 plants | Engineering commitment broken | Critical recommendation (dust collection) was a **bind condition in 2025** and is marked "closed" without evidence; a $1.4M fire claim in March 2026 at the same line | Unverified closure; broken commitment; claim linked to the recommendation (catalogue §45) | `CONDITION` + `REPRICE` + senior review; possible `NON_RENEW` |
| S10 | **Delta Scrap Metals**, admitted, Louisiana | Appetite change + notice deadline | 2026 guidelines move scrap and recycling to decline; renewal 15 Nov | Out of appetite under the current rule version; **latest non-renewal notice date shown, with a countdown**; alternative "conditional renewal" path | `NON_RENEW` or exception referral, before the deadline |
| S11 | **Summit University**, 41 buildings | Location matching / data quality | Broker renumbered every location; 2 buildings merged into 1 after a renovation; the SOV includes a totals row and values in $000s | 36 matched automatically, 3 proposed (confirmed by a human), 1 MERGED, 1 NEW; scale and totals-row handling logged; DQ score weighted by modelled-loss impact | `DATA_REQUEST` (5 secondary modifiers on the highest-AAL buildings) |
| S12 | **Meridian Data Centers**, shared layer | Large account / participation | $250M loss limit, Northgate holds 25% of $100M xs $50M; TIV $1.1B | Exposure, CAT and RARC all on the **carrier's share and layer**; concentration check against the Northern Virginia zone | `MAINTAIN` with a portfolio note |

### 22.3b Decision Assurance cases (new business)

| # | Case (fictional) | Situation | What the engine does | Outcome |
|---|---|---|---|---|
| D1 | **Halvorsen Precision Components** | Deck example: the application says fully sprinklered but the inspection disagrees; the roof is 23 years old | Contradiction priced by re-rating; technical $520K computed; $505K quote is −2.9% vs ±5% permitted | **Pass with flags**; roof schedule before bind; a later hail loss confirms the flag |
| D2 | **Larkspur Professional Plaza** | Clean office | Pack auto-prepared, no material flags | **Pass**, decided in a day |
| D3 | **Cardinal Ridge Cold Storage** | Underwriter intends to bind 18% below technical with 3 of 5 years of loss runs | Deviation beyond authority; missing years requested; the broker's full loss runs reveal a hidden $598K loss; re-rated | **Refer/Hold** → corrected re-quote within authority → bound |
| D4 | **Rivergate Industrial Services** | Declined class (scrap) hidden in the operations description, confirmed by the vendor's company NAICS code | Classification guide maps the description to the class; override refused | **Hold** → CUO declines |
| D5 | **Pelican Bay Resort Holdings** | Coastal hotels take Tampa Bay from 89.6% to 97% of its threshold | Portfolio referral to L3 | Approved at a 50% line; revised action passes with flags |
| D6 | **Palmetto Gateway Distribution** | Underwriter overrides a storage flag; the broker's manuscript wording deletes the water exclusion | Tier 2 catches both; L3 approves with conditions; verification clears them | Bound; a later $1.35M storm-surge loss is excluded under the corrected wording (outcome feedback) |

The background book has about 30 simulated new-business cases, running from Nov 2024, so the dashboard shows a real distribution and 6-month outcomes.

### 22.3c Delegated Authority coverholders

| # | Coverholder (fictional) | Story | Shown by |
|---|---|---|---|
| A1 | **Meridian Gulf Underwriting LLC** | Exceptions rising month on month (0.8% → 1.2% → 1.9% → 2.3%): limit and deductible breaches, missing referrals, commission over-deduction; Q3 RARC below the headline | Monthly close; referrals & commission; quarterly review (grade D, audit, authority tightened) |
| A2 | **Northfield Specialty Partners** | Clean benchmark; requests a capacity increase | Authority amendment by endorsement mid-period (one $8M risk beyond even the new limit, ratified) |
| A3 | **Palm Coast Commercial MGA** | South Florida CAT aggregate at 93% against a 90% warning | Zone set to referral-only by endorsement; about $58M TIV declined at the referral desk; zone ends at 94.7% instead of 98.3% |
| A4 | **Ridgeway Programs Inc.** | Late bordereaux in a non-standard layout with missing mandatory fields | CRS v5.2 mapping, resubmission; two breaches that the missing fields had hidden |
| A5 | **Sierra Crest Underwriting** | Wildfire loss on a risk in an excluded county, notified late; reserve jump | Claims review, coverage escalation, audit |

Bordereaux cover May–Aug 2026 (about 3,000 policy rows). May–July are history at 1 Aug; August files arrive 3–12 Sep during the demo.

### 22.4 Walkthrough, S2 (hero demo, about 6 minutes)

1. **T-150, Pass 1 (no new broker data).**
   - Queue shows ABC: 2 new water claims since bind; recommendation R-114 overdue.
   - Guideline v2026 raised the wind deductible floor → pre-flag.
   - Technical rerun on expiring exposure: $395K vs $410K expiring (104% adequate before any change).
2. **T-75, Pass 2.**
   - Renewal SOV arrives by email and ingests automatically.
   - Location redline: Location 5 is NEW; Reno occupancy drift. Click the roof year → evidence drawer shows the SOV cell (2011) next to engineering page 7 (2019).
3. **RARC workbench.**
   - Three model runs; the broker counter of $450K entered.
   - Screen shows **+9.8% headline, −26.8% RARC, 76.0% adequacy**, CUO (level 4) authority required.
   - What-if: $585K with a 3% deductible and $250K minimum → RARC −4.8%, adequacy 98.8%; still level 3 because of the Tampa accumulation and the loss linked to an open recommendation.
4. **Contract diff.** Binder BI $10M vs policy $15M highlighted → "endorsement correction" action.
5. **Referral.**
   - Pre-filled memo with 11 cited findings.
   - The approver signs off the exact terms; the approval is locked to that terms hash, and an L3 approver is blocked from an L4 referral.
6. **Disposition.**
   - UW accepts 9 findings and rejects 2. Reason for one of them: `already_known`.
   - Book view: dollars corrected goes up by $65K.

### 22.5 Book-level demo (CUO, about 4 minutes)

**Headline numbers** (produced by the showcase engine, not typed in):

| Measure | At reset (1 Aug 2026) | After fast-forward to 30 Sep 2026 |
|---|---|---|
| Renewals analysed | 120 (114 past T-150) | 120 |
| Fast-tracked | 52 | 54 |
| Material action | 62 | 60 |
| Economic leakage identified | $7.4M | $9.3M |
| Validated by underwriters | $0.6M | $5.1M |
| Approved (quoted within / above authority) | $0.2M | $5.0M |
| Corrected (bound terms actually cure the finding) | $0 | $0.5M |
| Book RARC, UW-reported vs computed | −2.0% vs −4.6% | +2.2% vs +0.5% |

**Interactive views:**

- **Book RARC:** underwriters under-allow for exposure growth, so self-reported rate change overstates the like-for-like figure. Click through to the account list and then to the three model runs behind each.
- **Exceptions by underwriter and broker:** pricing deviations and open findings per underwriter and broker.
- **Accumulation:** Tampa Bay passes its 90% referral threshold (92.3%) only once ABC's new location is added — the platform refers that specific renewal, not the whole zone.

### 22.6 Demo kit deliverables

| Deliverable | Contents |
|---|---|
| `demo-book/` | 120 accounts × documents (Excel, PDF, email `.eml`), guidelines v2025/v2026, authority matrix, form library |
| `expected_findings.json` | Expected findings, actions and dollar impact per scenario, for CI regression |
| `generator/` | Seeded data generator + error injector (reproducible, extendable) |
| Demo scripts | Per product, in its Start here guide: 20-minute and 45-minute scripts, and which workflow for which audience |
| Workflow playbooks | Renewal 11, Decision Assurance 6, Delegated Authority 7, plus a stage-by-stage lifecycle per subject. Narrated, with a printable client brief each |
| Real-mode sandboxes | Upload your own SOV (renewal, decision) or bordereau (delegated) and run the real parsers and controls |
| Reset + fast-forward | Frozen-clock controls in the `demo` tenant |

**Build effort:** about 3–4 weeks for 1 engineer plus the underwriter product owner, running alongside Phase 2. S1–S6 and S11 are needed for the Stage A backtest dry run anyway. Mocking the surrounding systems (§22.7) adds about 3 more engineer-weeks.

### 22.7 Mocked surrounding systems, so the pipeline runs end to end

§1 and §21 put intake, rating, policy admin, CAT, claims and billing *out of scope as products*. The showcase still has to run the whole lifecycle, so each of those gets a **basic mock**. Nothing is skipped.

**Principles:**

- **Same contract as production.** Each mock sits behind the connector interface the real system will use (§15), for example `PolicyAdminPort` and `RaterPort`. Swapping in Guidewire, hx or Moody's is a configuration change, not a rebuild.
- **Deterministic and seeded:** the same inputs always give the same outputs, so scenarios double as regression tests.
- **Fault injection:** each mock has toggles that plant the scenario errors, such as an issuance error or a stale certificate.
- **Clearly labelled:** every screen and document from a mock shows a `MOCK` badge.

| Pipeline stage (deck slide 2) | Component | Real or mock | Basic flow the mock supports |
|---|---|---|---|
| 01 Submission received | Broker mailbox + portal | **Mock** | Scripted emails with attachments arrive at set demo dates. The broker answers a data request 3 demo days later with real documents (licence, certificates, schedules, reports), which are parsed and clear the related findings and subjectivities. |
| 02 Clearance | Clearance service | **Mock** data, **real** gate | Duplicate check; broker licence checked in **every location state**; sanctions screening. A HOLD blocks quoting and binding until resolved (e.g. S6 expired licence) |
| 03 Appetite & triage | Rule engine | **Real** (ours) | Current guideline version applied; decline or refer with reason |
| 04 Extraction & enrichment | Ingestion (ours) + vendor stubs | Real + **mock vendors** | Geocoder, hazard, crime, valuation and imagery return fixture JSON keyed by address, with vendor name, version and date so provenance looks real |
| 05 Risk assessment | Engineering module | **Mock** | Order a survey → the engineer's report arrives 7 days later and is ingested as verified evidence; recommendations move OPEN → CLOSED (evidence) → VERIFIED_CLOSED, or new ones are raised (S4) |
| 06 Pricing & modelling | Rater + CAT stubs | **Mock** | Rater: Σ locations of TIV × base rate (occupancy × construction × PPC) × modifiers, plus CAT load, deductible credit curve, expense and profit loads, and schedule modifiers, versioned `rater-stub v1.x`. CAT: AAL = TIV × zone peril rate × secondary modifiers; OEP 1-in-100/250 from a fixed curve; DQ flags for missing fields. Both callable three times for the RARC split. |
| 07 Authority & portfolio | Authority + accumulation | **Real** (ours) | Authority matrix, referral, approvals locked to a terms hash; zone-grid accumulation over the demo book |
| 08 Terms & quote | Quote builder | **Real** (ours) | Terms and forms → quote version locked to a terms hash → quote PDF, read back by the extractor; blocked while clearance is on hold |
| 09 Broker negotiation | Broker bot | **Mock** | Accepts at or near target/technical, otherwise counters at the midpoint |
| 10 Bind | Bind flow | **Real** (ours) | Bind blocked without an approval for the exact terms; approval conditions printed on the binder as subjectivities and cleared by matching documents |
| 11 Policy issuance | Policy admin stub | **Mock** | Stores policy, coverage, forms and safeguards; generates the dec page and forms schedule. An **issuance-error toggle** creates the S2/S8 mismatches, which are then fixed by a **corrective endorsement** |
| 11b Billing | Billing stub | **Mock** (minimal) | Invoice record and booked premium; enough to show the premium-booked figure on the book view |
| 12 Mid-term monitoring | Policy admin endorsements + claims stub | **Mock** | Endorsements posted on the demo timeline (add location, vacancy). Claims stub posts first notice of loss, then reserve changes and payments. The presenter can also raise a claim, impairment or vacancy live. Each event triggers **real** re-evaluation by our platform. |
| 13 Claims & exposure feedback | Outcome capture | **Real** (ours) | Claims and endorsements feed `outcome` and risk-quality deltas |
| 14 Portfolio steering | Book view | **Real** (ours) | CUO view; accumulation; exceptions by underwriter and broker |
| 15 Renewal | Renewal engine | **Real** (ours) | Passes 1–3; the account goes back into stage 03 for the next term |
| — | Data warehouse extract | **Mock** | CSV/Parquet drop, the same format a pilot carrier would send. Exercises the backtest path (§18). |
| — | Notifications | **Mock** | In-app plus a mock email outbox (referral requests, broker data requests, notice-deadline alerts) |

**Demo timeline engine:** each scenario is a script of dated events. Fast-forward replays them through the mocks, and our platform reacts as it would in production:

```yaml
scenario: S7_pinecrest_vacancy
events:
  - day: -365  pas.issue_policy        {policy: PP-2025-0311}
  - day: -120  pas.endorse             {type: vacancy, pct: 0.62}
  - day:  -60  imagery.publish         {condition: empty_lot}
  - day:  -55  engineering.impairment  {system: sprinkler, status: impaired}
  - day:  -55  expect.finding          {rule: VAC.FIRE.SPRINKLER_OFF, severity: critical}
  - day:  -54  expect.action           {type: REFER}
```

`expect.*` lines are checked automatically, so the same script is both the demo and a test.

**Result:** a viewer can follow one account from broker email, through clearance, triage, enrichment, pricing, referral, quote, negotiation, bind, issuance, endorsements and claims, to renewal and back again. Only the components we sell are production-grade; everything else is a clearly labelled, swappable mock.

Products 02 and 03 use the same principles, with their own stand-ins (§20.1, §20.2, §23.3):
- **Decision Assurance:** submission mailbox, broker, inspection vendor, rater/CAT, policy admin, claims outcomes.
- **Delegated Authority:** coverholder portal and responder, referral system, finance ledger, CAT aggregate feed, DA registry.

---

## 23. Showcase implementation (as built, 26 Sep 2026)

### 23.1 One core, three product modules

- **Backend:** Python 3.12 and FastAPI. Each product is a module with the same interface (`backend/uwc/products/__init__.py`). It declares:
  - pipeline stages;
  - its subjects (accounts, cases or coverholders);
  - a stage-workspace builder;
  - playbooks and a step runner;
  - live facts, a mocks console, and rule backtest and publish hooks;
  - state initialised once per reset and a daily clock hook.

  The shared API, pipeline pages, workflow player, briefs, rule studio, documents viewer and outbox work for all three unchanged.
- **Shared runtime:** one demo clock (frozen at 1 Aug 2026), one reset snapshot, dated events and dynamic events (broker replies, coverholder responses, engineering visits). Every playbook starts from the same clean state, so every run can be repeated.
- **Frontend:** React 19, Vite, TypeScript, Tailwind v4, TanStack Query, MapLibre, pdf.js, react-three-fiber and recharts.
  - A **Product** selector at the top of the sidebar switches the nav.
  - Each product lives in `web/src/products/<id>/` (nav, routes, (i) help, pages). Shared pages mount under `/<product>/pipeline…`.

| | 01 Renewal Integrity | 02 Decision Assurance | 03 Delegated Authority |
|---|---|---|---|
| Base URL | `/` | `/decision` | `/delegated` |
| Subjects | 12 hero accounts + 108 background | 6 hero cases + background book | 5 coverholders |
| Pipeline stages | 15 | 10 | 11 |
| Rules | 38 | 28 (20 tier-1, 8 tier-2) | 27 |
| Workflows | 11 + a 15-stage lifecycle per account | 6 + a 10-stage lifecycle per case | 7 + an 11-stage lifecycle per coverholder |
| Pages | Book, Renewals, Account, Referrals, Portfolio, Documents, Data quality | Dashboard, Case queue, Case, Referrals & assurance | Dashboard, Coverholders, Breach register, Bordereaux, Aggregates |
| Real-mode sandbox | Your SOV → parser, mapping, DQ checks, year-over-year matching | Your SOV (+ application PDF) → decision pack → your intended action → verdict | Your bordereau (+ BAA) → CRS mapping, validation, authority checks |

### 23.2 Same demo structure in every product

- **Start here guide:**
  - what it is, and what you're looking at
  - real vs mock, and "can I run it for real"
  - how to run it, and a 10-minute first-time tour
  - 20 and 45-minute demo scripts, and which workflow to show which audience
  - takeaways and a glossary
- **(i) help on every page and section:** what it is, how it fits, how to use it, and a REAL / MOCK / MIXED badge.
- **Pipeline & mocks:** stage cards open that system loaded with the chosen subject's data, alongside a mocks console and an outbox.
- **Workflow player (presenter mode):**
  - Play, pause, resume, stop, single-step and restart, with a pace slider.
  - Voiceover and captions, and a visible cursor that clicks what each step acts on.
  - Narration is written without figures; the **engine's live result** for each step is read out after it runs.
- **Client brief per workflow:** audience, business problem, what happens, real vs stand-in, what to point at, value, and questions to ask. A live-facts tab shows engine figures, and a printable version is at `/<product>/pipeline/brief/<id>`.

### 23.3 The mocks close the loop

| Product | Stand-in | Behaviour |
|---|---|---|
| 01 | Broker | Accepts at or near target/technical, otherwise counters at the midpoint. Returns requested documents 3 days after a data request; the documents are parsed and clear findings and subjectivities |
| 01 | Clearance | Broker licence by location state, sanctions, duplicates. A hold blocks quoting and binding |
| 01 | Engineering | Site visit 7 days after it is ordered; the report verifies or raises recommendations |
| 01 | Policy admin | Issues the policy, optionally mis-keys a term (fault injection); corrective endorsement; invoice |
| 01 | Claims / impairments | Scripted, or raised live by the presenter |
| 02 | Submission mailbox, broker | Broker returns requested documents after 3 days |
| 02 | Inspection vendor | Report 7 days after order |
| 02 | Rater + MockCat | Technical price |
| 02 | Policy admin, claims | Quote and binder documents; outcome months later |
| 03 | Coverholder portal | Monthly bordereaux in the coverholder's own template, on dated events |
| 03 | Coverholder responder | Corrects, supplies a referral reference, cancels, disputes or agrees; the correction file is re-checked |
| 03 | Referral system | Approvals; zone referrals decided by a headroom rule |
| 03 | Finance ledger, CAT aggregate feed, DA registry, audit team | Debit notes and settlement; county → zone mapping and PML ratio; binder store; audit findings |

Everything else is the product itself: extraction, evidence ledger, matching, rules, pricing split, authority, contract comparison, verdicts, breach register, reports and scorecards.

**Known simplifications (stated in the UI):**
- The tier-2 assurance model is a transparent heuristic.
- The mock rater prices sprinklered industrial risk low, so D1 has a $491M schedule to reach the deck's $520K technical premium, and the new-business authority limits are scaled to match.
- The statutory notice table is illustrative.
- Referral approvals can't be verified for an uploaded bordereau without the carrier's referral system.

### 23.4 Verification

The regression runs every workflow of all three products from a clean reset, with all three loaded together:
- 23 renewal, 12 Decision Assurance and 12 Delegated Authority playbooks (lifecycles included): **all passed**, with no step failures.
- Every pipeline stage opens for every subject.
- Mocks, rules and outbox endpoints respond for each product.
- The web app compiles cleanly (TypeScript, strict).
- Pages were checked in the browser with no console errors, and two workflows per product were played through in the player.
- The renewal scenario regression (S1–S12 expected findings) is unchanged.

### 23.5 Run it

```bash
./start.sh
```

Then open `http://localhost:5173`, choose a product in the sidebar and open **Start here**. Reset any time from the demo-clock menu; every workflow's Play button resets first. To rebuild the demo world, delete `data/runtime/reset_state.pkl` and restart.

---

### Sources

- Project deck *Insurance Overview* (slides 2, 7–18, incl. Product 02 slides 13–15 and Product 03 slides 16–17) and *Commercial Property Data Points* (§§2–48).
- Lloyd's Coverholder Reporting Standards v5.2 (bordereau fields).
- Lloyd's PMDR Underwriters' Guide (RARC method) and MS3 Price & Rate Monitoring.
- Vendor sources:
  - Cytora (Applied acquisition, Autopilot, renewals);
  - Federato (Velocity Risk case, Series D);
  - Sixfold (P&C product, AI Underwriter);
  - Kalepa (Berkley);
  - hx (Renew, hyperoperator, Allianz);
  - Send / Duck Creek (acquisition, delegated authority module);
  - Guidewire UnderwritingCenter / Olos;
  - Archipelago (data model, SOV cleansing);
  - Moody's (Risk Data Refinery, UnderwriteIQ, DQ Toolkit, CAPE);
  - Verisk ProMetrix;
  - Nearmap renewal underwriting;
  - Athenium CairnQA;
  - VIPR; Charles Taylor Tide; Lloyd's DDM.
- Carrier sources: AIG (Reinsurance News, Carrier Management), Chubb (PEX), Travelers (Carrier Management), FM RiskMark (Risk & Insurance), Allianz BRIAN, Hiscox.
- Vendor outcome figures are self-reported and have no control groups.
