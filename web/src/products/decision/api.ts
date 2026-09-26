// Decision Assurance — local API types and hooks (backend: /api/decision/*).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, getCurrentUserId } from '@/api/client';
import type { Anchor, DocumentMeta, Severity, TimelineEvent } from '@/api/types';

export type Verdict = 'PASS' | 'PASS_WITH_FLAGS' | 'REFER_HOLD';
export type CheckResult = 'PASS' | 'FLAG' | 'FAIL' | 'CONDITION';
export interface Citation { label: string; doc_id: string | null; page: number | null }
export interface Side { obs_id: string; value: string; source: string; obs_type: string; doc_id: string | null; anchor: Anchor | null; confidence: number }
export interface Contradiction {
  contradiction_id: string; location_uid: string; location: string; field: string; field_label: string; resolved: Side; other: Side; sources: Side[];
  impact_usd: number; impact_note: string; material: boolean; policy: string; status: 'OPEN' | 'RESOLVED';
  resolution: { choice: string; value: string; by: string; at: string; note: string } | null;
}
export interface Factor {
  title: string; subject: string; subject_id: string | null; observed: string; expected: string; rule_id: string | null; severity: Severity; outcome: string;
  impact_usd: number; citation: Citation; tier: number; evidence_obs_ids: string[];
}
export interface Missing { item: string; why: string; rule_id: string | null; blocking: boolean; status: 'OPEN' | 'REQUESTED' }
export interface Requirement { requirement: string; level: number; rule_id: string | null; within: boolean; source: string }
export interface Zone { zone_id: string; name: string; peril: string; threshold: number; before: number; after: number; util_before: number; util_after: number; increase: number; max_line: number }
export interface Pricing {
  technical: number; band_low: number; band_high: number; components: { component: string; value: number }[]; aal: number; oep_250: number;
  per_loc: { location_uid: string; label: string; class: string; base_rate: number; construction_factor: number; ppc_factor: number; sprinkler_factor: number; roof_factor: number; aal: number; tiv: number }[];
  modifiers: { label: string; value: number }[]; exp_mod: number; model: string; line: number; prior_premium: number | null; target_premium: number | null; bind_offer: number | null;
}
export interface Pack {
  built_at: string; tiv: number; governing_class: string | null;
  classification: { governing: string | null; label: string; evidence: { class: string; source: string; obs_id: string; confidence: number }[]; classes: { key: string; label: string }[] };
  suggested: { type: string; aop: number; line: number; limit: number; ns_pct?: number; ns_min?: number; wh_pct?: number };
  pricing: Pricing; portfolio: { zones: Zone[]; zone_name: string | null; zone_util_before: number; zone_util_after: number; max_line: number };
  contradictions: Contradiction[]; missing: Missing[]; factors: Factor[];
  guidelines: { rule_id: string; title: string; result: string; subject: string; observed: string; citation: Citation; tier: number; version: number }[];
  requirements: Requirement[]; required_level: number; draft: { action: string; why: string; before_final: string[]; premium_range: [number, number] };
  claims: { claim_id: string; incurred?: number; date_of_loss?: string; cause?: string; obs: Record<string, string> }[]; loss_run_years: number;
  evidence: { facts: number; documents: number; sources: string[] }; prep: { manual: number; platform: number; saved: number; method: string }; auto_prepared: boolean;
}
export interface Fact { field: string; label: string; value: string; obs_id: string; source: string; obs_type: string; confidence: number; sources: number; conflict: boolean }
export interface Facts { account: Fact[]; locations: { location_uid: string; label: string; address: string; tiv: number; occupancy: string; facts: Fact[] }[] }
export interface Check {
  check_id: string; rule_id: string; rule_version: number; tier: number; dimension: string; title: string; subject: string; subject_id: string | null; observed: string;
  expected: string; source: string; citation: Citation; severity: Severity; outcome: string; level: number; impact_usd: number; result: CheckResult;
  covered_by: { referral_id: string; approver: string; level: number; at: string } | null; overridden: { reason: string; by_name: string } | null; note: string | null; evidence_obs_ids: string[];
}
export interface Assurance {
  assurance_id: string; action_id: string; action_version: number; action_type: string; premium: number; verdict: Verdict;
  dimensions: { key: string; label: string; result: CheckResult; checks: number; issues: number; summary: string }[];
  checks: Check[]; conditions: { text: string; source: string; status: string; due: string }[]; required_level: number;
  owner: { user_id: string; name: string; level: number; why: string }; tier3: string[]; technical: number; deviation: number; permitted_dev: number; band: [number, number];
  exposure_usd: number; summary: string; run_at: string; uw_level: number; counts: { tier1: number; tier2: number; fail: number; flag: number; pass: number };
  portfolio: Pack['portfolio']; pricing: { technical: number; components: { component: string; value: number }[]; aal: number; oep_250: number; line: number; manuscript_load: number };
}
export interface Action {
  action_id: string; version: number; type: string; premium: number; aop: number; limit: number; line: number; ns_pct?: number | null; ns_min?: number | null; wh_pct?: number | null;
  manuscript?: string | null; rationale: string; by: string; by_name: string; at: string;
}
export interface Referral {
  referral_id: string; case_id: string; insured: string; scenario: string | null; kind: 'pre' | 'action'; requested_by: string; requested_at: string; required_level: number;
  triggers: { rule_id: string; title: string; subject: string; observed: string; level: number }[]; memo: string; action: Action | null; status: 'PENDING' | 'APPROVED' | 'DECLINED';
  approver: string | null; approver_level: number | null; decided_at: string | null; conditions: string[]; envelope: Record<string, number | string>; envelope_text: string;
  decision_note: string | null; href: string;
}
export interface QueueItem {
  case_id: string; insured: string; short: string; scenario: string | null; title: string | null; broker: string; underwriter: string; underwriter_id: string; segment: string;
  state: string; class_label: string | null; tiv: number | null; received: string | null; expected: string; effective: string; quote_by: string | null; sla_days: number | null;
  status: string; stage: number; draft: string | null; verdict: Verdict | null; technical: number | null; premium: number | null; deviation: number | null;
  contradictions: number; missing: number; referral_pending: boolean; exposure: number; auto_prepared: boolean | null; hero: boolean;
}
export interface Outcome {
  at: string; clean: boolean; flags: number; confirmed: number; overrides: number; prevented_loss: number | null;
  loss: { claim_id: string; cause: string; incurred: number; location: string; desc: string; excluded: boolean; dol: string } | null;
}
export interface CaseDetail extends QueueItem {
  contact: string; uw_level: number; clock: string; pack: Pack | null; facts: Facts | null; actions: Action[]; assurance: Assurance | null;
  assurances: { assurance_id: string; action_version: number; action_type: string; premium: number; verdict: Verdict; run_at: string; deviation: number; fails: number; flags: number; summary: string; rerun?: string }[];
  referrals: Referral[]; conditions: { cond_id: string; text: string; source: string; kind: string; status: string; evidence: string | null }[];
  requests: { request_id: string; items: string[]; sent: string; due: string; status: string; by: string; docs: string[] }[];
  overrides: { rule_id: string; subject_id: string | null; reason: string; by_name: string; at: string }[];
  decision: { decision: string; by: string; level: number; at: string; note: string; verdict?: Verdict } | null;
  quote: { doc_id: string; premium: number; at: string; status: string; readback: { summary: string }; subjectivities: { text: string; status: string }[] } | null;
  bound: { doc_id: string; premium: number; at: string; limit: number; line: number; readback: { summary: string } } | null;
  outcome: Outcome | null; feedback: { rule_id: string; tier: number; overridden: boolean; outcome: string | null }[];
  exposure_detail: { preparation: number; assurance: number; total: number; kind: string | null; loss_avoided: number };
  documents: DocumentMeta[]; timeline: TimelineEvent[]; pending: { date: string; title: string; type: string }[];
  authority: Record<string, { max_price_dev: number; max_account_tiv: number; max_loc_tiv: number; max_premium: number; label: string }>;
}
export interface Dashboard {
  as_of: string; cases: number; prepared: number; expected: number; auto_prepared: number; assured: number; verdicts: Record<Verdict, number>; first_verdicts: Record<Verdict, number>;
  exposure: { total: number; preparation: number; assurance: number; loss_avoided: number; cases: number; by_case: { case_id: string; insured: string; scenario: string | null; total: number; preparation: number; assurance: number; kind: string | null }[] };
  errors_intercepted: number; commitments_changed: number; hours_saved: number; hours_manual: number; median_days_to_decision: number | null; decided: number;
  funnel: { code: string; name: string; count: number }[];
  tiers: { tier1: { checks: number; fired: number }; tier2: { checks: number; fired: number }; tier3: { human_decisions: number; referrals: number } };
  by_underwriter: { user_id: string; name: string; level: number; cases: number; pass: number; flags: number; refer: number; overrides: number; avg_dev: number | null; bound: number }[];
  by_broker: { broker: string; cases: number; contradictions: number; missing: number; refer: number; quoted: number; bound: number; premium: number }[];
  by_segment: { segment: string; cases: number; refer: number; bound: number; premium: number; tiv: number }[];
  top_issues: { rule_id: string; title: string; tier: number; dimension: string; cases: number; impact_usd: number }[];
  feedback: { flags: number; overrides: number; override_rate: number | null; scored: number; confirmed: number; overrides_confirmed: number; bound: number; with_outcome: number;
    loss_ratio_flagged: number | null; loss_ratio_clean: number | null; losses: number;
    rules: { rule_id: string; title: string; tier: number; fired: number; accepted: number; rejected: number; confirmed: number; not_confirmed: number; precision: number | null }[] };
  portfolio: { zones: { zone_id: string; name: string; peril: string; threshold: number; in_force: number; nb_bound: number; util: number; util_in_force: number }[]; mix: { class: string; bound: number; premium: number }[] };
  bound_premium: number; quoted: number; bound: number;
}
export interface ActionInput { type: string; premium?: number; dev?: number; aop?: number; limit?: number; line?: number; ns_pct?: number | null; ns_min?: number | null; wh_pct?: number | null; manuscript?: string | null; rationale?: string }
export interface SandboxResult { token: string; sov: string; application: string | null; pack: Pack; facts: Facts; issues: { code: string; label: string; severity: string }[]; observations: number; real: string[]; not_real: string[] }

const inv = () => { const qc = useQueryClient(); return () => qc.invalidateQueries(); };

/** Current persona as a query, so views re-render when the header switcher invalidates queries. */
export const useMe = () => useQuery({ queryKey: ['da', 'me'], queryFn: async () => getCurrentUserId() }).data ?? getCurrentUserId();
export const useDashboard = () => useQuery({ queryKey: ['da', 'dash'], queryFn: () => api<Dashboard>('/decision/dashboard') });
export const useCases = () => useQuery({ queryKey: ['da', 'cases'], queryFn: () => api<QueueItem[]>('/decision/cases') });
export const useCase = (id?: string) => useQuery({ queryKey: ['da', 'case', id], queryFn: () => api<CaseDetail>(`/decision/cases/${id}`), enabled: !!id });
export const useDaReferrals = () => useQuery({ queryKey: ['da', 'refs'], queryFn: () => api<Referral[]>('/decision/referrals') });
export const useAssuranceLog = () => useQuery({ queryKey: ['da', 'log'], queryFn: () => api<{ assurance_id: string; case_id: string; insured: string; scenario: string | null; at: string; verdict: Verdict; action_type: string; premium: number; deviation: number; fails: number; flags: number; underwriter: string }[]>('/decision/assurance-log') });

function post<R>(path: string) {
  const i = inv();
  return useMutation({ mutationFn: (b: unknown) => api<R>(path, { method: 'POST', json: b ?? {} }), onSuccess: i });
}
export const useResolve = (id: string, ctr: string) => post<CaseDetail>(`/decision/cases/${id}/contradictions/${ctr}/resolve`);
export const useRequestInfo = (id: string) => post<CaseDetail>(`/decision/cases/${id}/requests`);
export const useOrderInspection = (id: string) => post<CaseDetail>(`/decision/cases/${id}/inspection`);
export const useOverride = (id: string) => post<CaseDetail>(`/decision/cases/${id}/overrides`);
export const usePrerefer = (id: string) => post<CaseDetail>(`/decision/cases/${id}/prerefer`);
export const useSubmitAction = (id: string) => post<CaseDetail>(`/decision/cases/${id}/actions`);
export const useRoute = (id: string) => post<{ message: string }>(`/decision/cases/${id}/route`);
export const useFinalDecision = (id: string) => post<{ message: string }>(`/decision/cases/${id}/decision`);
export const useBindCase = (id: string) => post<{ message: string }>(`/decision/cases/${id}/bind`);
export function useDecideDaReferral() {
  const i = inv();
  return useMutation({ mutationFn: (b: { rid: string; decision: 'APPROVE' | 'DECLINE'; conditions?: string[]; envelope?: Record<string, number | string>; note?: string }) => api<Referral>(`/decision/referrals/${b.rid}/decision`, { method: 'POST', json: b }), onSuccess: i });
}
export function usePreview(id: string) {
  return useMutation({ mutationFn: (b: ActionInput) => api<{ action: Action; assurance: Assurance }>(`/decision/cases/${id}/assure/preview`, { method: 'POST', json: b }) });
}
export function useSandbox() {
  return useMutation({ mutationFn: (f: { sov: File; application?: File | null }) => { const fd = new FormData(); fd.append('sov', f.sov); if (f.application) fd.append('application', f.application); return api<SandboxResult>('/decision/sandbox', { method: 'POST', body: fd }); } });
}
export function useSandboxAssure(token: string) {
  return useMutation({ mutationFn: (b: ActionInput) => api<{ action: Action; assurance: Assurance }>(`/decision/sandbox/${token}/assure`, { method: 'POST', json: b }) });
}

export const VERDICT_LABEL: Record<Verdict, string> = { PASS: 'Pass', PASS_WITH_FLAGS: 'Pass with flags', REFER_HOLD: 'Refer / hold' };
export const VERDICT_TONE: Record<Verdict, 'ok' | 'med' | 'crit'> = { PASS: 'ok', PASS_WITH_FLAGS: 'med', REFER_HOLD: 'crit' };
export const RESULT_TONE: Record<string, 'ok' | 'med' | 'crit' | 'info' | 'neutral'> = { PASS: 'ok', FLAG: 'med', FAIL: 'crit', CONDITION: 'info', 'N/A': 'neutral' };
export const DRAFT_LABEL: Record<string, string> = { DECLINE: 'Decline', REFER_CONDITIONAL_QUOTE: 'Refer / conditionally quote', REFER: 'Refer', REQUEST_INFO: 'Request information', QUOTE_SUBJECT_TO: 'Quote subject to conditions', QUOTE: 'Quote' };
export const STATUS_LABEL: Record<string, string> = { EXPECTED: 'Expected', PREPARED: 'Pack ready', IN_REVIEW: 'In review', READY: 'Assured', HOLD: 'Hold', REFERRED: 'Referred', APPROVED: 'Approved', QUOTED: 'Quoted', ACCEPTED: 'Accepted', BOUND: 'Bound', DECLINED: 'Declined', LOST: 'Not taken' };
export const STAGES = ['Submission', 'Document intelligence', 'Carrier context', 'Draft', 'Judgement', 'Intended action', 'Assurance', 'Verdict', 'Final decision', 'Outcome'];
