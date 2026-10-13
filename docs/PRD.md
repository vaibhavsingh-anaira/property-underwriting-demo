# PRD: SMB Risk Verification (Quick check)

## Problem
Small-business insurance applications are self-declared, and misclassification is common (Verisk: about 52% of small
commercial records carry the wrong industry code). The evidence to check them is scattered across public registers, city
records and the business's own website.

## Goal and users
Show that we can verify an underwriter's application answers by joining messy public sources, reading unstructured text with
an LLM, and showing the evidence behind every answer. Users: underwriters (check answers) and carrier or MGA demo audiences
(see accuracy on real data). **Not in scope:** loss prediction, automated decisions, storing Google reviews, lines other than
restaurants. **Scope:** Manhattan food businesses listed in NYC health inspections; configurable to all five boroughs.

## Source map: what each source actually reports
"States" means the source records the fact. "Inferred" means we derive it, and the evidence shown says how. Every dataset
link below was checked and resolves to the named dataset.

| Source | Link | Fields we use | What we derive | How | Level |
|---|---|---|---|---|---|
| NYC health inspections | [43nn-pn8j](https://data.cityofnewyork.us/d/43nn-pn8j) | name, address, cuisine, inspection date, action, violation, critical flag, grade, BIN, BBL | Business identity; first inspection; last grade; closures and critical violations in 3 yrs | States | Business |
| NYS liquor licences | [9s3h-dpkz](https://data.ny.gov/d/9s3h-dpkz) | licence type, legal name, trade name, address, location, first issue, expiry | **Serves alcohol = yes**; licence first issued; legal name | States (licence held). No licence found = weak "no" | Business |
| NYC Dining Out licences | [fpeh-f7ci](https://data.cityofnewyork.us/d/fpeh-f7ci) | legal name, trade name, sidewalk/roadway type, status, issue date | **Outdoor seating = yes** | States (licensed sidewalk or roadway dining) | Business |
| NYS company register | [n9v6-gdp6](https://data.ny.gov/d/n9v6-gdp6) | entity name, formation date, entity type | Legal entity formed | States | Legal entity |
| FDNY summonses (OATH) | [jz4z-kudi](https://data.cityofnewyork.us/d/jz4z-kudi) | respondent name, block/lot, charge, hearing result | Number of fire summonses and main charges | States; attributed only when respondent name matches the business | Business |
| PLUTO | [64uk-42ks](https://data.cityofnewyork.us/d/64uk-42ks) | year built, floors, building class | Building age, height, class | States | Tax lot |
| DOB violations | [3h2n-5cm9](https://data.cityofnewyork.us/d/3h2n-5cm9) | violation status, description | Open DOB violations | States | **Whole building**, not the tenant |
| DOB ECB violations | [6bgk-3dad](https://data.cityofnewyork.us/d/6bgk-3dad) | violation status, description | Active ECB violations | States | **Whole building**, not the tenant |
| 311 complaints | [erm2-nwe9](https://data.cityofnewyork.us/d/erm2-nwe9) | complaint type, venue type, time | **Open after midnight = yes** if 2+ bar/restaurant noise complaints between 00:00 and 05:00 | Inferred (complaint time is not opening hours); used only where one food business is on the lot | Tax lot |
| OpenStreetMap | [licence](https://www.openstreetmap.org/copyright) · [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | venue category, opening hours, outdoor_seating, delivery, website | **Serves alcohol = yes** only if mapped as bar, pub, nightclub or beer garden; open after midnight from posted hours; outdoor seating and delivery tags; website URL | Category is inferred (OSM has no alcohol field); hours and tags are crowd-entered | Venue |
| Business website | No dataset: each business's own site (URL from its OpenStreetMap entry), shown on its profile | home page and one menu page | Serves alcohol (drinks or wine list); **fried items on menu**; delivery (own or app); posted hours past midnight; outdoor seating mention | Inferred from what the business publishes. Read by an LLM (Gemini 2.5 Flash), which must copy the supporting sentence word for word from the page. Deep frying comes from menu items (fries, tempura, wings), not a statement | Business |
| Google Maps reviews (live) | No dataset: a Google Maps place link is returned with each answer · [method](https://ai.google.dev/gemini-api/docs/maps-grounding) | Maps place data and reviews, summarised live by Gemini | Nothing stored or derived; shown to the underwriter only | n/a | Venue |

## Requirements
1. Download each source as one snapshot; fail if the row count differs from the server.
2. Match businesses across sources; keep the method and score of every match.
3. For each website answer, Gemini must copy the sentence from the page that supports it. We then search the page for that
   exact sentence; if it is not there, the answer is discarded. This stops the LLM from inventing evidence.
4. Resolve facts by trust (official > own website > missing licence > crowd/complaints) and flag conflicts.
5. App: search, profile with evidence links, application check (consistent / contradicted / no evidence), live Maps insight.

## Success metrics
| Metric | How it is measured |
|---|---|
| Accuracy of website answers | Website "serves alcohol" answers compared with the liquor licence records; disagreements hand-reviewed |
| Evidence integrity | Share of website answers whose supporting sentence is found word for word in the page |
| Match accuracy | Hand-check of a random sample of matches for each matching method |
| Coverage | Share of businesses with a value for each fact, and linked to each source |
| Conflicts surfaced | Number of businesses where sources disagree on an application fact |

## Constraints, risks, next steps
- Google Maps terms forbid saving reviews or deriving content from them; NYC Open Data needs legal review for commercial use.
- Building-level records cannot be pinned to one tenant where several businesses share the lot.
- Public data shows facts, not losses. Next: read websites for every business, extend to five boroughs, and test against a design
  partner's real applications and claims.
