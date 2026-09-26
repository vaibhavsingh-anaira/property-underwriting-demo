// S2 — ABC Manufacturing. The hero account; every figure matches blueprint §10.2–10.4.
import type { CatResult, ClaimsEngineering, ContractDiff, DeltaCard, Finding, LocationRow, Observation, TimelineEvent } from '@/api/types';
import type { AccountBundle, RarcBase } from './model';
import { buildBundle, docsFor, type AccountSpec } from './builders';
import { doc, ev, fnd, loc, pdfA, sysA, xlsA } from './util';

const A = 'acc-abc';
const SOV26 = `${A}-sov-current`, SOV25 = `${A}-sov-prior`;
const ENG_TPA = `${A}-eng-tampa`, ENG_RNO = `${A}-eng-reno`, BINDER = `${A}-binder-prior`, DEC = `${A}-dec-prior`;
const EML_SUB = `${A}-email-sub`, EML_CTR = `${A}-email-counter`, GUIDE = 'ref-guidelines-2026';

const locations: LocationRow[] = [
  loc({ location_uid: 'abc-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Dayton Machining Plant', address: '1450 Stanley Ave', city: 'Dayton', state: 'OH', lat: 39.7801, lon: -84.2105,
    match_method: 'loc_no + address', match_score: 0.99, tiv_prior: 48_000_000, tiv_current: 49_400_000, occupancy: 'Metal fabrication & machining', construction: 'Non-combustible (ISO 3)', year_built: 1978, stories: 1, sqft: 212_000, roof_year: 2014,
    sprinkler: 'Wet pipe, full', valuation_ratio: 0.71, cat_zone: 'Ohio Valley SCS', aal: 16_900, buildings: 2,
    flags: [{ code: 'UNDERVALUED', label: 'Under-valued: 71% of model RC', severity: 'HIGH', finding_id: 'f-abc-dayton-val' }] }),
  loc({ location_uid: 'abc-l2', loc_no_prior: '2', loc_no_current: '2', name: 'Tampa Assembly & Distribution', address: '5210 E Adamo Dr', city: 'Tampa', state: 'FL', lat: 27.9660, lon: -82.3920,
    match_method: 'loc_no + address', match_score: 0.97, tiv_prior: 31_000_000, tiv_current: 38_500_000, occupancy: 'Light assembly', construction: 'Masonry non-combustible (ISO 4)', year_built: 1996, stories: 1, sqft: 164_000, roof_year: 2019,
    sprinkler: 'Wet pipe, full', valuation_ratio: 0.96, wind_tier: 'T1', cat_zone: 'Tampa Bay', aal: 74_800, buildings: 1,
    flags: [
      { code: 'NS_DED_FLOOR', label: 'Named-storm ded 2% < 3% floor', severity: 'HIGH', finding_id: 'f-abc-windded' },
      { code: 'ROOF_CONFLICT', label: 'Roof year: SOV 2011 vs engineering 2019', severity: 'MEDIUM', finding_id: 'f-abc-roof' },
      { code: 'ACCUMULATION', label: 'Tampa Bay zone 93%', severity: 'HIGH', finding_id: 'f-abc-accum' },
    ], model_doc_id: `${A}-glb-tampa`, imagery_doc_ids: [`${A}-img-2023`, `${A}-img-2026`] }),
  loc({ location_uid: 'abc-l3', loc_no_prior: '3', loc_no_current: '3', name: 'Reno Warehouse', address: '900 Glendale Ave, Sparks', city: 'Reno', state: 'NV', lat: 39.5180, lon: -119.7580,
    match_method: 'loc_no + address', match_score: 0.98, tiv_prior: 26_000_000, tiv_current: 26_000_000, occupancy: 'Lithium-ion battery storage', occupancy_prior: 'Warehouse — general merchandise', construction: 'Tilt-up concrete (ISO 5)', year_built: 2004, stories: 1, sqft: 186_000, roof_year: 2016,
    sprinkler: 'Wet pipe, 0.45/2500 (Class IV design)', valuation_ratio: 0.9, cat_zone: 'Reno–Carson EQ', aal: 11_100, buildings: 1,
    flags: [
      { code: 'OCC_DRIFT', label: 'Occupancy drift → lithium-ion', severity: 'HIGH', finding_id: 'f-abc-reno-occ' },
      { code: 'FLAT_VALUES', label: 'Flat TIV vs +5.1% cost trend', severity: 'LOW' },
    ] }),
  loc({ location_uid: 'abc-l4', loc_no_prior: '4', loc_no_current: '4', name: 'Austin Electronics Assembly', address: '10800 Metric Blvd', city: 'Austin', state: 'TX', lat: 30.3935, lon: -97.6925,
    match_method: 'loc_no + address', match_score: 0.99, tiv_prior: 15_000_000, tiv_current: 15_100_000, occupancy: 'Electronics assembly', construction: 'Masonry non-combustible (ISO 4)', year_built: 2001, stories: 2, sqft: 88_000, roof_year: 2015,
    sprinkler: 'Wet pipe, full', valuation_ratio: 0.88, wind_tier: 'T3', cat_zone: 'Central TX SCS', aal: 26_100, buildings: 1,
    flags: [
      { code: 'WATER_LOSSES', label: '2 water losses since bind', severity: 'MEDIUM', finding_id: 'f-abc-water' },
      { code: 'REC_OVERDUE', label: 'R-114 overdue 94d', severity: 'MEDIUM', finding_id: 'f-abc-r114' },
    ] }),
  loc({ location_uid: 'abc-l5', loc_no_prior: null, loc_no_current: '5', name: 'Tampa Brandon Distribution', address: '1620 N Falkenburg Rd', city: 'Tampa', state: 'FL', lat: 27.9705, lon: -82.3855,
    match_status: 'NEW', match_method: null, match_score: null, tiv_prior: null, tiv_current: 22_000_000, tiv_change_pct: null, occupancy: 'Warehouse — finished goods', construction: 'Unknown', year_built: null, stories: 1, sqft: 120_000, roof_year: null,
    sprinkler: 'Y (unverified)', valuation_ratio: null, wind_tier: 'T1', cat_zone: 'Tampa Bay', aal: null, buildings: 1,
    flags: [
      { code: 'NOT_IN_CAT', label: 'Not in CAT run', severity: 'HIGH', finding_id: 'f-abc-newloc-cat' },
      { code: 'ACCUMULATION', label: '0.8 km from loc 2', severity: 'HIGH', finding_id: 'f-abc-accum' },
    ] }),
];

const up = (note: string) => ({ verdict: 'UPHELD' as const, note });
const findings: Finding[] = [
  fnd({ finding_id: 'f-abc-rarc', account_id: A, title: 'Like-for-like rate given away: RARC −8.1% behind a +9.8% headline', family: 'pricing', rule_id: 'PRC.RARC.BAND', rule_version: 2, severity: 'HIGH', outcome: 'REFER',
    observed: 'Proposed $450,000 vs expected $489,700 (RARC −8.1%)', expected: 'RARC ≥ −5.0% within L1 authority', impact_usd: 39_700, impact_method: 'expected_premium − proposed', confidence: 0.92,
    description: 'Expected premium = $410,000 × exposure factor 1.235 × terms factor 0.967. The broker counter of $450,000 is below expected on a like-for-like basis.',
    evidence_obs_ids: ['o-abc-prem-counter', 'o-abc-tp-e1t1', 'o-abc-prem-exp'], source: 'Pricing Authority Matrix 2026 §2.1', critique: up('Three model runs share rater-stub v1.4; factor chain reproduces.') }),
  fnd({ finding_id: 'f-abc-adequacy', account_id: A, title: 'Adequacy 95.3% — at the 95% floor', family: 'pricing', rule_id: 'PRC.ADEQ.FLOOR', rule_version: 3, severity: 'MEDIUM', outcome: 'FLAG',
    observed: 'Proposed $450,000 / TP(E1,T1) $472,000 = 95.3%', expected: 'Adequacy ≥ 95% floor; ≥ 100% for L1', impact_usd: 22_000, impact_method: 'TP(E1,T1) − proposed', confidence: 0.92,
    evidence_obs_ids: ['o-abc-tp-e1t1', 'o-abc-prem-counter'], source: 'Property UW Guidelines 2026 §4.2, p.18', critique: up('Floor passes by 0.3 pts; flag appropriate.') }),
  fnd({ finding_id: 'f-abc-windded', account_id: A, subject_type: 'location', subject_id: 'abc-l2', subject_label: 'Loc 2 · Tampa FL (and Loc 5)', title: 'Named-storm deductible 2% below the 3% guideline floor (Tier-1 wind)', family: 'cat_terms', rule_id: 'CAT.WIND.DED_FLOOR', rule_version: 4, severity: 'HIGH', outcome: 'TERM_BREACH',
    observed: 'Expiring and broker-requested: 2% per location, $100K min', expected: 'Named storm deductible ≥ 3% per location', impact_usd: 16_000, impact_method: 'cat_model_delta (AAL at 3% vs 2%)', confidence: 0.95,
    description: 'Guideline v2026 raised the Tier-1 named-storm floor from 2% to 3% effective 2026-07-01. Broker submission asks to renew as expiring.',
    evidence_obs_ids: ['o-abc-ns-ded', 'o-abc-ns-floor'], pass: 1, created_at: '2026-07-01', source: 'Property UW Guidelines 2026 §7.3, p.41', critique: up('Location 2 and 5 are both Tier-1; rule version 4 applies from 2026-07-01.') }),
  fnd({ finding_id: 'f-abc-bi', account_id: A, subject_type: 'contract', subject_id: `pol-${A}`, subject_label: 'Policy NGP-2025-01842', title: 'Issued policy grants $15M BI; binder bound $10M', family: 'contract_integrity', rule_id: 'CTR.BINDER_POLICY.SUBLIMIT', rule_version: 1, severity: 'CRITICAL', outcome: 'TERM_BREACH',
    observed: 'Binder BI sublimit $10,000,000 · issued policy $15,000,000', expected: 'Issued policy = binder (quote v3 accepted)', impact_usd: 30_000, impact_method: 'Δ limit $5M × P(reach limit) 0.6%', confidence: 0.98,
    description: 'Business income sublimit over-granted at issuance. Exposure of $5M uncharged for 9 months of the term.',
    evidence_obs_ids: ['o-abc-bi-binder', 'o-abc-bi-policy'], pass: 1, created_at: '2026-06-03', source: 'Standard library — contract integrity', critique: up('Binder p.1 and dec page p.2 differ; no endorsement explains the change.') }),
  fnd({ finding_id: 'f-abc-newloc-cat', account_id: A, subject_type: 'location', subject_id: 'abc-l5', subject_label: 'Loc 5 · Tampa FL (NEW)', title: 'New Tampa location #5 ($22.0M) not in the CAT run', family: 'cat_data', rule_id: 'CAT.INPUT.COMPLETENESS', rule_version: 2, severity: 'HIGH', outcome: 'DATA_REQUEST',
    observed: 'Loc 5 on renewal SOV; absent from CAT exposure file (4 of 5 locations)', expected: 'All renewal locations modelled before quote', impact_usd: 31_000, impact_method: 'AAL from proxy location (Loc 2 rate × TIV)', confidence: 0.88,
    evidence_obs_ids: ['o-abc-tiv-l5', 'o-abc-cat-locs'], source: 'CAT Modelling Standards 2026 §3.1', critique: up('Exposure file has 4 LocNumbers; SOV has 5.') }),
  fnd({ finding_id: 'f-abc-accum', account_id: A, subject_type: 'location', subject_id: 'abc-l5', subject_label: 'Tampa Bay zone', title: 'Tampa Bay named-storm zone at 93% of capacity after renewal', family: 'portfolio', rule_id: 'PORT.ZONE.UTIL', rule_version: 1, severity: 'HIGH', outcome: 'REFER',
    observed: 'Zone PML $325.5M post-renewal vs $350M capacity (93%); Loc 5 is 0.8 km from Loc 2', expected: 'Zone utilisation ≤ 90% without senior referral', impact_usd: 12_000, impact_method: 'control exposure — PML load on $22M new TIV', confidence: 0.9,
    evidence_obs_ids: ['o-abc-accum'], source: 'Portfolio Management Guidelines 2026 §2', critique: up('Zone model includes 2 other accounts; S2 adds $9.1M PML.') }),
  fnd({ finding_id: 'f-abc-reno-occ', account_id: A, subject_type: 'location', subject_id: 'abc-l3', subject_label: 'Loc 3 · Reno NV', title: 'Reno occupancy drift: general warehouse → lithium-ion battery storage', family: 'occupancy', rule_id: 'OCC.DRIFT.HAZARD', rule_version: 2, severity: 'HIGH', outcome: 'CONDITION',
    observed: 'Broker email 2026-07-28: "now storing e-bike and ESS lithium-ion battery inventory"; SOV still says general merchandise', expected: 'Occupancy matches rated class; Li-ion storage requires re-survey (FM DS 8-1)', impact_usd: 24_000, impact_method: 'rate differential (ATC class 21 → hazardous storage)', confidence: 0.84,
    evidence_obs_ids: ['o-abc-occ-reno-eml'], conflicting_obs_ids: ['ob-abc-l3-occ'], source: 'Property UW Guidelines 2026 §9.4 (Hazardous storage)', critique: up('Email statement is specific and recent; SOV value carried forward.') }),
  fnd({ finding_id: 'f-abc-dayton-val', account_id: A, subject_type: 'location', subject_id: 'abc-l1', subject_label: 'Loc 1 · Dayton OH', title: 'Dayton insured at 71% of modelled replacement cost', family: 'valuation', rule_id: 'VAL.RC.RATIO', rule_version: 3, severity: 'HIGH', outcome: 'PRICE_ADJUST',
    observed: 'Reported $49.4M vs model RC $69.6M ($233/sq ft reported vs $328)', expected: 'Reported ≥ 80% of model RC', impact_usd: 54_500, impact_method: '(model RC − reported) × rate on line 0.27%', confidence: 0.78,
    evidence_obs_ids: ['ob-abc-l1-tiv', 'o-abc-val-dayton'], source: 'Valuation Standards 2026 §1.2', critique: up('Valuation vendor and cost trend agree within 4%. Coinsurance shortfall noted separately.') }),
  fnd({ finding_id: 'f-abc-roof', account_id: A, subject_type: 'location', subject_id: 'abc-l2', subject_label: 'Loc 2 · Tampa FL', title: 'Roof year conflict at Tampa: SOV 2011 vs engineering 2019', family: 'data_quality', rule_id: 'DQ.CONFLICT.ROOF', rule_version: 1, severity: 'MEDIUM', outcome: 'FLAG',
    observed: 'SOV 2011 (C) · engineering survey 2019 (V) · imagery 2018–20 (M)', expected: 'Single roof year; CAT input uses resolved value', impact_usd: 6_000, impact_method: 'AAL delta at resolved roof age', confidence: 0.9,
    evidence_obs_ids: ['o-abc-roof-eng', 'ob-abc-l2-roof', 'o-abc-roof-img'], conflicting_obs_ids: ['ob-abc-l2-roof'], source: 'Standard library — evidence resolution', critique: { verdict: 'CHALLENGED', note: 'Resolved to 2019 by engineering (V); pricing effect is nil — this is a CAT input hygiene issue, not a rate issue.' } }),
  fnd({ finding_id: 'f-abc-water', account_id: A, subject_type: 'location', subject_id: 'abc-l4', subject_label: 'Loc 4 · Austin TX', title: 'Two water losses at Austin since bind ($186K incurred)', family: 'claims', rule_id: 'CLM.REPEAT.CAUSE', rule_version: 1, severity: 'MEDIUM', outcome: 'FLAG',
    observed: 'CLM-7A31F0 2026-01-14 $71K · CLM-7B0C22 2026-04-02 $115K, both domestic water', expected: 'No repeat cause within 12 months', impact_usd: 9_000, impact_method: 'experience mod on attritional', confidence: 0.96,
    evidence_obs_ids: ['o-abc-clm1', 'o-abc-clm2'], pass: 1, created_at: '2026-06-03', source: 'Property UW Guidelines 2026 §5.1', critique: up('Same cause, same building; linked to R-114.') }),
  fnd({ finding_id: 'f-abc-r114', account_id: A, subject_type: 'recommendation', subject_id: 'R-114', subject_label: 'R-114 · Austin TX', title: 'R-114 (leak detection / supply-line replacement) overdue 94 days', family: 'engineering', rule_id: 'ENG.REC.OVERDUE', rule_version: 2, severity: 'MEDIUM', outcome: 'CONDITION',
    observed: 'Due 2026-04-29 · status OPEN · no completion evidence', expected: 'Recommendations closed with evidence by due date', impact_usd: 4_000, impact_method: 'attritional loading', confidence: 0.95, pass: 1, created_at: '2026-06-03', source: 'Risk Engineering Standards §3', critique: up('Register and survey agree.') }),
  fnd({ finding_id: 'f-abc-r117', account_id: A, subject_type: 'recommendation', subject_id: 'R-117', subject_label: 'R-117 · Reno NV', title: 'R-117 (sprinkler hydraulic re-evaluation) overdue 32 days', family: 'engineering', rule_id: 'ENG.REC.OVERDUE', rule_version: 2, severity: 'LOW', outcome: 'CONDITION',
    observed: 'Due 2026-06-30 · status OPEN', expected: 'Closed with evidence by due date', impact_usd: 3_000, impact_method: 'attritional loading', confidence: 0.95, pass: 1, created_at: '2026-07-01', source: 'Risk Engineering Standards §3', critique: up('Becomes material given Reno occupancy drift.') }),
];

const obsBase = { vendor: null, model_version: null, valid_from: '2026-07-28', recorded_at: '2026-07-28' };
const observations: Observation[] = [
  { ...obsBase, obs_id: 'o-abc-roof-eng', subject_type: 'location', subject_id: 'abc-l2', subject_label: 'Loc 2 · Tampa Assembly & Distribution', field_code: 'roof_year', field_label: 'Roof year', value: 2019, value_display: '2019', obs_type: 'V', source_family: 'Engineering', source_label: 'Engineering survey 2024-03-15 (E. Brooks)', anchor: pdfA(ENG_TPA, 7, [72, 412, 468, 428], 'Roof covering replaced 2019 (TPO over polyiso), FM 1-90 rated'), confidence: 0.96, verification_status: 'VERIFIED', valid_from: '2024-03-15', recorded_at: '2024-03-22', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-roof-img', subject_type: 'location', subject_id: 'abc-l2', subject_label: 'Loc 2 · Tampa Assembly & Distribution', field_code: 'roof_year', field_label: 'Roof year', value: '2018–2020', value_display: '2018–2020 (change detected)', obs_type: 'M', source_family: 'External data', source_label: 'Aerial imagery change detection', anchor: { doc_id: `${A}-img-2023`, kind: 'image', text: 'Roof surface change between 2018 and 2020 captures' }, vendor: 'SkyFrame (mock)', model_version: 'roofage-2.3', confidence: 0.74, verification_status: 'UNVERIFIED', is_resolved: false },
  { ...obsBase, obs_id: 'o-abc-roof-prior', subject_type: 'location', subject_id: 'abc-l2', subject_label: 'Loc 2 · Tampa Assembly & Distribution', field_code: 'roof_year', field_label: 'Roof year', value: 2011, value_display: '2011', obs_type: 'C', source_family: 'Broker / insured', source_label: '2025–2026 SOV', anchor: xlsA(SOV25, 'SOV 2025', 'K5', 'A5:P5'), confidence: 0.9, verification_status: 'SUPERSEDED', valid_from: '2025-08-02', recorded_at: '2025-08-02', is_resolved: false },
  { ...obsBase, obs_id: 'o-abc-occ-reno-eml', subject_type: 'location', subject_id: 'abc-l3', subject_label: 'Loc 3 · Reno Warehouse', field_code: 'occupancy', field_label: 'Occupancy', value: 'Lithium-ion battery storage', value_display: 'Lithium-ion battery storage', obs_type: 'C', source_family: 'Broker / insured', source_label: 'Broker email 2026-07-28', anchor: { doc_id: EML_SUB, kind: 'eml', text: 'Reno is now storing e-bike and ESS lithium-ion battery inventory for a new customer' }, confidence: 0.86, verification_status: 'UNVERIFIED', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-occ-reno-prior', subject_type: 'location', subject_id: 'abc-l3', subject_label: 'Loc 3 · Reno Warehouse', field_code: 'occupancy', field_label: 'Occupancy', value: 'Warehouse — general merchandise', value_display: 'Warehouse — general merchandise', obs_type: 'V', source_family: 'Engineering', source_label: 'Engineering survey 2024-05-20', anchor: pdfA(ENG_RNO, 3, [72, 188, 520, 204], 'Occupancy: general merchandise, Class I–III commodities, 20 ft storage'), confidence: 0.95, verification_status: 'SUPERSEDED', valid_from: '2024-05-20', recorded_at: '2024-05-27', is_resolved: false },
  { ...obsBase, obs_id: 'o-abc-bi-binder', subject_type: 'coverage', subject_id: 'abc-cov-bi', subject_label: 'Business income sublimit', field_code: 'bi_sublimit', field_label: 'BI sublimit', value: 10_000_000, value_display: '$10,000,000', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Binder 2025-10-24', anchor: pdfA(BINDER, 1, [72, 300, 540, 314], 'Business Income / Extra Expense ........ $10,000,000'), confidence: 0.99, verification_status: 'VERIFIED', valid_from: '2025-11-01', recorded_at: '2025-10-24', is_resolved: false },
  { ...obsBase, obs_id: 'o-abc-bi-policy', subject_type: 'coverage', subject_id: 'abc-cov-bi', subject_label: 'Business income sublimit', field_code: 'bi_sublimit', field_label: 'BI sublimit', value: 15_000_000, value_display: '$15,000,000', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Issued policy NGP-2025-01842 (dec page)', anchor: pdfA(DEC, 2, [72, 300, 540, 314], 'Business Income / Extra Expense ........ $15,000,000'), confidence: 0.99, verification_status: 'VERIFIED', valid_from: '2025-11-01', recorded_at: '2025-11-06', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-ns-ded', subject_type: 'policy', subject_id: `pol-${A}`, subject_label: 'Named storm deductible', field_code: 'named_storm_ded_pct', field_label: 'Named-storm deductible', value: 0.02, value_display: '2% per location, $100K min', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Issued policy dec page', anchor: pdfA(DEC, 2, [72, 256, 540, 270], 'Named Storm: 2% of TIV per location, $100,000 minimum'), confidence: 0.99, verification_status: 'VERIFIED', valid_from: '2025-11-01', recorded_at: '2025-11-06', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-ns-floor', subject_type: 'policy', subject_id: `pol-${A}`, subject_label: 'Guideline floor', field_code: 'guideline_ns_floor', field_label: 'Guideline NS floor (Tier-1)', value: 0.03, value_display: '3% per location', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Property UW Guidelines 2026 §7.3', anchor: pdfA(GUIDE, 41, [72, 318, 540, 348], 'For Tier 1 and Tier 2 wind locations the named storm deductible shall be not less than 3% of TIV per location.'), confidence: 1, verification_status: 'VERIFIED', valid_from: '2026-07-01', recorded_at: '2026-06-15', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-prem-exp', subject_type: 'policy', subject_id: `pol-${A}`, subject_label: 'Expiring premium', field_code: 'premium_expiring', field_label: 'Expiring premium', value: 410_000, value_display: '$410,000', obs_type: 'S', source_family: 'Carrier systems', source_label: 'PAS (mock) · booked premium', anchor: sysA('PAS (mock)', 'NGP-2025-01842', 'Written premium $410,000'), confidence: 1, verification_status: 'VERIFIED', valid_from: '2025-11-01', recorded_at: '2025-11-06', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-prem-counter', subject_type: 'policy', subject_id: `pol-${A}`, subject_label: 'Broker counter', field_code: 'premium_counter', field_label: 'Broker counter-offer', value: 450_000, value_display: '$450,000', obs_type: 'C', source_family: 'Broker / insured', source_label: 'Broker email 2026-07-30', anchor: { doc_id: EML_CTR, kind: 'eml', text: 'we can get this bound today at $450,000' }, confidence: 0.97, verification_status: 'UNVERIFIED', valid_from: '2026-07-30', recorded_at: '2026-07-30', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-tp-e1t1', subject_type: 'account', subject_id: A, subject_label: 'ABC Manufacturing', field_code: 'tp_e1t1', field_label: 'Technical premium TP(E1,T1)', value: 472_000, value_display: '$472,000', obs_type: 'M', source_family: 'Platform', source_label: 'Rater (mock) run 3 of 3', anchor: { doc_id: null, kind: 'vendor', system: 'Rater (mock)', record_id: 'run-abc-e1t1', path: '$.technical_premium' }, vendor: 'rater-stub', model_version: 'rater-stub v1.4', confidence: 0.9, verification_status: 'VERIFIED', valid_from: '2026-07-31', recorded_at: '2026-07-31', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-tiv-l5', subject_type: 'location', subject_id: 'abc-l5', subject_label: 'Loc 5 · Tampa Brandon Distribution', field_code: 'tiv', field_label: 'Total insured value', value: 22_000_000, value_display: '$22,000,000', obs_type: 'C', source_family: 'Broker / insured', source_label: '2026–2027 SOV', anchor: xlsA(SOV26, 'SOV 2026', 'P8', 'A8:P8'), confidence: 0.97, verification_status: 'UNVERIFIED', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-cat-locs', subject_type: 'account', subject_id: A, subject_label: 'CAT exposure file', field_code: 'cat_location_count', field_label: 'Locations in CAT run', value: 4, value_display: '4 of 5 (Loc 5 absent)', obs_type: 'M', source_family: 'CAT model', source_label: 'MockCat run 2026-07-22', anchor: { doc_id: `${A}-cat-exp`, kind: 'csv', text: 'LocNumber 1–4' }, vendor: 'MockCat', model_version: 'MockCat 23.1', confidence: 1, verification_status: 'VERIFIED', valid_from: '2026-07-22', recorded_at: '2026-07-22', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-accum', subject_type: 'account', subject_id: A, subject_label: 'Tampa Bay zone', field_code: 'zone_utilization', field_label: 'Zone utilisation post-renewal', value: 0.93, value_display: '93% ($325.5M / $350M)', obs_type: 'D', source_family: 'Platform', source_label: 'Accumulation engine (zone grid)', anchor: { doc_id: null, kind: 'derived', text: 'Σ zone PML over 16 contributing accounts' }, confidence: 0.9, verification_status: 'VERIFIED', valid_from: '2026-07-31', recorded_at: '2026-07-31', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-val-dayton', subject_type: 'location', subject_id: 'abc-l1', subject_label: 'Loc 1 · Dayton Machining Plant', field_code: 'model_rc', field_label: 'Model replacement cost', value: 69_600_000, value_display: '$69,600,000 ($328/sq ft)', obs_type: 'M', source_family: 'External data', source_label: 'Valuation vendor (mock)', anchor: { doc_id: null, kind: 'vendor', system: 'ValuQuest (mock)', record_id: 'vq-abc-l1', path: '$.replacement_cost' }, vendor: 'ValuQuest (mock)', model_version: 'vq-2026.2', confidence: 0.82, verification_status: 'UNVERIFIED', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-clm1', subject_type: 'claim', subject_id: 'CLM-7A31F0', subject_label: 'Claim CLM-7A31F0', field_code: 'incurred', field_label: 'Incurred', value: 71_000, value_display: '$71,000', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Claims (mock)', anchor: sysA('Claims (mock)', 'CLM-7A31F0', 'Domestic water — failed supply line, 2nd floor'), confidence: 1, verification_status: 'VERIFIED', valid_from: '2026-01-14', recorded_at: '2026-01-15', is_resolved: true },
  { ...obsBase, obs_id: 'o-abc-clm2', subject_type: 'claim', subject_id: 'CLM-7B0C22', subject_label: 'Claim CLM-7B0C22', field_code: 'incurred', field_label: 'Incurred', value: 115_000, value_display: '$115,000', obs_type: 'S', source_family: 'Carrier systems', source_label: 'Claims (mock)', anchor: sysA('Claims (mock)', 'CLM-7B0C22', 'Domestic water — ice-maker line, production floor'), confidence: 1, verification_status: 'VERIFIED', valid_from: '2026-04-02', recorded_at: '2026-04-03', is_resolved: true },
];

const deltas: DeltaCard[] = [
  { key: 'exposure', title: 'Exposure', status: 'ACTION', headline: 'TIV $120.0M → $151.0M (+25.8%)', metrics: [
    { label: 'Total insured value', before: '$120.0M', after: '$151.0M', display: '+25.8%', flag: 'warn', obs_ids: ['ob-abc-l2-tiv'] },
    { label: 'New locations', before: '4', after: '5', display: '+$22.0M', flag: 'breach', note: 'Loc 5 Tampa FL — not in CAT run', finding_ids: ['f-abc-newloc-cat'], obs_ids: ['o-abc-tiv-l5'] },
    { label: 'Matched-location value change', before: '$120.0M', after: '$129.0M', display: '+7.5%', flag: 'info', obs_ids: ['ob-abc-l2-tiv'] },
    { label: 'Occupancy drift', before: 'Warehouse', after: 'Li-ion storage', display: 'Reno', flag: 'breach', finding_ids: ['f-abc-reno-occ'], obs_ids: ['o-abc-occ-reno-eml'] },
    { label: 'Valuation vs model RC', display: '71%', after: 'Dayton', flag: 'breach', finding_ids: ['f-abc-dayton-val'], obs_ids: ['o-abc-val-dayton'] },
  ] },
  { key: 'pricing', title: 'Pricing', status: 'ACTION', headline: 'Headline +9.8% · RARC −8.1%', metrics: [
    { label: 'Premium', before: '$410K', after: '$450K', display: '+9.8%', flag: 'info', obs_ids: ['o-abc-prem-exp', 'o-abc-prem-counter'] },
    { label: 'Expected (like-for-like)', display: '$489.7K', note: '410 × 1.235 × 0.967', flag: 'info' },
    { label: 'Computed RARC', display: '−8.1%', flag: 'breach', finding_ids: ['f-abc-rarc'] },
    { label: 'Adequacy vs TP(E1,T1)', display: '95.3%', after: 'floor 95%', flag: 'warn', finding_ids: ['f-abc-adequacy'], obs_ids: ['o-abc-tp-e1t1'] },
  ] },
  { key: 'terms', title: 'Terms & contract', status: 'ACTION', headline: 'NS ded 2% < 3% floor · binder BI $10M vs policy $15M', metrics: [
    { label: 'Named-storm deductible', before: '2%', after: 'floor 3%', display: '−1 pt', flag: 'breach', finding_ids: ['f-abc-windded'], obs_ids: ['o-abc-ns-ded', 'o-abc-ns-floor'] },
    { label: 'BI sublimit binder → policy', before: '$10M', after: '$15M', display: '+$5M', flag: 'breach', finding_ids: ['f-abc-bi'], obs_ids: ['o-abc-bi-binder', 'o-abc-bi-policy'] },
    { label: 'Protective safeguards', display: 'P-1 verified', flag: 'ok' },
  ] },
  { key: 'risk_quality', title: 'Risk quality', status: 'WATCH', headline: '2 new water losses · 2 engineering actions overdue', metrics: [
    { label: 'Losses since bind', before: '0', after: '2', display: '$186K', flag: 'warn', finding_ids: ['f-abc-water'], obs_ids: ['o-abc-clm1', 'o-abc-clm2'] },
    { label: 'Recommendations overdue', display: '2', note: 'R-114 94d · R-117 32d', flag: 'warn', finding_ids: ['f-abc-r114', 'f-abc-r117'] },
    { label: 'Roof year (Tampa)', before: '2011 SOV', after: '2019 eng.', display: 'conflict', flag: 'warn', finding_ids: ['f-abc-roof'], obs_ids: ['o-abc-roof-eng', 'ob-abc-l2-roof'] },
  ] },
  { key: 'appetite_portfolio', title: 'Appetite & portfolio', status: 'ACTION', headline: 'Tampa Bay zone 86% → 93% after renewal', metrics: [
    { label: 'Tampa Bay zone utilisation', before: '86%', after: '93%', display: '+7 pts', flag: 'breach', finding_ids: ['f-abc-accum'], obs_ids: ['o-abc-accum'] },
    { label: 'Loc 5 distance to Loc 2', display: '0.8 km', flag: 'warn' },
    { label: 'Appetite (guidelines v2026)', display: 'In appetite', flag: 'ok' },
  ] },
  { key: 'retention', title: 'Retention & commercial', status: 'OK', headline: '7-year relationship · 5y loss ratio 42%', metrics: [
    { label: '5-year loss ratio', display: '42.1%', flag: 'ok' },
    { label: 'Broker counter vs expected', display: '−8.1%', flag: 'warn', note: 'Marsh: incumbent quote from Zurich rumoured at $440K' },
    { label: 'Tenure', display: '7 yrs', flag: 'info' },
  ] },
  { key: 'net', title: 'Net & reinsurance', status: 'OK', headline: 'Net 1-in-250 OEP $17.6M within cat treaty', metrics: [
    { label: 'OEP 1-in-250 (current)', display: '$17.6M', flag: 'info', note: 'Excl. Loc 5 — rerun pending' },
    { label: 'Facultative needed', display: 'No', flag: 'ok' },
  ] },
];

const narrativeText = `**ABC Manufacturing needs action before quoting.** Insured values rise from $120.0M to $151.0M (+25.8%) [O:ob-abc-l2-tiv], driven by a new Tampa location #5 ($22.0M) that is not in the CAT run [F:f-abc-newloc-cat] and sits 0.8 km from location 2, taking the Tampa Bay zone to 93% of capacity [F:f-abc-accum].

The broker's $450K counter reads as **+9.8%**, but on a like-for-like basis it gives away **8.1% of rate** [F:f-abc-rarc]; adequacy is 95.3%, just above the 95% floor [F:f-abc-adequacy].

Terms: the named-storm deductible is 2% against the 3% floor in guideline v2026 [F:f-abc-windded] [O:o-abc-ns-floor], and the issued policy grants $15M business income where the binder said $10M [F:f-abc-bi].

Risk quality: Reno has drifted from general warehouse to lithium-ion battery storage [F:f-abc-reno-occ] [O:o-abc-occ-reno-eml]; Austin has two water losses since bind with R-114 still open [F:f-abc-water] [F:f-abc-r114]; Dayton is insured at 71% of modelled replacement cost [F:f-abc-dayton-val].

**Recommended:** reprice toward $475K at a 3% named-storm deductible, correct the BI sublimit by endorsement, re-survey Reno before bind, and refer for the Tampa accumulation. Underwriter decides.`;

const rarc: RarcBase = {
  expiring_premium: 410_000, proposed_premium: 450_000, tp_at_bind: 402_300,
  expiring_terms: { aop_deductible: 50_000, named_storm_ded_pct: 0.02, named_storm_ded_min: 100_000, wind_hail_ded_pct: null, bi_sublimit: 10_000_000, flood_sublimit: 10_000_000, eq_sublimit: 15_000_000 },
  proposed_terms: { aop_deductible: 50_000, named_storm_ded_pct: 0.03, named_storm_ded_min: 100_000, wind_hail_ded_pct: null, bi_sublimit: 10_000_000, flood_sublimit: 10_000_000, eq_sublimit: 15_000_000 },
  brokerage_expiring: 0.15, brokerage_proposed: 0.175, tiv_expiring: 120_000_000, tiv_renewal: 151_000_000, adequacy_floor: 0.95,
  method: 'model_rerun', model_version: 'rater-stub v1.4 (held fixed across runs)', wind_floor: 0.03,
  components: [
    { component: 'Fire & AOP (building + BPP)', kind: 'aop', e0: 142_000, e1: 168_000 },
    { component: 'Business income', kind: 'bi', e0: 41_000, e1: 50_000 },
    { component: 'Named storm (CAT load)', kind: 'wind', e0: 96_000, e1: 142_000 },
    { component: 'Flood', kind: 'flood', e0: 14_000, e1: 17_000 },
    { component: 'Earthquake (Reno)', kind: 'eq', e0: 9_000, e1: 9_000 },
    { component: 'Experience mod (water)', kind: 'other', e0: 6_000, e1: 6_000 },
    { component: 'Expense & profit load', kind: 'other', e0: 87_181, e1: 96_000 },
  ],
};

const bA = (d: string, page: number, y: number, text?: string) => pdfA(d, page, [72, y, 540, y + 14], text);
const Q25 = `${A}-quote-prior`;
const contract: ContractDiff = {
  term: '2025–2026', quote_version: 'v3',
  rows: [
    { field: 'limit', label: 'Blanket limit', group: 'Limits', values: { quote: '$120.0M', binder: '$120.0M', policy: '$120.0M', endorsed: '$120.0M' }, anchors: { quote: bA(Q25, 2, 180), binder: bA(BINDER, 1, 180), policy: bA(DEC, 1, 220), endorsed: bA(DEC, 1, 220) }, result: 'MATCH', finding_id: null },
    { field: 'aop', label: 'AOP deductible', group: 'Deductibles', values: { quote: '$50K', binder: '$50K', policy: '$50K', endorsed: '$50K' }, anchors: { quote: bA(Q25, 2, 240), binder: bA(BINDER, 1, 240), policy: bA(DEC, 2, 240), endorsed: bA(DEC, 2, 240) }, result: 'MATCH', finding_id: null },
    { field: 'ns', label: 'Named storm deductible', group: 'Deductibles', values: { quote: '2% / loc, $100K min', binder: '2% / loc, $100K min', policy: '2% / loc, $100K min', endorsed: '2% / loc, $100K min' }, anchors: { quote: bA(Q25, 2, 256), binder: bA(BINDER, 1, 256), policy: bA(DEC, 2, 256, 'Named Storm: 2% of TIV per location, $100,000 minimum'), endorsed: bA(DEC, 2, 256) }, result: 'MATCH', finding_id: null },
    { field: 'eq', label: 'Earthquake deductible (Reno)', group: 'Deductibles', values: { quote: '5%, $250K min', binder: '5%, $250K min', policy: '5%, $250K min', endorsed: '5%, $250K min' }, anchors: { quote: bA(Q25, 2, 272), binder: bA(BINDER, 1, 272), policy: bA(DEC, 2, 272), endorsed: bA(DEC, 2, 272) }, result: 'MATCH', finding_id: null },
    { field: 'bi', label: 'Business income / EE sublimit', group: 'Sublimits', values: { quote: '$10.0M', binder: '$10.0M', policy: '$15.0M', endorsed: '$15.0M' }, anchors: { quote: bA(Q25, 2, 300), binder: bA(BINDER, 1, 300, 'Business Income / Extra Expense ........ $10,000,000'), policy: bA(DEC, 2, 300, 'Business Income / Extra Expense ........ $15,000,000'), endorsed: bA(DEC, 2, 300) }, result: 'MISMATCH', finding_id: 'f-abc-bi' },
    { field: 'flood', label: 'Flood sublimit (outside SFHA)', group: 'Sublimits', values: { quote: '$10.0M', binder: '$10.0M', policy: '$10.0M', endorsed: '$10.0M' }, anchors: { quote: bA(Q25, 2, 316), binder: bA(BINDER, 1, 316), policy: bA(DEC, 2, 316), endorsed: bA(DEC, 2, 316) }, result: 'MATCH', finding_id: null },
    { field: 'debris', label: 'Debris removal', group: 'Sublimits', values: { quote: '25% / $2.5M', binder: '25% / $2.5M', policy: '25% / $2.5M', endorsed: '25% / $2.5M' }, anchors: { quote: bA(Q25, 2, 332), binder: bA(BINDER, 1, 332), policy: bA(DEC, 2, 332), endorsed: bA(DEC, 2, 332) }, result: 'MATCH', finding_id: null },
    { field: 'cp0010', label: 'CP 00 10 Building & personal property', group: 'Forms', values: { quote: 'Attached', binder: 'Attached', policy: 'Attached', endorsed: 'Attached' }, anchors: { quote: bA(Q25, 3, 120), binder: bA(BINDER, 2, 120), policy: bA(DEC, 3, 120), endorsed: bA(DEC, 3, 120) }, result: 'MATCH', finding_id: null },
    { field: 'cp0030', label: 'CP 00 30 Business income', group: 'Forms', values: { quote: 'Attached', binder: 'Attached', policy: 'Attached', endorsed: 'Attached' }, anchors: { quote: bA(Q25, 3, 136), binder: bA(BINDER, 2, 136), policy: bA(DEC, 3, 136), endorsed: bA(DEC, 3, 136) }, result: 'MATCH', finding_id: null },
    { field: 'ngs112', label: 'NGS-PR 112 Named storm deductible endt', group: 'Forms', values: { quote: 'Attached', binder: 'Attached', policy: 'Attached', endorsed: 'Attached' }, anchors: { quote: bA(Q25, 3, 152), binder: bA(BINDER, 2, 152), policy: bA(DEC, 3, 152), endorsed: bA(DEC, 3, 152) }, result: 'MATCH', finding_id: null },
    { field: 'p1', label: 'P-1 Automatic sprinkler — Locs 1–4', group: 'Safeguards', values: { quote: 'Required', binder: 'Required', policy: 'Required', endorsed: 'Required' }, anchors: { quote: bA(Q25, 3, 220), binder: bA(BINDER, 2, 220), policy: bA(DEC, 4, 180), endorsed: bA(DEC, 4, 180) }, result: 'MATCH', finding_id: null },
    { field: 'p2', label: 'P-2 Central-station alarm — Dayton', group: 'Safeguards', values: { quote: 'Required', binder: 'Required', policy: 'Required', endorsed: 'Required' }, anchors: { quote: bA(Q25, 3, 236), binder: bA(BINDER, 2, 236), policy: bA(DEC, 4, 196), endorsed: bA(DEC, 4, 196) }, result: 'MATCH', finding_id: null },
    { field: 'subj-roof', label: 'Roof-condition report, Tampa (pre-bind)', group: 'Subjectivities', values: { quote: 'Before bind', binder: 'Received 2025-10-22', policy: '—', endorsed: '—' }, anchors: { quote: bA(Q25, 4, 140), binder: bA(BINDER, 2, 300), policy: null, endorsed: null }, result: 'MATCH', finding_id: null },
    { field: 'premium', label: 'Annual premium', group: 'Premium', values: { quote: '$410,000', binder: '$410,000', policy: '$410,000', endorsed: '$410,000' }, anchors: { quote: bA(Q25, 1, 520), binder: bA(BINDER, 1, 520), policy: bA(DEC, 1, 520), endorsed: bA(DEC, 1, 520) }, result: 'MATCH', finding_id: null },
  ],
  endorsements: [
    { endt_id: 'NGP-E-01', effective: '2026-02-10', type: 'Additional insured', description: 'Add Fifth Third Bank as mortgagee — Dayton', premium_delta: 0, doc_id: `${A}-endt-1` },
    { endt_id: 'NGP-E-02', effective: '2026-05-02', type: 'Loss payee', description: 'Equipment lessor as loss payee — Austin SMT line', premium_delta: 0, doc_id: null },
  ],
  subjectivities: [{ text: 'Roof-condition report, Tampa (Loc 2)', due: '2025-10-25', status: 'CLEARED', age_days: 0, finding_id: null }],
  quotes: [
    { quote_id: 'q-abc-25-v3', version: 3, term: '2025–2026', created_at: '2025-10-18', created_by: 'Maya Chen', premium: 410_000, terms: rarc.expiring_terms, status: 'BOUND', terms_hash: 'b7e2c41a', doc_id: Q25, rarc: -0.021, adequacy: 1.019 },
    { quote_id: 'q-abc-26-v1', version: 1, term: '2026–2027', created_at: '2026-07-14', created_by: 'Maya Chen', premium: 470_000, terms: rarc.proposed_terms, status: 'SENT', terms_hash: '3fa9d20e', doc_id: `${A}-quote-v1`, rarc: -0.041, adequacy: 0.996 },
  ],
  referrals: [],
};

const cat: CatResult[] = (() => {
  const oep = (s: number) => [[10, 0.9], [25, 3.1], [50, 6.4], [100, 10.8], [250, 17.6], [500, 22.9], [1000, 28.0]].map(([rp, l]) => ({ rp, loss: Math.round(l * 1e6 * s) }));
  const aep = (s: number) => [[10, 1.1], [25, 3.5], [50, 6.9], [100, 11.4], [250, 18.3], [500, 23.6], [1000, 28.9]].map(([rp, l]) => ({ rp, loss: Math.round(l * 1e6 * s) }));
  const base = { account_id: A, vendor: "MockCat (stand-in for Moody's RMS / Verisk)", model_version: 'MockCat 23.1 · HU/SCS/FL/EQ', perils: ['Named storm', 'Severe convective', 'Flood', 'Earthquake', 'Wildfire'], basis: 'Carrier share 100%, net of deductibles (2% NS)', exposure_doc_id: `${A}-cat-exp`, elt_doc_id: `${A}-cat-elt`, ep_doc_id: `${A}-cat-ep` };
  const cur: CatResult = { ...base, run_id: 'cat-abc-current', snapshot: 'CURRENT', run_date: '2026-07-22', aal_total: 128_900,
    aal_by_peril: [{ peril: 'Named storm', aal: 96_400 }, { peril: 'Severe convective', aal: 14_800 }, { peril: 'Flood', aal: 11_200 }, { peril: 'Earthquake', aal: 6_100 }, { peril: 'Wildfire', aal: 400 }],
    oep: oep(1), aep: aep(1),
    location_contrib: [
      { location_uid: 'abc-l2', label: 'Loc 2 · Tampa FL', aal: 74_800, pct: 0.58, tiv: 38_500_000 },
      { location_uid: 'abc-l4', label: 'Loc 4 · Austin TX', aal: 26_100, pct: 0.202, tiv: 15_100_000 },
      { location_uid: 'abc-l1', label: 'Loc 1 · Dayton OH', aal: 16_900, pct: 0.131, tiv: 49_400_000 },
      { location_uid: 'abc-l3', label: 'Loc 3 · Reno NV', aal: 11_100, pct: 0.086, tiv: 26_000_000 },
    ],
    dq_flags: [
      { location_uid: 'abc-l5', label: 'Loc 5 · Tampa FL', field: 'location', issue: 'Not in exposure file — $22.0M TIV unmodelled', impact: 'HIGH' },
      { location_uid: 'abc-l2', label: 'Loc 2 · Tampa FL', field: 'roof_year', issue: 'Model input 2011; resolved 2019 (engineering)', impact: 'MEDIUM' },
      { location_uid: 'abc-l2', label: 'Loc 2 · Tampa FL', field: 'roof_cover', issue: 'Secondary modifier missing (roof cover / anchorage)', impact: 'MEDIUM' },
      { location_uid: 'abc-l4', label: 'Loc 4 · Austin TX', field: 'first_floor_height', issue: 'Defaulted — flood vulnerability uncertain', impact: 'LOW' },
    ],
    input_mismatches: [
      { location_uid: 'abc-l5', field: 'Location present', cat_input: 'Absent', resolved: 'NEW · TIV $22.0M' },
      { location_uid: 'abc-l2', field: 'Roof year', cat_input: '2011', resolved: '2019 (engineering, V)' },
      { location_uid: 'abc-l2', field: 'Construction', cat_input: 'Joisted masonry (ISO 2)', resolved: 'Masonry non-combustible (ISO 4)' },
      { location_uid: 'abc-l3', field: 'Occupancy', cat_input: 'ATC 21 — general warehouse', resolved: 'Lithium-ion battery storage' },
      { location_uid: 'abc-l2', field: 'TIV', cat_input: '$31.0M (expiring)', resolved: '$38.5M (renewal SOV)' },
    ],
    compare: [
      { label: 'As bound 2025–2026', aal_total: 101_300, oep_100: 8_900_000, oep_250: 14_600_000 },
      { label: 'Current (4 locs)', aal_total: 128_900, oep_100: 10_800_000, oep_250: 17_600_000 },
      { label: 'Renewal proposed (5 locs, proxy)', aal_total: 159_700, oep_100: 14_100_000, oep_250: 22_400_000 },
    ],
  };
  const bound: CatResult = { ...cur, run_id: 'cat-abc-bound', snapshot: 'AS_BOUND', run_date: '2025-10-10', aal_total: 101_300, oep: oep(0.824), aep: aep(0.824), aal_by_peril: cur.aal_by_peril.map((p) => ({ ...p, aal: Math.round(p.aal * 0.786) })), dq_flags: [], input_mismatches: [], compare: [] };
  const prop: CatResult = { ...cur, run_id: 'cat-abc-proposed', snapshot: 'RENEWAL_PROPOSED', run_date: '2026-07-31', basis: 'Carrier share 100%, net of deductibles (3% NS); Loc 5 via proxy', aal_total: 159_700, oep: oep(1.306), aep: aep(1.306), aal_by_peril: cur.aal_by_peril.map((p) => ({ ...p, aal: Math.round(p.aal * (p.peril === 'Named storm' ? 1.3 : 1.05)) })), compare: [] };
  return [cur, bound, prop];
})();

const claims: ClaimsEngineering = {
  claims: [
    { claim_id: 'CLM-7B0C22', location_uid: 'abc-l4', location_label: 'Loc 4 · Austin TX', date_of_loss: '2026-04-02', cause: 'Water damage', cat_event: null, status: 'OPEN', paid: 64_000, reserve: 51_000, incurred: 115_000, description: 'Ice-maker supply line failure; production floor and SMT line', linked_recommendation: 'R-114' },
    { claim_id: 'CLM-7A31F0', location_uid: 'abc-l4', location_label: 'Loc 4 · Austin TX', date_of_loss: '2026-01-14', cause: 'Water damage', cat_event: null, status: 'CLOSED', paid: 71_000, reserve: 0, incurred: 71_000, description: 'Failed braided supply line, 2nd-floor restroom', linked_recommendation: 'R-114' },
    { claim_id: 'CLM-6C9910', location_uid: 'abc-l2', location_label: 'Loc 2 · Tampa FL', date_of_loss: '2023-08-30', cause: 'Wind / hail', cat_event: 'Hurricane Idalia', status: 'CLOSED', paid: 312_000, reserve: 0, incurred: 312_000, description: 'Roof flashing and dock doors; below NS deductible on building, BI claimed', linked_recommendation: null },
    { claim_id: 'CLM-5F2208', location_uid: 'abc-l1', location_label: 'Loc 1 · Dayton OH', date_of_loss: '2022-06-13', cause: 'Wind / hail', cat_event: 'PCS 2219', status: 'CLOSED', paid: 240_000, reserve: 0, incurred: 240_000, description: 'Hail damage to skylights and RTUs', linked_recommendation: null },
    { claim_id: 'CLM-4D1187', location_uid: 'abc-l1', location_label: 'Loc 1 · Dayton OH', date_of_loss: '2021-11-04', cause: 'Fire', cat_event: null, status: 'CLOSED', paid: 124_000, reserve: 0, incurred: 124_000, description: 'Dust collector fire, CNC cell 3; contained by sprinklers', linked_recommendation: 'R-109' },
  ],
  summary: { count_5y: 5, incurred_5y: 862_000, loss_ratio_5y: 0.421, by_cause: [
    { cause: 'Wind / hail', count: 2, incurred: 552_000 }, { cause: 'Water damage', count: 2, incurred: 186_000 }, { cause: 'Fire', count: 1, incurred: 124_000 },
  ] },
  recommendations: [
    { rec_id: 'R-114', location_uid: 'abc-l4', location_label: 'Loc 4 · Austin TX', raised: '2025-09-11', category: 'Water damage', description: 'Replace braided supply lines; install automatic water-leak shut-off on domestic mains', severity: 'HIGH', due: '2026-04-29', status: 'OPEN', bind_condition: false, days_overdue: 94, completion_evidence: null, doc_id: `${A}-eng-austin` },
    { rec_id: 'R-117', location_uid: 'abc-l3', location_label: 'Loc 3 · Reno NV', raised: '2024-05-20', category: 'Fire protection', description: 'Hydraulic re-evaluation of sprinkler design for any change in commodity class', severity: 'MEDIUM', due: '2026-06-30', status: 'OPEN', bind_condition: false, days_overdue: 32, completion_evidence: null, doc_id: ENG_RNO },
    { rec_id: 'R-109', location_uid: 'abc-l1', location_label: 'Loc 1 · Dayton OH', raised: '2022-01-10', category: 'Fire protection', description: 'Spark detection and extinguishing on dust-collection ductwork', severity: 'HIGH', due: '2022-09-30', status: 'VERIFIED_CLOSED', bind_condition: true, days_overdue: 0, completion_evidence: 'Engineer site verification 2022-09-14, photos + commissioning cert', doc_id: null },
    { rec_id: 'R-102', location_uid: 'abc-l2', location_label: 'Loc 2 · Tampa FL', raised: '2018-04-02', category: 'Roof', description: 'Replace roof covering; FM 1-90 uplift rating', severity: 'MEDIUM', due: '2019-12-31', status: 'VERIFIED_CLOSED', bind_condition: false, days_overdue: 0, completion_evidence: 'Survey 2024-03-15 p.7 — replaced 2019', doc_id: ENG_TPA },
  ],
  surveys: [
    { survey_id: 'SV-ABC-24T', location_label: 'Loc 2 · Tampa FL', date: '2024-03-15', engineer: 'Elena Brooks', doc_id: ENG_TPA },
    { survey_id: 'SV-ABC-24R', location_label: 'Loc 3 · Reno NV', date: '2024-05-20', engineer: 'Elena Brooks', doc_id: ENG_RNO },
    { survey_id: 'SV-ABC-25A', location_label: 'Loc 4 · Austin TX', date: '2025-09-11', engineer: 'Elena Brooks', doc_id: `${A}-eng-austin` },
    { survey_id: 'SV-ABC-23D', location_label: 'Loc 1 · Dayton OH', date: '2023-10-02', engineer: 'Marcus Lind (contract)', doc_id: null },
  ],
};

const timeline: TimelineEvent[] = [
  ev('abc-t15', '2026-07-31', 'engine', '07', 'Authority check on intended terms', 'L2 required: RARC −8.1% beyond −5% band; adequacy 95.3% < 100%', 'Authority engine'),
  ev('abc-t14', '2026-07-31', 'mock', '06', 'Rater rerun ×3 for RARC split', 'TP(E0,T0) $395K · TP(E1,T0) $488K · TP(E1,T1) $472K — rater-stub v1.4 held fixed', 'Rater (mock)', { finding_ids: ['f-abc-rarc', 'f-abc-adequacy'] }),
  ev('abc-t13', '2026-07-30', 'document', '09', 'Broker counter-offer received', 'Marsh: "we can get this bound today at $450,000"', 'Jenna Park (Marsh)', { doc_id: EML_CTR }),
  ev('abc-t12', '2026-07-29', 'engine', '15', 'Pass 2 · submission delta', '7 new findings: new location, occupancy drift, valuation, CAT input gap, accumulation', 'Renewal engine', { finding_ids: ['f-abc-newloc-cat', 'f-abc-reno-occ', 'f-abc-dayton-val', 'f-abc-accum', 'f-abc-roof'] }),
  ev('abc-t11', '2026-07-28', 'engine', '04', 'Extraction & enrichment', '5 locations, 70 fields, avg confidence 0.94; geocoded; hazard + valuation vendor calls', 'Ingestion'),
  ev('abc-t10', '2026-07-28', 'document', '01', 'Renewal submission received', 'SOV 2026 (xlsx), ACORD 140, loss runs — via broker email', 'Jenna Park (Marsh)', { doc_id: EML_SUB }),
  ev('abc-t09', '2026-07-22', 'mock', '06', 'CAT run on current exposure', 'MockCat 23.1 — 4 locations (exposure file predates Loc 5)', 'CAT (mock)', { doc_id: `${A}-cat-ep` }),
  ev('abc-t08', '2026-07-14', 'user', '08', 'Quote v1 sent', '$470,000 at 3% named-storm deductible', 'Maya Chen', { doc_id: `${A}-quote-v1` }),
  ev('abc-t07', '2026-07-01', 'engine', '03', 'Guidelines v2026 effective', 'CAT.WIND.DED_FLOOR v4: Tier-1 floor 2% → 3%; account re-evaluated', 'Rule engine', { finding_ids: ['f-abc-windded'], doc_id: GUIDE }),
  ev('abc-t06', '2026-06-03', 'engine', '15', 'Pass 1 · internal drift scan (T-150)', '4 findings on data already held: BI over-grant, water losses, R-114 overdue; TP(E0,T0) $395K vs $410K expiring', 'Renewal engine', { finding_ids: ['f-abc-bi', 'f-abc-water', 'f-abc-r114'] }),
  ev('abc-t05', '2026-04-29', 'mock', '05', 'R-114 due — not completed', 'No completion evidence received', 'Engineering (mock)'),
  ev('abc-t04', '2026-04-02', 'mock', '12', 'FNOL — water damage, Austin', 'CLM-7B0C22 reserve $115K', 'Claims (mock)'),
  ev('abc-t03', '2026-01-14', 'mock', '12', 'FNOL — water damage, Austin', 'CLM-7A31F0 $71K', 'Claims (mock)'),
  ev('abc-t02', '2025-11-06', 'mock', '11', 'Policy issued NGP-2025-01842', 'Dec page + forms schedule generated — BI sublimit $15M (binder $10M)', 'PAS (mock)', { doc_id: DEC, finding_ids: ['f-abc-bi'] }),
  ev('abc-t01', '2025-10-24', 'user', '10', 'Bound quote v3', '$410,000 · BI $10M · NS 2%', 'Maya Chen', { doc_id: BINDER }),
];

export const S2_SPEC: AccountSpec = {
  id: A, name: 'ABC Manufacturing', scenario: 'S2', scenario_title: 'Exposure + RARC + terms + accumulation', segment: 'Middle market', occupancy_family: 'Manufacturing', state: 'OH',
  broker: 'Marsh', broker_contact: 'Jenna Park (Marsh, Cincinnati)', underwriter_id: 'u_maya', tenure_years: 7,
  expiry: '2026-11-01', status: 'ACTION_REQUIRED', pass: 2, actions: ['REPRICE', 'RESTRUCTURE', 'REFER', 'ENDORSEMENT_CORRECTION', 'CONDITION'], confidence: 'HIGH',
  missing: ['Loc 5 construction, year built, roof', 'Updated roof-replacement schedule', 'Reno commodity classification & storage height'],
  admitted: true, notice_days: 45, premium: 410_000, limit: 120_000_000, layer: 'Primary blanket $120M', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-01842',
  locations, findings, rarc, seed: 2, deltas, contract, cat, claims, timeline, observations,
  narrative: { text: narrativeText, generated_by: 'llm', model: 'Claude (Bedrock, carrier VPC)', critique: { summary: '11 upheld · 1 challenged — roof-year conflict has no pricing effect', upheld: 11, challenged: 1 } },
  site_model_doc_id: null,
};

export function buildS2(): AccountBundle {
  const s = S2_SPEC;
  const base = { account_id: A, account_name: s.name };
  s.docs = [
    ...docsFor(s),
    doc({ ...base, doc_id: ENG_TPA, doc_type: 'Engineering report', title: 'Loss-control survey — Tampa (Loc 2)', filename: 'abc_manufacturing_survey_tampa_2024-03-15.pdf', format: 'pdf', term: '2024–2025', received_at: '2024-03-22', source_channel: 'Engineering (mock)', size_bytes: 2_310_000, extraction: { status: 'EXTRACTED', fields: 38, avg_confidence: 0.93 } }),
    doc({ ...base, doc_id: ENG_RNO, doc_type: 'Engineering report', title: 'Loss-control survey — Reno (Loc 3)', filename: 'abc_manufacturing_survey_reno_2024-05-20.pdf', format: 'pdf', term: '2024–2025', received_at: '2024-05-27', source_channel: 'Engineering (mock)', size_bytes: 1_870_000 }),
    doc({ ...base, doc_id: `${A}-eng-austin`, doc_type: 'Engineering report', title: 'Loss-control survey — Austin (Loc 4)', filename: 'abc_manufacturing_survey_austin_2025-09-11.pdf', format: 'pdf', term: '2025–2026', received_at: '2025-09-18', source_channel: 'Engineering (mock)', size_bytes: 1_420_000 }),
    doc({ ...base, doc_id: EML_CTR, doc_type: 'Broker email', title: 'RE: ABC Manufacturing renewal — counter', filename: 'abc_manufacturing_broker_counter.eml', format: 'eml', received_at: '2026-07-30', size_bytes: 9_800, extraction: { status: 'EXTRACTED', fields: 2, avg_confidence: 0.97 } }),
    doc({ ...base, doc_id: `${A}-quote-v1`, doc_type: 'Quote', title: 'Quote v1 2026–2027', filename: 'abc_manufacturing_quote_v1_2026.pdf', format: 'pdf', received_at: '2026-07-14', source_channel: 'Platform', size_bytes: 204_000 }),
    doc({ ...base, doc_id: `${A}-endt-1`, doc_type: 'Endorsement', title: 'Endorsement NGP-E-01 — mortgagee', filename: 'abc_manufacturing_endt_01.pdf', format: 'pdf', term: '2025–2026', received_at: '2026-02-10', source_channel: 'PAS (mock)', size_bytes: 58_000 }),
    doc({ ...base, doc_id: `${A}-glb-tampa`, doc_type: '3D site model', title: '3D model — Tampa Assembly & Distribution', filename: 'abc_tampa_site.glb', format: 'glb', received_at: '2026-07-28', source_channel: 'Vendor (mock)', size_bytes: 3_400_000 }),
    doc({ ...base, doc_id: `${A}-img-2023`, doc_type: 'Aerial imagery', title: 'Aerial — Tampa Loc 2 & 5 · 2023-11', filename: 'abc_tampa_aerial_2023-11.png', format: 'png', term: '2025–2026', received_at: '2023-11-20', source_channel: 'Vendor (mock)', size_bytes: 1_900_000 }),
    doc({ ...base, doc_id: `${A}-img-2026`, doc_type: 'Aerial imagery', title: 'Aerial — Tampa Loc 2 & 5 · 2026-06', filename: 'abc_tampa_aerial_2026-06.png', format: 'png', received_at: '2026-06-18', source_channel: 'Vendor (mock)', size_bytes: 2_050_000 }),
    doc({ ...base, doc_id: `${A}-cat-elt`, doc_type: 'CAT event loss table', title: 'Event loss table — current run', filename: 'abc_manufacturing_elt.csv', format: 'csv', received_at: '2026-07-22', source_channel: 'CAT (mock)', size_bytes: 88_000 }),
  ];
  const b = buildBundle(s);
  // SOV still carries roof year 2011 and "general merchandise" — the resolved values differ.
  for (const o of b.observations) {
    if (o.obs_id === 'ob-abc-l2-roof') { o.value = 2011; o.value_display = '2011'; o.is_resolved = false; o.confidence = 0.9; }
    if (o.obs_id === 'ob-abc-l3-occ') { o.value = 'Warehouse — general merchandise'; o.value_display = 'Warehouse — general merchandise'; o.is_resolved = false; }
  }
  b.eml[EML_SUB] = {
    from: 'Jenna Park <jenna.park@marsh.example>', to: ['property.renewals@northgate-specialty.example'], cc: ['maya.chen@northgate-specialty.example'],
    subject: 'ABC Manufacturing — 11/1 property renewal submission', date: '2026-07-28T14:12:00Z',
    text: `Hi Maya,\n\nAttached is the 11/1 renewal submission for ABC Manufacturing (NGP-2025-01842).\n\nHighlights:\n- New Tampa distribution location (1620 N Falkenburg Rd) added May 2026, $22.0M TIV.\n- Values updated at Dayton and Tampa per the insured's fixed-asset register.\n- Reno is now storing e-bike and ESS lithium-ion battery inventory for a new customer — no change to the building.\n\nThe client would like to renew as expiring, including the 2% named-storm deductible.\n\nAttached: renewal SOV, ACORD 140, 5-year loss runs.\n\nThanks,\nJenna Park\nMarsh — Cincinnati`,
    html: null,
    attachments: [
      { filename: 'abc_manufacturing_SOV_2026_renewal.xlsx', doc_id: SOV26, size_bytes: 52_900, content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
      { filename: 'abc_manufacturing_ACORD140.pdf', doc_id: `${A}-acord140`, size_bytes: 141_000, content_type: 'application/pdf' },
      { filename: 'abc_manufacturing_loss_run_2026-06-30.pdf', doc_id: `${A}-lossrun`, size_bytes: 96_000, content_type: 'application/pdf' },
    ],
    highlights: [
      { text: 'Reno is now storing e-bike and ESS lithium-ion battery inventory for a new customer', field_code: 'occupancy', obs_id: 'o-abc-occ-reno-eml' },
      { text: 'New Tampa distribution location (1620 N Falkenburg Rd) added May 2026, $22.0M TIV', field_code: 'tiv', obs_id: 'o-abc-tiv-l5' },
    ],
  };
  b.eml[EML_CTR] = {
    from: 'Jenna Park <jenna.park@marsh.example>', to: ['maya.chen@northgate-specialty.example'], cc: [],
    subject: 'RE: ABC Manufacturing — 11/1 renewal quote', date: '2026-07-30T16:40:00Z',
    text: `Maya,\n\nThanks for the $470K indication. The market is softening and we have an alternative at $440K.\nIf you can move, we can get this bound today at $450,000 with the 3% named-storm deductible you asked for.\n\nJenna`,
    html: null, attachments: [], highlights: [{ text: 'we can get this bound today at $450,000', field_code: 'premium_counter', obs_id: 'o-abc-prem-counter' }],
  };
  b.raw[`${A}-cat-elt`] = ['EventId,Peril,Rate,MeanLoss,SDLoss,ExposureValue', ...Array.from({ length: 60 }, (_, i) => {
    const peril = i % 5 === 0 ? 'SCS' : i % 7 === 0 ? 'EQ' : i % 9 === 0 ? 'FL' : 'HU';
    const rate = +(0.0008 + ((i * 37) % 97) / 9700).toFixed(5);
    const loss = Math.round(40_000 + ((i * 7919) % 23) * 380_000 * (peril === 'HU' ? 1 : 0.4));
    return `${100200 + i * 17},${peril},${rate},${loss},${Math.round(loss * 0.8)},${peril === 'HU' ? 38500000 : 120000000}`;
  })].join('\n');
  return b;
}
