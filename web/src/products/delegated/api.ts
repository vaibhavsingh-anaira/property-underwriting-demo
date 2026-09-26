// Delegated Authority Control — API types and hooks (local to this product).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Anchor, DocumentMeta, Severity, TimelineEvent } from '@/api/types';

export type ExcStatus = 'OPEN' | 'QUERIED' | 'RESPONDED' | 'ESCALATED' | 'ACCEPTED' | 'RESOLVED' | 'AUTHORISED';
export interface TrendPoint { month: string; rate: number; policies: number; with_exceptions: number }
export interface MonthStats {
  month: string; policies: number; with_exceptions: number; exception_rate: number; open_policies: number; within_authority: number; premium: number;
  premium_tied: number; commission_discrepancy: number; exposure_above: number; missing_referrals: number; by_type: Record<string, number>; exceptions: number; open: number;
}
export interface Rarc {
  quarter: string; months: string[]; label: string; renewals: number; used: number; excluded: number; expiring_premium: number; renewal_premium: number; expected_premium: number;
  headline: number | null; rarc: number | null; exposure_change: number | null; rate_on_tiv: number | null; rate_on_tiv_prior: number | null; rate_on_line: number | null;
  by_month: { month: string; renewals: number; headline: number | null; rarc: number | null }[];
}
export interface ChSummary {
  id: string; scenario: string; name: string; short: string; program: string; agreement: string; umr: string; pin: string; broker: string; contact: string; hq: string;
  story: string; title: string; period: [string, string]; authority_version: number; commission: number; max_limit: number; grade: string; score: number;
  within_authority: number; direction: string; trend: TrendPoint[]; latest_month: string | null; latest: MonthStats | null; open_exceptions: number; open_policies: number;
  at_stake: number; premium_tied: number; commission_open: number; top_zone: { zone: string; name: string; util: number; warn: number; status: string } | null;
  gpi_util: number | null; dq_score: number | null; avg_days_late: number; loss_ratio: number | null; turnaround_days: number | null; open_queries: number; rarc: Rarc | null;
  policies: number; gwp: number;
}
export interface Zone { zone: string; name: string; peril: string; limit: number; warn: number; status: string; tiv: number; opening: number; movement: number; policies: number; new_tiv: number; util: number; pml_100: number; anchor: Anchor | null }
export interface Scorecard {
  grade: string; score: number; within_authority: number; trend: TrendPoint[]; direction: string; dq_score: number | null; avg_days_late: number; on_time: number; gwp: number;
  incurred: number; loss_ratio: number | null; turnaround_days: number | null; open_queries: number; components: Record<string, number>;
}
export interface Report extends MonthStats { ch: string; zones: Zone[]; types: { family: string; label: string; count: number; open: number; impact_usd: number; premium_tied: number }[]; trend: TrendPoint[]; direction: string; recommendations: string[]; grade: string }
export interface Sourced { anchor: Anchor | null; doc_id: string | null }
export interface AuthorityView {
  version: number; kv: ({ key: string; label: string; value: string } & Sourced)[];
  classes: ({ code: string; label: string; rate: number; status: string } & Sourced)[];
  territories: ({ key: string; state: string; county: string; tier: string; factor: number | null; status: string } & Sourced)[];
  min_aop: ({ from: number; to: number | null; min: number } & Sourced)[]; ded_factors: ({ deductible: number; factor: number } & Sourced)[];
  construction: ({ iso: number; factor: number } & Sourced)[]; prohibited: ({ code: string; label: string } & Sourced)[];
  aggregates: ({ zone: string; name: string; peril: string; limit: number; warn: number; status: string } & Sourced)[];
  versions: { version: number; kind: string; number: number; title: string; doc_id: string; effective: string; issued: string; changes: { label: string; from: string; to: string }[]; terms: number; in_force: boolean }[];
}
export interface BdxRow { doc_id: string; ch: string; ch_name: string; kind: string; month: string; title: string; received: string; due: string; days_late: number; rows: number; dq_score: number; mapping_confidence: number; missing: string[]; issues: number; issues_high: number; correction: boolean; superseded_by: string | null; replaces: string | null; exceptions: number }
export interface Claim { claim_ref: string; certificate_ref: string; insured_name: string; state: string; date_of_loss: string; date_reported: string; cause: string; description: string; status: string; paid: number; reserve: number; incurred: number; prior_incurred: number | null; incurred_change: number; first_seen: string; days_to_carrier: number | null; handled_by: string; anchor: Anchor | null; doc_id: string; exceptions: { exc_id: string; title: string; severity: Severity }[] }
export interface Query { query_id: string; ch: string; kind: string; created: string; by: string; items: { policy_key: string; certificate_ref: string; insured: string; exc_ids: string[]; lines: string[] }[]; status: string; due: string; doc_id: string; response: string | null; responded: string | null; summary: Record<string, number> | null }
export interface Referral { ref: string; ch: string; certificate_ref: string; insured: string; requested: string; decided: string; status: string; approver: string | null; reasons: string[]; note: string | null }
export interface Ledger { entry_id: string; ch: string; date: string; type: string; amount: number; status: string; doc_id: string; by: string; settled: string | null; items: { certificate_ref: string; insured: string; reported: string; contract: string; amount: number }[] }
export interface RegCheck { exc_id: string; check: string; title: string; family: string; status: ExcStatus; outcome: string; written: string; authority: string; delta: string | null; impact_usd: number; referral: string | null }
export interface RegEntry {
  key: string; ch: string; ch_name: string; scenario: string; certificate_ref: string; insured: string; subject_type: string; month: string; txn: string | null; status: ExcStatus;
  severity: Severity; families: string[]; checks: RegCheck[]; exceptions: number; open: number; premium_tied: number; impact_usd: number; commission_discrepancy: number;
  exposure_above: number; raised_at: string; resolved_at: string | null; query_ids: string[]; action: string | null; tiv: number | null; state: string | null;
}
export interface SideCheck { rule_id: string; check: string; title: string; result: string; outcome: string; severity: Severity; written: string; authority: string; delta: string | null; impact_usd: number; source: string; action: string | null; anchor_written: Anchor | null; anchor_authority: Anchor | null; referral: { result: string; detail: string; ref: string | null } | null; exc_id: string | null; status: string }
export interface PolicyDetail extends RegEntry {
  row_fields: { field: string; label: string; value: string; anchor: Anchor | null }[]; side_by_side: SideCheck[]; claims: Claim[];
  history: { date: string; event: string; by: string; note: string; exc_id: string; check: string }[]; responses: { exc_id: string; check: string; date: string; kind: string; text: string }[];
  queries: Query[]; corrections: { date: string; doc_id: string; fields: string[] }[]; authority_doc_id: string | null; bordereau_doc_id: string | null; recommended: string[]; exc_ids_open: string[]; row_versions: string[];
}
export interface ChDetail extends ChSummary {
  authority: AuthorityView; scorecard: Scorecard; reports: Report[]; bordereaux: BdxRow[]; aggregates: Zone[]; zone_history: { month: string; zones: Record<string, number> }[];
  capacity: { ytd: number; projected: number; limit: number; util: number }; claims: Claim[]; referrals: Referral[]; queries: Query[]; ledger: Ledger[];
  audits: { audit_id: string; requested: string; visit: string; report_due: string; status: string; doc_id: string | null; findings: { sampled: number; confirmed: number; disputes: number; rating: string } | null }[];
  issued_reports: { report_id: string; month: string; issued: string; doc_id: string }[]; restrictions: { zone: string; name: string; mode: string; effective: string; doc_id: string; util_at_issue: number }[];
  amendments: { number: number; doc_id: string; effective: string; issued: string; kind: string; note: string; changes: { label: string; from: string; to: string }[] }[];
  prevented: { date: string; certificate_ref: string; insured: string; tiv: number; zone: string; ref: string }[]; rarc_detail: { method: string; quarters: Rarc[] };
  timeline: TimelineEvent[]; documents: DocumentMeta[]; register: RegEntry[];
}
export interface Overview {
  as_of: string; month: string; months: string[]; coverholders: ChSummary[]; trend: Record<string, number | string>[];
  totals: { policies: number; with_exceptions: number; exception_rate: number; within_authority: number; premium_tied: number; commission: number; missing_referrals: number; open_policies: number; exposure_above: number; premium: number };
  types: { family: string; label: string; count: number; by_ch: Record<string, number> }[]; zones: (Zone & { ch: string; ch_name: string })[]; at_stake: number;
  open_exceptions: number; open_policies: number; corrected: { count: number; exposure: number; premium: number }; prevented: { count: number; tiv: number };
  turnaround_days: number | null; queries_open: number; aggregate_warnings: number; ledger: Ledger[]; recent: (TimelineEvent & { ch: string; ch_name: string })[];
}
export interface BdxDetail {
  doc_id: string; ch: string; ch_name: string; kind: string; month: string; title: string; received: string; due: string; days_late: number; sheet: string; header_row: number;
  mapping: { col: string; header: string; field: string | null; label: string | null; confidence: number; method: string }[]; missing: string[]; missing_labels: string[];
  issues: { code: string; severity: Severity; label: string; cell: string | null; field: string | null; row: number | null }[];
  stats: { rows: number; completeness: number; validity: number; mapping_confidence: number; consistency: number; mapped: number; columns: number; dq_score: number };
  dq_score: number; rows: number; correction: boolean; replaces: string | null; superseded_by: string | null; skipped: { row: number; reason: string }[]; method: string;
  exceptions: { exc_id: string; policy_key: string; certificate_ref: string; insured: string; check: string; written: string; authority: string; status: ExcStatus; anchor: Anchor | null }[];
}
export interface AggregatesRow { ch: string; name: string; scenario: string; zones: Zone[]; capacity: { ytd: number; projected: number; limit: number; util: number }; history: { month: string; zones: Record<string, number> }[]; restrictions: ChDetail['restrictions']; prevented: ChDetail['prevented'] }

const qs = (o: Record<string, string | undefined | null>) => {
  const p = Object.entries(o).filter(([, v]) => v);
  return p.length ? '?' + new URLSearchParams(p as [string, string][]).toString() : '';
};

export const useOverview = (month?: string) => useQuery({ queryKey: ['delegated', 'overview', month], queryFn: () => api<Overview>('/delegated/overview' + qs({ month })) });
export const useCoverholders = () => useQuery({ queryKey: ['delegated', 'coverholders'], queryFn: () => api<ChSummary[]>('/delegated/coverholders') });
export const useCoverholder = (id?: string) => useQuery({ queryKey: ['delegated', 'coverholder', id], queryFn: () => api<ChDetail>(`/delegated/coverholders/${id}`), enabled: !!id });
export const useRegister = (f: { ch?: string; status?: string; family?: string; month?: string; subject?: string; query?: string }) =>
  useQuery({ queryKey: ['delegated', 'breaches', f], queryFn: () => api<RegEntry[]>('/delegated/breaches' + qs(f)) });
export const usePolicy = (key?: string | null) => useQuery({ queryKey: ['delegated', 'policy', key], queryFn: () => api<PolicyDetail>(`/delegated/breaches/${encodeURIComponent(key!)}`), enabled: !!key });
export const useBordereaux = (ch?: string) => useQuery({ queryKey: ['delegated', 'bdx', ch], queryFn: () => api<BdxRow[]>('/delegated/bordereaux' + qs({ ch })) });
export const useBordereau = (id?: string | null) => useQuery({ queryKey: ['delegated', 'bdx1', id], queryFn: () => api<BdxDetail>(`/delegated/bordereaux/${id}`), enabled: !!id });
export const useAggregates = () => useQuery({ queryKey: ['delegated', 'aggregates'], queryFn: () => api<AggregatesRow[]>('/delegated/aggregates') });

/** Carrier actions. Every one invalidates all delegated views (and the demo clock / outbox). */
export function useDaAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => api<{ message: string }>(`/delegated/${path}`, { method: 'POST', json: body ?? {} }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export const STATUS_TONE: Record<string, 'crit' | 'high' | 'med' | 'ok' | 'info' | 'neutral' | 'dark' | 'accent'> = {
  OPEN: 'crit', QUERIED: 'high', RESPONDED: 'med', ESCALATED: 'dark', ACCEPTED: 'info', RESOLVED: 'ok', AUTHORISED: 'ok', PASS: 'ok', NA: 'neutral',
  REFER: 'high', BREACH: 'crit', WARN: 'high', REVIEW: 'med',
};
export const STATUS_LABEL: Record<string, string> = { OPEN: 'Open', QUERIED: 'Queried', RESPONDED: 'Responded', ESCALATED: 'Escalated', ACCEPTED: 'Accepted', RESOLVED: 'Resolved', AUTHORISED: 'Authorised' };
export const FAMILY_LABEL: Record<string, string> = {
  class: 'Outside permitted class', limit: 'Above limit authority', deductible: 'Deductible breaches', pricing: 'Pricing deviations', referral: 'Missing mandatory referrals',
  commission: 'Commission discrepancies', exclusion: 'Prohibited risks', territory: 'Outside territory', period: 'Outside authority period', aggregate: 'Aggregate & restrictions',
  premium: 'Premium reconciliation', claims: 'Claims controls', capacity: 'Capacity', timeliness: 'Late bordereaux', data_quality: 'Bordereau data quality',
};
export const MONTH = (m: string) => new Date(m + '-01T00:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
export const CH_COLOR: Record<string, string> = { ch_meridian: '#c2263a', ch_northfield: '#1f8a4c', ch_palmcoast: '#2f5bd3', ch_ridgeway: '#b88404', ch_sierra: '#7c4dcc' };
