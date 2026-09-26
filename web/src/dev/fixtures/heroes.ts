// Hero scenarios S1, S3–S12 (S2 lives in heroS2.ts).
import type { LocationRow, RarcTerms, ContractDiff, ClaimsEngineering, TimelineEvent } from '@/api/types';
import type { AccountBundle, RarcBase } from './model';
import { buildBundle, claimsFor, docsFor, timelineFor, type AccountSpec } from './builders';
import { between, doc, ev, fnd, int, loc, pdfA, pick, rng, round } from './util';

// ------------------------------------------------------------------ helpers
export function rarcBase(o: { p0: number; ef: number; p1: number; adequacy: number; tiv0: number; tiv1: number; wind?: boolean; ns?: number | null; aop?: number; bi?: number | null; floor?: number }): RarcBase {
  const e1 = o.p1 / o.adequacy, e0 = e1 / o.ef;
  const w = o.wind ? 0.26 : 0;
  const split: [string, RarcBase['components'][number]['kind'], number][] = [
    ['Fire & AOP (building + BPP)', 'aop', 0.44 - w * 0.5], ['Business income', 'bi', 0.11], ...(o.wind ? [['Named storm (CAT load)', 'wind', w] as [string, 'wind', number]] : []),
    ['Flood', 'flood', 0.04], ['Earthquake', 'eq', 0.03], ['Severe convective / other CAT', 'other', 0.08 - (o.wind ? 0.02 : 0)], ['Expense & profit load', 'other', 0],
  ];
  const used = split.reduce((a, s) => a + s[2], 0);
  split[split.length - 1][2] = 1 - used;
  const terms: RarcTerms = { aop_deductible: o.aop ?? 25_000, named_storm_ded_pct: o.wind ? (o.ns ?? 0.03) : null, named_storm_ded_min: o.wind ? 100_000 : null, wind_hail_ded_pct: o.wind ? null : 0.01, bi_sublimit: o.bi === undefined ? 5_000_000 : o.bi, flood_sublimit: 5_000_000, eq_sublimit: 5_000_000 };
  return {
    expiring_premium: o.p0, proposed_premium: o.p1, tp_at_bind: Math.round(e0 * 1.018), expiring_terms: terms, proposed_terms: { ...terms },
    brokerage_expiring: 0.15, brokerage_proposed: 0.15, tiv_expiring: o.tiv0, tiv_renewal: o.tiv1, adequacy_floor: o.floor ?? 0.95,
    method: 'model_rerun', model_version: 'rater-stub v1.4 (held fixed across runs)', wind_floor: o.wind ? 0.03 : null,
    components: split.map(([component, kind, f]) => ({ component, kind, e0: Math.round(e0 * f), e1: Math.round(e1 * f) })),
  };
}

interface Site { city: string; state: string; lat: number; lon: number }
export function genLocs(prefix: string, sites: Site[], o: { names: string[]; occupancy: string; construction: string; tiv: [number, number]; growth: [number, number]; seed: number; wind?: (s: Site) => string | null; sqftPerM?: number }): LocationRow[] {
  const R = rng(o.seed);
  return sites.map((s, i) => {
    const tp = round(between(R, o.tiv[0], o.tiv[1]), 100_000);
    const tc = round(tp * (1 + between(R, o.growth[0], o.growth[1])), 100_000);
    return loc({ location_uid: `${prefix}-l${i + 1}`, loc_no_prior: String(i + 1), loc_no_current: String(i + 1), name: o.names[i % o.names.length].replace('#', String(i + 1)), address: `${int(R, 100, 9800)} ${pick(R, ['Commerce', 'Industrial', 'Main', 'Market', 'Parkway', 'Enterprise', 'Harbor', 'Lakeview'])} ${pick(R, ['Dr', 'Blvd', 'St', 'Ave', 'Way'])}`,
      city: s.city, state: s.state, lat: s.lat + between(R, -0.03, 0.03), lon: s.lon + between(R, -0.03, 0.03), match_method: 'loc_no + address', match_score: +between(R, 0.93, 0.995).toFixed(3),
      tiv_prior: tp, tiv_current: tc, occupancy: o.occupancy, construction: o.construction, year_built: int(R, 1968, 2016), stories: int(R, 1, 4), sqft: round(tp / 1e6 * (o.sqftPerM ?? 5200), 100),
      roof_year: int(R, 2006, 2022), sprinkler: 'Wet pipe, full', valuation_ratio: +between(R, 0.84, 1.02).toFixed(2), wind_tier: o.wind?.(s) ?? null, aal: round(tc * between(R, 0.00012, 0.0006), 100), buildings: 1 });
  });
}

const up = { verdict: 'UPHELD' as const, note: 'Evidence consistent across sources.' };

// ------------------------------------------------------------------ S1
const S1: AccountSpec = (() => {
  const id = 'acc-crestline';
  const sites: Site[] = [
    { city: 'Chicago', state: 'IL', lat: 41.8819, lon: -87.6278 }, { city: 'Denver', state: 'CO', lat: 39.7439, lon: -104.9903 }, { city: 'Minneapolis', state: 'MN', lat: 44.9765, lon: -93.2720 },
    { city: 'Columbus', state: 'OH', lat: 39.9632, lon: -82.9988 }, { city: 'Nashville', state: 'TN', lat: 36.1612, lon: -86.7775 }, { city: 'Charlotte', state: 'NC', lat: 35.2263, lon: -80.8434 },
    { city: 'Indianapolis', state: 'IN', lat: 39.7684, lon: -86.1581 }, { city: 'Kansas City', state: 'MO', lat: 39.0997, lon: -94.5786 },
  ];
  const locations = genLocs('crest', sites, { names: ['Crestline Tower #', 'Crestline Center #'], occupancy: 'Office — multi-tenant', construction: 'Fire resistive (ISO 6)', tiv: [38e6, 62e6], growth: [0.03, 0.045], seed: 101, sqftPerM: 2400 });
  const tiv0 = locations.reduce((a, l) => a + l.tiv_prior!, 0), tiv1 = locations.reduce((a, l) => a + l.tiv_current!, 0);
  locations[1].roof_year = null;
  return {
    id, name: 'Crestline Office REIT', scenario: 'S1', scenario_title: 'Fast-track — no material change', segment: 'Large', occupancy_family: 'Office', state: 'IL',
    broker: 'Aon', broker_contact: 'Rachel Kim (Aon, Chicago)', underwriter_id: 'u_daniel', tenure_years: 9, expiry: '2026-10-01', status: 'FAST_TRACK', pass: 2, actions: ['MAINTAIN'], confidence: 'HIGH', missing: [],
    admitted: true, notice_days: 60, premium: 620_000, limit: round(tiv1 * 1.02, 1e6), layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-00977',
    locations, seed: 101,
    findings: [fnd({ finding_id: 'f-crest-roof', account_id: id, subject_type: 'location', subject_id: 'crest-l2', subject_label: 'Loc 2 · Denver CO', title: 'Roof year blank at Denver (hail zone)', family: 'data_quality', severity: 'LOW', outcome: 'DATA_REQUEST', observed: 'Roof year empty on renewal SOV', expected: 'Roof year populated for SCS-exposed locations', impact_usd: 1_200, confidence: 0.8, critique: up })],
    rarc: rarcBase({ p0: 620_000, ef: 1.0386, p1: 644_000, adequacy: 1.04, tiv0, tiv1 }),
  };
})();

// ------------------------------------------------------------------ S3
const S3: AccountSpec = (() => {
  const id = 'acc-lumen';
  const sites: Site[] = [
    ['Houston', 'TX', 29.7604, -95.3698], ['Houston', 'TX', 29.7370, -95.4610], ['Dallas', 'TX', 32.7767, -96.797], ['Plano', 'TX', 33.0198, -96.6989], ['Austin', 'TX', 30.2672, -97.7431], ['San Antonio', 'TX', 29.4241, -98.4936],
    ['Atlanta', 'GA', 33.749, -84.388], ['Atlanta', 'GA', 33.8470, -84.3620], ['Miami', 'FL', 25.7617, -80.1918], ['Orlando', 'FL', 28.5383, -81.3792], ['Tampa', 'FL', 27.9506, -82.4572], ['Charlotte', 'NC', 35.2271, -80.8431],
    ['Raleigh', 'NC', 35.7796, -78.6382], ['Nashville', 'TN', 36.1627, -86.7816],
  ].map(([city, state, lat, lon]) => ({ city: city as string, state: state as string, lat: lat as number, lon: lon as number }));
  const locations = genLocs('lumen', sites, { names: ['Lumen Jewelers #'], occupancy: 'Retail — jewelry', construction: 'Masonry non-combustible (ISO 4)', tiv: [4.9e6, 8.6e6], growth: [0.02, 0.06], seed: 303, sqftPerM: 700 });
  const unmon = [2, 8, 11];
  unmon.forEach((i) => locations[i].flags.push({ code: 'ALARM_UNMONITORED', label: 'Alarm local only — not central station', severity: 'HIGH', finding_id: 'f-lumen-alarm' }));
  [0, 2, 6, 8, 9].forEach((i) => locations[i].flags.push({ code: 'BURGLARY_92P', label: 'Burglary score 92nd pct', severity: 'MEDIUM', finding_id: 'f-lumen-burg' }));
  const tiv0 = locations.reduce((a, l) => a + l.tiv_prior!, 0), tiv1 = locations.reduce((a, l) => a + l.tiv_current!, 0);
  return {
    id, name: 'Lumen Jewelers', scenario: 'S3', scenario_title: 'Theft & security — protective safeguard risk', segment: 'Middle market', occupancy_family: 'Retail', state: 'TX',
    broker: 'Gallagher', broker_contact: 'Omar Haddad (Gallagher, Houston)', underwriter_id: 'u_aisha', tenure_years: 4, expiry: '2026-10-15', status: 'ACTION_REQUIRED', pass: 2, actions: ['CONDITION', 'REFER'], confidence: 'HIGH',
    missing: ['Central-station alarm certificates (UL 2050) — stores 3, 9, 12', 'Safe / vault ratings per store'],
    admitted: true, notice_days: 45, premium: 382_000, limit: round(tiv1, 1e6), layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-01311', locations, seed: 303,
    findings: [
      fnd({ finding_id: 'f-lumen-alarm', account_id: id, title: '3 stores rely on P-3 central-station alarm but certificates show local-only alarms', family: 'safeguards', rule_id: 'SAFE.CP0411.VERIFIED', rule_version: 2, severity: 'CRITICAL', outcome: 'CONDITION', observed: 'SOV: alarm "Y" at all 14 · certificates: stores 3, 9, 12 local bell only', expected: 'UL-certificated central-station alarm where P-3 applies', impact_usd: 84_000, impact_method: 'stock at risk × theft frequency × breach probability', confidence: 0.91, source: 'Theft & Security Guidelines 2026 §40.2', critique: up }),
      fnd({ finding_id: 'f-lumen-burg', account_id: id, title: 'Burglary score in 92nd percentile at 5 stores', family: 'security', rule_id: 'SEC.CRIME.SCORE', severity: 'HIGH', outcome: 'REFER', observed: 'CrimeCast percentile 92–97 (stores 1, 3, 7, 9, 10)', expected: '< 85th percentile or enhanced security', impact_usd: 36_000, impact_method: 'theft loading', confidence: 0.83, source: 'Theft & Security Guidelines 2026 §40.1', critique: up }),
      fnd({ finding_id: 'f-lumen-crime', account_id: id, title: 'Money & securities exposure with no crime policy — coverage review', family: 'security', rule_id: 'COV.GAP.CRIME', severity: 'MEDIUM', outcome: 'FLAG', observed: 'Daily cash on hand $40–120K per store; no crime placement on file', expected: 'Crime / fidelity coverage or exclusion acknowledged', impact_usd: 6_000, impact_method: 'cross-sell / E&O exposure', confidence: 0.7, source: 'Standard library — coverage gaps', critique: { verdict: 'CHALLENGED', note: 'May be placed with another carrier; confirm with broker.' } }),
      fnd({ finding_id: 'f-lumen-stock', account_id: id, title: 'Peak-season stock values above scheduled limits at 4 stores', family: 'valuation', severity: 'MEDIUM', outcome: 'PRICE_ADJUST', observed: 'Nov–Dec stock up to $4.2M vs $3.1M scheduled', expected: 'Peak-season endorsement or blanket stock', impact_usd: 11_000, confidence: 0.8, critique: up }),
    ],
    rarc: rarcBase({ p0: 382_000, ef: 1.041, p1: 405_000, adequacy: 0.97, tiv0, tiv1 }),
  };
})();

// ------------------------------------------------------------------ S4
const S4: AccountSpec = (() => {
  const id = 'acc-redline';
  const locations: LocationRow[] = [
    loc({ location_uid: 'red-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Memphis DC-1', address: '4100 Tchulahoma Rd', city: 'Memphis', state: 'TN', lat: 35.0423, lon: -89.9731, tiv_prior: 52_000_000, tiv_current: 57_400_000, occupancy: 'Lithium-ion battery storage (e-bike)', occupancy_prior: 'Warehouse — general commodities', construction: 'Tilt-up concrete (ISO 5)', year_built: 2009, stories: 1, sqft: 412_000, roof_year: 2017, sprinkler: 'ESFR K-17, 20 ft storage design', valuation_ratio: 0.93, cat_zone: 'New Madrid EQ', aal: 21_400,
      flags: [{ code: 'OCC_DRIFT', label: 'Occupancy drift → lithium-ion', severity: 'CRITICAL', finding_id: 'f-red-occ' }, { code: 'STORAGE_HEIGHT', label: 'Storage 28 ft > design 20 ft', severity: 'CRITICAL', finding_id: 'f-red-sprk' }],
      model_doc_id: 'acc-redline-glb-memphis', imagery_doc_ids: ['acc-redline-img-2024', 'acc-redline-img-2026'] }),
    loc({ location_uid: 'red-l2', loc_no_prior: '2', loc_no_current: '2', name: 'Louisville DC-2', address: '7800 National Tpke', city: 'Louisville', state: 'KY', lat: 38.1360, lon: -85.7400, tiv_prior: 38_000_000, tiv_current: 39_100_000, occupancy: 'Warehouse — general commodities', construction: 'Tilt-up concrete (ISO 5)', year_built: 2012, stories: 1, sqft: 298_000, roof_year: 2012, sprinkler: 'ESFR K-17, 30 ft design', valuation_ratio: 0.91, aal: 9_800 }),
    loc({ location_uid: 'red-l3', loc_no_prior: '3', loc_no_current: '3', name: 'Indianapolis Cross-dock', address: '2250 S Mitthoeffer Rd', city: 'Indianapolis', state: 'IN', lat: 39.7280, lon: -85.9950, tiv_prior: 21_000_000, tiv_current: 21_600_000, occupancy: 'Warehouse — cross-dock', construction: 'Non-combustible (ISO 3)', year_built: 1999, stories: 1, sqft: 164_000, roof_year: 2015, sprinkler: 'Wet pipe, CMDA', valuation_ratio: 0.88, aal: 6_900 }),
  ];
  return {
    id, name: 'Redline Logistics', scenario: 'S4', scenario_title: 'Occupancy drift + sprinkler adequacy', segment: 'Middle market', occupancy_family: 'Warehouse', state: 'TN',
    broker: 'Lockton', broker_contact: 'Beth Morales (Lockton, Nashville)', underwriter_id: 'u_tom', tenure_years: 3, expiry: '2026-10-20', status: 'ACTION_REQUIRED', pass: 2, actions: ['CONDITION', 'REPRICE'], confidence: 'MEDIUM',
    missing: ['Commodity classification & rack configuration — Memphis', 'Updated sprinkler hydraulic calcs'],
    admitted: true, notice_days: 30, premium: 438_000, limit: 118_000_000, layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-01566', locations, seed: 404,
    findings: [
      fnd({ finding_id: 'f-red-occ', account_id: id, subject_type: 'location', subject_id: 'red-l1', subject_label: 'Loc 1 · Memphis DC-1', title: 'Memphis occupancy drift: general commodities → lithium-ion (e-bike) batteries', family: 'occupancy', rule_id: 'OCC.DRIFT.HAZARD', rule_version: 2, severity: 'CRITICAL', outcome: 'CONDITION', observed: 'Broker email 2026-07-22 "now storing e-bike batteries"; imagery shows new racking', expected: 'Rated as general commodities (engineering 2024)', impact_usd: 96_000, impact_method: 'rate differential + FM DS 8-1 hazard loading', confidence: 0.88, source: 'Property UW Guidelines 2026 §9.4', critique: up }),
      fnd({ finding_id: 'f-red-sprk', account_id: id, subject_type: 'location', subject_id: 'red-l1', subject_label: 'Loc 1 · Memphis DC-1', title: 'Storage height 28 ft exceeds 20 ft sprinkler design — adequacy FAIL', family: 'safeguards', rule_id: 'SPK.ADEQ.HEIGHT', rule_version: 1, severity: 'CRITICAL', outcome: 'BLOCK', observed: 'Top-of-storage 28 ft (3D model racks) vs ESFR design 20 ft', expected: 'Storage height ≤ sprinkler design height', impact_usd: 142_000, impact_method: 'PML uplift × rate on line', confidence: 0.9, source: 'Risk Engineering Standards §6 (NFPA 13 / FM DS 8-9)', critique: up }),
      fnd({ finding_id: 'f-red-class', account_id: id, title: 'CAT and pricing occupancy class still general warehouse', family: 'pricing', rule_id: 'PRC.CLASS.MISMATCH', severity: 'MEDIUM', outcome: 'PRICE_ADJUST', observed: 'Rater class 21 (general warehouse) at Memphis', expected: 'Hazardous storage class', impact_usd: 28_000, confidence: 0.85, critique: up }),
    ],
    rarc: rarcBase({ p0: 438_000, ef: 1.062, p1: 452_000, adequacy: 0.91, tiv0: 111_000_000, tiv1: 118_100_000 }),
  };
})();

// ------------------------------------------------------------------ S5
const S5: AccountSpec = (() => {
  const id = 'acc-harborview';
  const sites: Site[] = [
    { city: 'Charleston', state: 'SC', lat: 32.7765, lon: -79.9311 }, { city: 'Savannah', state: 'GA', lat: 32.0809, lon: -81.0912 }, { city: 'Myrtle Beach', state: 'SC', lat: 33.6891, lon: -78.8867 },
    { city: 'Wilmington', state: 'NC', lat: 34.2257, lon: -77.9447 }, { city: 'Jacksonville', state: 'FL', lat: 30.3322, lon: -81.6557 }, { city: 'Hilton Head', state: 'SC', lat: 32.2163, lon: -80.7526 },
  ];
  const locations = genLocs('harbor', sites, { names: ['Harborview Inn #'], occupancy: 'Hotel — limited service', construction: 'Masonry non-combustible (ISO 4)', tiv: [17e6, 24e6], growth: [0, 0], seed: 505, wind: (s) => (['Myrtle Beach', 'Hilton Head', 'Charleston'].includes(s.city) ? 'T1' : 'T2'), sqftPerM: 4600 });
  locations.forEach((l, i) => { l.valuation_ratio = [0.68, 0.66, 0.71, 0.7, 0.67, 0.69][i]; l.flags.push({ code: 'UNDERVALUED', label: `Under-valued: ${Math.round(l.valuation_ratio! * 100)}% of model RC`, severity: 'HIGH', finding_id: 'f-harbor-val' }, { code: 'FLAT_VALUES', label: 'Flat 3 years', severity: 'MEDIUM', finding_id: 'f-harbor-flat' }); l.tiv_change_pct = 0; });
  const tiv = locations.reduce((a, l) => a + l.tiv_prior!, 0);
  return {
    id, name: 'Harborview Hotels', scenario: 'S5', scenario_title: 'Under-valuation — flat values 3 years', segment: 'Middle market', occupancy_family: 'Hospitality', state: 'SC',
    broker: 'Lockton', broker_contact: 'Grant Ellis (Lockton, Charleston)', underwriter_id: 'u_daniel', tenure_years: 6, expiry: '2026-10-10', status: 'ACTION_REQUIRED', pass: 2, actions: ['DATA_REQUEST', 'REPRICE'], confidence: 'MEDIUM',
    missing: ['Current appraisal (last 2021)', 'Building sq ft per hotel verified'],
    admitted: true, notice_days: 30, premium: 708_000, limit: round(tiv, 1e6), layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-01402', locations, seed: 505,
    findings: [
      fnd({ finding_id: 'f-harbor-val', account_id: id, title: 'Building values at 68% of model RC — $38M under-insured', family: 'valuation', rule_id: 'VAL.RC.RATIO', rule_version: 3, severity: 'HIGH', outcome: 'PRICE_ADJUST', observed: 'Reported $142/sq ft vs model $209/sq ft (68%)', expected: 'Reported ≥ 80% of model RC', impact_usd: 171_000, impact_method: '(model RC − reported) × rate on line 0.45%', confidence: 0.82, source: 'Valuation Standards 2026 §1.2', critique: up }),
      fnd({ finding_id: 'f-harbor-flat', account_id: id, title: 'Building values flat for 3 years vs +5.1%/yr construction-cost trend', family: 'valuation', rule_id: 'VAL.FLAT.MULTIYEAR', severity: 'MEDIUM', outcome: 'FLAG', observed: 'Identical building values 2024, 2025, 2026 SOVs', expected: 'Values trended at least by cost index', impact_usd: 22_000, confidence: 0.95, source: 'Valuation Standards 2026 §1.4', critique: up }),
      fnd({ finding_id: 'f-harbor-appr', account_id: id, title: 'Last appraisal 2021 — stale (> 3 years)', family: 'data_quality', rule_id: 'DQ.STALE.APPRAISAL', severity: 'MEDIUM', outcome: 'DATA_REQUEST', observed: 'Appraisal dated 2021-04-12', expected: 'Appraisal ≤ 3 years for coastal hospitality', impact_usd: 0, confidence: 1, critique: up }),
      fnd({ finding_id: 'f-harbor-coins', account_id: id, title: 'Coinsurance / limit shortfall exposure noted', family: 'valuation', severity: 'LOW', outcome: 'FLAG', observed: 'Agreed value not endorsed; 90% coinsurance', expected: 'Agreed value or adequate values', impact_usd: 3_000, impact_method: 'noted separately — insured penalty, not carrier loss', confidence: 0.7, critique: up }),
    ],
    rarc: rarcBase({ p0: 708_000, ef: 1.0, p1: 729_000, adequacy: 0.93, tiv0: tiv, tiv1: tiv, wind: true, ns: 0.05 }),
  };
})();

// ------------------------------------------------------------------ S6
const S6: AccountSpec = (() => {
  const id = 'acc-ember';
  const cities: [string, string, number, number][] = [['Dallas', 'TX', 32.7767, -96.797], ['Fort Worth', 'TX', 32.7555, -97.3308], ['Plano', 'TX', 33.0198, -96.6989], ['Houston', 'TX', 29.7604, -95.3698], ['Austin', 'TX', 30.2672, -97.7431], ['San Antonio', 'TX', 29.4241, -98.4936], ['Oklahoma City', 'OK', 35.4676, -97.5164], ['Tulsa', 'OK', 36.154, -95.9928], ['Little Rock', 'AR', 34.7465, -92.2896], ['Shreveport', 'LA', 32.5252, -93.7502], ['Waco', 'TX', 31.5493, -97.1467]];
  const sites: Site[] = Array.from({ length: 22 }, (_, i) => { const c = cities[i % cities.length]; return { city: c[0], state: c[1], lat: c[2], lon: c[3] }; });
  const locations = genLocs('ember', sites, { names: ['Ember & Oak #', 'Oak Tavern #'], occupancy: 'Restaurant — full service, open broiling', construction: 'Joisted masonry (ISO 2)', tiv: [2.2e6, 4.6e6], growth: [0.02, 0.05], seed: 606, sqftPerM: 2100 });
  [3, 9, 14].forEach((i) => locations[i].flags.push({ code: 'GREASE_FIRES', label: 'Repeat grease fires', severity: 'HIGH', finding_id: 'f-ember-repeat' }));
  [1, 4, 6, 11, 15, 18, 20].forEach((i) => locations[i].flags.push({ code: 'HOOD_CERT', label: 'Hood cleaning cert missing', severity: 'HIGH', finding_id: 'f-ember-hood' }));
  const tiv0 = locations.reduce((a, l) => a + l.tiv_prior!, 0), tiv1 = locations.reduce((a, l) => a + l.tiv_current!, 0);
  return {
    id, name: 'Ember & Oak Restaurant Group', scenario: 'S6', scenario_title: 'Fire / cooking hazard — repeat cause', segment: 'Middle market', occupancy_family: 'Restaurant', state: 'TX',
    broker: 'Brown & Brown', broker_contact: 'Kyle Tran (Brown & Brown, Dallas)', underwriter_id: 'u_tom', tenure_years: 5, expiry: '2026-10-05', status: 'IN_REVIEW', pass: 2, actions: ['CONDITION', 'RESTRUCTURE'], confidence: 'HIGH',
    missing: ['Semi-annual hood & duct cleaning certificates (NFPA 96) — 7 sites', 'UL 300 suppression inspection tags'],
    admitted: true, notice_days: 60, premium: 291_000, limit: round(tiv1, 1e6), layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-01238', locations, seed: 606,
    findings: [
      fnd({ finding_id: 'f-ember-repeat', account_id: id, title: '4 grease fires in 3 years at 3 sites — repeat-cause indicator', family: 'claims', rule_id: 'CLM.REPEAT.CAUSE', severity: 'HIGH', outcome: 'PRICE_ADJUST', observed: '4 cooking fires 2023–2026, $612K incurred (sites 4, 10, 15)', expected: 'No repeat cause at same site within 36 months', impact_usd: 58_000, impact_method: 'experience mod on fire', confidence: 0.95, source: 'Property UW Guidelines 2026 §5.1', critique: up }),
      fnd({ finding_id: 'f-ember-hood', account_id: id, title: 'Cooking suppression relied on; hood cleaning certificates missing at 7 sites', family: 'safeguards', rule_id: 'SAFE.COOKING.VERIFIED', severity: 'HIGH', outcome: 'CONDITION', observed: 'No NFPA 96 certificates within 6 months at 7 of 22 sites', expected: 'Current hood/duct certificates where safeguard applies', impact_usd: 31_000, confidence: 0.9, source: 'Occupancy add-on §39 (restaurants)', critique: up }),
      fnd({ finding_id: 'f-ember-rec', account_id: id, title: 'Claims linked to open recommendation R-231 (fusible-link replacement)', family: 'engineering', rule_id: 'ENG.REC.CLAIM_LINK', severity: 'MEDIUM', outcome: 'CONDITION', observed: 'R-231 open 140 days; 2 fires at the same site since', expected: 'Recommendation closed with evidence', impact_usd: 9_000, confidence: 0.88, critique: up }),
    ],
    rarc: rarcBase({ p0: 291_000, ef: 1.036, p1: 309_000, adequacy: 0.96, tiv0, tiv1 }),
  };
})();

// ------------------------------------------------------------------ S7
const S7: AccountSpec = (() => {
  const id = 'acc-pinecrest';
  const locations = [loc({ location_uid: 'pine-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Pinecrest Plaza', address: '8500 Pineville-Matthews Rd', city: 'Charlotte', state: 'NC', lat: 35.0880, lon: -80.8480, tiv_prior: 62_000_000, tiv_current: 62_000_000, occupancy: 'Retail centre — 62% vacant', occupancy_prior: 'Retail centre — anchor + inline', construction: 'Masonry non-combustible (ISO 4)', year_built: 1988, stories: 1, sqft: 412_000, roof_year: 2010, sprinkler: 'Wet pipe — IMPAIRED (since 2026-06-07)', valuation_ratio: 0.9, aal: 18_200,
    flags: [{ code: 'VACANCY', label: '62% vacant > 60-day threshold', severity: 'HIGH', finding_id: 'f-pine-vac' }, { code: 'IMPAIRED', label: 'Sprinkler impaired', severity: 'CRITICAL', finding_id: 'f-pine-fire' }], imagery_doc_ids: ['acc-pinecrest-img-2025', 'acc-pinecrest-img-2026'] })];
  const timeline: TimelineEvent[] = [
    ev('pine-t5', '2026-06-08', 'engine', '07', 'Referral raised (CRITICAL)', 'VAC.FIRE.SPRINKLER_OFF fired — referred to Senior UW now, not at renewal', 'Authority engine', { finding_ids: ['f-pine-fire'] }),
    ev('pine-t4', '2026-06-07', 'mock', '05', 'Sprinkler impairment notice', 'Main riser valve closed — contractor ETA unknown', 'Engineering (mock)', { finding_ids: ['f-pine-fire'] }),
    ev('pine-t3', '2026-06-02', 'mock', '04', 'Imagery published', 'Empty parking lot at 3 captures; anchor tenant signage removed', 'Imagery vendor (mock)', { doc_id: 'acc-pinecrest-img-2026' }),
    ev('pine-t2', '2026-04-01', 'mock', '12', 'Endorsement — anchor tenant vacates', 'Occupancy 62% vacant; vacancy provision clock starts', 'PAS (mock)', { finding_ids: ['f-pine-vac'] }),
    ev('pine-t1', '2026-01-15', 'mock', '11', 'Policy issued', 'NGP-2026-00114', 'PAS (mock)'),
  ];
  return {
    id, name: 'Pinecrest Plaza', scenario: 'S7', scenario_title: 'Event-driven mid-term — vacancy + sprinkler impairment', segment: 'Middle market', occupancy_family: 'Retail', state: 'NC',
    broker: 'USI', broker_contact: 'Dana Whitlock (USI, Charlotte)', underwriter_id: 'u_aisha', tenure_years: 2, expiry: '2027-01-15', status: 'REFERRED', pass: 1, actions: ['REFER', 'CONDITION'], confidence: 'HIGH',
    missing: ['Impairment restoration date', 'Vacant-space security plan'],
    admitted: true, notice_days: 45, premium: 188_000, limit: 62_000_000, layer: 'Primary', share: 1, limit_basis: 'scheduled', policy_no: 'NGP-2026-00114', locations, seed: 707, timeline,
    findings: [
      fnd({ finding_id: 'f-pine-fire', account_id: id, subject_type: 'location', subject_id: 'pine-l1', subject_label: 'Pinecrest Plaza', title: 'Vacant + sprinkler impaired → fire referral', family: 'safeguards', rule_id: 'VAC.FIRE.SPRINKLER_OFF', rule_version: 1, severity: 'CRITICAL', outcome: 'REFER', observed: '62% vacant since 2026-04-01; sprinkler impaired since 2026-06-07', expected: 'Impairment restored ≤ 10 days or fire watch + referral', impact_usd: 94_000, impact_method: 'PML uplift (unsprinklered) × probability', confidence: 0.93, pass: 1, created_at: '2026-06-08', source: 'Catalogue §41 · Property UW Guidelines 2026 §8.2', critique: up }),
      fnd({ finding_id: 'f-pine-vac', account_id: id, subject_type: 'location', subject_id: 'pine-l1', subject_label: 'Pinecrest Plaza', title: 'Vacancy 62% beyond 60-day policy threshold — vacancy provision applies', family: 'occupancy', rule_id: 'VAC.THRESHOLD', severity: 'HIGH', outcome: 'CONDITION', observed: 'Anchor tenant left 2026-04-01 (endorsement); imagery 2026-06 empty lot', expected: 'Vacancy < 60 days or vacancy permit endorsement', impact_usd: 21_000, confidence: 0.95, pass: 1, created_at: '2026-06-02', critique: up }),
    ],
    rarc: rarcBase({ p0: 188_000, ef: 1.0, p1: 188_000, adequacy: 0.86, tiv0: 62e6, tiv1: 62e6 }),
  };
})();

// ------------------------------------------------------------------ S8
const S8: AccountSpec = (() => {
  const id = 'acc-aurelia';
  const locations = [loc({ location_uid: 'aur-l1', loc_no_prior: '1', loc_no_current: '1', name: 'St. Aurelia Campus (12 bldgs)', address: '6400 Fannin St', city: 'Houston', state: 'TX', lat: 29.7079, lon: -95.4000, tiv_prior: 522_000_000, tiv_current: 540_000_000, occupancy: 'Hospital — acute care', construction: 'Fire resistive (ISO 6)', year_built: 1974, stories: 9, sqft: 1_840_000, roof_year: 2016, sprinkler: 'Wet pipe, full (Bldg 2 per P-1)', valuation_ratio: 0.94, wind_tier: 'T2', cat_zone: 'Houston / Galveston', aal: 412_000, buildings: 12,
    flags: [{ code: 'NS_MIN_LOST', label: 'NS $250K minimum lost at issuance', severity: 'HIGH', finding_id: 'f-aur-min' }, { code: 'SAFEGUARD_DROPPED', label: 'CP 04 11 dropped — Bldg 2', severity: 'HIGH', finding_id: 'f-aur-safe' }], model_doc_id: 'acc-aurelia-glb-campus' })];
  const contract: ContractDiff = {
    term: '2026–2027', quote_version: 'v3',
    rows: [
      { field: 'limit', label: 'Blanket limit', group: 'Limits', values: { quote: '$540.0M', binder: '$540.0M', policy: '$540.0M' }, anchors: { quote: pdfA(`${id}-quote-v3`, 2, [72, 180, 540, 194]), binder: pdfA(`${id}-binder`, 1, [72, 180, 540, 194]), policy: pdfA(`${id}-dec`, 1, [72, 220, 540, 234]) }, result: 'MATCH', finding_id: null },
      { field: 'aop', label: 'AOP deductible', group: 'Deductibles', values: { quote: '$100K (v3) — approved v2: $250K', binder: '$100K', policy: '$100K' }, anchors: { quote: pdfA(`${id}-quote-v3`, 2, [72, 240, 540, 254], 'All Other Perils Deductible: $100,000'), binder: pdfA(`${id}-binder`, 1, [72, 240, 540, 254]), policy: pdfA(`${id}-dec`, 2, [72, 240, 540, 254]) }, result: 'MISMATCH', finding_id: 'f-aur-auth' },
      { field: 'ns', label: 'Named storm deductible', group: 'Deductibles', values: { quote: '5% per location, $250K min', binder: '5% per location, $250K min', policy: '5% per location — no minimum' }, anchors: { quote: pdfA(`${id}-quote-v3`, 2, [72, 256, 540, 270]), binder: pdfA(`${id}-binder`, 1, [72, 256, 540, 270]), policy: pdfA(`${id}-dec`, 2, [72, 256, 540, 270], 'Named Storm: 5% of TIV per location') }, result: 'MISMATCH', finding_id: 'f-aur-min' },
      { field: 'bi', label: 'Business income / EE', group: 'Sublimits', values: { quote: '$120.0M', binder: '$120.0M', policy: '$120.0M' }, anchors: { quote: pdfA(`${id}-quote-v3`, 2, [72, 300, 540, 314]), binder: pdfA(`${id}-binder`, 1, [72, 300, 540, 314]), policy: pdfA(`${id}-dec`, 2, [72, 300, 540, 314]) }, result: 'MATCH', finding_id: null },
      { field: 'flood', label: 'Flood sublimit', group: 'Sublimits', values: { quote: '$25.0M', binder: '$25.0M', policy: '$25.0M' }, anchors: { quote: pdfA(`${id}-quote-v3`, 2, [72, 316, 540, 330]), binder: pdfA(`${id}-binder`, 1, [72, 316, 540, 330]), policy: pdfA(`${id}-dec`, 2, [72, 316, 540, 330]) }, result: 'MATCH', finding_id: null },
      { field: 'cp0411', label: 'CP 04 11 Protective safeguards (P-1 sprinkler, Bldg 2)', group: 'Safeguards', values: { quote: 'Required', binder: 'Required', policy: null }, anchors: { quote: pdfA(`${id}-quote-v3`, 3, [72, 220, 540, 234]), binder: pdfA(`${id}-binder`, 2, [72, 220, 540, 234]), policy: pdfA(`${id}-dec`, 4, [72, 120, 540, 400], 'Forms schedule — CP 04 11 not listed') }, result: 'MISSING', finding_id: 'f-aur-safe' },
      { field: 'cp0010', label: 'CP 00 10 Building & personal property', group: 'Forms', values: { quote: 'Attached', binder: 'Attached', policy: 'Attached' }, anchors: { quote: pdfA(`${id}-quote-v3`, 3, [72, 120, 540, 134]), binder: pdfA(`${id}-binder`, 2, [72, 120, 540, 134]), policy: pdfA(`${id}-dec`, 3, [72, 120, 540, 134]) }, result: 'MATCH', finding_id: null },
      { field: 'subj-gen', label: 'Emergency generator full-load test report', group: 'Subjectivities', values: { quote: 'Before bind', binder: 'Outstanding', policy: '—' }, anchors: { quote: pdfA(`${id}-quote-v3`, 4, [72, 140, 540, 154]), binder: pdfA(`${id}-binder`, 2, [72, 300, 540, 314], 'Subject to: generator load test report — OUTSTANDING'), policy: null }, result: 'MISSING', finding_id: 'f-aur-subj' },
      { field: 'premium', label: 'Annual premium', group: 'Premium', values: { quote: '$1,350,000', binder: '$1,350,000', policy: '$1,350,000' }, anchors: { quote: pdfA(`${id}-quote-v3`, 1, [72, 520, 540, 534]), binder: pdfA(`${id}-binder`, 1, [72, 520, 540, 534]), policy: pdfA(`${id}-dec`, 1, [72, 520, 540, 534]) }, result: 'MATCH', finding_id: null },
    ],
    endorsements: [{ endt_id: 'NGP-E-11', effective: '2026-03-01', type: 'Location schedule', description: 'Add Research Bldg (Bldg 10) values +$18M', premium_delta: 21_400, doc_id: null }],
    subjectivities: [{ text: 'Emergency generator full-load test report (NFPA 110)', due: '2025-12-31', status: 'OPEN', age_days: 212, finding_id: 'f-aur-subj' }, { text: 'Signed SOV', due: '2025-12-31', status: 'CLEARED', age_days: 0, finding_id: null }],
    quotes: [], referrals: [],
  };
  const docs = [
    ...docsFor({ id, name: 'St. Aurelia Medical Center', pass: 3, expiry: '2027-01-01', locations, findings: [], seed: 808, broker: 'WTW' } as unknown as AccountSpec),
    doc({ account_id: id, account_name: 'St. Aurelia Medical Center', doc_id: `${id}-quote-v2`, doc_type: 'Quote', title: 'Quote v2 2026 (approved by P. Raman)', filename: 'st_aurelia_quote_v2.pdf', format: 'pdf', term: '2026–2027', received_at: '2025-12-12', source_channel: 'Platform' }),
    doc({ account_id: id, account_name: 'St. Aurelia Medical Center', doc_id: `${id}-quote-v3`, doc_type: 'Quote', title: 'Quote v3 2026 (bound)', filename: 'st_aurelia_quote_v3.pdf', format: 'pdf', term: '2026–2027', received_at: '2025-12-19', source_channel: 'Platform' }),
    doc({ account_id: id, account_name: 'St. Aurelia Medical Center', doc_id: `${id}-binder`, doc_type: 'Binder', title: 'Binder 2026–2027', filename: 'st_aurelia_binder_2026.pdf', format: 'pdf', term: '2026–2027', received_at: '2025-12-31', source_channel: 'Platform' }),
    doc({ account_id: id, account_name: 'St. Aurelia Medical Center', doc_id: `${id}-dec`, doc_type: 'Declarations', title: 'Declarations & forms schedule 2026–2027', filename: 'st_aurelia_declarations_2026.pdf', format: 'pdf', term: '2026–2027', received_at: '2026-01-09', source_channel: 'PAS (mock)' }),
    doc({ account_id: id, account_name: 'St. Aurelia Medical Center', doc_id: `${id}-glb-campus`, doc_type: '3D site model', title: '3D campus model — 12 buildings', filename: 'st_aurelia_campus.glb', format: 'glb', term: '2026–2027', received_at: '2026-02-03', source_channel: 'Vendor (mock)', size_bytes: 5_200_000 }),
  ];
  return {
    id, name: 'St. Aurelia Medical Center', scenario: 'S8', scenario_title: 'Contract integrity + authority — approval invalidated', segment: 'Large', occupancy_family: 'Healthcare', state: 'TX',
    broker: 'WTW', broker_contact: 'Hannah Cole (WTW, Houston)', underwriter_id: 'u_daniel', tenure_years: 11, expiry: '2027-01-01', status: 'REFERRED', pass: 3, actions: ['REFER', 'ENDORSEMENT_CORRECTION', 'CONDITION'], confidence: 'HIGH',
    missing: ['Generator full-load test report (open 212 days)'],
    admitted: true, notice_days: 60, premium: 1_350_000, limit: 540_000_000, layer: 'Primary blanket $540M', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2026-00003', locations, seed: 808, contract, docs,
    site_model_doc_id: `${id}-glb-campus`,
    findings: [
      fnd({ finding_id: 'f-aur-auth', account_id: id, subject_type: 'referral', subject_id: 'ref-aur-v2', subject_label: 'Referral on quote v2', title: 'Approval invalid: quote v3 changed AOP deductible $250K → $100K after senior approval', family: 'authority', rule_id: 'AUTH.APPROVAL.TERMS_HASH', rule_version: 1, severity: 'CRITICAL', outcome: 'REFER', observed: 'Approved hash 9f3a17c2 (v2, AOP $250K) · bound hash c41e08b5 (v3, AOP $100K)', expected: 'Bound terms hash = approved terms hash', impact_usd: 118_000, impact_method: 'control exposure — premium at stake on deductible change', confidence: 1, pass: 3, created_at: '2025-12-31', source: 'Authority Matrix 2026 §1.4', critique: up }),
      fnd({ finding_id: 'f-aur-min', account_id: id, subject_type: 'contract', subject_id: `pol-${id}`, subject_label: 'Named storm deductible', title: 'Named-storm $250K minimum lost at issuance', family: 'contract_integrity', rule_id: 'CTR.BINDER_POLICY.DEDUCTIBLE', severity: 'HIGH', outcome: 'TERM_BREACH', observed: 'Binder: 5% per location, $250K min · policy: 5%, no minimum', expected: 'Issued policy = binder', impact_usd: 46_000, impact_method: 'ΔAAL at no-minimum', confidence: 0.98, pass: 3, created_at: '2026-01-10', source: 'Standard library — contract integrity', critique: up }),
      fnd({ finding_id: 'f-aur-safe', account_id: id, subject_type: 'contract', subject_id: `pol-${id}`, subject_label: 'CP 04 11 — Bldg 2', title: 'CP 04 11 protective safeguard dropped from issued policy (Bldg 2)', family: 'contract_integrity', rule_id: 'CTR.FORMS.SAFEGUARD', severity: 'HIGH', outcome: 'TERM_BREACH', observed: 'Quote & binder: P-1 required · forms schedule: CP 04 11 absent', expected: 'Safeguard endorsement attached as bound', impact_usd: 24_000, confidence: 0.97, pass: 3, created_at: '2026-01-10', source: 'Standard library — contract integrity', critique: up }),
      fnd({ finding_id: 'f-aur-subj', account_id: id, subject_type: 'contract', subject_id: `pol-${id}`, subject_label: 'Subjectivity', title: 'Bound with open subjectivity — generator load test, 212 days', family: 'contract_integrity', rule_id: 'CTR.SUBJ.AGING', severity: 'MEDIUM', outcome: 'CONDITION', observed: 'Subjectivity due 2025-12-31; still OPEN', expected: 'Cleared ≤ 30 days after bind', impact_usd: 8_000, confidence: 1, pass: 3, created_at: '2026-01-31', source: 'Standard library — subjectivities', critique: up }),
    ],
    rarc: rarcBase({ p0: 1_350_000, ef: 1.034, p1: 1_350_000, adequacy: 0.97, tiv0: 522e6, tiv1: 540e6, wind: true, ns: 0.05, aop: 100_000, bi: 120_000_000 }),
  };
})();

// ------------------------------------------------------------------ S9
const S9: AccountSpec = (() => {
  const id = 'acc-keystone';
  const locations = [
    loc({ location_uid: 'key-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Allentown Extrusion Plant', address: '3100 Hamilton Blvd', city: 'Allentown', state: 'PA', lat: 40.5890, lon: -75.5210, tiv_prior: 54_000_000, tiv_current: 55_900_000, occupancy: 'Plastics — extrusion & compounding', construction: 'Non-combustible (ISO 3)', year_built: 1986, stories: 1, sqft: 246_000, roof_year: 2013, sprinkler: 'Wet pipe, full', valuation_ratio: 0.89, aal: 7_400,
      flags: [{ code: 'REC_UNVERIFIED', label: 'Bind-condition rec closed w/o evidence', severity: 'CRITICAL', finding_id: 'f-key-rec' }, { code: 'LARGE_LOSS', label: '$1.4M fire 2026-03', severity: 'HIGH', finding_id: 'f-key-claim' }] }),
    loc({ location_uid: 'key-l2', loc_no_prior: '2', loc_no_current: '2', name: 'Erie Molding Plant', address: '1800 W 12th St', city: 'Erie', state: 'PA', lat: 42.1170, lon: -80.1070, tiv_prior: 31_000_000, tiv_current: 32_300_000, occupancy: 'Plastics — injection molding', construction: 'Non-combustible (ISO 3)', year_built: 1994, stories: 1, sqft: 158_000, roof_year: 2018, sprinkler: 'Wet pipe, full', valuation_ratio: 0.92, aal: 4_100 }),
  ];
  const base = claimsFor({ id, locations, findings: [], seed: 909, premium: 520_000 } as unknown as AccountSpec);
  const claims: ClaimsEngineering = {
    ...base,
    claims: [{ claim_id: 'CLM-9K2041', location_uid: 'key-l1', location_label: 'Loc 1 · Allentown PA', date_of_loss: '2026-03-18', cause: 'Fire', cat_event: null, status: 'OPEN', paid: 910_000, reserve: 490_000, incurred: 1_400_000, description: 'Dust deflagration in compounding line 2 ductwork; 11 days BI', linked_recommendation: 'R-088' }, ...base.claims],
    recommendations: [
      { rec_id: 'R-088', location_uid: 'key-l1', location_label: 'Loc 1 · Allentown PA', raised: '2025-03-04', category: 'Combustible dust', description: 'Install explosion isolation + spark detection on compounding line dust collection (NFPA 660)', severity: 'CRITICAL', due: '2025-09-30', status: 'CLOSED', bind_condition: true, days_overdue: 0, completion_evidence: null, doc_id: `${id}-eng` },
      { rec_id: 'R-091', location_uid: 'key-l2', location_label: 'Loc 2 · Erie PA', raised: '2025-03-06', category: 'Housekeeping', description: 'Dust housekeeping program — weekly high-level cleaning', severity: 'MEDIUM', due: '2025-06-30', status: 'VERIFIED_CLOSED', bind_condition: false, days_overdue: 0, completion_evidence: 'Program document + engineer visit 2025-07-02', doc_id: null },
    ],
  };
  claims.summary = { ...claims.summary, count_5y: claims.claims.length, incurred_5y: claims.claims.reduce((a, c) => a + c.incurred, 0), loss_ratio_5y: claims.claims.reduce((a, c) => a + c.incurred, 0) / (520_000 * 5), by_cause: [{ cause: 'Fire', count: 1 + claims.claims.filter((c, i) => i > 0 && c.cause === 'Fire').length, incurred: 1_400_000 + claims.claims.filter((c, i) => i > 0 && c.cause === 'Fire').reduce((a, c) => a + c.incurred, 0) }, ...base.summary.by_cause.filter((b) => b.cause !== 'Fire')] };
  return {
    id, name: 'Keystone Plastics', scenario: 'S9', scenario_title: 'Engineering commitment broken — linked $1.4M claim', segment: 'Middle market', occupancy_family: 'Manufacturing', state: 'PA',
    broker: 'Marsh', broker_contact: 'Paul Sorensen (Marsh, Philadelphia)', underwriter_id: 'u_tom', tenure_years: 4, expiry: '2026-09-30', status: 'ACTION_REQUIRED', pass: 2, actions: ['CONDITION', 'REPRICE', 'REFER'], confidence: 'HIGH',
    missing: ['Completion evidence for R-088 (commissioning certificate, photos)'],
    admitted: true, notice_days: 60, premium: 520_000, limit: 88_000_000, layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: 'NGP-2025-00841', locations, seed: 909, claims,
    findings: [
      fnd({ finding_id: 'f-key-rec', account_id: id, subject_type: 'recommendation', subject_id: 'R-088', subject_label: 'R-088 · Allentown', title: 'Bind-condition recommendation R-088 marked "closed" without evidence', family: 'engineering', rule_id: 'ENG.REC.UNVERIFIED_CLOSE', rule_version: 1, severity: 'CRITICAL', outcome: 'CONDITION', observed: 'Status CLOSED 2025-09-28 by insured portal; no evidence attached', expected: 'VERIFIED_CLOSED with engineer sign-off for bind conditions', impact_usd: 88_000, confidence: 0.97, source: 'Catalogue §45 · Risk Engineering Standards §3.4', critique: up }),
      fnd({ finding_id: 'f-key-claim', account_id: id, subject_type: 'claim', subject_id: 'CLM-9K2041', subject_label: 'CLM-9K2041', title: '$1.4M dust fire on the same line as R-088', family: 'claims', rule_id: 'CLM.LINK.REC', severity: 'HIGH', outcome: 'REFER', observed: 'CLM-9K2041 2026-03-18, compounding line 2, $1.4M incurred', expected: 'No loss attributable to open bind condition', impact_usd: 112_000, impact_method: 'experience mod', confidence: 0.95, source: 'Property UW Guidelines 2026 §5.3', critique: up }),
      fnd({ finding_id: 'f-key-rarc', account_id: id, title: 'Proposed renewal +6% still 11% below technical after loss', family: 'pricing', rule_id: 'PRC.ADEQ.FLOOR', severity: 'HIGH', outcome: 'PRICE_ADJUST', observed: 'Adequacy 89%', expected: '≥ 95% floor', impact_usd: 61_000, confidence: 0.9, critique: up }),
    ],
    rarc: rarcBase({ p0: 520_000, ef: 1.036, p1: 551_000, adequacy: 0.89, tiv0: 85e6, tiv1: 88.2e6 }),
  };
})();

// ------------------------------------------------------------------ S10
const S10: AccountSpec = (() => {
  const id = 'acc-deltascrap';
  const locations = [
    loc({ location_uid: 'dsm-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Baton Rouge Yard & Shredder', address: '3900 Plank Rd', city: 'Baton Rouge', state: 'LA', lat: 30.4830, lon: -91.1660, tiv_prior: 26_000_000, tiv_current: 26_800_000, occupancy: 'Scrap metal processing', construction: 'Non-combustible (ISO 3)', year_built: 1979, stories: 1, sqft: 84_000, roof_year: 2009, sprinkler: 'None (yard); partial (office)', valuation_ratio: 0.85, wind_tier: 'T2', aal: 38_000, flags: [{ code: 'APPETITE', label: 'Out of appetite (2026)', severity: 'CRITICAL', finding_id: 'f-dsm-app' }] }),
    loc({ location_uid: 'dsm-l2', loc_no_prior: '2', loc_no_current: '2', name: 'Lake Charles Yard', address: '2400 Broad St', city: 'Lake Charles', state: 'LA', lat: 30.2266, lon: -93.2174, tiv_prior: 14_000_000, tiv_current: 14_200_000, occupancy: 'Scrap metal processing', construction: 'Metal clad (ISO 3)', year_built: 1991, stories: 1, sqft: 41_000, roof_year: 2021, sprinkler: 'None', valuation_ratio: 0.88, wind_tier: 'T1', aal: 29_000, flags: [{ code: 'APPETITE', label: 'Out of appetite (2026)', severity: 'CRITICAL', finding_id: 'f-dsm-app' }] }),
  ];
  return {
    id, name: 'Delta Scrap Metals', scenario: 'S10', scenario_title: 'Appetite change + non-renewal notice deadline', segment: 'Middle market', occupancy_family: 'Recycling', state: 'LA',
    broker: 'Amwins', broker_contact: 'Luis Ortega (Amwins, New Orleans)', underwriter_id: 'u_maya', tenure_years: 6, expiry: '2026-11-15', status: 'ACTION_REQUIRED', pass: 1, actions: ['NON_RENEW', 'CONDITIONAL_RENEWAL_NOTICE', 'REFER'], confidence: 'HIGH', missing: [],
    admitted: true, notice_days: 90, premium: 214_000, limit: 41_000_000, layer: 'Primary', share: 1, limit_basis: 'scheduled', policy_no: 'NGP-2025-01702', locations, seed: 1010,
    findings: [
      fnd({ finding_id: 'f-dsm-app', account_id: id, title: 'Scrap & recycling moved to DECLINE in guidelines v2026', family: 'appetite', rule_id: 'APP.CLASS.DECLINE', rule_version: 3, severity: 'CRITICAL', outcome: 'DECLINE', observed: 'Occupancy class 3089 (scrap metal processing)', expected: 'Class in appetite under current rule version', impact_usd: 214_000, impact_method: 'premium at stake (control exposure)', confidence: 1, pass: 1, created_at: '2026-07-01', source: 'Property UW Guidelines 2026 Appendix A (Appetite), p.72', critique: up }),
      fnd({ finding_id: 'f-dsm-notice', account_id: id, title: 'Louisiana non-renewal notice must be mailed by 17 Aug 2026', family: 'authority', rule_id: 'NOTICE.LATEST_DATE', severity: 'HIGH', outcome: 'BLOCK', observed: 'Admitted LA policy; 90-day notice window (demo table)', expected: 'Notice issued before latest valid date — else renew on expiring terms', impact_usd: 0, impact_method: 'control', confidence: 1, pass: 1, created_at: '2026-07-01', source: 'Demo notice table v1 — illustrative, verify with counsel', critique: up }),
    ],
    rarc: rarcBase({ p0: 214_000, ef: 1.022, p1: 214_000, adequacy: 0.84, tiv0: 40e6, tiv1: 41e6, wind: true, ns: 0.05 }),
  };
})();

// ------------------------------------------------------------------ S11
const S11: AccountSpec = (() => {
  const id = 'acc-summit';
  const R = rng(1111);
  const names = ['Hall', 'Library', 'Science Center', 'Residence Hall', 'Athletic Center', 'Dining Commons', 'Arts Building', 'Engineering Lab', 'Student Union', 'Chapel', 'Admin Building', 'Power Plant'];
  const locations: LocationRow[] = [];
  for (let i = 0; i < 41; i++) {
    const tp = round(between(R, 8e6, 58e6), 100_000), tc = round(tp * between(R, 1.02, 1.07), 100_000);
    const base = loc({ location_uid: `sum-l${i + 1}`, loc_no_prior: `B-${String(i + 1).padStart(2, '0')}`, loc_no_current: String(101 + i), name: `${pick(R, ['Whitman', 'Carver', 'Lowell', 'Hastings', 'Pierce', 'Ames', 'Morrow', 'Dunn', 'Ellery', 'Frost'])} ${names[i % names.length]}`, address: `${100 + i * 12} Campus Dr`, city: 'Ithaca', state: 'NY',
      lat: 42.4470 + between(R, -0.006, 0.006), lon: -76.4830 + between(R, -0.009, 0.009), match_method: 'geocode + name fuzzy (loc no renumbered)', match_score: +between(R, 0.9, 0.99).toFixed(2),
      tiv_prior: tp, tiv_current: tc, occupancy: i % 4 === 3 ? 'Dormitory' : 'Educational', construction: pick(R, ['Masonry non-combustible (ISO 4)', 'Fire resistive (ISO 6)', 'Joisted masonry (ISO 2)']), year_built: int(R, 1892, 2018), stories: int(R, 2, 7), sqft: round(tc / 320, 100), roof_year: int(R, 2002, 2023), valuation_ratio: +between(R, 0.82, 1.0).toFixed(2), aal: round(tc * between(R, 0.00004, 0.00016), 100) });
    locations.push(base);
  }
  [6, 19, 33].forEach((i, j) => { Object.assign(locations[i], { match_status: 'AMBIGUOUS', match_score: [0.71, 0.66, 0.62][j], match_method: 'geocode ± 40 m, name partial', flags: [{ code: 'MATCH_REVIEW', label: 'Match needs human confirmation', severity: 'MEDIUM', finding_id: 'f-sum-amb' }] }); });
  Object.assign(locations[13], { match_status: 'MERGED', loc_no_prior: 'B-14 + B-15', loc_no_current: '114', name: 'Hastings Science Center (renovated, merged)', match_method: 'footprint overlap 0.91 (renovation)', match_score: 0.91, tiv_prior: 21_400_000 + 17_800_000, tiv_current: 44_600_000 });
  Object.assign(locations[40], { match_status: 'NEW', loc_no_prior: null, loc_no_current: '141', name: 'Innovation Hub (new build)', match_method: null, match_score: null, tiv_prior: null, tiv_current: 36_000_000, year_built: 2026, flags: [{ code: 'NEW', label: 'New building', severity: 'LOW' }] });
  locations.forEach((l) => { l.tiv_change_pct = l.tiv_prior && l.tiv_current ? l.tiv_current / l.tiv_prior - 1 : null; });
  const top5 = [...locations].sort((a, b) => (b.aal ?? 0) - (a.aal ?? 0)).slice(0, 5);
  top5.forEach((l) => l.flags.push({ code: 'SECONDARY_MODS', label: 'Secondary modifiers missing', severity: 'MEDIUM', finding_id: 'f-sum-mods' }));
  const tiv0 = locations.reduce((a, l) => a + (l.tiv_prior ?? 0), 0), tiv1 = locations.reduce((a, l) => a + (l.tiv_current ?? 0), 0);
  return {
    id, name: 'Summit University', scenario: 'S11', scenario_title: 'Location matching & data quality', segment: 'Large', occupancy_family: 'Education', state: 'NY',
    broker: 'Aon', broker_contact: 'Meera Shah (Aon, New York)', underwriter_id: 'u_aisha', tenure_years: 12, expiry: '2026-12-01', status: 'IN_REVIEW', pass: 2, actions: ['DATA_REQUEST'], confidence: 'MEDIUM',
    missing: ['Roof cover & anchorage for 5 highest-AAL buildings', 'Basement / first-floor height for 5 highest-AAL buildings'],
    admitted: true, notice_days: 60, premium: 1_120_000, limit: 750_000_000, layer: 'Primary loss limit $750M', share: 1, limit_basis: 'loss_limit', policy_no: 'NGP-2025-02210', locations, seed: 1111,
    site_model_doc_id: `${id}-glb-campus`,
    findings: [
      fnd({ finding_id: 'f-sum-amb', account_id: id, title: '3 location matches proposed — human confirmation required', family: 'data_quality', rule_id: 'DQ.MATCH.AMBIGUOUS', severity: 'MEDIUM', outcome: 'DATA_REQUEST', observed: '36 auto-matched · 3 proposed (score 0.62–0.71) · 1 merged · 1 new', expected: 'All locations matched with score ≥ 0.85 or confirmed', impact_usd: 7_000, confidence: 0.9, critique: up }),
      fnd({ finding_id: 'f-sum-mods', account_id: id, title: 'Secondary modifiers missing on 5 highest-AAL buildings', family: 'cat_data', rule_id: 'CAT.INPUT.SECONDARY_MODS', severity: 'MEDIUM', outcome: 'DATA_REQUEST', observed: 'Roof cover, anchorage, first-floor height blank', expected: 'Populated where building AAL in top decile', impact_usd: 14_000, impact_method: 'AAL uncertainty band', confidence: 0.85, critique: up }),
      fnd({ finding_id: 'f-sum-scale', account_id: id, title: 'SOV values in $000s and totals row — normalised', family: 'data_quality', rule_id: 'DQ.SOV.SCALE', severity: 'LOW', outcome: 'FLAG', observed: 'Header "Bldg Value ($000s)"; row 45 TOTAL', expected: 'Values in USD; no totals rows', impact_usd: 0, confidence: 0.99, critique: up }),
    ],
    rarc: rarcBase({ p0: 1_120_000, ef: 1.041, p1: 1_176_000, adequacy: 1.02, tiv0, tiv1 }),
  };
})();

// ------------------------------------------------------------------ S12
const S12: AccountSpec = (() => {
  const id = 'acc-meridian';
  const locations = [
    loc({ location_uid: 'mer-l1', loc_no_prior: '1', loc_no_current: '1', name: 'Ashburn Campus A (IAD-1/2)', address: '21701 Filigree Ct', city: 'Ashburn', state: 'VA', lat: 39.0160, lon: -77.4590, tiv_prior: 360_000_000, tiv_current: 372_000_000, occupancy: 'Data center — Tier III', construction: 'Fire resistive (ISO 6)', year_built: 2015, stories: 2, sqft: 420_000, roof_year: 2015, sprinkler: 'Pre-action, double interlock', valuation_ratio: 0.97, cat_zone: 'Northern Virginia', aal: 38_000 }),
    loc({ location_uid: 'mer-l2', loc_no_prior: '2', loc_no_current: '2', name: 'Ashburn Campus B (IAD-3)', address: '44480 Hastings Dr', city: 'Ashburn', state: 'VA', lat: 39.0290, lon: -77.4800, tiv_prior: 290_000_000, tiv_current: 301_000_000, occupancy: 'Data center — Tier III', construction: 'Fire resistive (ISO 6)', year_built: 2018, stories: 2, sqft: 330_000, roof_year: 2018, sprinkler: 'Pre-action, double interlock', valuation_ratio: 0.98, cat_zone: 'Northern Virginia', aal: 29_000 }),
    loc({ location_uid: 'mer-l3', loc_no_prior: '3', loc_no_current: '3', name: 'Manassas MNZ-1', address: '10900 Wakeman Dr', city: 'Manassas', state: 'VA', lat: 38.7510, lon: -77.4750, tiv_prior: 240_000_000, tiv_current: 246_000_000, occupancy: 'Data center — Tier III', construction: 'Fire resistive (ISO 6)', year_built: 2020, stories: 1, sqft: 280_000, roof_year: 2020, sprinkler: 'Pre-action', valuation_ratio: 0.96, cat_zone: 'Northern Virginia', aal: 22_000 }),
    loc({ location_uid: 'mer-l4', loc_no_prior: '4', loc_no_current: '4', name: 'Sterling STL-2', address: '45845 Nokes Blvd', city: 'Sterling', state: 'VA', lat: 39.0060, lon: -77.4290, tiv_prior: 176_000_000, tiv_current: 181_000_000, occupancy: 'Data center — Tier III', construction: 'Fire resistive (ISO 6)', year_built: 2012, stories: 2, sqft: 210_000, roof_year: 2012, sprinkler: 'Pre-action', valuation_ratio: 0.95, cat_zone: 'Northern Virginia', aal: 17_000 }),
  ];
  return {
    id, name: 'Meridian Data Centers', scenario: 'S12', scenario_title: 'Shared layer — 25% of $100M xs $50M', segment: 'Large', occupancy_family: 'Data center', state: 'VA',
    broker: 'WTW', broker_contact: 'Sofia Lindqvist (WTW, New York)', underwriter_id: 'u_daniel', tenure_years: 5, expiry: '2026-12-15', status: 'FAST_TRACK', pass: 2, actions: ['MAINTAIN'], confidence: 'HIGH', missing: [],
    admitted: false, notice_days: null, premium: 482_000, limit: 100_000_000, layer: '$100M xs $50M (of $250M loss limit)', share: 0.25, limit_basis: 'loss_limit', policy_no: 'NGX-2025-00412', locations, seed: 1212,
    findings: [fnd({ finding_id: 'f-mer-zone', account_id: id, title: 'Northern Virginia zone at 64% — portfolio note, no action', family: 'portfolio', severity: 'LOW', outcome: 'FLAG', observed: 'Carrier-share PML $41M in zone after renewal', expected: '≤ 80% utilisation', impact_usd: 0, confidence: 0.9, critique: up })],
    rarc: rarcBase({ p0: 482_000, ef: 1.028, p1: 499_000, adequacy: 1.03, tiv0: 1_066e6, tiv1: 1_100e6 }),
  };
})();

export const HERO_SPECS: AccountSpec[] = [S1, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12];

export function buildHeroes(): AccountBundle[] {
  return HERO_SPECS.map((s) => {
    const b = buildBundle(s);
    if (s.id === 'acc-redline') {
      b.detail.documents.push(
        doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-redline-glb-memphis', doc_type: '3D site model', title: '3D model — Memphis DC-1 racking vs sprinkler design plane', filename: 'redline_memphis_dc1.glb', format: 'glb', received_at: '2026-07-24', source_channel: 'Vendor (mock)', size_bytes: 2_800_000 }),
        doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-redline-img-2024', doc_type: 'Aerial imagery', title: 'Aerial — Memphis DC-1 · 2024-09', filename: 'redline_memphis_2024-09.png', format: 'png', received_at: '2024-09-30', source_channel: 'Vendor (mock)' }),
        doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-redline-img-2026', doc_type: 'Aerial imagery', title: 'Aerial — Memphis DC-1 · 2026-06 (new racking, trailer yard)', filename: 'redline_memphis_2026-06.png', format: 'png', received_at: '2026-06-28', source_channel: 'Vendor (mock)' }),
      );
    }
    if (s.id === 'acc-pinecrest') {
      b.detail.documents.push(
        doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-pinecrest-img-2025', doc_type: 'Aerial imagery', title: 'Aerial — Pinecrest Plaza · 2025-10', filename: 'pinecrest_2025-10.png', format: 'png', received_at: '2025-10-15', source_channel: 'Vendor (mock)' }),
        doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-pinecrest-img-2026', doc_type: 'Aerial imagery', title: 'Aerial — Pinecrest Plaza · 2026-06 (empty lot)', filename: 'pinecrest_2026-06.png', format: 'png', received_at: '2026-06-02', source_channel: 'Vendor (mock)' }),
      );
    }
    if (s.id === 'acc-summit') {
      b.detail.documents.push(doc({ account_id: s.id, account_name: s.name, doc_id: 'acc-summit-glb-campus', doc_type: '3D site model', title: '3D campus model — 41 buildings', filename: 'summit_campus.glb', format: 'glb', received_at: '2026-08-01', source_channel: 'Vendor (mock)', size_bytes: 6_100_000 }));
    }
    if (s.id === 'acc-aurelia') b.detail.timeline = [
      ev('aur-t6', '2026-01-31', 'engine', '15', 'Subjectivity ageing breach', 'Generator load test still open 30 days after bind', 'Renewal engine', { finding_ids: ['f-aur-subj'] }),
      ev('aur-t5', '2026-01-10', 'engine', '15', 'Pass 3 · contract integrity', 'Binder vs issued policy: NS minimum lost; CP 04 11 dropped', 'Renewal engine', { finding_ids: ['f-aur-min', 'f-aur-safe'], doc_id: 'acc-aurelia-dec' }),
      ev('aur-t4', '2026-01-09', 'mock', '11', 'Policy issued NGP-2026-00003', 'PAS (mock) with issuance-error injection', 'PAS (mock)', { doc_id: 'acc-aurelia-dec' }),
      ev('aur-t3', '2025-12-31', 'engine', '07', 'Approval invalidated', 'Bound terms hash c41e08b5 ≠ approved 9f3a17c2 — AOP $250K → $100K', 'Authority engine', { finding_ids: ['f-aur-auth'] }),
      ev('aur-t2', '2025-12-19', 'user', '08', 'Quote v3 created', 'AOP deductible $250K → $100K at broker request', 'Daniel Okafor', { doc_id: 'acc-aurelia-quote-v3' }),
      ev('aur-t1', '2025-12-15', 'user', '07', 'Quote v2 approved', 'Priya Raman approved at $1.35M, AOP $250K — hash 9f3a17c2', 'Priya Raman', { doc_id: 'acc-aurelia-quote-v2' }),
    ];
    else if (!s.timeline) b.detail.timeline = timelineFor(s);
    return b;
  });
}
