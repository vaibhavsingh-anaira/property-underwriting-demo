# Anaira Underwriting Control — Commercial Property (showcase build)

A working implementation of `commercial-property-platform-blueprint.md`: a real control engine
(evidence ledger, extraction, location matching, RARC split, rule engine, contract integrity,
authority) running over a fictional carrier book, with every surrounding carrier system mocked
behind the same connector contracts production would use.

## Three products, one core

Switch with the **Product** selector at the top of the sidebar. Each product has the same structure:
Start here guide, dashboard, domain pages, pipeline & mocks, narrated workflow player with client briefs,
(i) help on every page, rule studio, and a "Your data (real)" sandbox.

| Product | Base URL | Subjects | Workflows |
|---|---|---|---|
| 01 Renewal Integrity | `/` | 12 renewal accounts (S1–S12) + 108 background | 11 + 15-stage lifecycle per account |
| 02 Decision Assurance | `/decision` | 6 new-business cases (D1–D6) + background book | 6 + 10-stage lifecycle per case |
| 03 Delegated Authority Control | `/delegated` | 5 coverholders (A1–A5), monthly risk/premium/claims bordereaux | 7 + 11-stage lifecycle per coverholder |

Code: `backend/uwc/products/{renewal.py,decision/,delegated/}` (same interface, see `products/__init__.py`),
`web/src/products/{renewal.tsx,decision/,delegated/}`. Rules per product in `backend/uwc/products/<id>/rules/`.

## Run

```bash
./start.sh
```

Then open http://localhost:5173 and click **Start here** in the sidebar — it explains the product, what is
real vs mocked, a 10-minute first-time tour, 20/45-minute demo scripts and which workflow to show to whom.
First boot builds the demo world and the reset snapshot (~20 s). To rebuild, delete `data/runtime/reset_state.pkl`.

**Real mode:** `/sandbox` ("Your data (real)") runs your own .xlsx/.csv SOV through the real parser,
occupancy/construction mapping, data-quality controls and year-over-year matching. Pricing, CAT and contract
checks need the carrier's rater, CAT model and policy system, so they only run against the stand-ins.

Manual start:

```bash
cd backend && uv sync && PYTHONPATH=. uv run python -m uwc.generate      # build the demo world (once)
cd backend && PYTHONPATH=. uv run uvicorn uwc.api:app --port 8765
cd web && npm install && npx vite --port 5173
```

## What is real vs mocked

| Real (the product) | Mocked (stand-ins, labelled `MOCK` in the UI) |
|---|---|
| SOV parser (header band, synonyms, $000s, totals, hidden rows/cols, placeholders) | Broker mailbox & broker bot |
| PDF extraction with bounding-box anchors (pdfplumber) | Policy admin (quotes, binders, issuance, endorsements) |
| Email statement extraction | Claims system |
| Bitemporal evidence ledger (C S N V D M R), per-field resolution policies | Engineering register |
| Location matching across years (6-rung cascade, merges, human review) | Rater (NS-PROP-RATER v8.0 mock) |
| RARC split from three model reruns, gross/net, model drift | CAT model (event-based MockCat: ELT, OEP/AEP) |
| Versioned YAML rule engine (CEL-style, sandboxed), tests, backtest, publish | Geocoder, hazard, valuation, crime, aerial imagery, 3D models |
| Contract integrity quote → binder → policy → endorsed; corrective endorsements | Clearance data (broker licence table, screening list) |
| Authority & referrals locked to a terms hash; bind blocked without a valid approval; clearance hold blocks quoting | Billing |
| Approval conditions → binder subjectivities, cleared by matching documents | |
| Materiality in $, actions, narrative with citations, critique pass | |
| Accumulation by CAT zone, statutory notice windows | |

## Demo script (20 minutes)

1. **Book** (persona Robert Hale, CUO): the dollar pipeline, reported vs computed RARC, accumulation.
2. **Renewals → ABC Manufacturing (S2)** at 1 Aug: Pass 1 found the 2% named-storm deductible
   against the new 3% floor, a binder/policy BI mismatch, water losses linked to an overdue
   recommendation. Click any number → evidence drawer → source PDF/Excel cell highlighted.
3. **Demo clock → jump to 18 Aug** (renewal SOV arrives): Pass 2 — new Tampa location, Reno
   lithium-ion drift, headline +9.8% but RARC −26.8%, adequacy 76%, CUO authority required.
4. **Pricing** what-if → save quote → refer (Maya, L1) → switch persona to Robert → approve →
   send → advance 5 days → broker accepts → **Contract** tab → Bind → Issue. The mock PAS drops
   the named-storm minimum; Pass 3 catches it immediately.
5. **Pinecrest Plaza (S7)**: advance past 6 Aug — sprinkler impairment on a 62%-vacant building
   triggers an event-driven critical referral mid-term.
6. **Redline Logistics (S4) → Locations**: 3D warehouse, racks at 28 ft above the 20 ft sprinkler
   design plane; before/after imagery.
7. **Rule studio**: edit a threshold, run tests, backtest on the frozen book, publish v+1.
8. **Pipeline & mocks**: all 15 lifecycle stages, which are real / basic / mock. Click any stage to open
   its system (mailbox, clearance, rule engine, extraction, engineering, rater + CAT, authority, quote
   builder, broker bot, bind, PAS, in-force events, claims, portfolio, renewal engine) loaded with a
   scenario account's data, and run that stage's step.
9. **Workflow player** (`/pipeline/journey`): eleven complete flows, each from submission to an issued (or
   non-renewed) policy — full renewal with issuance error + corrective endorsement + subjectivity cleared (S2),
   fast-track (S1), appetite decline & notice (S10), mid-term impairment with restoration verified by an engineer
   visit (S7), broker counter that invalidates an approval (S2), declined referral → alarm certificates → crime
   form (S3), renumbered campus matching (S11), broken engineering commitment verified on site (S9), contract &
   authority (S8), clearance hold on an expired broker licence (S6), occupancy drift → survey → new critical
   recommendation (S4) — plus "all 15 stages" for every scenario account.
   The mocks close the loop: a data request makes the broker return real documents 3 days later (parsed like any
   other file), an ordered survey produces an engineering report 7 days later, issuance produces an invoice.
   Each flow has a **Client brief** (audience, problem, what happens, real vs mocked, what to point at, value,
   questions) in the player and as a printable page (`/pipeline/brief/<id>`), plus **Live facts** computed by
   the engine. Narration is written without figures; the live result of each step is read out after it runs.
   Controls: **Play** (clean run from 1 Aug), **Pause**, **Resume**, **Stop** (keeps state), **Step**,
   **Restart**. Keyboard: space = play/pause/resume, → = step, esc = stop. Pace slider 0.4×–1.5×, voice picker,
   voice speed, captions. For the best voice install a Premium system voice (e.g. "Ava (Premium)").
10. **Stage 12 workspace**: raise a claim, impairment or vacancy live and watch the account re-evaluate.

Every page and most panels have an (i) button explaining what it is and how it fits the product.

Reset any time from the demo-clock menu.

## Layout

```
backend/uwc/   engine (ingest, ledger, engine, rules), mocks, world generator, API
data/world/    generated documents + mock-system stores + event script
data/runtime/  runtime documents, reset snapshot, ledger.sqlite (inspection copy)
web/src/       React app (pages, viewers, components)
docs/          ARCHITECTURE.md (API contract, structure, scenarios)
```

All data is fictional; every document is watermarked SAMPLE.
