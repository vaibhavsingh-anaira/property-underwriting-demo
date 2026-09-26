// Generic builders: turn a compact AccountSpec into a full AccountBundle.
// Hero scenarios override individual pieces; background accounts use these as-is.
import type {
  AccountDetail, ActionType, CatResult, ClaimsEngineering, ContractDiff, ContractDiffRow, DeltaCard, DocumentMeta,
  Finding, LocationRow, Narrative, Observation, PassNo, PolicySummary, RenewalStatus, TimelineEvent, XlsxPayload, XlsxSheet,
  EmlPayload, ExtractionPayload, Anchor, NoticeInfo, Claim, Recommendation,
} from '@/api/types';
import { computeRarc, type AccountBundle, type RarcBase } from './model';
import { userName } from './users';
import { addDays, CLOCK0, daysBetween, doc, ev, hash, k, m, p1, pdfA, rng, int, pick, between, round, xlsA, sysA } from './util';

export interface AccountSpec {
  id: string; name: string; scenario: string | null; scenario_title: string | null;
  segment: 'Middle market' | 'Large' | 'E&S'; occupancy_family: string; state: string;
  broker: string; broker_contact: string; underwriter_id: string; tenure_years: number;
  expiry: string; status: RenewalStatus; pass: PassNo; actions: ActionType[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH'; missing: string[]; admitted: boolean; notice_days: number | null;
  premium: number; limit: number; layer: string; share: number; limit_basis: PolicySummary['limit_basis'];
  policy_no: string;
  locations: LocationRow[];
  findings: Finding[];
  rarc: RarcBase | null;
  seed: number;
  site_model_doc_id?: string | null;
  // overrides
  deltas?: DeltaCard[]; narrative?: Narrative; contract?: ContractDiff; cat?: CatResult[]; claims?: ClaimsEngineering;
  timeline?: TimelineEvent[]; docs?: DocumentMeta[]; observations?: Observation[];
  xlsx?: Record<string, XlsxPayload>; eml?: Record<string, EmlPayload>;
}

export const FAMILY_LABEL: Record<string, string> = {
  pricing: 'Pricing adequacy', valuation: 'Valuation', cat_terms: 'CAT terms', contract_integrity: 'Contract integrity',
  occupancy: 'Occupancy / COPE drift', engineering: 'Engineering recommendations', claims: 'Loss experience',
  cat_data: 'CAT data quality', portfolio: 'Accumulation', appetite: 'Appetite', authority: 'Authority & referral',
  data_quality: 'Data completeness', safeguards: 'Protective safeguards', security: 'Theft & security',
};

const CARD_FAMILIES: Record<DeltaCard['key'], string[]> = {
  exposure: ['valuation', 'occupancy', 'data_quality', 'cat_data'],
  pricing: ['pricing'],
  terms: ['cat_terms', 'contract_integrity', 'safeguards', 'authority'],
  risk_quality: ['claims', 'engineering', 'security'],
  appetite_portfolio: ['appetite', 'portfolio'],
  retention: [],
  net: [],
};

export const termLabel = (expiry: string) => { const y = +expiry.slice(0, 4); return `${y - 1}–${y}`; };
export const nextTerm = (expiry: string) => { const y = +expiry.slice(0, 4); return `${y}–${y + 1}`; };

export function policyFor(s: AccountSpec): PolicySummary {
  return {
    policy_id: `pol-${s.id}`, policy_no: s.policy_no,
    term_start: addDays(s.expiry, -365), term_end: s.expiry,
    carrier_share: s.share, layer: s.layer, limit: s.limit, limit_basis: s.limit_basis, admitted: s.admitted, premium: s.premium,
    forms: [
      { form_no: 'CP 00 10 10 12', title: 'Building and Personal Property Coverage Form' },
      { form_no: 'CP 00 30 10 12', title: 'Business Income (and Extra Expense) Coverage Form' },
      { form_no: 'CP 10 30 09 17', title: 'Causes of Loss — Special Form' },
      { form_no: 'CP 04 11 09 17', title: 'Protective Safeguards' },
      { form_no: 'NGS-PR 112 06 25', title: 'Named Storm Deductible Endorsement (Northgate)' },
    ],
  };
}

export function noticeFor(s: AccountSpec, clock = CLOCK0): NoticeInfo {
  if (!s.admitted || s.notice_days === null) {
    return { required: false, state: s.state, admitted: s.admitted, days_required: null, latest_notice_date: null, days_remaining: null, rule_ref: s.admitted ? 'Demo notice table v1 — illustrative, verify with counsel' : 'E&S — surplus lines, statutory notice not required (demo table v1)' };
  }
  const latest = addDays(s.expiry, -s.notice_days);
  return { required: true, state: s.state, admitted: true, days_required: s.notice_days, latest_notice_date: latest, days_remaining: daysBetween(clock, latest), rule_ref: 'Demo notice table v1 — illustrative, verify with counsel' };
}

export function integrityScore(findings: Finding[]) {
  const w = { CRITICAL: 11, HIGH: 5.5, MEDIUM: 2.5, LOW: 0.8 } as const;
  let s = 100;
  for (const f of findings) {
    const mult = f.status === 'OPEN' || f.status === 'DEFERRED' ? 1 : f.status === 'ACCEPTED' ? 0.45 : 0;
    s -= w[f.severity] * mult;
  }
  return Math.max(18, Math.round(s));
}

// ------------------------------------------------------------------ deltas
export function deltasFor(s: AccountSpec): DeltaCard[] {
  const fam = (keys: string[]) => s.findings.filter((f) => keys.includes(f.family));
  const status = (fs: Finding[]): DeltaCard['status'] =>
    fs.some((f) => f.status === 'OPEN' && (f.severity === 'HIGH' || f.severity === 'CRITICAL')) ? 'ACTION' : fs.some((f) => f.status === 'OPEN') ? 'WATCH' : 'OK';
  const tp = s.locations.reduce((a, l) => a + (l.tiv_prior ?? 0), 0);
  const tc = s.locations.reduce((a, l) => a + (l.tiv_current ?? 0), 0);
  const newL = s.locations.filter((l) => l.match_status === 'NEW');
  const minVal = s.locations.filter((l) => l.valuation_ratio !== null).sort((a, b) => a.valuation_ratio! - b.valuation_ratio!)[0];
  const occ = s.locations.filter((l) => l.occupancy_prior && l.occupancy_prior !== l.occupancy);
  const r = s.rarc ? computeRarc(s.id, s.rarc) : null;
  const expF = fam(CARD_FAMILIES.exposure), prF = fam(CARD_FAMILIES.pricing), teF = fam(CARD_FAMILIES.terms), rqF = fam(CARD_FAMILIES.risk_quality), apF = fam(CARD_FAMILIES.appetite_portfolio);
  const R = rng(s.seed + 7);
  const lr = between(R, 0.18, 0.72);
  const ids = (fs: Finding[]) => fs.map((f) => f.finding_id);
  return [
    { key: 'exposure', title: 'Exposure', status: status(expF), headline: tc ? `TIV ${m(tp)} → ${m(tc)} (${p1(tc / tp - 1, true)})` : 'Awaiting renewal SOV',
      metrics: [
        { label: 'Total insured value', before: m(tp), after: tc ? m(tc) : '—', display: tc ? p1(tc / tp - 1, true) : '—', flag: tc && Math.abs(tc / tp - 1) < 0.02 ? 'warn' : 'info', note: tc && Math.abs(tc / tp - 1) < 0.02 ? 'Flat values vs +5.1% construction-cost trend' : undefined, obs_ids: s.locations[0] ? [`ob-${s.locations[0].location_uid}-tiv`] : [] },
        { label: 'Locations', before: String(s.locations.filter((l) => l.match_status !== 'NEW').length), after: String(s.locations.filter((l) => l.match_status !== 'DELETED').length), display: newL.length ? `+${newL.length} new` : 'no change', flag: newL.length ? 'warn' : 'ok' },
        ...(minVal ? [{ label: 'Lowest valuation vs model RC', display: p1(minVal.valuation_ratio!), after: minVal.name, flag: (minVal.valuation_ratio! < 0.8 ? 'breach' : minVal.valuation_ratio! < 0.9 ? 'warn' : 'ok') as 'breach' | 'warn' | 'ok', finding_ids: ids(expF.filter((f) => f.family === 'valuation')) }] : []),
        { label: 'Occupancy changes', display: occ.length ? `${occ.length} location${occ.length > 1 ? 's' : ''}` : 'none', flag: occ.length ? 'breach' : 'ok', finding_ids: ids(expF.filter((f) => f.family === 'occupancy')) },
      ] },
    { key: 'pricing', title: 'Pricing', status: r ? (r.rarc < -0.05 || r.adequacy < 1 ? 'ACTION' : status(prF)) : 'WATCH', headline: r ? `Headline ${p1(r.headline_change, true)} · RARC ${p1(r.rarc, true)}` : 'Pricing not yet run',
      metrics: r ? [
        { label: 'Premium', before: k(r.expiring_premium), after: k(r.proposed_premium), display: p1(r.headline_change, true), flag: 'info' },
        { label: 'Computed RARC', display: p1(r.rarc, true), flag: r.rarc < -0.05 ? 'breach' : r.rarc < 0 ? 'warn' : 'ok', finding_ids: ids(prF) },
        { label: 'Adequacy vs TP(E1,T1)', display: p1(r.adequacy), after: `floor ${p1(r.adequacy_floor, false)}`, flag: r.adequacy < r.adequacy_floor ? 'breach' : r.adequacy < 1 ? 'warn' : 'ok' },
        { label: 'Model drift since bind', display: p1(r.model_drift.drift, true), flag: 'info' },
      ] : [] },
    { key: 'terms', title: 'Terms & contract', status: status(teF), headline: teF.length ? teF[0].title : 'Terms consistent with guidelines and contract',
      metrics: [
        { label: 'Named-storm deductible', display: s.rarc?.expiring_terms.named_storm_ded_pct != null ? `${(s.rarc.expiring_terms.named_storm_ded_pct * 100).toFixed(0)}%` : 'n/a', after: s.rarc?.wind_floor ? `floor ${(s.rarc.wind_floor * 100).toFixed(0)}%` : undefined, flag: teF.some((f) => f.family === 'cat_terms') ? 'breach' : 'ok', finding_ids: ids(teF.filter((f) => f.family === 'cat_terms')) },
        { label: 'Quote ↔ binder ↔ policy', display: teF.some((f) => f.family === 'contract_integrity') ? `${teF.filter((f) => f.family === 'contract_integrity').length} mismatch` : 'all match', flag: teF.some((f) => f.family === 'contract_integrity') ? 'breach' : 'ok', finding_ids: ids(teF.filter((f) => f.family === 'contract_integrity')) },
        { label: 'Protective safeguards', display: teF.some((f) => f.family === 'safeguards') ? 'unverified' : 'verified', flag: teF.some((f) => f.family === 'safeguards') ? 'warn' : 'ok', finding_ids: ids(teF.filter((f) => f.family === 'safeguards')) },
      ] },
    { key: 'risk_quality', title: 'Risk quality', status: status(rqF), headline: rqF.length ? rqF[0].title : 'No new losses; recommendations verified',
      metrics: [
        { label: 'Losses since bind', display: String(rqF.filter((f) => f.family === 'claims').length ? int(R, 1, 3) : 0), flag: rqF.some((f) => f.family === 'claims') ? 'warn' : 'ok', finding_ids: ids(rqF.filter((f) => f.family === 'claims')) },
        { label: 'Recommendations overdue', display: String(rqF.filter((f) => f.family === 'engineering').length), flag: rqF.some((f) => f.family === 'engineering') ? 'warn' : 'ok', finding_ids: ids(rqF.filter((f) => f.family === 'engineering')) },
      ] },
    { key: 'appetite_portfolio', title: 'Appetite & portfolio', status: status(apF), headline: apF.length ? apF[0].title : 'In appetite; no zone above 80%',
      metrics: [
        { label: 'Appetite (guidelines v2026)', display: apF.some((f) => f.family === 'appetite') ? 'Out of appetite' : 'In appetite', flag: apF.some((f) => f.family === 'appetite') ? 'breach' : 'ok', finding_ids: ids(apF.filter((f) => f.family === 'appetite')) },
        { label: 'Peak zone utilisation', display: apF.some((f) => f.family === 'portfolio') ? '91%' : `${int(R, 38, 76)}%`, flag: apF.some((f) => f.family === 'portfolio') ? 'breach' : 'ok', finding_ids: ids(apF.filter((f) => f.family === 'portfolio')) },
      ] },
    { key: 'retention', title: 'Retention & commercial', status: lr > 0.6 ? 'WATCH' : 'OK', headline: `${s.tenure_years}-year relationship · 5y loss ratio ${p1(lr)}`,
      metrics: [
        { label: '5-year loss ratio', display: p1(lr), flag: lr > 0.6 ? 'warn' : 'ok' },
        { label: 'Tenure', display: `${s.tenure_years} yrs`, flag: 'info' },
        { label: 'Broker', display: s.broker, flag: 'info' },
      ] },
    { key: 'net', title: 'Net & reinsurance', status: 'OK', headline: 'Within per-risk treaty retention', metrics: [
      { label: 'Net retained line', display: m(Math.min(s.limit * s.share, 25_000_000)), flag: 'info', note: 'Per-risk XoL attaches at $25M' },
      { label: 'Facultative needed', display: 'No', flag: 'ok' },
    ] },
  ];
}

// ------------------------------------------------------------------ narrative
export function narrativeFor(s: AccountSpec): Narrative {
  const mat = s.findings.filter((f) => f.material).sort((a, b) => b.impact_usd - a.impact_usd);
  if (s.pass === 0) return { text: `Renewal is outside the T-150 window; Pass 1 runs on ${addDays(s.expiry, -150)}.`, generated_by: 'template', model: null, critique: null };
  if (!mat.length) {
    return { text: `**${s.name} qualifies for fast-track.** No material findings across exposure, pricing, terms and risk quality. Values move in line with the cost trend and adequacy is above technical. Recommended: **maintain** on expiring terms.`, generated_by: 'template', model: null, critique: { summary: 'Fast-track decision upheld by critique pass', upheld: 1, challenged: 0 } };
  }
  const total = mat.reduce((a, f) => a + f.impact_usd, 0);
  const lines = mat.slice(0, 4).map((f) => `- ${f.title} [F:${f.finding_id}]`);
  const up = s.findings.filter((f) => f.critique?.verdict === 'UPHELD').length, ch = s.findings.filter((f) => f.critique?.verdict === 'CHALLENGED').length;
  return {
    text: `**${s.name} needs action before quoting** — ${mat.length} material finding${mat.length > 1 ? 's' : ''} worth ${k(total)}.\n\n${lines.join('\n')}\n\n**Recommended:** ${s.actions.map((a) => a.toLowerCase().replace(/_/g, ' ')).join(', ')}. Underwriter decides.`,
    generated_by: 'template', model: null,
    critique: { summary: `${up} upheld · ${ch} challenged`, upheld: up, challenged: ch },
  };
}

// ------------------------------------------------------------------ documents
export function docsFor(s: AccountSpec): DocumentMeta[] {
  const prior = termLabel(s.expiry), cur = nextTerm(s.expiry);
  const base = { account_id: s.id, account_name: s.name };
  const slug = s.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+$/, '');
  const out: DocumentMeta[] = [
    doc({ ...base, doc_id: `${s.id}-sov-prior`, doc_type: 'SOV', title: `Statement of values ${prior}`, filename: `${slug}_SOV_${prior.slice(0, 4)}.xlsx`, format: 'xlsx', term: prior, received_at: addDays(s.expiry, -400), size_bytes: 48_200, extraction: { status: 'EXTRACTED', fields: s.locations.length * 14, avg_confidence: 0.95 } }),
    doc({ ...base, doc_id: `${s.id}-quote-prior`, doc_type: 'Quote', title: `Quote v3 ${prior} (accepted)`, filename: `${slug}_quote_v3_${prior.slice(0, 4)}.pdf`, format: 'pdf', term: prior, received_at: addDays(s.expiry, -380), source_channel: 'Platform', size_bytes: 212_000 }),
    doc({ ...base, doc_id: `${s.id}-binder-prior`, doc_type: 'Binder', title: `Binder ${prior}`, filename: `${slug}_binder_${prior.slice(0, 4)}.pdf`, format: 'pdf', term: prior, received_at: addDays(s.expiry, -368), source_channel: 'Platform', size_bytes: 164_000 }),
    doc({ ...base, doc_id: `${s.id}-dec-prior`, doc_type: 'Declarations', title: `Declarations & forms schedule ${prior}`, filename: `${slug}_declarations_${prior.slice(0, 4)}.pdf`, format: 'pdf', term: prior, received_at: addDays(s.expiry, -360), source_channel: 'PAS (mock)', size_bytes: 318_000 }),
    doc({ ...base, doc_id: `${s.id}-lossrun`, doc_type: 'Loss run', title: 'Loss run — 5 years valued 2026-06-30', filename: `${slug}_loss_run_2026-06-30.pdf`, format: 'pdf', term: prior, received_at: '2026-07-02', source_channel: 'Claims (mock)', size_bytes: 96_000, extraction: { status: 'EXTRACTED', fields: 22, avg_confidence: 0.97 } }),
  ];
  if (s.pass >= 2) {
    out.push(
      doc({ ...base, doc_id: `${s.id}-sov-current`, doc_type: 'SOV', title: `Renewal statement of values ${cur}`, filename: `${slug}_SOV_${cur.slice(0, 4)}_renewal.xlsx`, format: 'xlsx', term: cur, received_at: addDays(s.expiry, -85), size_bytes: 52_900, extraction: { status: 'EXTRACTED', fields: s.locations.length * 14, avg_confidence: 0.92 } }),
      doc({ ...base, doc_id: `${s.id}-email-sub`, doc_type: 'Broker email', title: `Renewal submission — ${s.name}`, filename: `${slug}_renewal_submission.eml`, format: 'eml', term: cur, received_at: addDays(s.expiry, -85), size_bytes: 28_400, extraction: { status: 'EXTRACTED', fields: 6, avg_confidence: 0.88 } }),
      doc({ ...base, doc_id: `${s.id}-acord140`, doc_type: 'ACORD 140', title: 'ACORD 140 Property section', filename: `${slug}_ACORD140.pdf`, format: 'pdf', term: cur, received_at: addDays(s.expiry, -85), size_bytes: 141_000 }),
    );
  }
  if (s.findings.some((f) => f.family === 'engineering') || s.seed % 3 === 0) {
    out.push(doc({ ...base, doc_id: `${s.id}-eng`, doc_type: 'Engineering report', title: `Loss-control survey — ${s.locations[0]?.city ?? ''}`, filename: `${slug}_engineering_survey.pdf`, format: 'pdf', term: prior, received_at: addDays(s.expiry, -240), source_channel: 'Engineering (mock)', size_bytes: 1_240_000, extraction: { status: 'EXTRACTED', fields: 31, avg_confidence: 0.9 } }));
  }
  if (s.pass >= 1) {
    out.push(
      doc({ ...base, doc_id: `${s.id}-cat-exp`, doc_type: 'CAT exposure file', title: 'CAT exposure (OED) — current', filename: `${slug}_oed_location.csv`, format: 'csv', term: cur, received_at: addDays(s.expiry, -70), source_channel: 'CAT (mock)', size_bytes: 12_400 }),
      doc({ ...base, doc_id: `${s.id}-cat-ep`, doc_type: 'CAT EP curve', title: 'EP curve — current run', filename: `${slug}_ep_curve.json`, format: 'json', term: cur, received_at: addDays(s.expiry, -70), source_channel: 'CAT (mock)', size_bytes: 3_100 }),
    );
  }
  return out;
}

// ------------------------------------------------------------------ SOV workbook
export function sovXlsx(s: AccountSpec, which: 'prior' | 'current'): XlsxPayload {
  const rows = s.locations.filter((l) => (which === 'prior' ? l.match_status !== 'NEW' : l.match_status !== 'DELETED'));
  const hdr = ['Loc #', 'Location name', 'Street address', 'City', 'State', 'Occupancy', 'Construction', 'Year built', 'Stories', 'Sq ft', 'Roof year', 'Sprinkler', 'Building value', 'Contents', 'Business income', 'Total insured value', 'Internal ref'];
  const cols = 'ABCDEFGHIJKLMNOPQ'.split('');
  const cells: XlsxSheet['cells'] = {};
  const yr = which === 'prior' ? termLabel(s.expiry) : nextTerm(s.expiry);
  cells.A1 = { v: `${s.name} — Statement of Values ${yr}`, t: 's', bold: true };
  cells.A2 = { v: `Prepared by ${s.broker} · values in USD`, t: 's' };
  hdr.forEach((h, i) => { cells[`${cols[i]}3`] = { v: h, t: 's', bold: true, fill: '#e8edf5' }; });
  rows.forEach((l, i) => {
    const r = 4 + i;
    const tiv = (which === 'prior' ? l.tiv_prior : l.tiv_current) ?? 0;
    const vals: (string | number | null)[] = [
      which === 'prior' ? l.loc_no_prior : l.loc_no_current, l.name, l.address, l.city, l.state,
      which === 'prior' ? l.occupancy_prior ?? l.occupancy : l.occupancy, l.construction, l.year_built, l.stories, l.sqft, l.roof_year, l.sprinkler,
      round(tiv * 0.62, 1000), round(tiv * 0.23, 1000), round(tiv * 0.15, 1000), tiv, `NG-${hash(l.location_uid).slice(0, 5)}`,
    ];
    vals.forEach((v, j) => { cells[`${cols[j]}${r}`] = v === null ? { v: null, t: 'z' } : typeof v === 'number' ? { v, t: 'n', num_fmt: j >= 12 ? '#,##0' : '0' } : { v, t: 's' }; });
  });
  const tr = 4 + rows.length;
  cells[`A${tr}`] = { v: 'TOTAL', t: 's', bold: true };
  cells[`P${tr}`] = { v: rows.reduce((a, l) => a + ((which === 'prior' ? l.tiv_prior : l.tiv_current) ?? 0), 0), t: 'n', f: `SUM(P4:P${tr - 1})`, bold: true, num_fmt: '#,##0' };
  const sheet: XlsxSheet = {
    name: `SOV ${yr.slice(0, 4)}`, hidden: false, max_row: tr, max_col: 17, cells, merges: ['A1:P1'], hidden_rows: [], hidden_cols: ['Q'],
    col_widths: { A: 7, B: 26, C: 26, D: 14, E: 6, F: 22, G: 22, H: 9, I: 7, J: 9, K: 9, L: 16, M: 14, N: 12, O: 14, P: 16, Q: 10 }, freeze: 'C4',
  };
  const notes: XlsxSheet = { name: 'Broker notes', hidden: true, max_row: 3, max_col: 1, cells: { A1: { v: 'Values carried forward from prior year unless noted', t: 's' }, A2: { v: 'Roof years per insured, not verified', t: 's' } }, merges: [], hidden_rows: [], hidden_cols: [], col_widths: { A: 60 }, freeze: null };
  return { sheets: [sheet, notes] };
}

export function sovRowAnchor(s: AccountSpec, l: LocationRow, col: string, which: 'prior' | 'current' = 'current'): Anchor {
  const rows = s.locations.filter((x) => (which === 'prior' ? x.match_status !== 'NEW' : x.match_status !== 'DELETED'));
  const r = 4 + Math.max(0, rows.findIndex((x) => x.location_uid === l.location_uid));
  return xlsA(`${s.id}-sov-${which}`, `SOV ${(which === 'prior' ? termLabel(s.expiry) : nextTerm(s.expiry)).slice(0, 4)}`, `${col}${r}`, `A${r}:P${r}`);
}

// ------------------------------------------------------------------ observations
export function locationObs(s: AccountSpec): Observation[] {
  const which = s.pass >= 2 ? 'current' : 'prior';
  const out: Observation[] = [];
  for (const l of s.locations) {
    if (l.match_status === 'DELETED') continue;
    const tiv = (which === 'current' ? l.tiv_current : l.tiv_prior) ?? 0;
    const common = { subject_type: 'location' as const, subject_id: l.location_uid, subject_label: `Loc ${l.loc_no_current ?? l.loc_no_prior} · ${l.name}`, obs_type: 'C' as const, source_family: 'Broker / insured', source_label: `${which === 'current' ? nextTerm(s.expiry) : termLabel(s.expiry)} SOV`, vendor: null, model_version: null, verification_status: 'UNVERIFIED' as const, valid_from: addDays(s.expiry, -85), recorded_at: addDays(s.expiry, -85), is_resolved: true };
    out.push({ ...common, obs_id: `ob-${l.location_uid}-tiv`, field_code: 'tiv', field_label: 'Total insured value', value: tiv, value_display: `$${tiv.toLocaleString('en-US')}`, unit: 'USD', anchor: sovRowAnchor(s, l, 'P', which), confidence: 0.97 });
    out.push({ ...common, obs_id: `ob-${l.location_uid}-roof`, field_code: 'roof_year', field_label: 'Roof year', value: l.roof_year, value_display: String(l.roof_year ?? 'blank'), anchor: sovRowAnchor(s, l, 'K', which), confidence: l.roof_year ? 0.9 : 0.2 });
    out.push({ ...common, obs_id: `ob-${l.location_uid}-occ`, field_code: 'occupancy', field_label: 'Occupancy', value: l.occupancy, value_display: l.occupancy, anchor: sovRowAnchor(s, l, 'F', which), confidence: 0.93 });
    out.push({ ...common, obs_id: `ob-${l.location_uid}-const`, field_code: 'construction', field_label: 'Construction', value: l.construction, value_display: l.construction, anchor: sovRowAnchor(s, l, 'G', which), confidence: 0.91 });
  }
  return out;
}

export function findingObs(s: AccountSpec): Observation[] {
  const out: Observation[] = [];
  for (const f of s.findings) {
    if (f.evidence_obs_ids.length) continue;
    const id = `ob-${f.finding_id}`;
    f.evidence_obs_ids = [id];
    const fromClaims = f.family === 'claims', fromEng = f.family === 'engineering';
    out.push({
      obs_id: id, subject_type: f.subject_type === 'location' ? 'location' : 'account', subject_id: f.subject_id, subject_label: f.subject_label,
      field_code: f.family, field_label: FAMILY_LABEL[f.family] ?? f.family, value: f.observed, value_display: f.observed,
      obs_type: fromClaims || fromEng ? 'S' : f.family === 'pricing' ? 'D' : 'C',
      source_family: fromClaims ? 'Carrier systems' : fromEng ? 'Engineering' : f.family === 'pricing' ? 'Platform' : 'Broker / insured',
      source_label: fromClaims ? 'Claims system (mock)' : fromEng ? 'Recommendation register' : f.family === 'pricing' ? 'RARC split (rater-stub v1.4)' : 'Renewal SOV',
      anchor: fromClaims ? sysA('Claims (mock)', `CLM-${hash(f.finding_id).slice(0, 6)}`) : fromEng ? sysA('Engineering (mock)', `REC-${hash(f.finding_id).slice(0, 4)}`) : f.family === 'pricing' ? { doc_id: null, kind: 'derived', text: f.observed } : (s.pass >= 2 ? xlsA(`${s.id}-sov-current`, `SOV ${nextTerm(s.expiry).slice(0, 4)}`, 'P4', 'A4:P4') : xlsA(`${s.id}-sov-prior`, `SOV ${termLabel(s.expiry).slice(0, 4)}`, 'P4', 'A4:P4')),
      vendor: null, model_version: f.family === 'pricing' ? 'rater-stub v1.4' : null, confidence: f.confidence, verification_status: fromClaims ? 'VERIFIED' : 'UNVERIFIED',
      valid_from: f.created_at, recorded_at: f.created_at, is_resolved: true,
    });
  }
  return out;
}

// ------------------------------------------------------------------ contract
export function contractFor(s: AccountSpec): ContractDiff {
  const t = s.rarc?.expiring_terms;
  const A = (col: string, page: number, y: number): Anchor => pdfA(`${s.id}-${col}-prior`, page, [72, y, 540, y + 14]);
  const row = (field: string, label: string, group: ContractDiffRow['group'], v: string, y: number): ContractDiffRow => ({
    field, label, group, values: { quote: v, binder: v, policy: v, endorsed: v },
    anchors: { quote: A('quote', 2, y), binder: A('binder', 1, y), policy: A('dec', 2, y), endorsed: A('dec', 2, y) }, result: 'MATCH', finding_id: null,
  });
  const rows: ContractDiffRow[] = [
    row('limit', s.limit_basis === 'loss_limit' ? 'Loss limit' : 'Blanket limit', 'Limits', m(s.limit), 180),
    ...(s.share < 1 ? [row('share', 'Carrier participation', 'Limits', `${(s.share * 100).toFixed(0)}% of ${s.layer}`, 196)] : []),
    row('aop', 'AOP deductible', 'Deductibles', t ? k(t.aop_deductible) : '$25K', 240),
    ...(t?.named_storm_ded_pct != null ? [row('ns', 'Named storm deductible', 'Deductibles', `${(t.named_storm_ded_pct * 100).toFixed(0)}% per location, ${k(t.named_storm_ded_min ?? 100000)} min`, 256)] : []),
    ...(t?.bi_sublimit ? [row('bi', 'Business income sublimit', 'Sublimits', m(t.bi_sublimit), 300)] : []),
    ...(t?.flood_sublimit ? [row('flood', 'Flood sublimit (outside SFHA)', 'Sublimits', m(t.flood_sublimit), 316)] : []),
    row('cp0010', 'CP 00 10 Building & personal property', 'Forms', 'Attached', 380),
    row('cp0030', 'CP 00 30 Business income', 'Forms', 'Attached', 396),
    row('cp1030', 'CP 10 30 Causes of loss — special', 'Forms', 'Attached', 412),
    row('p1', 'P-1 Automatic sprinkler (CP 04 11)', 'Safeguards', 'Required', 460),
    row('premium', 'Annual premium', 'Premium', `$${s.premium.toLocaleString('en-US')}`, 520),
  ];
  return {
    term: termLabel(s.expiry), quote_version: 'v3', rows,
    endorsements: [{ endt_id: `${s.id}-e1`, effective: addDays(s.expiry, -250), type: 'Additional insured', description: 'Add lender as loss payee', premium_delta: 0, doc_id: null }],
    subjectivities: [], quotes: [], referrals: [],
  };
}

// ------------------------------------------------------------------ CAT
export function catFor(s: AccountSpec): CatResult[] {
  const R = rng(s.seed + 31);
  const locs = s.locations.filter((l) => l.match_status !== 'DELETED');
  const aal = locs.reduce((a, l) => a + (l.aal ?? 0), 0) || Math.round((s.premium * between(R, 0.05, 0.22)));
  const total = locs.reduce((a, l) => a + (l.aal ?? 0), 0) || aal;
  const wind = s.rarc?.wind_floor != null;
  const perils = wind ? [['Named storm', 0.71], ['Severe convective', 0.14], ['Flood', 0.11], ['Earthquake', 0.03], ['Wildfire', 0.01]] : [['Severe convective', 0.46], ['Flood', 0.24], ['Earthquake', 0.2], ['Winter storm', 0.08], ['Wildfire', 0.02]];
  const oep = (x: number) => [[10, 7], [25, 24], [50, 52], [100, 88], [250, 142], [500, 184], [1000, 222]].map(([rp, f]) => ({ rp, loss: Math.round(x * f) }));
  const aep = (x: number) => oep(x * 1.08);
  const mk = (snapshot: CatResult['snapshot'], mult: number, date: string): CatResult => ({
    run_id: `${s.id}-cat-${snapshot.toLowerCase()}`, account_id: s.id, snapshot,
    vendor: "MockCat (stand-in for Moody's RMS / Verisk)", model_version: 'MockCat 23.1 · HU/SCS/FL/EQ', run_date: date, perils: perils.map((p) => p[0] as string),
    basis: s.share < 1 ? `Carrier share ${(s.share * 100).toFixed(0)}% of ${s.layer}, net of deductibles` : 'Carrier share 100%, net of deductibles',
    aal_total: Math.round(total * mult),
    aal_by_peril: perils.map(([p, f]) => ({ peril: p as string, aal: Math.round(total * mult * (f as number)) })),
    oep: oep(total * mult), aep: aep(total * mult),
    location_contrib: locs.map((l) => ({ location_uid: l.location_uid, label: `Loc ${l.loc_no_current ?? l.loc_no_prior} · ${l.city}, ${l.state}`, aal: Math.round((l.aal ?? total / locs.length) * mult), pct: (l.aal ?? total / locs.length) / total, tiv: l.tiv_current ?? l.tiv_prior ?? 0 })).sort((a, b) => b.aal - a.aal),
    dq_flags: locs.filter((l) => !l.roof_year || !l.year_built).slice(0, 4).map((l) => ({ location_uid: l.location_uid, label: l.name, field: !l.roof_year ? 'roof_year' : 'year_built', issue: 'Missing — model defaulted to regional average', impact: 'MEDIUM' as const })),
    input_mismatches: [], exposure_doc_id: `${s.id}-cat-exp`, elt_doc_id: null, ep_doc_id: `${s.id}-cat-ep`,
    compare: [],
  });
  const cur = mk('CURRENT', 1, addDays(s.expiry, -70));
  const bound = mk('AS_BOUND', 0.94, addDays(s.expiry, -380));
  cur.compare = [
    { label: `As bound ${termLabel(s.expiry)}`, aal_total: bound.aal_total, oep_100: bound.oep[3].loss, oep_250: bound.oep[4].loss },
    { label: 'Current exposure', aal_total: cur.aal_total, oep_100: cur.oep[3].loss, oep_250: cur.oep[4].loss },
  ];
  return [cur, bound];
}

// ------------------------------------------------------------------ claims & engineering
export function claimsFor(s: AccountSpec): ClaimsEngineering {
  const R = rng(s.seed + 57);
  const causes = ['Water damage', 'Fire', 'Wind / hail', 'Theft', 'Equipment breakdown', 'Freeze'];
  const hasClaims = s.findings.some((f) => f.family === 'claims');
  const nC = hasClaims ? int(R, 3, 6) : int(R, 0, 2);
  const claims: Claim[] = Array.from({ length: nC }, (_, i) => {
    const l = pick(R, s.locations);
    const inc = round(between(R, 18_000, 420_000), 1000);
    const date = addDays(CLOCK0, -int(R, 30, 1700));
    const open = daysBetween(date, CLOCK0) < 150;
    return { claim_id: `CLM-${hash(s.id + i).slice(0, 6).toUpperCase()}`, location_uid: l?.location_uid ?? null, location_label: l ? `${l.city}, ${l.state}` : '—', date_of_loss: date, cause: pick(R, causes), cat_event: null, status: (open ? 'OPEN' : 'CLOSED') as Claim['status'], paid: open ? round(inc * 0.4, 1000) : inc, reserve: open ? round(inc * 0.6, 1000) : 0, incurred: inc, description: 'Reported via broker; adjuster assigned', linked_recommendation: null };
  }).sort((a, b) => b.date_of_loss.localeCompare(a.date_of_loss));
  const byCause = new Map<string, { count: number; incurred: number }>();
  claims.forEach((c) => { const x = byCause.get(c.cause) ?? { count: 0, incurred: 0 }; x.count++; x.incurred += c.incurred; byCause.set(c.cause, x); });
  const incurred = claims.reduce((a, c) => a + c.incurred, 0);
  const recs: Recommendation[] = s.findings.filter((f) => f.family === 'engineering').map((f, i) => {
    const l = s.locations[i % s.locations.length];
    const due = addDays(CLOCK0, -int(R, 20, 140));
    return { rec_id: `R-${200 + i + (s.seed % 60)}`, location_uid: l.location_uid, location_label: `${l.city}, ${l.state}`, raised: addDays(due, -180), category: 'Fire protection', description: f.title, severity: f.severity, due, status: 'OPEN', bind_condition: false, days_overdue: daysBetween(due, CLOCK0), completion_evidence: null, doc_id: `${s.id}-eng` };
  });
  if (recs.length === 0 && s.locations[0]) {
    const l = s.locations[0];
    recs.push({ rec_id: `R-${100 + (s.seed % 80)}`, location_uid: l.location_uid, location_label: `${l.city}, ${l.state}`, raised: '2025-02-11', category: 'Housekeeping', description: 'Maintain 18 in clearance below sprinkler deflectors', severity: 'LOW', due: '2025-05-11', status: 'VERIFIED_CLOSED', bind_condition: false, days_overdue: 0, completion_evidence: 'Photo evidence + engineer sign-off 2025-05-02', doc_id: null });
  }
  return {
    claims,
    summary: { count_5y: claims.length, incurred_5y: incurred, loss_ratio_5y: incurred / (s.premium * 5), by_cause: [...byCause.entries()].map(([cause, v]) => ({ cause, ...v })).sort((a, b) => b.incurred - a.incurred) },
    recommendations: recs,
    surveys: s.locations.slice(0, 2).map((l, i) => ({ survey_id: `SV-${hash(l.location_uid).slice(0, 5)}`, location_label: `${l.city}, ${l.state}`, date: addDays(CLOCK0, -200 - i * 160), engineer: 'Elena Brooks', doc_id: i === 0 ? `${s.id}-eng` : null })),
  };
}

// ------------------------------------------------------------------ timeline
export function timelineFor(s: AccountSpec): TimelineEvent[] {
  const e: TimelineEvent[] = [
    ev(`${s.id}-t1`, addDays(s.expiry, -372), 'user', '10', 'Bound quote v3', `Premium $${s.premium.toLocaleString('en-US')}`, userName(s.underwriter_id), { doc_id: `${s.id}-binder-prior` }),
    ev(`${s.id}-t2`, addDays(s.expiry, -365), 'mock', '11', 'Policy issued', `${s.policy_no} · dec page + forms schedule generated`, 'PAS (mock)', { doc_id: `${s.id}-dec-prior` }),
  ];
  if (s.pass >= 1) e.push(ev(`${s.id}-t3`, addDays(s.expiry, -150), 'engine', '15', 'Pass 1 · internal drift scan', `${s.findings.filter((f) => f.pass === 1).length} findings on data already held`, 'Renewal engine', { finding_ids: s.findings.filter((f) => f.pass === 1).map((f) => f.finding_id) }));
  if (s.pass >= 2) {
    e.push(ev(`${s.id}-t4`, addDays(s.expiry, -85), 'document', '01', 'Renewal submission received', `SOV, ACORD 140 from ${s.broker}`, s.broker_contact, { doc_id: `${s.id}-email-sub` }));
    e.push(ev(`${s.id}-t5`, addDays(s.expiry, -85), 'engine', '04', 'Extraction & enrichment', `${s.locations.length * 14} fields extracted; geocoded; hazard scores attached`, 'Ingestion'));
    e.push(ev(`${s.id}-t6`, addDays(s.expiry, -84), 'engine', '15', 'Pass 2 · submission delta', `${s.findings.filter((f) => f.pass === 2).length} findings`, 'Renewal engine', { finding_ids: s.findings.filter((f) => f.pass === 2).map((f) => f.finding_id) }));
  }
  return e.filter((x) => x.date <= CLOCK0).sort((a, b) => b.date.localeCompare(a.date));
}

// ------------------------------------------------------------------ bundle
export function buildBundle(s: AccountSpec): AccountBundle {
  const obs = [...locationObs(s), ...findingObs(s), ...(s.observations ?? [])];
  const docs = s.docs ?? docsFor(s);
  const tiv_expiring = s.locations.reduce((a, l) => a + (l.tiv_prior ?? 0), 0);
  const tiv_current = s.pass >= 2 ? s.locations.reduce((a, l) => a + (l.tiv_current ?? 0), 0) : tiv_expiring;
  const detail: AccountDetail = {
    account_id: s.id, name: s.name, scenario: s.scenario, scenario_title: s.scenario_title, segment: s.segment,
    occupancy_family: s.occupancy_family, broker: s.broker, broker_contact: s.broker_contact,
    underwriter: userName(s.underwriter_id), underwriter_id: s.underwriter_id, state: s.state, tenure_years: s.tenure_years,
    policy: policyFor(s),
    renewal: {
      expiry: s.expiry, days_to_expiry: daysBetween(CLOCK0, s.expiry), pass: s.pass, status: s.status,
      integrity_score: integrityScore(s.findings), recommended_actions: s.actions, confidence: s.confidence,
      owner: userName(s.underwriter_id), due: s.status === 'FAST_TRACK' ? addDays(s.expiry, -45) : addDays(s.expiry, -60),
      notice: noticeFor(s), missing: s.missing,
    },
    deltas: s.deltas ?? deltasFor(s),
    findings: s.findings,
    actions: s.actions.map((a, i) => ({
      action_id: `${s.id}-a${i}`, account_id: s.id, type: a, title: ACTION_TITLE[a], detail: '',
      finding_ids: s.findings.filter((f) => ACTION_FAMILIES[a]?.includes(f.family)).map((f) => f.finding_id),
      owner: a === 'REFER' ? 'Priya Raman' : a === 'CONDITION' ? 'Elena Brooks' : userName(s.underwriter_id),
      due: addDays(s.expiry, a === 'DATA_REQUEST' ? -70 : -45), status: 'PROPOSED',
      impact_usd: s.findings.filter((f) => ACTION_FAMILIES[a]?.includes(f.family)).reduce((x, f) => x + f.impact_usd, 0),
    })),
    narrative: s.narrative ?? narrativeFor(s),
    locations: s.locations,
    timeline: s.timeline ?? timelineFor(s),
    documents: docs,
    site_model_doc_id: s.site_model_doc_id ?? null,
  };
  const xlsx: Record<string, XlsxPayload> = { [`${s.id}-sov-prior`]: sovXlsx(s, 'prior'), ...(s.pass >= 2 ? { [`${s.id}-sov-current`]: sovXlsx(s, 'current') } : {}), ...(s.xlsx ?? {}) };
  const eml: Record<string, EmlPayload> = {
    [`${s.id}-email-sub`]: {
      from: s.broker_contact, to: ['property.renewals@northgate-specialty.example'], cc: [`${userName(s.underwriter_id).toLowerCase().replace(' ', '.')}@northgate-specialty.example`],
      subject: `${s.name} — ${nextTerm(s.expiry)} property renewal submission`, date: addDays(s.expiry, -85) + 'T14:12:00Z',
      text: `Hi team,\n\nPlease find attached the renewal submission for ${s.name} (${s.policy_no}), expiring ${s.expiry}.\n\nAttached: updated SOV, ACORD 140, 5-year loss runs.\n\nWe'd appreciate indications by ${addDays(s.expiry, -45)}.\n\nBest,\n${s.broker_contact}`,
      html: null,
      attachments: [
        { filename: docs.find((d) => d.doc_id === `${s.id}-sov-current`)?.filename ?? 'SOV.xlsx', doc_id: `${s.id}-sov-current`, size_bytes: 52_900, content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
        { filename: 'ACORD140.pdf', doc_id: `${s.id}-acord140`, size_bytes: 141_000, content_type: 'application/pdf' },
      ],
      highlights: [],
    },
    ...(s.eml ?? {}),
  };
  const extraction: Record<string, ExtractionPayload> = {};
  for (const d of docs.filter((x) => x.doc_type === 'SOV')) {
    const which = d.doc_id.endsWith('prior') ? 'prior' : 'current';
    extraction[d.doc_id] = {
      doc_id: d.doc_id, method: 'SOV parser v2 (header band detection + synonym map)',
      fields: s.locations.filter((l) => (which === 'prior' ? l.match_status !== 'NEW' : l.match_status !== 'DELETED')).slice(0, 12).flatMap((l) => [
        { obs_id: `ob-${l.location_uid}-tiv`, field_code: 'tiv', label: 'TIV', subject_label: l.name, value_display: m((which === 'prior' ? l.tiv_prior : l.tiv_current) ?? 0), anchor: sovRowAnchor(s, l, 'P', which), confidence: 0.97 },
        { obs_id: `ob-${l.location_uid}-roof`, field_code: 'roof_year', label: 'Roof year', subject_label: l.name, value_display: String(l.roof_year ?? '—'), anchor: sovRowAnchor(s, l, 'K', which), confidence: l.roof_year ? 0.9 : 0.2 },
      ]),
      issues: [{ code: 'TOTALS_ROW', label: 'Totals row detected and excluded', anchor: xlsA(d.doc_id, `SOV ${(which === 'prior' ? termLabel(s.expiry) : nextTerm(s.expiry)).slice(0, 4)}`, `A${4 + s.locations.length}`), severity: 'LOW' }, { code: 'HIDDEN_COL', label: 'Hidden column Q (internal ref) ignored', anchor: null, severity: 'LOW' }],
    };
  }
  const cat = s.cat ?? (s.pass >= 1 ? catFor(s) : []);
  const raw: Record<string, string> = {};
  if (cat[0]) {
    raw[`${s.id}-cat-exp`] = ['LocNumber,AccNumber,StreetAddress,City,AreaCode,Latitude,Longitude,OccupancyCode,ConstructionCode,YearBuilt,NumberOfStoreys,RoofYear,BuildingTIV,ContentsTIV,BITIV',
      ...s.locations.filter((l) => l.match_status !== 'DELETED' && l.match_status !== 'NEW').map((l) => [l.loc_no_current ?? l.loc_no_prior, s.policy_no, `"${l.address}"`, l.city, l.state, l.lat.toFixed(4), l.lon.toFixed(4), 1100, 5100, l.year_built ?? '', l.stories ?? '', l.roof_year ?? '', round((l.tiv_prior ?? 0) * 0.62, 1000), round((l.tiv_prior ?? 0) * 0.23, 1000), round((l.tiv_prior ?? 0) * 0.15, 1000)].join(','))].join('\n');
    raw[`${s.id}-cat-ep`] = JSON.stringify({ run_id: cat[0].run_id, vendor: cat[0].vendor, model_version: cat[0].model_version, basis: cat[0].basis, aal: cat[0].aal_total, oep: cat[0].oep, aep: cat[0].aep }, null, 2);
  }
  return {
    detail, rarc: s.rarc, contract: s.contract ?? contractFor(s), cat, claims: s.claims ?? claimsFor(s),
    observations: obs, xlsx, eml, extraction, raw,
    premium_expiring: s.premium, tiv_expiring, tiv_current,
  };
}

export const ACTION_TITLE: Record<ActionType, string> = {
  MAINTAIN: 'Confirm renewal on expiring terms', REPRICE: 'Reprice to technical', RESTRUCTURE: 'Restructure deductibles / sublimits',
  CONDITION: 'Impose engineering condition / subjectivity', DATA_REQUEST: 'Request missing data from broker', REFER: 'Refer to senior underwriter',
  CONDITIONAL_RENEWAL_NOTICE: 'Issue conditional renewal notice', NON_RENEW: 'Issue non-renewal notice', ENDORSEMENT_CORRECTION: 'Correct issued policy by endorsement',
};
export const ACTION_FAMILIES: Partial<Record<ActionType, string[]>> = {
  REPRICE: ['pricing', 'valuation', 'occupancy'], RESTRUCTURE: ['cat_terms'], CONDITION: ['engineering', 'safeguards', 'security', 'occupancy'],
  DATA_REQUEST: ['data_quality', 'cat_data', 'valuation'], REFER: ['portfolio', 'authority', 'appetite', 'pricing'],
  NON_RENEW: ['appetite'], CONDITIONAL_RENEWAL_NOTICE: ['appetite'], ENDORSEMENT_CORRECTION: ['contract_integrity'], MAINTAIN: [],
};
