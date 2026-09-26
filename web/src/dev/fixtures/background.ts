// 108 seeded background accounts so the book totals match the blueprint:
// 120 renewals · 640 locations · $9.2B TIV · $48M premium · 55 fast-track · 48 material · 17 not started.
import type { ActionType, Finding, LocationRow, RenewalStatus, Severity } from '@/api/types';
import { buildBundle, type AccountSpec } from './builders';
import { rarcBase } from './heroes';
import type { AccountBundle } from './model';
import { computeRarc } from './model';
import { addDays, between, fnd, int, loc, pick, rng, round, shuffleInPlace } from './util';

const PLACES = ['Ridgeway', 'Bayshore', 'Granite Peak', 'Cobalt', 'Lakeside', 'Ironbridge', 'Westfield', 'Tidewater', 'Copperline', 'Northstar', 'Sable Creek', 'Blue Heron', 'Pioneer', 'Canyon Ridge', 'Everly', 'Harrow', 'Maple Grove', 'Atlas', 'Oakhurst', 'Silverline', 'Brightwater', 'Cedar Point', 'Falcon', 'Glenmore', 'Hawthorne', 'Juniper', 'Kingsbridge', 'Larkspur', 'Millbrook', 'Newport', 'Orchard Hill', 'Prairie', 'Quarry', 'Riverside', 'Stonegate', 'Thornbury', 'Union', 'Vantage', 'Willow', 'Zephyr', 'Ashford', 'Beacon', 'Clearwater', 'Driftwood', 'Emberly', 'Fairhaven', 'Greystone', 'Highland', 'Keel', 'Lighthouse', 'Meadowbrook', 'Northfield', 'Oakridge', 'Palisade', 'Redstone', 'Summitview', 'Tallgrass', 'Evergreen'];
const FAMILIES: { family: string; words: string[]; occ: string; cons: string; seg: AccountSpec['segment'][] }[] = [
  { family: 'Manufacturing', words: ['Precision Machining', 'Metal Works', 'Components', 'Fabrication', 'Packaging', 'Industries'], occ: 'Light manufacturing', cons: 'Non-combustible (ISO 3)', seg: ['Middle market', 'Middle market', 'Large'] },
  { family: 'Warehouse', words: ['Distribution', 'Logistics', 'Cold Storage', 'Self Storage'], occ: 'Warehouse — general commodities', cons: 'Tilt-up concrete (ISO 5)', seg: ['Middle market', 'Large'] },
  { family: 'Office', words: ['Office Partners', 'Office Trust', 'Tower Holdings'], occ: 'Office — multi-tenant', cons: 'Fire resistive (ISO 6)', seg: ['Middle market', 'Large'] },
  { family: 'Habitational', words: ['Apartments', 'Senior Living', 'Residential'], occ: 'Apartments — garden style', cons: 'Frame (ISO 1)', seg: ['Middle market', 'E&S'] },
  { family: 'Retail', words: ['Shopping Center', 'Retail Partners', 'Grocers'], occ: 'Retail — strip centre', cons: 'Masonry non-combustible (ISO 4)', seg: ['Middle market'] },
  { family: 'Hospitality', words: ['Hospitality', 'Hotels', 'Resorts'], occ: 'Hotel — select service', cons: 'Masonry non-combustible (ISO 4)', seg: ['Middle market', 'E&S'] },
  { family: 'Healthcare', words: ['Medical Office', 'Surgical Partners', 'Health'], occ: 'Medical office', cons: 'Fire resistive (ISO 6)', seg: ['Middle market', 'Large'] },
  { family: 'Food processing', words: ['Foods', 'Bakeries', 'Beverage Co.'], occ: 'Food processing', cons: 'Non-combustible (ISO 3)', seg: ['Middle market'] },
];
const SUFFIX = ['LLC', 'Inc.', 'Holdings', 'Group', 'Co.', 'Partners'];
type City = [string, string, number, number, boolean];
const CITIES: City[] = [
  ['Tampa', 'FL', 27.9506, -82.4572, true], ['St. Petersburg', 'FL', 27.7676, -82.6403, true], ['Miami', 'FL', 25.7617, -80.1918, true], ['Orlando', 'FL', 28.5383, -81.3792, true], ['Jacksonville', 'FL', 30.3322, -81.6557, true],
  ['Houston', 'TX', 29.7604, -95.3698, true], ['Corpus Christi', 'TX', 27.8006, -97.3964, true], ['Dallas', 'TX', 32.7767, -96.797, false], ['San Antonio', 'TX', 29.4241, -98.4936, false],
  ['New Orleans', 'LA', 29.9511, -90.0715, true], ['Charleston', 'SC', 32.7765, -79.9311, true], ['Savannah', 'GA', 32.0809, -81.0912, true], ['Atlanta', 'GA', 33.749, -84.388, false],
  ['Charlotte', 'NC', 35.2271, -80.8431, false], ['Raleigh', 'NC', 35.7796, -78.6382, false], ['Nashville', 'TN', 36.1627, -86.7816, false], ['Memphis', 'TN', 35.1495, -90.049, false],
  ['Chicago', 'IL', 41.8781, -87.6298, false], ['Columbus', 'OH', 39.9612, -82.9988, false], ['Cleveland', 'OH', 41.4993, -81.6944, false], ['Pittsburgh', 'PA', 40.4406, -79.9959, false], ['Philadelphia', 'PA', 39.9526, -75.1652, false],
  ['Newark', 'NJ', 40.7357, -74.1724, false], ['Boston', 'MA', 42.3601, -71.0589, false], ['Richmond', 'VA', 37.5407, -77.436, false], ['Phoenix', 'AZ', 33.4484, -112.074, false], ['Denver', 'CO', 39.7392, -104.9903, false],
  ['Los Angeles', 'CA', 34.0522, -118.2437, false], ['San Jose', 'CA', 37.3382, -121.8863, false], ['Sacramento', 'CA', 38.5816, -121.4944, false], ['Seattle', 'WA', 47.6062, -122.3321, false], ['Minneapolis', 'MN', 44.9778, -93.265, false],
  ['St. Louis', 'MO', 38.627, -90.1994, false], ['Kansas City', 'MO', 39.0997, -94.5786, false], ['Indianapolis', 'IN', 39.7684, -86.1581, false], ['Detroit', 'MI', 42.3314, -83.0458, false],
];
const BROKERS: [string, string][] = [['Marsh', 'Marsh'], ['Aon', 'Aon'], ['WTW', 'WTW'], ['Gallagher', 'Gallagher'], ['Lockton', 'Lockton'], ['Brown & Brown', 'Brown & Brown'], ['USI', 'USI'], ['Alliant', 'Alliant'], ['Amwins', 'Amwins'], ['CRC Group', 'CRC']];
const CONTACTS = ['Alex Rivera', 'Jordan Lee', 'Sam Whitaker', 'Priya Nair', 'Chris Donovan', 'Taylor Brooks', 'Morgan Price', 'Casey Nguyen', 'Riley Bennett', 'Jamie Foster'];

interface Tmpl { family: string; sev: Severity; outcome: Finding['outcome']; title: (c: Ctx) => string; observed: (c: Ctx) => string; expected: string; impact: [number, number]; action: ActionType }
interface Ctx { r: () => number; loc: LocationRow; n: number; wind: boolean }
const TEMPLATES: Tmpl[] = [
  { family: 'pricing', sev: 'HIGH', outcome: 'PRICE_ADJUST', title: () => 'Like-for-like RARC below −5% band', observed: (c) => `RARC −${(5 + c.r() * 8).toFixed(1)}% on computed split`, expected: 'RARC ≥ −5% within L1', impact: [14e3, 48e3], action: 'REPRICE' },
  { family: 'pricing', sev: 'MEDIUM', outcome: 'FLAG', title: () => 'Proposed premium below technical', observed: (c) => `Adequacy ${(88 + c.r() * 10).toFixed(1)}%`, expected: 'Adequacy ≥ 100% for L1', impact: [6e3, 30e3], action: 'REPRICE' },
  { family: 'valuation', sev: 'HIGH', outcome: 'PRICE_ADJUST', title: (c) => `Loc ${c.n} insured at ${Math.round(66 + c.r() * 12)}% of model RC`, observed: (c) => `Reported $${Math.round(110 + c.r() * 50)}/sq ft vs model $${Math.round(190 + c.r() * 60)}`, expected: 'Reported ≥ 80% of model RC', impact: [12e3, 60e3], action: 'REPRICE' },
  { family: 'valuation', sev: 'MEDIUM', outcome: 'FLAG', title: () => 'Building values flat 3 years vs +5.1%/yr cost trend', observed: () => 'Identical building values on 3 consecutive SOVs', expected: 'Values trended by cost index', impact: [4e3, 18e3], action: 'DATA_REQUEST' },
  { family: 'cat_terms', sev: 'HIGH', outcome: 'TERM_BREACH', title: () => 'Named-storm deductible 2% below 3% floor (Tier-1 wind)', observed: () => '2% per location', expected: '≥ 3% per location', impact: [8e3, 26e3], action: 'RESTRUCTURE' },
  { family: 'engineering', sev: 'MEDIUM', outcome: 'CONDITION', title: (c) => `Recommendation R-${300 + Math.floor(c.r() * 400)} overdue ${Math.floor(30 + c.r() * 150)} days`, observed: () => 'Status OPEN · no completion evidence', expected: 'Closed with evidence by due date', impact: [2e3, 9e3], action: 'CONDITION' },
  { family: 'claims', sev: 'MEDIUM', outcome: 'FLAG', title: (c) => `${2 + Math.floor(c.r() * 3)} losses since bind — repeat cause`, observed: () => 'Same cause, same building within 12 months', expected: 'No repeat cause within 12 months', impact: [5e3, 22e3], action: 'REPRICE' },
  { family: 'cat_data', sev: 'MEDIUM', outcome: 'DATA_REQUEST', title: (c) => `Year built / construction missing at ${2 + Math.floor(c.r() * 4)} locations — CAT model defaulted`, observed: () => 'Blank fields on SOV; model used regional defaults', expected: 'Primary modifiers complete for all locations', impact: [3e3, 12e3], action: 'DATA_REQUEST' },
  { family: 'occupancy', sev: 'HIGH', outcome: 'CONDITION', title: (c) => `Occupancy changed at Loc ${c.n}`, observed: () => 'SOV occupancy differs from rated class', expected: 'Occupancy matches rated class', impact: [8e3, 30e3], action: 'CONDITION' },
  { family: 'data_quality', sev: 'LOW', outcome: 'DATA_REQUEST', title: () => 'Secondary modifiers missing on highest-AAL locations', observed: () => 'Roof cover / anchorage blank', expected: 'Populated where AAL in top decile', impact: [1e3, 6e3], action: 'DATA_REQUEST' },
  { family: 'contract_integrity', sev: 'HIGH', outcome: 'TERM_BREACH', title: () => 'Binder vs issued policy — flood sublimit mismatch', observed: () => 'Binder $5M · policy $10M', expected: 'Issued policy = binder', impact: [6e3, 20e3], action: 'ENDORSEMENT_CORRECTION' },
  { family: 'safeguards', sev: 'MEDIUM', outcome: 'CONDITION', title: () => 'Protective safeguard relied on — no current inspection certificate', observed: () => 'Last sprinkler inspection > 12 months', expected: 'Annual NFPA 25 inspection on file', impact: [3e3, 12e3], action: 'CONDITION' },
  { family: 'portfolio', sev: 'MEDIUM', outcome: 'REFER', title: () => 'Contributes to a zone above 85% utilisation', observed: () => 'Zone PML share increase on renewal', expected: 'Zone ≤ 85% without referral', impact: [4e3, 14e3], action: 'REFER' },
];

export function buildBackground(heroTotals: { tiv: number; premium: number; locations: number; rarcW: number; premW: number }): AccountBundle[] {
  const R = rng(20260801);
  const N = 108;
  const statuses: RenewalStatus[] = [...Array(53).fill('FAST_TRACK'), ...Array(17).fill('NOT_STARTED'), ...Array(24).fill('ACTION_REQUIRED'), ...Array(8).fill('IN_REVIEW'), ...Array(4).fill('REFERRED'), ...Array(2).fill('QUOTED')];
  shuffleInPlace(R, statuses);
  // Location counts to reach 640 total.
  const target = 640 - heroTotals.locations;
  const counts = Array.from({ length: N }, () => int(R, 1, 9));
  let diff = target - counts.reduce((a, b) => a + b, 0);
  for (let i = 0; diff !== 0; i = (i + 1) % N) { if (diff > 0 && counts[i] < 12) { counts[i]++; diff--; } else if (diff < 0 && counts[i] > 1) { counts[i]--; diff++; } }
  const used = new Set<string>();
  const raw = Array.from({ length: N }, (_, i) => {
    const r = rng(9000 + i * 17);
    const fam = pick(r, FAMILIES);
    let name = '';
    do { name = `${pick(r, PLACES)} ${pick(r, fam.words)}${r() < 0.35 ? ' ' + pick(r, SUFFIX) : ''}`; } while (used.has(name));
    used.add(name);
    const home = i < 2 ? CITIES[i] : pick(r, CITIES);
    return { i, r, fam, name, home, tiv: Math.exp(between(r, Math.log(8e6), Math.log(160e6))), rol: between(r, 0.0035, 0.011) * (home[4] ? 1.6 : 1) };
  });
  const tivScale = (9.2e9 - heroTotals.tiv) / raw.reduce((a, x) => a + x.tiv, 0);
  const premRaw = raw.map((x) => x.tiv * tivScale * x.rol);
  const premScale = (48e6 - heroTotals.premium) / premRaw.reduce((a, b) => a + b, 0);

  // Sample RARC targets, then shift so the premium-weighted book RARC lands at −1.1%.
  const rarcT = raw.map((x, i) => {
    const st = statuses[i];
    if (st === 'NOT_STARTED') return null;
    return st === 'FAST_TRACK' ? between(x.r, -0.01, 0.05) : between(x.r, -0.13, 0.02);
  });
  const prem = premRaw.map((p) => round(p * premScale, 1000));
  const bgW = rarcT.reduce<number>((a, t, i) => a + (t ?? 0) * prem[i], 0), bgP = rarcT.reduce<number>((a, t, i) => a + (t === null ? 0 : prem[i]), 0);
  const shift = (-0.011 * (heroTotals.premW + bgP) - heroTotals.rarcW - bgW) / bgP;

  return raw.map((x, i) => {
    const { r, fam, name, home } = x;
    const st = statuses[i];
    const id = `acc-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+$/, '')}`;
    const tiv0 = round(x.tiv * tivScale, 100_000);
    const growth = st === 'FAST_TRACK' ? between(r, 0.02, 0.06) : between(r, -0.02, 0.18);
    const n = counts[i];
    const weights = Array.from({ length: n }, () => between(r, 0.4, 1.6));
    const wsum = weights.reduce((a, b) => a + b, 0);
    const locations: LocationRow[] = weights.map((w, j) => {
      const c = j === 0 ? home : r() < 0.7 ? home : pick(r, CITIES);
      const tp = round(tiv0 * w / wsum, 100_000), tc = round(tp * (1 + growth + between(r, -0.02, 0.02)), 100_000);
      const vr = st === 'FAST_TRACK' ? between(r, 0.86, 1.02) : between(r, 0.7, 1.0);
      return loc({ location_uid: `${id}-l${j + 1}`, loc_no_prior: String(j + 1), loc_no_current: String(j + 1), name: `${name.split(' ')[0]} ${fam.family === 'Office' ? 'Center' : fam.family === 'Habitational' ? 'Residences' : 'Site'} ${j + 1}`,
        address: `${int(r, 100, 9900)} ${pick(r, ['Commerce', 'Industrial', 'Main', 'Market', 'Parkway', 'Enterprise', 'Harbor', 'Lakeview', 'Oak', 'Pine'])} ${pick(r, ['Dr', 'Blvd', 'St', 'Ave', 'Way'])}`,
        city: c[0], state: c[1], lat: c[2] + between(r, -0.08, 0.08), lon: c[3] + between(r, -0.08, 0.08), match_score: +between(r, 0.92, 0.995).toFixed(3),
        tiv_prior: tp, tiv_current: tc, occupancy: fam.occ, construction: fam.cons, year_built: int(r, 1962, 2019), stories: int(r, 1, 6), sqft: round(tp / 260, 100),
        roof_year: r() < 0.08 ? null : int(r, 2004, 2023), sprinkler: r() < 0.85 ? 'Wet pipe, full' : 'None', valuation_ratio: +vr.toFixed(2),
        wind_tier: c[4] ? (r() < 0.6 ? 'T1' : 'T2') : null, cat_zone: c[4] ? `${c[0]} wind` : null, aal: round(tc * (c[4] ? between(r, 0.0006, 0.0018) : between(r, 0.00006, 0.0003)), 100) });
    });
    const wind = locations.some((l) => l.wind_tier === 'T1' || l.wind_tier === 'T2');
    const findings: Finding[] = [];
    let actions: ActionType[] = ['MAINTAIN'];
    const pass = st === 'NOT_STARTED' ? 0 : (st === 'FAST_TRACK' ? (r() < 0.5 ? 1 : 2) : r() < 0.25 ? 1 : 2) as 0 | 1 | 2;
    if (st !== 'NOT_STARTED' && st !== 'FAST_TRACK') {
      const k = int(r, 2, 6);
      const pool = TEMPLATES.filter((t) => (t.family === 'cat_terms' ? wind : true));
      const chosen = new Set<Tmpl>();
      chosen.add(pool[0]);
      while (chosen.size < k) chosen.add(pick(r, pool));
      [...chosen].forEach((t, j) => {
        const l = pick(r, locations);
        const ctx: Ctx = { r, loc: l, n: +(l.loc_no_current ?? 1), wind };
        const impact = round(between(r, t.impact[0], t.impact[1]), 100);
        findings.push(fnd({ finding_id: `f-${id.slice(4, 16)}-${j}`, account_id: id, subject_type: t.family === 'valuation' || t.family === 'occupancy' ? 'location' : 'account', subject_id: t.family === 'valuation' || t.family === 'occupancy' ? l.location_uid : id, subject_label: t.family === 'valuation' || t.family === 'occupancy' ? `Loc ${l.loc_no_current} · ${l.city} ${l.state}` : name,
          title: t.title(ctx), family: t.family, severity: t.sev, outcome: t.outcome, observed: t.observed(ctx), expected: t.expected, impact_usd: impact, confidence: +between(r, 0.72, 0.97).toFixed(2), rule_id: `${t.family.toUpperCase().slice(0, 4)}.${t.outcome}`, pass: pass === 1 ? 1 : 2, created_at: addDays('2026-08-01', -int(r, 1, 40)),
          critique: r() < 0.9 ? { verdict: 'UPHELD', note: 'Evidence consistent across sources.' } : { verdict: 'CHALLENGED', note: 'Single source; confidence below 0.8.' } }));
        if (t.family === 'occupancy') { l.occupancy_prior = l.occupancy; l.occupancy = pick(r, ['Warehouse — plastics storage', 'Light manufacturing — woodworking', 'Vacant (partial)', 'Commercial cooking']); l.flags.push({ code: 'OCC_DRIFT', label: 'Occupancy drift', severity: 'HIGH', finding_id: findings[findings.length - 1].finding_id }); }
        if (t.family === 'valuation' && t.sev === 'HIGH') { l.valuation_ratio = +between(r, 0.66, 0.78).toFixed(2); l.flags.push({ code: 'UNDERVALUED', label: `Under-valued: ${Math.round(l.valuation_ratio * 100)}% of model RC`, severity: 'HIGH', finding_id: findings[findings.length - 1].finding_id }); }
      });
      actions = [...new Set([...chosen].map((t) => t.action))];
      if (st === 'REFERRED' && !actions.includes('REFER')) actions.push('REFER');
    } else if (st === 'FAST_TRACK' && r() < 0.3) {
      findings.push(fnd({ finding_id: `f-${id.slice(4, 16)}-0`, account_id: id, title: 'Roof year blank at 1 location', family: 'data_quality', severity: 'LOW', outcome: 'DATA_REQUEST', observed: 'Roof year empty', expected: 'Populated', impact_usd: round(between(r, 400, 2400), 100), confidence: 0.8 }));
    }
    const premium = prem[i];
    const t = rarcT[i] === null ? null : rarcT[i]! + shift;
    const ef = Math.pow(1 + growth, 0.92);
    const ade = st === 'FAST_TRACK' ? between(r, 1.0, 1.12) : st === 'NOT_STARTED' ? 1 : between(r, 0.86, 1.02);
    const tiv1 = locations.reduce((a, l) => a + (l.tiv_current ?? 0), 0);
    const [bk, bkShort] = pick(r, BROKERS);
    const tom = findings.some((f) => f.family === 'pricing') && r() < 0.62;
    const uw = tom ? 'u_tom' : pick(r, ['u_maya', 'u_daniel', 'u_aisha', 'u_tom', 'u_daniel', 'u_maya']);
    const month = st === 'NOT_STARTED' ? pick(r, ['2027-01']) : pick(r, ['2026-09', '2026-10', '2026-10', '2026-11', '2026-11', '2026-12']);
    const expiry = `${month}-${String(pick(r, [1, 1, 1, 15, 15])).padStart(2, '0')}`;
    const segment = pick(r, fam.seg);
    const spec: AccountSpec = {
      id, name, scenario: null, scenario_title: null, segment, occupancy_family: fam.family, state: home[1],
      broker: bk, broker_contact: `${pick(r, CONTACTS)} (${bkShort}, ${home[0]})`, underwriter_id: uw, tenure_years: int(r, 1, 14),
      expiry, status: st, pass, actions: st === 'NOT_STARTED' ? [] : actions, confidence: st === 'FAST_TRACK' ? 'HIGH' : pick(r, ['MEDIUM', 'HIGH']),
      missing: findings.some((f) => f.outcome === 'DATA_REQUEST') ? ['Secondary modifiers for top-AAL locations'] : [],
      admitted: segment !== 'E&S', notice_days: segment === 'E&S' ? null : pick(r, [30, 45, 60, 60, 90]),
      premium, limit: round(tiv1 * 1.0, 1e6), layer: 'Primary blanket', share: 1, limit_basis: 'blanket', policy_no: `NGP-2025-0${2300 + i * 7}`,
      locations, findings, seed: 5000 + i,
      rarc: t === null ? null : rarcBase({ p0: premium, ef, p1: round(premium * ef * (1 + t), 100), adequacy: ade, tiv0, tiv1, wind, ns: wind ? (findings.some((f) => f.family === 'cat_terms') ? 0.02 : 0.03) : null }),
    };
    return buildBundle(spec);
  });
}

export function heroRarcWeight(bundles: AccountBundle[]) {
  let rarcW = 0, premW = 0;
  for (const b of bundles) if (b.rarc) { rarcW += computeRarc(b.detail.account_id, b.rarc).rarc * b.premium_expiring; premW += b.premium_expiring; }
  return { rarcW, premW };
}
