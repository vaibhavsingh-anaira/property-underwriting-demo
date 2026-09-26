// In-memory fixture store. Every mutation updates state so screens visibly react.
import type * as T from '@/api/types';
import { buildS2 } from './fixtures/heroS2';
import { buildHeroes } from './fixtures/heroes';
import { buildBackground, heroRarcWeight } from './fixtures/background';
import { computeRarc, type AccountBundle } from './fixtures/model';
import { FAMILY_LABEL, integrityScore, nextTerm } from './fixtures/builders';
import { HAZARDS, MOCK_SYSTEMS, NOTICE_TABLE_YAML, PIPELINE, REFERENCE_DOCS, RULES, ZONES } from './fixtures/reference';
import { USERS, userName } from './fixtures/users';
import { addDays, CLOCK0, daysBetween, hash, k, rng, pick, between } from './fixtures/util';

export class HttpError extends Error { status: number; constructor(status: number, msg: string) { super(msg); this.status = status; } }

interface ScriptEvent { date: string; account_id: string | null; title: string; detail: string; stage: string; kind: T.TimelineEvent['kind']; apply?: (db: Db) => number }
interface Db {
  clock: string;
  bundles: Map<string, AccountBundle>;
  order: string[];
  quotes: Map<string, T.QuoteVersion[]>;
  referrals: T.Referral[];
  outbox: T.OutboxMessage[];
  rules: T.Rule[];
  pipe: { identified: number; validated: number; approved: number; corrected: number };
  injections: Record<string, boolean>;
  script: ScriptEvent[];
  applied: number;
  review: T.DataQualitySummary['review_queue'];
  seq: number;
}

let db: Db;

// ------------------------------------------------------------------ init
function init(): Db {
  const s2 = buildS2();
  const heroes = [s2, ...buildHeroes()];
  const locs = heroes.reduce((a, b) => a + b.detail.locations.length, 0);
  const { rarcW, premW } = heroRarcWeight(heroes);
  const bg = buildBackground({ tiv: heroes.reduce((a, b) => a + b.tiv_current, 0), premium: heroes.reduce((a, b) => a + b.premium_expiring, 0), locations: locs, rarcW, premW });
  const all = [...heroes, ...bg];
  const bundles = new Map(all.map((b) => [b.detail.account_id, b]));
  const quotes = new Map<string, T.QuoteVersion[]>();
  quotes.set('acc-abc', s2.contract.quotes);
  const aurT = bundles.get('acc-aurelia')!.rarc!;
  quotes.set('acc-aurelia', [
    { quote_id: 'q-aur-v1', version: 1, term: '2026–2027', created_at: '2025-12-02', created_by: 'Daniel Okafor', premium: 1_410_000, terms: { ...aurT.expiring_terms, aop_deductible: 250_000 }, status: 'SUPERSEDED', terms_hash: '5b21e7d4', doc_id: null, rarc: 0.012, adequacy: 1.01 },
    { quote_id: 'q-aur-v2', version: 2, term: '2026–2027', created_at: '2025-12-12', created_by: 'Daniel Okafor', premium: 1_350_000, terms: { ...aurT.expiring_terms, aop_deductible: 250_000 }, status: 'SUPERSEDED', terms_hash: '9f3a17c2', doc_id: 'acc-aurelia-quote-v2', rarc: -0.031, adequacy: 0.99 },
    { quote_id: 'q-aur-v3', version: 3, term: '2026–2027', created_at: '2025-12-19', created_by: 'Daniel Okafor', premium: 1_350_000, terms: aurT.expiring_terms, status: 'BOUND', terms_hash: 'c41e08b5', doc_id: 'acc-aurelia-quote-v3', rarc: -0.058, adequacy: 0.97 },
  ]);
  for (const b of all) {
    const id = b.detail.account_id;
    if (!quotes.has(id)) {
      const t = b.rarc?.expiring_terms;
      const prior = termOf(b.detail.renewal.expiry);
      quotes.set(id, t ? [{ quote_id: `q-${id}-p3`, version: 3, term: prior, created_at: addDays(b.detail.renewal.expiry, -380), created_by: b.detail.underwriter, premium: b.premium_expiring, terms: t, status: 'BOUND', terms_hash: hash(id + 'prior').slice(0, 8), doc_id: `${id}-quote-prior`, rarc: null, adequacy: null }] : []);
    }
  }
  const memo = (lines: string[]) => lines.join('\n\n');
  const referrals: T.Referral[] = [
    { referral_id: 'ref-pine', account_id: 'acc-pinecrest', account_name: 'Pinecrest Plaza', quote_id: null, terms_hash: null, requested_by: 'Aisha Patel', requested_at: '2026-06-08', required_level: 3, reasons: ['VAC.FIRE.SPRINKLER_OFF — vacant 62% + sprinkler impaired (CRITICAL)', 'Mid-term: event-driven, not at renewal'],
      memo: memo(['**Mid-term fire referral — Pinecrest Plaza.** Anchor tenant vacated 1 Apr; the centre is 62% vacant [F:f-pine-vac]. On 7 Jun the main riser was closed and the sprinkler system is impaired [F:f-pine-fire].', 'Proposed: require fire watch and impairment restoration within 10 days; issue vacancy permit endorsement with a vacancy deductible; re-inspect before renewal.']),
      status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null },
    { referral_id: 'ref-aur-v2', account_id: 'acc-aurelia', account_name: 'St. Aurelia Medical Center', quote_id: 'q-aur-v2', terms_hash: '9f3a17c2', requested_by: 'Daniel Okafor', requested_at: '2025-12-12', required_level: 3, reasons: ['Limit $540M above L2 authority ($250M)', 'Healthcare — senior review'],
      memo: memo(['**St. Aurelia Medical Center — 2026 renewal at $1.35M.** AOP deductible $250K, named storm 5% / $250K min.', 'Adequacy 99% of technical; RARC −3.1%.']),
      status: 'INVALIDATED', approver: 'Priya Raman', decided_at: '2025-12-15', conditions: 'Generator load test report before bind', invalidated_reason: 'Terms changed after approval — quote v3 AOP deductible $250K → $100K (hash 9f3a17c2 → c41e08b5)' },
    { referral_id: 'ref-aur-v3', account_id: 'acc-aurelia', account_name: 'St. Aurelia Medical Center', quote_id: 'q-aur-v3', terms_hash: 'c41e08b5', requested_by: 'Daniel Okafor', requested_at: '2026-01-10', required_level: 3, reasons: ['Bound terms differ from approved terms (AUTH.APPROVAL.TERMS_HASH)', 'Endorsement correction required: NS minimum, CP 04 11'],
      memo: memo(['**Re-approval required.** The approval on quote v2 is invalid because v3 reduced the AOP deductible to $100K after sign-off [F:f-aur-auth].', 'At issuance the $250K named-storm minimum was lost [F:f-aur-min] and CP 04 11 was dropped for Bldg 2 [F:f-aur-safe]. The generator load-test subjectivity is 212 days open [F:f-aur-subj].', 'Proposed: ratify $100K AOP with +$38K premium, correct NS minimum and CP 04 11 by endorsement, 30-day cure on the subjectivity.']),
      status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null },
    { referral_id: 'ref-lumen', account_id: 'acc-lumen', account_name: 'Lumen Jewelers', quote_id: null, terms_hash: null, requested_by: 'Aisha Patel', requested_at: '2026-07-30', required_level: 3, reasons: ['SEC.CRIME.SCORE — burglary 92nd pct at 5 stores', 'Protective safeguard P-3 not verified at 3 stores'],
      memo: memo(['**Security referral — Lumen Jewelers.** Three stores rely on the P-3 central-station alarm safeguard, but certificates show local-bell alarms only [F:f-lumen-alarm]. Five stores sit in the 92nd+ burglary percentile [F:f-lumen-burg].', 'Proposed: condition renewal on UL 2050 certificates within 30 days; theft deductible $25K at the five high-score stores.']),
      status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null },
    { referral_id: 'ref-dsm', account_id: 'acc-deltascrap', account_name: 'Delta Scrap Metals', quote_id: null, terms_hash: null, requested_by: 'Maya Chen', requested_at: '2026-07-29', required_level: 4, reasons: ['APP.CLASS.DECLINE — scrap & recycling out of appetite (v2026)', 'Exception to appetite requires CUO'],
      memo: memo(['**Appetite exception request — Delta Scrap Metals.** Guidelines v2026 move scrap metal processing to decline [F:f-dsm-app]. Louisiana non-renewal notice must be mailed by 17 Aug [F:f-dsm-notice].', 'Options: (a) non-renew now; (b) conditional renewal with shredder fire suppression and 5% wind at Lake Charles; (c) one-term exception.']),
      status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null },
  ];
  // Background referred accounts get a pending referral each.
  for (const b of bg.filter((x) => x.detail.renewal.status === 'REFERRED')) {
    const f = b.detail.findings.filter((x) => x.material).slice(0, 2);
    referrals.push({ referral_id: `ref-${b.detail.account_id.slice(4)}`, account_id: b.detail.account_id, account_name: b.detail.name, quote_id: null, terms_hash: null, requested_by: b.detail.underwriter, requested_at: addDays(CLOCK0, -3), required_level: 3, reasons: f.map((x) => x.title),
      memo: `**Referral — ${b.detail.name}.** ${f.map((x) => `${x.title} [F:${x.finding_id}]`).join('. ')}.`, status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null });
  }
  referrals.push({ referral_id: 'ref-hist-1', account_id: bg[5].detail.account_id, account_name: bg[5].detail.name, quote_id: null, terms_hash: 'a1c93e20', requested_by: 'Tom Brennan', requested_at: '2026-07-18', required_level: 3, reasons: ['Adequacy below 95% floor'], memo: 'Adequacy 93%; long-tenured account; broker committed to values update next term.', status: 'APPROVED', approver: 'Priya Raman', decided_at: '2026-07-19', conditions: 'Values update at next renewal', invalidated_reason: null });
  referrals.push({ referral_id: 'ref-hist-2', account_id: bg[9].detail.account_id, account_name: bg[9].detail.name, quote_id: null, terms_hash: '77be01f3', requested_by: 'Daniel Okafor', requested_at: '2026-07-11', required_level: 3, reasons: ['RARC −12.4% beyond L2 band'], memo: 'Broker requests flat renewal against a +6% exposure increase.', status: 'DECLINED', approver: 'Priya Raman', decided_at: '2026-07-12', conditions: null, invalidated_reason: null });

  const outbox: T.OutboxMessage[] = [
    { message_id: 'ob-1', at: '2026-07-31T09:14:00Z', channel: 'email', to: 'grant.ellis@lockton.example', subject: 'Harborview Hotels — data request for 10/10 renewal', body: 'Please provide: (1) a current appraisal (last on file 2021-04-12); (2) verified building square footage per hotel. Values have been flat for three years against a +5.1%/yr construction-cost trend.', account_id: 'acc-harborview', related: 'f-harbor-appr' },
    { message_id: 'ob-2', at: '2026-07-30T15:02:00Z', channel: 'in_app', to: 'Robert Hale (CUO)', subject: 'Referral L4 — Delta Scrap Metals appetite exception', body: 'Maya Chen requests an appetite exception. Latest LA non-renewal notice date: 2026-08-17 (16 days).', account_id: 'acc-deltascrap', related: 'ref-dsm' },
    { message_id: 'ob-3', at: '2026-07-30T08:00:00Z', channel: 'email', to: 'maya.chen@northgate-specialty.example', subject: 'Notice deadline alert — Delta Scrap Metals (16 days)', body: 'Latest valid non-renewal notice date is 17 Aug 2026 (Demo notice table v1 — illustrative, verify with counsel).', account_id: 'acc-deltascrap', related: 'f-dsm-notice' },
    { message_id: 'ob-4', at: '2026-07-30T11:20:00Z', channel: 'in_app', to: 'Priya Raman (Senior UW)', subject: 'Referral L3 — Lumen Jewelers security', body: 'Aisha Patel referred Lumen Jewelers: 3 stores with local-only alarms under a P-3 safeguard.', account_id: 'acc-lumen', related: 'ref-lumen' },
    { message_id: 'ob-5', at: '2026-07-29T10:05:00Z', channel: 'broker_portal', to: 'Aon — Meera Shah', subject: 'Summit University — secondary modifiers for 5 buildings', body: 'Roof cover, roof anchorage and first-floor height for buildings 108, 112, 114, 121, 133 (highest modelled loss).', account_id: 'acc-summit', related: 'f-sum-mods' },
    { message_id: 'ob-6', at: '2026-06-08T14:40:00Z', channel: 'in_app', to: 'Priya Raman (Senior UW)', subject: 'CRITICAL referral — Pinecrest Plaza vacancy + impairment', body: 'VAC.FIRE.SPRINKLER_OFF fired mid-term. Fire watch required.', account_id: 'acc-pinecrest', related: 'ref-pine' },
  ];

  const summit = bundles.get('acc-summit')!;
  const amb = summit.detail.locations.filter((l) => l.match_status === 'AMBIGUOUS');
  const review: T.DataQualitySummary['review_queue'] = [
    ...amb.map((l, i) => ({ item_id: `rv-sum-${i}`, account_id: 'acc-summit', account_name: 'Summit University', kind: 'LOCATION_MATCH' as const, label: `Bldg ${l.loc_no_current} ${l.name} ↔ prior ${l.loc_no_prior}`, detail: `Match score ${l.match_score?.toFixed(2)} · ${l.match_method}. Renumbered SOV; address differs by building suffix.`, options: [`${l.loc_no_prior} (score ${l.match_score?.toFixed(2)})`, `B-${String(+(l.loc_no_prior ?? 'B-1').slice(2) + 1).padStart(2, '0')} (score ${((l.match_score ?? 0.6) - 0.09).toFixed(2)})`, 'No match — treat as NEW'] })),
    { item_id: 'rv-sum-map', account_id: 'acc-summit', account_name: 'Summit University', kind: 'MAPPING', label: 'Header "Bldg Val ($000s)" → building_value × 1,000', detail: 'Scale inferred from header text and value range (8,000–58,000). Totals row 45 excluded.', options: ['Confirm × 1,000', 'Values already in USD'] },
    { item_id: 'rv-abc-l5', account_id: 'acc-abc', account_name: 'ABC Manufacturing', kind: 'LOW_CONFIDENCE', label: 'Loc 5 construction "Unknown" (confidence 0.31)', detail: 'SOV cell G8 blank; imagery suggests tilt-up concrete (0.58). Requested from broker.', options: ['Tilt-up concrete (ISO 5)', 'Keep unknown — data request'] },
    { item_id: 'rv-harbor-sqft', account_id: 'acc-harborview', account_name: 'Harborview Hotels', kind: 'LOW_CONFIDENCE', label: 'Hilton Head sq ft 61,200 vs assessor 94,800', detail: 'SOV value may exclude conference wing; drives $/sq ft valuation test.', options: ['Use assessor 94,800', 'Keep SOV 61,200'] },
  ];
  const script: ScriptEvent[] = [
    { date: '2026-08-04', account_id: 'acc-harborview', stage: '01', kind: 'document', title: 'Broker reply: 2026 appraisal uploaded', detail: 'Lockton uploaded appraisal (Marshall & Swift) — building RC $118.4M', apply: (d) => { resolve(d, 'acc-harborview', 'f-harbor-appr'); return 0; } },
    { date: '2026-08-06', account_id: 'acc-abc', stage: '12', kind: 'mock', title: 'Reserve change CLM-7B0C22', detail: 'Reserve reduced $51K → $34K', apply: () => 0 },
    { date: '2026-08-10', account_id: 'acc-redline', stage: '05', kind: 'mock', title: 'Survey report received — Memphis DC-1', detail: 'Top-of-storage 28 ft confirmed; ESFR designed for 20 ft', apply: () => 0 },
    { date: '2026-08-12', account_id: 'acc-pinecrest', stage: '12', kind: 'mock', title: 'Sprinkler impairment restored', detail: 'Riser valve reopened; contractor certificate received', apply: () => 0 },
    { date: '2026-08-17', account_id: 'acc-deltascrap', stage: '15', kind: 'engine', title: 'Non-renewal notice deadline reached', detail: 'Latest valid LA notice date — renew-as-expiring exposure if not sent', apply: (d) => { const b = d.bundles.get('acc-deltascrap')!; if (!d.outbox.some((o) => o.account_id === 'acc-deltascrap' && o.subject.startsWith('Notice'))) addFinding(b, { finding_id: 'f-dsm-missed', title: 'Notice deadline passed — must renew on expiring terms', family: 'authority', severity: 'CRITICAL', outcome: 'BLOCK', observed: 'No notice issued by 2026-08-17', expected: 'Notice before latest valid date', impact_usd: 214_000 }); return 1; } },
    { date: '2026-08-24', account_id: null, stage: '10', kind: 'mock', title: '7 fast-track renewals bound', detail: 'Maintain on expiring terms + trend; booked premium +$85K', apply: (d) => { let n = 0; for (const b of d.bundles.values()) if (n < 7 && b.detail.renewal.status === 'FAST_TRACK' && !b.detail.scenario) { b.detail.renewal.status = 'BOUND'; n++; } d.pipe.corrected += 85_000; return 0; } },
    { date: '2026-09-10', account_id: 'acc-crestline', stage: '11', kind: 'mock', title: 'Crestline Office REIT renewal issued', detail: 'Pass 3 clean — quote, binder and policy match', apply: (d) => { d.bundles.get('acc-crestline')!.detail.renewal.status = 'ISSUED'; d.pipe.corrected += 24_000; return 0; } },
    { date: '2026-09-15', account_id: null, stage: '14', kind: 'engine', title: 'Book RARC refresh', detail: 'Corrected dollars recognised on 14 bound renewals', apply: (d) => { d.pipe.corrected += 141_000; return 0; } },
  ];
  return {
    clock: CLOCK0, bundles, order: all.map((b) => b.detail.account_id), quotes, referrals, outbox, rules: structuredClone(RULES),
    pipe: { identified: 3_100_000, validated: 2_400_000, approved: 1_900_000, corrected: 1_350_000 },
    injections: { issuance_error: true, broker_autoreply: true, stale_certificate: false, rater_timeout: false },
    script, applied: 0, review, seq: 100,
  };
}

export function reset() { db = init(); return demoState(); }
function D() { if (!db) db = init(); return db; }

const termOf = (expiry: string) => { const y = +expiry.slice(0, 4); return `${y - 1}–${y}`; };
const me = (uid: string) => USERS.find((u) => u.user_id === uid) ?? USERS[0];
const bundle = (id: string) => { const b = D().bundles.get(id); if (!b) throw new HttpError(404, `Account ${id} not found`); return b; };
const nid = (p: string) => `${p}-${++D().seq}`;

function resolve(d: Db, acc: string, fid: string) {
  const f = d.bundles.get(acc)?.detail.findings.find((x) => x.finding_id === fid);
  if (f) { f.status = 'RESOLVED'; }
}
function addFinding(b: AccountBundle, p: Partial<T.Finding> & Pick<T.Finding, 'finding_id' | 'title' | 'family' | 'severity' | 'observed' | 'expected' | 'impact_usd' | 'outcome'>): T.Finding {
  const f: T.Finding = {
    account_id: b.detail.account_id, subject_type: 'contract', subject_id: b.detail.policy.policy_id, subject_label: b.detail.policy.policy_no, rule_id: 'CTR.RUNTIME', rule_version: 1, description: '',
    impact_method: 'contract_check', confidence: 0.98, materiality_score: p.impact_usd, material: p.impact_usd >= 5000, evidence_obs_ids: [], conflicting_obs_ids: [], status: 'OPEN', disposition: null, pass: 3,
    created_at: D().clock, critique: null, source: 'Standard library — contract integrity', ...p,
  };
  b.detail.findings.push(f);
  D().pipe.identified += f.material ? f.impact_usd : 0;
  return f;
}
function tl(b: AccountBundle, stage: string, kind: T.TimelineEvent['kind'], title: string, detail: string, actor: string, extra: Partial<T.TimelineEvent> = {}) {
  b.detail.timeline.unshift({ event_id: nid('ev'), date: D().clock, kind, stage, title, detail, actor, ...extra });
}

// ------------------------------------------------------------------ derived views
function rarcOf(b: AccountBundle) { return b.rarc ? computeRarc(b.detail.account_id, b.rarc) : null; }
function refreshDetail(b: AccountBundle): T.AccountDetail {
  const d = b.detail;
  d.renewal.days_to_expiry = daysBetween(D().clock, d.renewal.expiry);
  d.renewal.integrity_score = integrityScore(d.findings);
  if (d.renewal.notice.latest_notice_date) d.renewal.notice.days_remaining = daysBetween(D().clock, d.renewal.notice.latest_notice_date);
  d.actions.forEach((a) => { a.impact_usd = d.findings.filter((f) => a.finding_ids.includes(f.finding_id) && f.status !== 'REJECTED').reduce((s, f) => s + f.impact_usd, 0); });
  return d;
}
const SEV_RANK: Record<T.Severity, number> = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };
export function queueItem(b: AccountBundle): T.RenewalQueueItem {
  const d = refreshDetail(b);
  const open = d.findings.filter((f) => f.status === 'OPEN' || f.status === 'DEFERRED');
  const mat = open.filter((f) => f.material);
  const r = rarcOf(b);
  const gaps = d.locations.filter((l) => !l.roof_year || !l.year_built || l.construction === 'Unknown').length + d.renewal.missing.length;
  return {
    account_id: d.account_id, name: d.name, scenario: d.scenario, segment: d.segment as T.RenewalQueueItem['segment'], occupancy_family: d.occupancy_family, state: d.state,
    broker: d.broker, underwriter: d.underwriter, underwriter_id: d.underwriter_id, expiry: d.renewal.expiry, days_to_expiry: d.renewal.days_to_expiry,
    notice_deadline: d.renewal.notice.latest_notice_date, days_to_notice: d.renewal.notice.days_remaining, status: d.renewal.status, pass: d.renewal.pass,
    recommended_actions: d.renewal.recommended_actions, impact_usd: mat.reduce((a, f) => a + f.impact_usd, 0),
    materiality: mat.reduce<T.Severity>((a, f) => (SEV_RANK[f.severity] > SEV_RANK[a] ? f.severity : a), 'LOW'),
    integrity_score: d.renewal.integrity_score, finding_count: open.length, families: [...new Set(mat.map((f) => f.family))],
    top_findings: [...open].sort((a, c) => c.impact_usd - a.impact_usd).slice(0, 3).map((f) => ({ finding_id: f.finding_id, title: f.title, severity: f.severity, impact_usd: f.impact_usd })),
    tiv_expiring: b.tiv_expiring, tiv_current: b.tiv_current, premium_expiring: b.premium_expiring,
    rarc: r?.rarc ?? null, adequacy: r?.adequacy ?? null, data_gaps: gaps, locations: d.locations.filter((l) => l.match_status !== 'DELETED').length,
  };
}

export function renewals(q: URLSearchParams): T.RenewalQueueItem[] {
  let items = D().order.map((id) => queueItem(D().bundles.get(id)!));
  const st = q.get('status'), uw = q.get('uw'), s = q.get('q')?.toLowerCase();
  if (st) items = items.filter((i) => i.status === st);
  if (uw) items = items.filter((i) => i.underwriter_id === uw);
  if (s) items = items.filter((i) => i.name.toLowerCase().includes(s) || i.broker.toLowerCase().includes(s));
  const rank = (i: T.RenewalQueueItem) => (i.impact_usd + 1) / Math.max(7, i.days_to_notice ?? i.days_to_expiry - 30);
  return items.sort((a, b) => rank(b) - rank(a));
}

export function account(id: string): T.AccountDetail {
  const b = bundle(id);
  return refreshDetail(b);
}

export function rarc(id: string, body?: T.RarcWhatIfRequest): T.RarcResult {
  const b = bundle(id);
  if (!b.rarc) throw new HttpError(409, 'Pricing not yet run — Pass 1 has not reached this renewal');
  return body ? computeRarc(id, b.rarc, body.proposed_premium, body.terms, body.brokerage) : computeRarc(id, b.rarc);
}

export function contract(id: string): T.ContractDiff {
  const b = bundle(id);
  return { ...b.contract, quotes: [...(D().quotes.get(id) ?? [])].sort((a, c) => c.version - a.version + (c.term > a.term ? 100 : c.term < a.term ? -100 : 0)), referrals: D().referrals.filter((r) => r.account_id === id) };
}

// ------------------------------------------------------------------ book
export function book(): T.BookSummary {
  const all = D().order.map((id) => D().bundles.get(id)!);
  const items = all.map(queueItem);
  const withR = all.map((b) => ({ b, r: rarcOf(b) })).filter((x) => x.r);
  const premR = withR.reduce((a, x) => a + x.b.premium_expiring, 0);
  const rarcComputed = withR.reduce((a, x) => a + x.r!.rarc * x.b.premium_expiring, 0) / premR;
  const buckets: [string, number, number][] = [['< 85%', 0, 0.85], ['85–90%', 0.85, 0.9], ['90–95%', 0.9, 0.95], ['95–100%', 0.95, 1], ['100–105%', 1, 1.05], ['105–110%', 1.05, 1.1], ['≥ 110%', 1.1, 9]];
  const adequacy_hist = buckets.map(([bucket, lo, hi]) => { const xs = withR.filter((x) => x.r!.adequacy >= lo && x.r!.adequacy < hi); return { bucket, count: xs.length, premium: xs.reduce((a, x) => a + x.b.premium_expiring, 0) }; });
  const fam = new Map<string, { count: number; impact_usd: number }>();
  const act = new Map<T.ActionType, { count: number; impact_usd: number }>();
  for (const b of all) {
    for (const f of b.detail.findings) if ((f.status === 'OPEN' || f.status === 'DEFERRED') && f.material) { const x = fam.get(f.family) ?? { count: 0, impact_usd: 0 }; x.count++; x.impact_usd += f.impact_usd; fam.set(f.family, x); }
    const qi = items.find((i) => i.account_id === b.detail.account_id)!;
    for (const a of b.detail.renewal.recommended_actions) { const x = act.get(a) ?? { count: 0, impact_usd: 0 }; x.count++; x.impact_usd += qi.impact_usd; act.set(a, x); }
  }
  const uws = USERS.filter((u) => u.role === 'UNDERWRITER');
  const by_underwriter = uws.map((u) => {
    const mine = all.filter((b) => b.detail.underwriter_id === u.user_id);
    const qs = items.filter((i) => i.underwriter_id === u.user_id);
    const rs = mine.map(rarcOf).filter((r): r is T.RarcResult => !!r);
    return { user_id: u.user_id, name: u.name, accounts: mine.length, findings: qs.reduce((a, i) => a + i.finding_count, 0), impact_usd: qs.reduce((a, i) => a + i.impact_usd, 0),
      pricing_deviations: rs.filter((r) => r.rarc < -0.05 || r.adequacy < 0.95).length, avg_rarc: rs.length ? rs.reduce((a, r) => a + r.rarc, 0) / rs.length : 0 };
  });
  const brokers = [...new Set(all.map((b) => b.detail.broker))];
  const by_broker = brokers.map((br) => {
    const mine = all.filter((b) => b.detail.broker === br);
    const rs = mine.map(rarcOf).filter((r): r is T.RarcResult => !!r);
    return { broker: br, accounts: mine.length, premium: mine.reduce((a, b) => a + b.premium_expiring, 0), impact_usd: items.filter((i) => i.broker === br).reduce((a, i) => a + i.impact_usd, 0), avg_rarc: rs.length ? rs.reduce((a, r) => a + r.rarc, 0) / rs.length : 0 };
  }).sort((a, b) => b.premium - a.premium);
  const months = [...new Set(items.map((i) => i.expiry.slice(0, 7)))].sort();
  const by_month = months.map((mo) => { const xs = items.filter((i) => i.expiry.startsWith(mo)); return { month: mo, renewals: xs.length, premium: xs.reduce((a, i) => a + i.premium_expiring, 0), fast_track: xs.filter((i) => i.recommended_actions.length === 1 && i.recommended_actions[0] === 'MAINTAIN').length, action: xs.filter((i) => !(i.recommended_actions.length === 1 && i.recommended_actions[0] === 'MAINTAIN')).length }; });
  return {
    as_of: D().clock, carrier: 'Northgate Specialty Insurance Co.', renewals: items.length, locations: items.reduce((a, i) => a + i.locations, 0),
    tiv: items.reduce((a, i) => a + i.tiv_current, 0), premium_expiring: items.reduce((a, i) => a + i.premium_expiring, 0),
    fast_track: items.filter((i) => i.status === 'FAST_TRACK').length,
    material_action: items.filter((i) => ['ACTION_REQUIRED', 'IN_REVIEW', 'REFERRED'].includes(i.status) || (i.status === 'QUOTED' && !i.recommended_actions.includes('MAINTAIN'))).length,
    not_started: items.filter((i) => i.status === 'NOT_STARTED').length,
    pipeline: { ...D().pipe }, rarc_reported: 0.042, rarc_computed: rarcComputed, adequacy_hist,
    by_family: [...fam.entries()].map(([family, v]) => ({ family, label: FAMILY_LABEL[family] ?? family, ...v })).sort((a, b) => b.impact_usd - a.impact_usd),
    by_action: [...act.entries()].map(([action, v]) => ({ action, ...v })).sort((a, b) => b.count - a.count),
    by_underwriter, by_broker, by_month, accumulation: accumulation(),
  };
}

const hav = (a: number, b: number, c: number, d: number) => { const R = 6371, t = Math.PI / 180; const x = Math.sin(((c - a) * t) / 2) ** 2 + Math.cos(a * t) * Math.cos(c * t) * Math.sin(((d - b) * t) / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };
export function accumulation(): T.AccumulationZone[] {
  return ZONES.map((z) => {
    const accounts: T.AccumulationZone['accounts'] = [];
    for (const b of D().bundles.values()) {
      let c = 0;
      for (const l of b.detail.locations) {
        if (l.match_status === 'DELETED') continue;
        if (hav(z.lat, z.lon, l.lat, l.lon) > z.radius_km) continue;
        const f = z.peril === 'Named storm' ? (l.wind_tier === 'T1' ? 0.16 : l.wind_tier === 'T2' ? 0.1 : 0.05) : z.peril === 'Earthquake' ? 0.11 : 0.04;
        c += (l.tiv_current ?? l.tiv_prior ?? 0) * b.detail.policy.carrier_share * f;
      }
      if (c > 0) accounts.push({ account_id: b.detail.account_id, name: b.detail.name, contribution: Math.round(c) });
    }
    accounts.sort((a, b) => b.contribution - a.contribution);
    return { ...z, utilization: z.post_renewal / z.threshold, accounts };
  });
}

// ------------------------------------------------------------------ evidence
const POLICIES: Record<string, [string, string]> = {
  roof_year: ['roof_year.v3', 'Engineering (V) > permit (S) > imagery (M) > SOV (C)'],
  occupancy: ['occupancy.v2', 'Engineering (V) unless a more recent specific broker/insured statement (C) exists; SOV carry-forward lowest'],
  tiv: ['tiv.v1', 'Most recent SOV (C); appraisal (V) overrides; totals rows excluded'],
  construction: ['construction.v2', 'Engineering (V) > vendor (M) > SOV (C)'],
  bi_sublimit: ['contract.issued_wins', 'Issued policy (S) is the contract of record; binder retained as comparison'],
};
function allObs() { const out: T.Observation[] = []; for (const b of D().bundles.values()) out.push(...b.observations); return out; }
function fieldFor(o: T.Observation, pool: T.Observation[]): T.ResolvedField {
  const obs = pool.filter((x) => x.subject_id === o.subject_id && x.field_code === o.field_code);
  const win = obs.find((x) => x.is_resolved) ?? obs[0];
  const [policy, explainer] = POLICIES[o.field_code] ?? [`${o.field_code}.v1`, 'Highest verification level, then most recent'];
  const distinct = new Set(obs.map((x) => String(x.value)));
  return { field_code: o.field_code, label: o.field_label, value: win.value, value_display: win.value_display, resolved_obs_id: win.obs_id, policy, policy_explainer: explainer, conflict: distinct.size > 1, observations: obs };
}
export function observation(id: string): T.ObservationDetail {
  const pool = allObs();
  const o = pool.find((x) => x.obs_id === id);
  if (!o) throw new HttpError(404, `Observation ${id} not found`);
  return { observation: o, field: fieldFor(o, pool), document: o.anchor?.doc_id ? documentMeta(o.anchor.doc_id, false) : null };
}
export function fields(accountId: string, subject?: string | null): T.ResolvedField[] {
  const pool = bundle(accountId).observations.filter((o) => !subject || o.subject_id === subject);
  const seen = new Set<string>(); const out: T.ResolvedField[] = [];
  for (const o of pool) { const key = o.subject_id + '|' + o.field_code; if (seen.has(key)) continue; seen.add(key); out.push(fieldFor(o, pool)); }
  return out;
}

// ------------------------------------------------------------------ documents
function allDocs(): T.DocumentMeta[] { const out = [...REFERENCE_DOCS]; for (const id of D().order) out.push(...D().bundles.get(id)!.detail.documents); return out; }
export function documents(q: URLSearchParams): T.DocumentMeta[] {
  let ds = allDocs();
  const a = q.get('account_id'), t = q.get('type'), f = q.get('format'), s = q.get('q')?.toLowerCase();
  if (a) ds = ds.filter((d) => d.account_id === a);
  if (t) ds = ds.filter((d) => d.doc_type === t);
  if (f) ds = ds.filter((d) => d.format === f);
  if (s) ds = ds.filter((d) => d.title.toLowerCase().includes(s) || d.filename.toLowerCase().includes(s) || (d.account_name ?? '').toLowerCase().includes(s));
  return ds;
}
export function documentMeta(id: string, strict = true): T.DocumentMeta | null {
  const d = allDocs().find((x) => x.doc_id === id);
  if (!d && strict) throw new HttpError(404, `Document ${id} not found`);
  return d ?? null;
}
const ownerOf = (docId: string) => [...D().bundles.values()].find((b) => b.detail.documents.some((d) => d.doc_id === docId));
export function xlsx(id: string): T.XlsxPayload {
  const b = ownerOf(id);
  const p = b?.xlsx[id];
  if (p) return p;
  if (id === 'ref-authority-2026') return authorityMatrix();
  throw new HttpError(404, 'No workbook payload');
}
export function eml(id: string): T.EmlPayload {
  const p = ownerOf(id)?.eml[id];
  if (!p) throw new HttpError(404, 'No email payload');
  return p;
}
export function extraction(id: string): T.ExtractionPayload {
  const b = ownerOf(id);
  const ex = b?.extraction[id];
  const extra = (b?.observations ?? []).filter((o) => o.anchor?.doc_id === id && !(ex?.fields ?? []).some((f) => f.obs_id === o.obs_id))
    .map((o) => ({ obs_id: o.obs_id, field_code: o.field_code, label: o.field_label, subject_label: o.subject_label, value_display: o.value_display, anchor: o.anchor!, confidence: o.confidence }));
  const meta = documentMeta(id);
  return { doc_id: id, method: ex?.method ?? (meta?.format === 'pdf' ? 'Layout-aware PDF extractor v3 (text layer + table detection)' : meta?.format === 'eml' ? 'Email parser v2 (statement classifier)' : 'n/a'), fields: [...(ex?.fields ?? []), ...extra], issues: ex?.issues ?? [] };
}
export function rawText(id: string): string | null {
  const b = ownerOf(id);
  if (b?.raw[id]) return b.raw[id];
  if (id === 'ref-notice-table') return NOTICE_TABLE_YAML;
  if (id === 'ref-rule-wind') return D().rules.find((r) => r.rule_id === 'CAT.WIND.DED_FLOOR')!.yaml;
  if (id === 'ref-hazard-geojson') return JSON.stringify(HAZARDS, null, 2);
  return null;
}
function authorityMatrix(): T.XlsxPayload {
  const rows: (string | number)[][] = [['Authority level', 'Role', 'Max TIV per location', 'Max limit', 'RARC band', 'Adequacy floor', 'CAT PML (1-in-250)'], ['L1', 'Underwriter', 50e6, 100e6, '≥ −5%', '≥ 100%', 10e6], ['L2', 'Underwriter', 100e6, 250e6, '≥ −10%', '≥ 95%', 25e6], ['L3', 'Senior underwriter', 250e6, 500e6, 'any', '≥ 90%', 60e6], ['L4', 'CUO', 'unlimited', 'unlimited', 'any', 'any', 'treaty']];
  const cols = 'ABCDEFG'; const cells: T.XlsxSheet['cells'] = {};
  rows.forEach((r, i) => r.forEach((v, j) => { cells[`${cols[j]}${i + 1}`] = typeof v === 'number' ? { v, t: 'n', num_fmt: '#,##0' } : { v, t: 's', bold: i === 0, fill: i === 0 ? '#e8edf5' : undefined }; }));
  return { sheets: [{ name: 'Matrix', hidden: false, max_row: rows.length, max_col: 7, cells, merges: [], hidden_rows: [], hidden_cols: [], col_widths: { A: 14, B: 20, C: 20, D: 14, E: 12, F: 14, G: 20 }, freeze: 'A2' }] };
}

// ------------------------------------------------------------------ mutations
export function disposition(fid: string, body: { decision: T.Disposition['decision']; reason_code: T.Disposition['reason_code']; note: string }, uid: string): T.Finding {
  for (const b of D().bundles.values()) {
    const f = b.detail.findings.find((x) => x.finding_id === fid);
    if (!f) continue;
    if (!body.reason_code) throw new HttpError(422, 'reason_code is mandatory');
    const prev = f.status;
    f.status = body.decision === 'ACCEPT' ? 'ACCEPTED' : body.decision === 'REJECT' ? 'REJECTED' : 'DEFERRED';
    f.disposition = { decision: body.decision, reason_code: body.reason_code, note: body.note, actor: me(uid).name, at: D().clock };
    if (f.status === 'ACCEPTED' && prev !== 'ACCEPTED' && f.material) D().pipe.validated += f.impact_usd;
    if (prev === 'ACCEPTED' && f.status !== 'ACCEPTED' && f.material) D().pipe.validated -= f.impact_usd;
    const rule = D().rules.find((r) => r.rule_id === f.rule_id);
    if (rule) { if (body.decision === 'ACCEPT') rule.stats.accepted++; if (body.decision === 'REJECT') rule.stats.rejected++; rule.stats.precision = rule.stats.accepted / Math.max(1, rule.stats.accepted + rule.stats.rejected); }
    tl(b, '15', 'user', `Finding ${body.decision.toLowerCase()}ed`, `${f.title} — ${body.reason_code}${body.note ? `: ${body.note}` : ''}`, me(uid).name, { finding_ids: [fid] });
    const openMat = b.detail.findings.filter((x) => x.material && x.status === 'OPEN');
    if (openMat.length === 0 && b.detail.renewal.status === 'ACTION_REQUIRED') b.detail.renewal.status = 'IN_REVIEW';
    return f;
  }
  throw new HttpError(404, 'Finding not found');
}

function termsHash(premium: number, t: T.RarcTerms) { return hash(JSON.stringify([premium, t.aop_deductible, t.named_storm_ded_pct, t.named_storm_ded_min, t.wind_hail_ded_pct, t.bi_sublimit, t.flood_sublimit, t.eq_sublimit])); }

export function createQuote(id: string, body: { premium: number; terms: Partial<T.RarcTerms> }, uid: string): T.QuoteVersion {
  const b = bundle(id);
  if (!b.rarc) throw new HttpError(409, 'Pricing not yet run');
  const r = computeRarc(id, b.rarc, body.premium, body.terms);
  b.rarc.proposed_premium = body.premium;
  b.rarc.proposed_terms = r.proposed_terms;
  const list = D().quotes.get(id) ?? [];
  const term = nextTerm(b.detail.renewal.expiry);
  const cur = list.filter((q) => q.term === term);
  cur.forEach((q) => { if (q.status === 'DRAFT' || q.status === 'APPROVED' || q.status === 'REFERRED') q.status = 'SUPERSEDED'; });
  const q: T.QuoteVersion = { quote_id: nid(`q-${id.slice(4, 10)}`), version: (cur.reduce((a, x) => Math.max(a, x.version), 0) || 0) + 1, term, created_at: D().clock, created_by: me(uid).name, premium: body.premium, terms: r.proposed_terms, status: 'DRAFT', terms_hash: termsHash(body.premium, r.proposed_terms), doc_id: null, rarc: r.rarc, adequacy: r.adequacy };
  list.push(q); D().quotes.set(id, list);
  for (const ref of D().referrals) {
    if (ref.account_id === id && ref.status === 'APPROVED' && ref.terms_hash && ref.terms_hash !== q.terms_hash) {
      ref.status = 'INVALIDATED';
      ref.invalidated_reason = `Terms changed after approval — quote v${q.version} (hash ${ref.terms_hash} → ${q.terms_hash})`;
      tl(b, '07', 'engine', 'Approval invalidated', ref.invalidated_reason, 'Authority engine');
    }
  }
  tl(b, '08', 'user', `Quote v${q.version} saved`, `$${body.premium.toLocaleString('en-US')} · NS ${r.proposed_terms.named_storm_ded_pct != null ? (r.proposed_terms.named_storm_ded_pct * 100).toFixed(1) + '%' : 'n/a'} · RARC ${(r.rarc * 100).toFixed(1)}% · L${r.required_authority_level} required`, me(uid).name);
  if (b.detail.renewal.status === 'ACTION_REQUIRED' || b.detail.renewal.status === 'NOT_STARTED') b.detail.renewal.status = 'IN_REVIEW';
  return q;
}

function validApproval(id: string, hashv: string) { return D().referrals.some((r) => r.account_id === id && r.status === 'APPROVED' && r.terms_hash === hashv); }

export function sendQuote(id: string, qid: string, uid: string): T.QuoteVersion {
  const b = bundle(id);
  const q = (D().quotes.get(id) ?? []).find((x) => x.quote_id === qid);
  if (!q) throw new HttpError(404, 'Quote not found');
  const r = computeRarc(id, b.rarc!, q.premium, q.terms);
  const u = me(uid);
  if (r.required_authority_level > u.authority_level && !validApproval(id, q.terms_hash))
    throw new HttpError(403, `Authority control: L${r.required_authority_level} required for these terms (you are L${u.authority_level}). Refer first — approval is locked to terms hash ${q.terms_hash}.`);
  q.status = 'SENT';
  b.detail.renewal.status = 'QUOTED';
  D().outbox.unshift({ message_id: nid('ob'), at: D().clock + 'T10:00:00Z', channel: 'email', to: b.detail.broker_contact, subject: `${b.detail.name} — renewal quote v${q.version}`, body: `Please find our renewal quote v${q.version}: premium $${q.premium.toLocaleString('en-US')}. Terms hash ${q.terms_hash}.`, account_id: id, related: q.quote_id });
  tl(b, '09', 'user', `Quote v${q.version} sent to broker`, `$${q.premium.toLocaleString('en-US')}`, u.name);
  if (D().injections.broker_autoreply) {
    const idx = D().script.findIndex((e) => e.date > D().clock);
    const ev: ScriptEvent = { date: addDays(D().clock, 3), account_id: id, stage: '09', kind: 'mock', title: `Broker response to quote v${q.version}`, detail: '', apply: (d) => {
      const target = b.rarc!.expiring_premium * 1.1;
      if (q.premium <= target * 1.06) { q.status = 'ACCEPTED'; ev.detail = `${b.detail.broker} accepts $${q.premium.toLocaleString('en-US')}`; }
      else { ev.detail = `${b.detail.broker} counters at $${Math.round(target).toLocaleString('en-US')}`; }
      d.outbox.unshift({ message_id: nid('ob'), at: d.clock + 'T09:00:00Z', channel: 'broker_portal', to: u.name, subject: `Broker bot: ${b.detail.name}`, body: ev.detail, account_id: id, related: q.quote_id });
      return 0;
    } };
    D().script.splice(idx < 0 ? D().script.length : idx, 0, ev);
  }
  return q;
}

export function createReferral(id: string, body: { quote_id: string | null; note: string }, uid: string): T.Referral {
  const b = bundle(id);
  const q = body.quote_id ? (D().quotes.get(id) ?? []).find((x) => x.quote_id === body.quote_id) : null;
  const r = b.rarc ? computeRarc(id, b.rarc, q?.premium, q?.terms) : null;
  const mat = b.detail.findings.filter((f) => f.material && f.status !== 'REJECTED');
  const level = Math.max(r?.required_authority_level ?? 3, mat.some((f) => f.family === 'portfolio' && f.severity !== 'LOW') ? 3 : 0);
  const memo = [
    `**Referral — ${b.detail.name}${q ? `, quote v${q.version} at $${q.premium.toLocaleString('en-US')}` : ''}.**`,
    r ? `Headline ${(r.headline_change * 100).toFixed(1)}%, computed RARC ${(r.rarc * 100).toFixed(1)}%, adequacy ${(r.adequacy * 100).toFixed(1)}% of TP(E1,T1) $${Math.round(r.tp_e1_t1).toLocaleString('en-US')}.` : '',
    `${mat.length} cited findings: ${mat.map((f) => `${f.title} [F:${f.finding_id}]`).join('; ')}.`,
    body.note ? `Underwriter note: ${body.note}` : '',
  ].filter(Boolean).join('\n\n');
  const ref: T.Referral = { referral_id: nid('ref'), account_id: id, account_name: b.detail.name, quote_id: q?.quote_id ?? null, terms_hash: q?.terms_hash ?? null, requested_by: me(uid).name, requested_at: D().clock, required_level: level,
    reasons: r?.authority_reasons ?? ['Senior review requested'], memo, status: 'PENDING', approver: null, decided_at: null, conditions: null, invalidated_reason: null };
  D().referrals.unshift(ref);
  if (q) q.status = 'REFERRED';
  b.detail.renewal.status = 'REFERRED';
  D().outbox.unshift({ message_id: nid('ob'), at: D().clock + 'T11:00:00Z', channel: 'in_app', to: level >= 4 ? 'Robert Hale (CUO)' : 'Priya Raman (Senior UW)', subject: `Referral L${level} — ${b.detail.name}`, body: `${me(uid).name} requests approval${q ? ` of quote v${q.version} (hash ${q.terms_hash})` : ''}.`, account_id: id, related: ref.referral_id });
  tl(b, '07', 'user', `Referred to L${level}`, ref.reasons.join(' · '), me(uid).name);
  return ref;
}

export function decideReferral(rid: string, body: { decision: 'APPROVE' | 'DECLINE'; conditions?: string }, uid: string): T.Referral {
  const ref = D().referrals.find((r) => r.referral_id === rid);
  if (!ref) throw new HttpError(404, 'Referral not found');
  const u = me(uid);
  if (ref.status !== 'PENDING') throw new HttpError(409, `Referral is ${ref.status}`);
  if (u.authority_level < ref.required_level) throw new HttpError(403, `Requires authority L${ref.required_level}; ${u.name} is L${u.authority_level}`);
  ref.status = body.decision === 'APPROVE' ? 'APPROVED' : 'DECLINED';
  ref.approver = u.name; ref.decided_at = D().clock; ref.conditions = body.conditions ?? null;
  const b = D().bundles.get(ref.account_id);
  if (b) {
    const q = (D().quotes.get(ref.account_id) ?? []).find((x) => x.quote_id === ref.quote_id);
    if (q) q.status = body.decision === 'APPROVE' ? 'APPROVED' : 'DRAFT';
    if (body.decision === 'APPROVE') D().pipe.approved += b.detail.findings.filter((f) => f.material && f.status === 'ACCEPTED').reduce((a, f) => a + f.impact_usd, 0) || 25_000;
    b.detail.renewal.status = 'IN_REVIEW';
    tl(b, '07', 'user', `Referral ${ref.status.toLowerCase()}`, `${u.name}${ref.terms_hash ? ` · locked to terms hash ${ref.terms_hash}` : ''}${body.conditions ? ` · conditions: ${body.conditions}` : ''}`, u.name);
    D().outbox.unshift({ message_id: nid('ob'), at: D().clock + 'T12:00:00Z', channel: 'in_app', to: ref.requested_by, subject: `Referral ${ref.status.toLowerCase()} — ${ref.account_name}`, body: body.conditions ? `Conditions: ${body.conditions}` : 'No conditions.', account_id: ref.account_id, related: rid });
  }
  return ref;
}

export function dataRequest(id: string, items: string[], uid: string): T.OutboxMessage {
  const b = bundle(id);
  const msg: T.OutboxMessage = { message_id: nid('ob'), at: D().clock + 'T09:30:00Z', channel: 'email', to: b.detail.broker_contact, subject: `${b.detail.name} — data request for ${b.detail.renewal.expiry} renewal`, body: `Please provide:\n${items.map((x, i) => `${i + 1}. ${x}`).join('\n')}`, account_id: id, related: null };
  D().outbox.unshift(msg);
  tl(b, '01', 'user', 'Data request sent to broker', items.join('; '), me(uid).name);
  return msg;
}

export function bind(id: string, quoteId: string, uid: string) {
  const b = bundle(id);
  const q = (D().quotes.get(id) ?? []).find((x) => x.quote_id === quoteId);
  if (!q) throw new HttpError(404, 'Quote not found');
  const r = computeRarc(id, b.rarc!, q.premium, q.terms);
  const u = me(uid);
  const out: T.Finding[] = [];
  if (r.required_authority_level > u.authority_level && !validApproval(id, q.terms_hash))
    out.push(addFinding(b, { finding_id: nid('f-bind-auth'), title: `Bound without valid approval — L${r.required_authority_level} required`, family: 'authority', severity: 'CRITICAL', outcome: 'REFER', observed: `Bound by ${u.name} (L${u.authority_level}); no approval for hash ${q.terms_hash}`, expected: 'Approval locked to the bound terms hash', impact_usd: q.premium * 0.1 }));
  if (b.rarc!.wind_floor && q.terms.named_storm_ded_pct !== null && q.terms.named_storm_ded_pct < b.rarc!.wind_floor)
    out.push(addFinding(b, { finding_id: nid('f-bind-ns'), title: 'Bound below named-storm deductible floor', family: 'cat_terms', severity: 'HIGH', outcome: 'TERM_BREACH', observed: `${(q.terms.named_storm_ded_pct * 100).toFixed(1)}% per location`, expected: `≥ ${(b.rarc!.wind_floor * 100).toFixed(0)}%`, impact_usd: 16_000 }));
  if (b.detail.renewal.missing.length)
    out.push(addFinding(b, { finding_id: nid('f-bind-subj'), title: `Bound with ${b.detail.renewal.missing.length} open subjectivit${b.detail.renewal.missing.length > 1 ? 'ies' : 'y'}`, family: 'contract_integrity', severity: 'MEDIUM', outcome: 'CONDITION', observed: b.detail.renewal.missing.join('; '), expected: 'Subjectivities cleared ≤ 30 days after bind', impact_usd: 0 }));
  q.status = 'BOUND';
  b.detail.renewal.status = 'BOUND';
  b.detail.renewal.pass = 3;
  const binder = `${id}-binder-${q.version}`;
  b.detail.documents.push({ doc_id: binder, account_id: id, account_name: b.detail.name, doc_type: 'Binder', title: `Binder ${q.term} (quote v${q.version})`, filename: `${id}_binder_v${q.version}.pdf`, format: 'pdf', received_at: D().clock, source_channel: 'Platform', size_bytes: 162_000, term: q.term, is_sample: true, extraction: { status: 'EXTRACTED', fields: 24, avg_confidence: 0.99 } });
  const gain = Math.max(0, q.premium - (b.contract.quotes.find((x) => x.status === 'SENT')?.premium ?? b.rarc!.expiring_premium * (1 + 0.098)));
  D().pipe.corrected += Math.round(gain + b.detail.findings.filter((f) => f.status === 'ACCEPTED' && ['cat_terms', 'contract_integrity'].includes(f.family)).reduce((a, f) => a + f.impact_usd, 0));
  tl(b, '10', 'user', `Bound quote v${q.version}`, `$${q.premium.toLocaleString('en-US')} · Pass 3 contract check: ${out.length} finding${out.length === 1 ? '' : 's'}`, u.name, { doc_id: binder, finding_ids: out.map((f) => f.finding_id) });
  return { binder_doc_id: binder, findings: out };
}

export function issue(id: string, uid: string) {
  const b = bundle(id);
  if (b.detail.renewal.status !== 'BOUND') throw new HttpError(409, 'Bind before issuing');
  const out: T.Finding[] = [];
  if (D().injections.issuance_error) {
    const bi = b.rarc?.proposed_terms.bi_sublimit;
    out.push(addFinding(b, bi ? { finding_id: nid('f-iss-bi'), title: `Issued policy BI sublimit ${k(bi * 1.5)} ≠ binder ${k(bi)}`, family: 'contract_integrity', severity: 'CRITICAL', outcome: 'TERM_BREACH', observed: `Binder ${k(bi)} · PAS dec page ${k(bi * 1.5)}`, expected: 'Issued policy = binder', impact_usd: 30_000 }
      : { finding_id: nid('f-iss-min'), title: 'Deductible minimum missing on issued policy', family: 'contract_integrity', severity: 'HIGH', outcome: 'TERM_BREACH', observed: 'Dec page omits minimum', expected: 'Issued policy = binder', impact_usd: 12_000 }));
  }
  b.detail.renewal.status = 'ISSUED';
  const pol = `${id}-policy-${D().seq + 1}`;
  b.detail.documents.push({ doc_id: pol, account_id: id, account_name: b.detail.name, doc_type: 'Declarations', title: `Declarations ${nextTerm(b.detail.renewal.expiry)} (issued)`, filename: `${id}_declarations_issued.pdf`, format: 'pdf', received_at: D().clock, source_channel: 'PAS (mock)', size_bytes: 320_000, term: nextTerm(b.detail.renewal.expiry), is_sample: true, extraction: { status: 'EXTRACTED', fields: 38, avg_confidence: 0.98 } });
  tl(b, '11', 'mock', 'Policy issued (PAS mock)', out.length ? `Issuance-error injection on — ${out.length} contract-integrity finding` : 'Pass 3 clean — binder = policy', 'PAS (mock)', { doc_id: pol, finding_ids: out.map((f) => f.finding_id) });
  void uid;
  return { policy_doc_id: pol, findings: out };
}

export function confirmMaintain(id: string, uid: string): T.RenewalQueueItem {
  const b = bundle(id);
  b.detail.renewal.status = 'QUOTED';
  if (b.rarc) { const list = D().quotes.get(id) ?? []; const t = nextTerm(b.detail.renewal.expiry); list.push({ quote_id: nid(`q-${id.slice(4, 10)}`), version: 1, term: t, created_at: D().clock, created_by: me(uid).name, premium: b.rarc.proposed_premium, terms: b.rarc.proposed_terms, status: 'SENT', terms_hash: termsHash(b.rarc.proposed_premium, b.rarc.proposed_terms), doc_id: null, rarc: computeRarc(id, b.rarc).rarc, adequacy: computeRarc(id, b.rarc).adequacy }); D().quotes.set(id, list); }
  tl(b, '08', 'user', 'Fast-track confirmed — maintain', 'Renewal quote on expiring terms + trend sent to broker', me(uid).name);
  return queueItem(b);
}

export function matchDecision(itemId: string, body: { decision: 'CONFIRM' | 'REJECT'; option?: string }, uid: string) {
  const i = D().review.findIndex((r) => r.item_id === itemId);
  if (i < 0) throw new HttpError(404, 'Review item not found');
  const item = D().review[i];
  D().review.splice(i, 1);
  const b = D().bundles.get(item.account_id);
  if (b && item.kind === 'LOCATION_MATCH') {
    const l = b.detail.locations.find((x) => x.match_status === 'AMBIGUOUS');
    if (l) { if (body.decision === 'CONFIRM') { l.match_status = 'MATCHED'; l.match_confirmed_by = me(uid).name; } else { l.match_status = 'NEW'; l.loc_no_prior = null; l.tiv_prior = null; l.tiv_change_pct = null; } l.flags = l.flags.filter((f) => f.code !== 'MATCH_REVIEW'); }
    if (!b.detail.locations.some((x) => x.match_status === 'AMBIGUOUS')) resolve(D(), item.account_id, 'f-sum-amb');
    tl(b, '04', 'user', `Location match ${body.decision === 'CONFIRM' ? 'confirmed' : 'rejected'}`, item.label + (body.option ? ` → ${body.option}` : ''), me(uid).name);
  }
  return { ok: true };
}

// ------------------------------------------------------------------ rules
function parseYaml(y: string) {
  const when = /^when:\s*(.+)$/m.exec(y)?.[1]?.trim();
  const outcome = /^\s+type:\s*(\w+)/m.exec(y)?.[1] as T.RuleOutcome | undefined;
  const states = /^\s+states:\s*\[([^\]]*)\]/m.exec(y)?.[1]?.split(',').map((s) => s.trim()).filter(Boolean);
  const title = /^title:\s*"?(.*?)"?$/m.exec(y)?.[1];
  const tests: T.RuleTestCase[] = [];
  const re = /-\s*name:\s*(\S+)\s*\n\s*fixture:\s*(\{.*\})\s*\n\s*expect:\s*(\w+)/g;
  let mm: RegExpExecArray | null;
  while ((mm = re.exec(y))) { try { tests.push({ name: mm[1], fixture: JSON.parse(mm[2]), expect: mm[3] as T.RuleOutcome }); } catch { tests.push({ name: mm[1], fixture: { __invalid: mm[2] }, expect: mm[3] as T.RuleOutcome }); } }
  if (!when) throw new HttpError(422, 'YAML: missing `when:` expression');
  if (!outcome) throw new HttpError(422, 'YAML: missing `outcome.type`');
  return { when, outcome, states, title, tests };
}
function compile(when: string) {
  const js = when.replace(/([\w.]+)\s+in\s+(\[[^\]]*\])/g, '$2.includes($1)');
  if (/[;{}=]\s*>|\bfunction\b|\bwindow\b|\bdocument\b|\bfetch\b|=>/.test(js)) throw new HttpError(422, 'Expression not allowed');
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  return new Function('ctx', `with (ctx) { return (${js}); }`) as (ctx: Record<string, unknown>) => unknown;
}
function evalRule(p: ReturnType<typeof parseYaml>, fixture: Record<string, unknown>): string {
  const scoped = fixture as { loc?: { state?: string } };
  if (p.states && scoped.loc?.state && !p.states.includes(scoped.loc.state)) return 'NOT_APPLICABLE';
  if ('__invalid' in fixture) throw new Error('fixture is not valid JSON');
  const fn = compile(p.when);
  const ctx = new Proxy(fixture, { has: () => true, get: (t, key) => { if (key === Symbol.unscopables) return undefined; if (typeof key === 'string' && key in t) return (t as Record<string, unknown>)[key]; if (key === 'null' || key === 'true' || key === 'false') return undefined; return (globalThis as Record<string | symbol, unknown>)[key as string] ?? {}; } });
  return fn(ctx) ? p.outcome : 'PASS';
}
export function ruleTest(id: string, yaml: string): T.RuleTestResult[] {
  const p = parseYaml(yaml);
  const tests = p.tests.length ? p.tests : D().rules.find((r) => r.rule_id === id)?.tests ?? [];
  return tests.map((t) => { try { const a = evalRule(p, t.fixture); return { name: t.name, expected: t.expect, actual: a, pass: a === t.expect, error: null }; } catch (e) { return { name: t.name, expected: t.expect, actual: 'ERROR', pass: false, error: e instanceof Error ? e.message : String(e) }; } });
}
function controlSet(rule: T.Rule) {
  const r = rng(Number.parseInt(hash(rule.rule_id), 16));
  const names = D().order.map((id) => D().bundles.get(id)!.detail.name);
  const cities = ['Tampa FL', 'Houston TX', 'Miami FL', 'Charleston SC', 'Mobile AL', 'Dayton OH', 'Memphis TN', 'Reno NV', 'Denver CO', 'Atlanta GA'];
  const vals = new Map<string, unknown[]>();
  const walk = (o: Record<string, unknown>, pre: string) => { for (const [kk, v] of Object.entries(o)) { if (v && typeof v === 'object' && !Array.isArray(v)) walk(v as Record<string, unknown>, pre + kk + '.'); else { const a = vals.get(pre + kk) ?? []; a.push(v); vals.set(pre + kk, a); } } };
  rule.tests.forEach((t) => walk(t.fixture, ''));
  return Array.from({ length: 500 }, (_, i) => {
    const fx: Record<string, Record<string, unknown>> = {};
    for (const [path, vs] of vals) {
      const [a, b2] = path.split('.');
      let v = pick(r, vs);
      if (typeof v === 'number' && r() < 0.55) { const x = v * between(r, 0.6, 1.45); v = Math.abs(x) < 1 ? +x.toFixed(3) : Math.round(x); }
      if (typeof v === 'boolean' && r() < 0.3) v = !v;
      (fx[a] ??= {})[b2] = v;
    }
    return { fx, account_name: `${pick(r, names)} (${pick(r, ['2024', '2025'])})`, subject_label: `Loc ${1 + (i % 9)} · ${pick(r, cities)}` };
  });
}
export function ruleBacktest(id: string, yaml: string): T.BacktestResult {
  const rule = D().rules.find((r) => r.rule_id === id);
  if (!rule) throw new HttpError(404, 'Rule not found');
  const t0 = performance.now();
  const before = parseYaml(rule.yaml), after = parseYaml(yaml);
  const set = controlSet(rule);
  const fired = (p: ReturnType<typeof parseYaml>, fx: Record<string, unknown>) => { try { const o = evalRule(p, fx); return o !== 'PASS' && o !== 'NOT_APPLICABLE'; } catch { return false; } };
  const added: T.BacktestResult['added'] = [], removed: T.BacktestResult['removed'] = [];
  let nb = 0, na = 0;
  set.forEach((c, i) => {
    const a = fired(before, c.fx), b2 = fired(after, c.fx);
    if (a) nb++; if (b2) na++;
    const obs = Object.entries(c.fx).map(([kk, v]) => `${kk}: ${Object.entries(v).map(([x, y]) => `${x}=${y}`).join(', ')}`).join(' · ');
    if (b2 && !a) added.push({ account_id: `ctl-${i}`, account_name: c.account_name, subject_label: c.subject_label, observed: obs });
    if (a && !b2) removed.push({ account_id: `ctl-${i}`, account_name: c.account_name, subject_label: c.subject_label, observed: obs });
  });
  return { control_set: 'Frozen control set — 2024–2025 renewals (500 accounts, as of 2026-06-30)', accounts: 500, before: nb, after: na, added: added.slice(0, 40), removed: removed.slice(0, 40), duration_ms: Math.round(performance.now() - t0 + 380) };
}
export function rulePublish(id: string, yaml: string): T.Rule {
  const rule = D().rules.find((r) => r.rule_id === id);
  if (!rule) throw new HttpError(404, 'Rule not found');
  const p = parseYaml(yaml);
  const failing = ruleTest(id, yaml).filter((t) => !t.pass);
  if (failing.length) throw new HttpError(422, `Cannot publish: ${failing.length} failing test${failing.length > 1 ? 's' : ''} (${failing.map((f) => f.name).join(', ')})`);
  rule.version += 1;
  rule.yaml = yaml.replace(/^version:\s*\d+/m, `version: ${rule.version}`).replace(/^effective_from:\s*\S+/m, `effective_from: ${D().clock}`);
  rule.when = p.when; rule.outcome = p.outcome; if (p.title) rule.title = p.title; rule.tests = p.tests.length ? p.tests : rule.tests;
  rule.effective_from = D().clock;
  rule.stats = { fired: 0, accepted: 0, rejected: 0, precision: null };
  return rule;
}

// ------------------------------------------------------------------ data quality
export function dataQuality(): T.DataQualitySummary {
  const all = D().order.map((id) => D().bundles.get(id)!);
  const matching = { matched: 0, new: 0, deleted: 0, ambiguous: 0, merged: 0, split: 0 };
  const accounts: T.DataQualityAccount[] = all.filter((b) => b.detail.renewal.pass > 0).map((b) => {
    const d = b.detail;
    for (const l of d.locations) { const key = l.match_status.toLowerCase() as keyof typeof matching; matching[key]++; }
    const totalAal = d.locations.reduce((a, l) => a + (l.aal ?? 0), 0) || 1;
    const gaps: T.DataQualityAccount['top_gaps'] = [];
    const ranked = [...d.locations].sort((a, c) => (c.aal ?? 0) - (a.aal ?? 0));
    ranked.forEach((l, i) => {
      const w = (l.aal ?? totalAal / d.locations.length) / totalAal;
      if (!l.roof_year) gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.city}`, field: 'roof_year', reason: 'Missing on SOV', impact_rank: i + 1, aal_weight: w });
      if (!l.year_built) gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.city}`, field: 'year_built', reason: 'Missing on SOV', impact_rank: i + 1, aal_weight: w });
      if (l.construction === 'Unknown') gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.city}`, field: 'construction', reason: 'Unknown — CAT defaulted to regional mix', impact_rank: i + 1, aal_weight: w });
      if (l.aal === null && l.match_status === 'NEW') gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.city}`, field: 'cat_model', reason: 'Not in CAT exposure file', impact_rank: i + 1, aal_weight: 0.3 });
      if (l.flags.some((f) => f.code === 'SECONDARY_MODS')) gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.name}`, field: 'roof_cover / anchorage', reason: 'Secondary modifier blank on top-AAL building', impact_rank: i + 1, aal_weight: w });
      if (l.match_status === 'AMBIGUOUS') gaps.push({ location_label: `Loc ${l.loc_no_current} · ${l.name}`, field: 'location_match', reason: `Match score ${l.match_score}`, impact_rank: i + 1, aal_weight: w });
    });
    const conflicts = fields(d.account_id).filter((f) => f.conflict).length;
    const low = b.observations.filter((o) => o.confidence < 0.7).length;
    const stale = d.findings.filter((f) => f.rule_id.startsWith('DQ.STALE') || f.family === 'valuation' && f.title.includes('flat')).length;
    const unmatched = d.locations.filter((l) => l.match_status === 'AMBIGUOUS' || l.match_status === 'NEW').length;
    const penalty = gaps.reduce((a, g) => a + 4 + g.aal_weight * 40, 0) + conflicts * 3 + low * 1.5 + stale * 4;
    return { account_id: d.account_id, name: d.name, score: Math.max(32, Math.min(100, Math.round(100 - penalty))), missing_fields: gaps.filter((g) => g.reason.startsWith('Missing') || g.reason.startsWith('Unknown') || g.reason.startsWith('Secondary')).length, low_confidence: low, stale_fields: stale, unmatched_locations: unmatched, conflicts, top_gaps: gaps.sort((a, c) => c.aal_weight - a.aal_weight).slice(0, 5) };
  }).sort((a, c) => a.score - c.score);
  const docs = allDocs().filter((d) => d.extraction?.status === 'EXTRACTED');
  const nf = docs.reduce((a, d) => a + (d.extraction?.fields ?? 0), 0);
  return {
    avg_score: accounts.reduce((a, x) => a + x.score, 0) / accounts.length,
    extraction: { documents: docs.length, fields: nf, avg_confidence: docs.reduce((a, d) => a + (d.extraction!.avg_confidence ?? 0) * d.extraction!.fields, 0) / nf, human_review_queue: D().review.length },
    matching, accounts, review_queue: D().review,
  };
}

// ------------------------------------------------------------------ pipeline & demo
export function pipeline(): T.PipelineStage[] {
  const all = [...D().bundles.values()];
  const st = (s: T.RenewalStatus[]) => all.filter((b) => s.includes(b.detail.renewal.status)).length;
  const docs = allDocs();
  const counts: Record<string, { label: string; value: number }[]> = {
    '01': [{ label: 'submissions', value: all.filter((b) => b.detail.renewal.pass >= 2).length }, { label: 'emails', value: docs.filter((d) => d.format === 'eml').length }],
    '02': [{ label: 'cleared', value: all.length }, { label: 'sanctions hits', value: 0 }],
    '03': [{ label: 'rules live', value: D().rules.length }, { label: 'declines', value: all.filter((b) => b.detail.findings.some((f) => f.outcome === 'DECLINE')).length }],
    '04': [{ label: 'documents', value: docs.filter((d) => d.extraction?.status === 'EXTRACTED').length }, { label: 'fields', value: docs.reduce((a, d) => a + (d.extraction?.fields ?? 0), 0) }],
    '05': [{ label: 'recs open', value: all.reduce((a, b) => a + b.claims.recommendations.filter((r) => r.status === 'OPEN').length, 0) }, { label: 'surveys', value: all.reduce((a, b) => a + b.claims.surveys.length, 0) }],
    '06': [{ label: 'rater runs', value: all.filter((b) => b.rarc).length * 3 }, { label: 'CAT runs', value: all.reduce((a, b) => a + b.cat.length, 0) }],
    '07': [{ label: 'referrals pending', value: D().referrals.filter((r) => r.status === 'PENDING').length }, { label: 'invalidated', value: D().referrals.filter((r) => r.status === 'INVALIDATED').length }],
    '08': [{ label: 'quote versions', value: [...D().quotes.values()].reduce((a, q) => a + q.length, 0) }],
    '09': [{ label: 'quoted', value: st(['QUOTED']) }],
    '10': [{ label: 'bound', value: st(['BOUND']) }],
    '11': [{ label: 'issued', value: st(['ISSUED']) }, { label: 'issuance errors', value: all.reduce((a, b) => a + b.detail.findings.filter((f) => f.family === 'contract_integrity' && f.status === 'OPEN').length, 0) }],
    '12': [{ label: 'mid-term events', value: all.reduce((a, b) => a + b.detail.timeline.filter((e) => e.stage === '12').length, 0) }],
    '13': [{ label: 'claims (5y)', value: all.reduce((a, b) => a + b.claims.claims.length, 0) }],
    '14': [{ label: 'zones', value: ZONES.length }, { label: '> 90%', value: ZONES.filter((z) => z.post_renewal / z.threshold > 0.9).length }],
    '15': [{ label: 'renewals', value: all.length }, { label: 'fast-track', value: st(['FAST_TRACK']) }],
  };
  return PIPELINE.map((p) => ({ ...p, counts: counts[p.code] ?? [] }));
}
export function mockSystems(): T.MockSystem[] { return MOCK_SYSTEMS.map((m) => (m.port === 'NotificationPort' ? { ...m, records: D().outbox.length } : m)); }
export function outbox() { return D().outbox; }
export function referrals(status?: string | null) { return D().referrals.filter((r) => !status || r.status === status); }
export function rules() { return D().rules; }
export function rule(id: string) { const r = D().rules.find((x) => x.rule_id === id); if (!r) throw new HttpError(404, 'Rule not found'); return r; }
export function claims(id: string) { return bundle(id).claims; }
export function cat(id: string) { return bundle(id).cat; }

export function demoState(): T.DemoState {
  const d = D();
  return { clock: d.clock, start: CLOCK0, end: '2027-01-31', events_applied: d.applied, events_total: d.script.length,
    next_events: d.script.filter((e) => e.date > d.clock).slice(0, 8).map((e) => ({ date: e.date, title: e.title, account_name: e.account_id ? d.bundles.get(e.account_id)?.detail.name ?? null : null })), injections: d.injections };
}
export function advance(body: { days?: number; to?: string }): T.AdvanceResult {
  const d = D();
  const to = body.to ?? addDays(d.clock, body.days ?? 7);
  const applied: T.TimelineEvent[] = [];
  let nf = 0;
  for (const e of d.script) {
    if (e.date <= d.clock || e.date > to) continue;
    const prevClock = d.clock; d.clock = e.date;
    nf += e.apply?.(d) ?? 0;
    const tev: T.TimelineEvent = { event_id: nid('ev'), date: e.date, kind: e.kind, stage: e.stage, title: e.title, detail: e.detail, actor: e.kind === 'mock' ? 'Demo timeline' : e.kind === 'engine' ? 'Renewal engine' : 'Broker' };
    if (e.account_id) d.bundles.get(e.account_id)?.detail.timeline.unshift(tev);
    applied.push(tev); d.applied++;
    void prevClock;
  }
  d.clock = to;
  return { clock: to, applied, new_findings: nf };
}
export function setInjections(b: Record<string, boolean>) { Object.assign(D().injections, b); return demoState(); }
export function users() { return USERS; }
export function hazards() { return HAZARDS; }

export function search(q: string): T.SearchHit[] {
  const s = q.toLowerCase(); const out: T.SearchHit[] = [];
  for (const id of D().order) { const b = D().bundles.get(id)!; if (b.detail.name.toLowerCase().includes(s)) out.push({ kind: 'account', id, title: b.detail.name, subtitle: `${b.detail.scenario ?? b.detail.segment} · ${b.detail.broker}`, href: `/accounts/${id}` }); }
  for (const r of D().rules) if (r.rule_id.toLowerCase().includes(s) || r.title.toLowerCase().includes(s)) out.push({ kind: 'rule', id: r.rule_id, title: r.rule_id, subtitle: r.title, href: `/rules/${r.rule_id}` });
  for (const b of D().bundles.values()) for (const f of b.detail.findings) if (f.title.toLowerCase().includes(s)) out.push({ kind: 'finding', id: f.finding_id, title: f.title, subtitle: b.detail.name, href: `/accounts/${b.detail.account_id}` });
  for (const dd of allDocs()) if (dd.title.toLowerCase().includes(s)) out.push({ kind: 'document', id: dd.doc_id, title: dd.title, subtitle: dd.account_name ?? dd.doc_type, href: `/documents/${dd.doc_id}` });
  return out.slice(0, 20);
}
export { userName };
