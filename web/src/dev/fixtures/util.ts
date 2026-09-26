// Deterministic helpers for fixture generation.
import type { Anchor, DocumentMeta, Finding, LocationRow, Severity, TimelineEvent } from '@/api/types';

export const CLOCK0 = '2026-08-01';

export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export type Rng = ReturnType<typeof rng>;
export const pick = <T,>(r: Rng, xs: readonly T[]): T => xs[Math.floor(r() * xs.length)];
export const between = (r: Rng, a: number, b: number) => a + (b - a) * r();
export const int = (r: Rng, a: number, b: number) => Math.floor(between(r, a, b + 1));
export function shuffleInPlace<T>(r: Rng, xs: T[]) { for (let i = xs.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [xs[i], xs[j]] = [xs[j], xs[i]]; } return xs; }
export const round = (n: number, step = 1) => Math.round(n / step) * step;

export function addDays(iso: string, d: number) {
  const t = new Date(iso + 'T00:00:00Z');
  t.setUTCDate(t.getUTCDate() + d);
  return t.toISOString().slice(0, 10);
}
export function daysBetween(a: string, b: string) {
  return Math.round((new Date(b + 'T00:00:00Z').getTime() - new Date(a + 'T00:00:00Z').getTime()) / 86400000);
}
export const m = (n: number) => `$${(n / 1e6).toFixed(1)}M`;
export const k = (n: number) => `$${Math.round(n / 1e3)}K`;
export const p1 = (r: number, sign = false) => `${sign && r > 0 ? '+' : r < 0 ? '−' : ''}${Math.abs(r * 100).toFixed(1)}%`;
export const hash = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16).padStart(8, '0');
};

export const SEV_W: Record<Severity, number> = { CRITICAL: 10, HIGH: 5, MEDIUM: 2.5, LOW: 1 };

// ------------------------------------------------------------------ builders
export function loc(p: Partial<LocationRow> & Pick<LocationRow, 'location_uid' | 'name' | 'city' | 'state' | 'lat' | 'lon'>): LocationRow {
  const tp = p.tiv_prior ?? null, tc = p.tiv_current ?? null;
  return {
    loc_no_prior: null, loc_no_current: null, address: '', match_status: 'MATCHED', match_method: 'address+geocode', match_score: 0.98,
    match_confirmed_by: null, tiv_prior: tp, tiv_current: tc,
    tiv_change_pct: tp && tc ? tc / tp - 1 : null,
    occupancy: 'Office', occupancy_prior: null, construction: 'Masonry non-combustible', year_built: 1998, stories: 2, sqft: 60000,
    roof_year: 2012, sprinkler: 'Wet pipe, full', valuation_ratio: 0.92, wind_tier: null, cat_zone: null, aal: null, buildings: 1,
    flags: [], model_doc_id: null, imagery_doc_ids: [],
    ...p,
  };
}

export function fnd(p: Partial<Finding> & Pick<Finding, 'finding_id' | 'account_id' | 'title' | 'family' | 'severity' | 'observed' | 'expected' | 'impact_usd'>): Finding {
  const conf = p.confidence ?? 0.9;
  return {
    subject_type: 'account', subject_id: p.account_id, subject_label: 'Account', rule_id: 'GEN.RULE', rule_version: 1,
    description: '', outcome: 'FLAG', impact_method: 'rate_on_line', confidence: conf,
    materiality_score: Math.round(p.impact_usd * conf), material: p.impact_usd * conf >= 5000,
    evidence_obs_ids: [], conflicting_obs_ids: [], status: 'OPEN', disposition: null, pass: 2, created_at: '2026-07-29',
    critique: { verdict: 'UPHELD', note: 'Evidence consistent across sources.' }, source: 'Property UW Guidelines 2026',
    ...p,
  };
}

export function doc(p: Partial<DocumentMeta> & Pick<DocumentMeta, 'doc_id' | 'doc_type' | 'title' | 'filename' | 'format'>): DocumentMeta {
  return {
    account_id: null, account_name: null, received_at: '2026-07-28', source_channel: 'Broker email',
    size_bytes: 184_000, term: '2026–2027', is_sample: true,
    extraction: ['pdf', 'xlsx', 'eml'].includes(p.format) ? { status: 'EXTRACTED', fields: 40, avg_confidence: 0.93 } : { status: 'NOT_APPLICABLE', fields: 0, avg_confidence: null },
    ...p,
  };
}

export function ev(id: string, date: string, kind: TimelineEvent['kind'], stage: string, title: string, detail: string, actor: string, extra: Partial<TimelineEvent> = {}): TimelineEvent {
  return { event_id: id, date, kind, stage, title, detail, actor, ...extra };
}

export const pdfA = (doc_id: string, page: number, bbox: [number, number, number, number], text?: string): Anchor =>
  ({ doc_id, kind: 'pdf', page, bbox, page_size: [612, 792], text });
export const xlsA = (doc_id: string, sheet: string, cell: string, range?: string, text?: string): Anchor =>
  ({ doc_id, kind: 'xlsx', sheet, cell, range, text });
export const sysA = (system: string, record_id: string, text?: string): Anchor => ({ doc_id: null, kind: 'system', system, record_id, text });
