# Anaira Underwriting Control — Showcase Build

Implements `commercial-property-platform-blueprint.md` (repo root) as a working
showcase: real control engine + mocked surrounding carrier systems + a fictional
book (Northgate Specialty Insurance Co., 120 renewing accounts).

```
/backend      FastAPI + SQLite. Engine (real), mocks, data generator.
/data         Generated world (documents + fixtures). Rebuilt by `uv run python -m uwc.generate`.
/web          React 19 + Vite + Tailwind v4 + TanStack Query.
/docs         This file.
```

Run: `cd backend && uv run uvicorn uwc.api:app --port 8765` and `cd web && npm run dev` (proxy `/api` → 8765).

## Contract

`web/src/api/types.ts` is the **single source of truth** for every payload.
`web/src/api/client.ts` has one hook per endpoint. Backend conforms to both.

| Method | Path | Returns |
|---|---|---|
| GET | `/api/users` | `User[]` (header `X-User-Id` selects persona) |
| GET | `/api/demo/state` | `DemoState` |
| POST | `/api/demo/reset` | `DemoState` |
| POST | `/api/demo/advance` `{days?, to?}` | `AdvanceResult` |
| POST | `/api/demo/injections` `{key: bool}` | `DemoState` |
| GET | `/api/book` | `BookSummary` |
| GET | `/api/renewals?status&uw&q` | `RenewalQueueItem[]` |
| GET | `/api/accounts/{id}` | `AccountDetail` |
| GET | `/api/accounts/{id}/fields?subject_id` | `ResolvedField[]` |
| GET | `/api/observations/{obs_id}` | `ObservationDetail` |
| GET | `/api/accounts/{id}/rarc` | `RarcResult` |
| POST | `/api/accounts/{id}/rarc/whatif` | `RarcResult` |
| GET | `/api/accounts/{id}/contract` | `ContractDiff` |
| GET | `/api/accounts/{id}/cat` | `CatResult[]` (CURRENT first) |
| GET | `/api/accounts/{id}/claims-engineering` | `ClaimsEngineering` |
| POST | `/api/findings/{id}/disposition` | `Finding` |
| POST | `/api/accounts/{id}/quotes` `{premium, terms}` | `QuoteVersion` |
| POST | `/api/accounts/{id}/quotes/{qid}/send` | `QuoteVersion` (broker bot answers on next advance) |
| POST | `/api/accounts/{id}/referrals` `{quote_id, note}` | `Referral` |
| GET | `/api/referrals?status` | `Referral[]` |
| POST | `/api/referrals/{id}/decision` `{decision, conditions?}` | `Referral` |
| POST | `/api/accounts/{id}/data-request` `{items}` | `OutboxMessage` |
| POST | `/api/accounts/{id}/bind` `{quote_id}` | `{binder_doc_id, findings}` |
| POST | `/api/accounts/{id}/issue` | `{policy_doc_id, findings}` (mock PAS; error injection toggle) |
| GET | `/api/documents?account_id&type&format&q` | `DocumentMeta[]` |
| GET | `/api/documents/{id}` | `DocumentMeta` |
| GET | `/api/documents/{id}/raw` | file bytes with correct content-type |
| GET | `/api/documents/{id}/xlsx` | `XlsxPayload` |
| GET | `/api/documents/{id}/eml` | `EmlPayload` |
| GET | `/api/documents/{id}/extraction` | `ExtractionPayload` |
| GET | `/api/rules` / `/api/rules/{id}` | `Rule[]` / `Rule` |
| POST | `/api/rules/{id}/test` `{yaml}` | `RuleTestResult[]` |
| POST | `/api/rules/{id}/backtest` `{yaml}` | `BacktestResult` |
| POST | `/api/rules/{id}/publish` `{yaml}` | `Rule` |
| GET | `/api/data-quality` | `DataQualitySummary` |
| POST | `/api/data-quality/review/{item_id}` | ok |
| GET | `/api/portfolio/accumulation` | `AccumulationZone[]` |
| GET | `/api/geo/hazards` | GeoJSON FeatureCollection (`properties.layer` ∈ wind, flood, eq, wildfire; `properties.tier`, `label`) |
| GET | `/api/pipeline` | `PipelineStage[]` (15 stages; REAL / BASIC / MOCK) |
| GET | `/api/mocks/systems` / `/api/mocks/outbox` | `MockSystem[]` / `OutboxMessage[]` |
| GET | `/api/search?q` | `SearchHit[]` |

## Frontend structure

- `layout/Shell.tsx` — sidebar, search (⌘K), **demo clock** (advance / reset / jump to next event), persona switcher. Done.
- `components/ui.tsx` — primitives (Page, Card, Stat, Button, Tabs, Segmented, Badge, SeverityPill, ObsTypeChip, MockBadge, KV, Delta, ScoreRing…). Use these; don't restyle ad hoc.
- `components/evidence.tsx` — `useEvidence()` → `openObs(obsId)`, `openFinding(f)`, `openDoc(docId, anchor)`; `<EvidenceLink obsId>` for any clickable number.
- `components/EvidenceDrawer.tsx` — right slide-over: observation, all competing observations for the field (type chip, source, confidence, date), resolution policy explainer, conflict flag, and an inline preview of the source document **scrolled/zoomed to the anchor**.
- `components/DocumentModal.tsx` — full-screen document viewer for `ev.doc`.
- `viewers/` — format viewers (see below). `DocumentViewer({docId, anchor})` dispatches by `DocumentMeta.format`.
- `pages/` — screens.

### Viewers (`web/src/viewers/`)

| Component | Input | Must support |
|---|---|---|
| `PdfViewer` | `url`, `anchor?`, `highlights?` | pdf.js render, page nav, zoom, **bbox highlight overlay** (bbox in PDF points, top-left origin), auto-scroll to anchored page, text layer for selection |
| `XlsxViewer` | `payload: XlsxPayload`, `anchor?` | sheet tabs (hidden sheets marked), column letters + row numbers, **merged cells**, **hidden rows/cols shown collapsed with a marker** (toggle "show hidden"), bold/fill, number formats, frozen header, virtualised, **cell highlight + scroll into view** for `anchor.cell`, row highlight for `anchor.range` |
| `EmlViewer` | `payload: EmlPayload` | header block, body, attachment chips (click → `openDoc`), extracted-statement highlights |
| `ModelViewer` | `url` (GLB), `colorBy?: Record<nodeName, string>`, `highlightNode?`, `onSelectNode?` | react-three-fiber, orbit controls, auto-fit camera, soft lighting + ground shadow, node hover tooltip (name + `extras`), click-select, legend, toggle for semi-transparent nodes (e.g. `SPRINKLER_DESIGN_PLANE`), measurement grid in ft |
| `ImageViewer` / `ImageCompare` | `url` / `before`, `after` | zoom/pan; before/after slider for aerial imagery |
| `CsvViewer` | text | sortable virtualised table; for CAT ELT also a loss histogram |
| `JsonViewer` | text | collapsible tree; special render for CAT EP-curve JSON (log-scale return-period chart) |
| `TextViewer` | text | YAML/plain with line numbers + syntax tint |
| `GeoMap` | `points`, `zones?`, `hazards?`, `onSelect?` | MapLibre, light basemap, clustered points coloured by severity, accumulation circles, hazard layer toggles |
| `EpCurveChart` | `oep`, `aep`, `compare?` | Recharts, log x-axis return period |

`viewers/ViewerGallery.tsx` at route `/_viewers` shows every viewer with sample files from `web/public/samples/`.

## Domain scenarios (demo book)

Demo clock starts **2026-08-01**. Northgate Specialty Insurance Co. (fictional).
Personas: Maya Chen (UW, L1), Daniel Okafor (UW, L2), Priya Raman (Senior UW, L3), Robert Hale (CUO, L4), Elena Brooks (Risk engineer).

| # | Account | What it demonstrates |
|---|---|---|
| S1 | Crestline Office REIT | Fast-track, no material change |
| S2 | ABC Manufacturing | Hero: TIV $120M→$151M, headline +9.8% but RARC −26.8% (engine output), wind ded 2% < 3% floor, new Tampa loc not in CAT run & accumulation, binder BI $10M vs policy $15M, Reno occupancy drift, roof-year conflict SOV 2011 vs engineering 2019 |
| S3 | Lumen Jewelers | Theft/security: unmonitored alarms, protective safeguard, crime gap |
| S4 | Redline Logistics | Occupancy drift → lithium-ion; storage 28 ft > sprinkler design 20 ft (3D model shows racks vs design plane) |
| S5 | Harborview Hotels | Under-valuation 68% of model RC; flat values 3 yrs |
| S6 | Ember & Oak Restaurant Group | Grease fires, cooking suppression unverified |
| S7 | Pinecrest Plaza | Mid-term vacancy + sprinkler impairment (event-driven) |
| S8 | St. Aurelia Medical Center | Approval invalidated by terms change; NS minimum lost at issuance; open subjectivity 212 days |
| S9 | Keystone Plastics | Bind-condition recommendation "closed" without evidence + linked $1.4M claim |
| S10 | Delta Scrap Metals | Appetite change → decline; non-renewal notice deadline countdown |
| S11 | Summit University | Location matching: renumbered, merged, $000s scale, totals row |
| S12 | Meridian Data Centers | Shared layer 25% of $100M xs $50M; exposure on carrier share |

Other 108 accounts are generated with realistic variation (≈46% fast-track).
