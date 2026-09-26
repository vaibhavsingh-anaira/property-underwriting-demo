import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type * as T from './types';

// Current user (role switcher) is sent on every request.
let currentUserId = localStorageGet('uwc.user') ?? 'u_maya';
export function setCurrentUserId(id: string) { currentUserId = id; localStorageSet('uwc.user', id); }
export function getCurrentUserId() { return currentUserId; }

function localStorageGet(k: string) { try { return localStorage.getItem(k); } catch { return null; } }
function localStorageSet(k: string, v: string) { try { localStorage.setItem(k, v); } catch { /* ignore */ } }

export class ApiError extends Error { status: number; constructor(status: number, message: string) { super(message); this.status = status; } }

export async function api<R>(path: string, init?: RequestInit & { json?: unknown }): Promise<R> {
  const headers: Record<string, string> = { 'X-User-Id': currentUserId };
  let body = init?.body;
  if (init?.json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(init.json); }
  const res = await fetch(`/api${path}`, { ...init, headers: { ...headers, ...(init?.headers as Record<string, string>) }, body });
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail ?? msg; } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }
  const ct = res.headers.get('content-type') ?? '';
  return (ct.includes('application/json') ? res.json() : res.text()) as Promise<R>;
}

export const rawUrl = (docId: string) => `/api/documents/${docId}/raw`;

const qs = (o: Record<string, string | number | undefined | null>) => {
  const p = Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== '');
  return p.length ? '?' + new URLSearchParams(p.map(([k, v]) => [k, String(v)])).toString() : '';
};

// ------------------------------------------------------------------ queries
export const useUsers = () => useQuery({ queryKey: ['users'], queryFn: () => api<T.User[]>('/users') });
export const useDemoState = () => useQuery({ queryKey: ['demo'], queryFn: () => api<T.DemoState>('/demo/state') });
export const useBook = () => useQuery({ queryKey: ['book'], queryFn: () => api<T.BookSummary>('/book') });
export const useRenewals = (f: { status?: string; uw?: string; q?: string } = {}) =>
  useQuery({ queryKey: ['renewals', f], queryFn: () => api<T.RenewalQueueItem[]>('/renewals' + qs(f)) });
export const useAccount = (id: string | undefined) =>
  useQuery({ queryKey: ['account', id], queryFn: () => api<T.AccountDetail>(`/accounts/${id}`), enabled: !!id });
export const useRarc = (id: string | undefined) =>
  useQuery({ queryKey: ['rarc', id], queryFn: () => api<T.RarcResult>(`/accounts/${id}/rarc`), enabled: !!id });
export const useContract = (id: string | undefined) =>
  useQuery({ queryKey: ['contract', id], queryFn: () => api<T.ContractDiff>(`/accounts/${id}/contract`), enabled: !!id });
export const useCat = (id: string | undefined) =>
  useQuery({ queryKey: ['cat', id], queryFn: () => api<T.CatResult[]>(`/accounts/${id}/cat`), enabled: !!id });
export const useClaimsEngineering = (id: string | undefined) =>
  useQuery({ queryKey: ['claims', id], queryFn: () => api<T.ClaimsEngineering>(`/accounts/${id}/claims-engineering`), enabled: !!id });
export const useFields = (accountId: string | undefined, subjectId?: string) =>
  useQuery({ queryKey: ['fields', accountId, subjectId], queryFn: () => api<T.ResolvedField[]>(`/accounts/${accountId}/fields` + qs({ subject_id: subjectId })), enabled: !!accountId });
export const useObservation = (obsId: string | null | undefined) =>
  useQuery({ queryKey: ['obs', obsId], queryFn: () => api<T.ObservationDetail>(`/observations/${obsId}`), enabled: !!obsId });
export const useReferrals = (status?: string) =>
  useQuery({ queryKey: ['referrals', status], queryFn: () => api<T.Referral[]>('/referrals' + qs({ status })) });
export const useDocuments = (f: { account_id?: string; type?: string; format?: string; q?: string } = {}) =>
  useQuery({ queryKey: ['documents', f], queryFn: () => api<T.DocumentMeta[]>('/documents' + qs(f)) });
export const useDocument = (id: string | null | undefined) =>
  useQuery({ queryKey: ['document', id], queryFn: () => api<T.DocumentMeta>(`/documents/${id}`), enabled: !!id });
export const useXlsx = (id: string | null | undefined) =>
  useQuery({ queryKey: ['xlsx', id], queryFn: () => api<T.XlsxPayload>(`/documents/${id}/xlsx`), enabled: !!id, staleTime: Infinity });
export const useEml = (id: string | null | undefined) =>
  useQuery({ queryKey: ['eml', id], queryFn: () => api<T.EmlPayload>(`/documents/${id}/eml`), enabled: !!id, staleTime: Infinity });
export const useExtraction = (id: string | null | undefined) =>
  useQuery({ queryKey: ['extraction', id], queryFn: () => api<T.ExtractionPayload>(`/documents/${id}/extraction`), enabled: !!id });
export const useDocText = (id: string | null | undefined) =>
  useQuery({ queryKey: ['doctext', id], queryFn: () => api<string>(`/documents/${id}/raw`), enabled: !!id, staleTime: Infinity });
export const useRules = () => useQuery({ queryKey: ['rules'], queryFn: () => api<T.Rule[]>('/rules') });
export const useRule = (id: string | undefined) =>
  useQuery({ queryKey: ['rule', id], queryFn: () => api<T.Rule>(`/rules/${id}`), enabled: !!id });
export const useDataQuality = () => useQuery({ queryKey: ['dq'], queryFn: () => api<T.DataQualitySummary>('/data-quality') });
export const useAccumulation = () => useQuery({ queryKey: ['accumulation'], queryFn: () => api<T.AccumulationZone[]>('/portfolio/accumulation') });
export const useHazards = () => useQuery({ queryKey: ['hazards'], queryFn: () => api<T.GeoFeatureCollection>('/geo/hazards'), staleTime: Infinity });
export const usePipeline = (product = 'renewal') => useQuery({ queryKey: ['pipeline', product], queryFn: () => api<T.PipelineStage[]>('/pipeline' + qs({ product })) });
export const usePipelineGroups = (product = 'renewal') => useQuery({ queryKey: ['pipeline-groups', product], queryFn: () => api<string[]>('/pipeline-groups' + qs({ product })) });
export const useSubjects = (product = 'renewal') => useQuery({ queryKey: ['subjects', product], queryFn: () => api<{ id: string; label: string }[]>('/pipeline-subjects' + qs({ product })) });
export const useMockSystems = (product = 'renewal') => useQuery({ queryKey: ['mocks', product], queryFn: () => api<T.MockSystem[]>('/mocks/systems' + qs({ product })) });
export const useOutbox = (product?: string) => useQuery({ queryKey: ['outbox', product], queryFn: () => api<T.OutboxMessage[]>('/mocks/outbox' + qs({ product })) });
export const useSearch = (q: string) =>
  useQuery({ queryKey: ['search', q], queryFn: () => api<T.SearchHit[]>('/search' + qs({ q })), enabled: q.trim().length > 1 });

// ------------------------------------------------------------------ mutations
function useInvalidateAll() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries();
}

export function useAdvance() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { days?: number; to?: string }) => api<T.AdvanceResult>('/demo/advance', { method: 'POST', json: b }), onSuccess: inv });
}
export function useReset() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: () => api<T.DemoState>('/demo/reset', { method: 'POST' }), onSuccess: inv });
}
export function useSetInjection() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: Record<string, boolean>) => api<T.DemoState>('/demo/injections', { method: 'POST', json: b }), onSuccess: inv });
}
export function useDisposition() {
  const inv = useInvalidateAll();
  return useMutation({
    mutationFn: (b: { finding_id: string; decision: T.Disposition['decision']; reason_code: T.Disposition['reason_code']; note: string }) =>
      api<T.Finding>(`/findings/${b.finding_id}/disposition`, { method: 'POST', json: b }),
    onSuccess: inv,
  });
}
export function useRarcWhatIf(accountId: string) {
  return useMutation({ mutationFn: (b: T.RarcWhatIfRequest) => api<T.RarcResult>(`/accounts/${accountId}/rarc/whatif`, { method: 'POST', json: b }) });
}
export function useCreateQuote(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { premium: number; terms: Partial<T.RarcTerms> }) => api<T.QuoteVersion>(`/accounts/${accountId}/quotes`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useSendQuote(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (quoteId: string) => api<T.QuoteVersion>(`/accounts/${accountId}/quotes/${quoteId}/send`, { method: 'POST' }), onSuccess: inv });
}
export function useCreateReferral(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { quote_id: string | null; note: string }) => api<T.Referral>(`/accounts/${accountId}/referrals`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useDecideReferral() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { referral_id: string; decision: 'APPROVE' | 'DECLINE'; conditions?: string }) => api<T.Referral>(`/referrals/${b.referral_id}/decision`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useDataRequest(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { items: string[] }) => api<T.OutboxMessage>(`/accounts/${accountId}/data-request`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useBind(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { quote_id: string }) => api<{ binder_doc_id: string; findings: T.Finding[] }>(`/accounts/${accountId}/bind`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useIssue(accountId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: () => api<{ policy_doc_id: string; findings: T.Finding[] }>(`/accounts/${accountId}/issue`, { method: 'POST' }), onSuccess: inv });
}
export function useMatchDecision() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { item_id: string; decision: 'CONFIRM' | 'REJECT'; option?: string }) => api<unknown>(`/data-quality/review/${b.item_id}`, { method: 'POST', json: b }), onSuccess: inv });
}
export function useRuleTest(ruleId: string) {
  return useMutation({ mutationFn: (yaml: string) => api<T.RuleTestResult[]>(`/rules/${ruleId}/test`, { method: 'POST', json: { yaml } }) });
}
export function useRuleBacktest(ruleId: string) {
  return useMutation({ mutationFn: (yaml: string) => api<T.BacktestResult>(`/rules/${ruleId}/backtest`, { method: 'POST', json: { yaml } }) });
}
export function useRulePublish(ruleId: string) {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (yaml: string) => api<T.Rule>(`/rules/${ruleId}/publish`, { method: 'POST', json: { yaml } }), onSuccess: inv });
}

export const useStage = (code: string | undefined, acct: string | undefined, product = 'renewal') =>
  useQuery({ queryKey: ['stage', code, acct, product], queryFn: () => api<T.StageView>(`/pipeline/${code}` + qs({ account_id: acct, product })), enabled: !!code });
export const useJourney = (acct: string, product = 'renewal') => useQuery({ queryKey: ['journey', acct, product], queryFn: () => api<T.JourneyStep[]>(`/pipeline/journey/${acct}` + qs({ product })) });
export function useRunStage() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { code: string; account_id: string; product?: string }) => api<{ message: string; stage: T.StageView }>(`/pipeline/${b.code}/run`, { method: 'POST', json: { account_id: b.account_id, product: b.product ?? 'renewal' } }), onSuccess: inv });
}

export const usePlaybooks = (product?: string) => useQuery({ queryKey: ['playbooks', product], queryFn: () => api<T.Playbook[]>('/playbooks' + qs({ product })) });
export const usePlaybook = (id: string) => useQuery({ queryKey: ['playbook', id], queryFn: () => api<T.Playbook>(`/playbooks/${id}`) });
export function useStartPlaybook() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (id: string) => api<T.Playbook>(`/playbooks/${id}/start`, { method: 'POST', json: { reset: true } }), onSuccess: inv });
}
export function useStepPlaybook() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (id: string) => api<T.Playbook>(`/playbooks/${id}/step`, { method: 'POST' }), onSuccess: inv });
}

export function usePresenterEvent() {
  const inv = useInvalidateAll();
  return useMutation({ mutationFn: (b: { account_id: string; kind: 'claim' | 'impairment' | 'vacancy'; params?: Record<string, unknown> }) =>
    api<{ message: string }>(`/accounts/${b.account_id}/events`, { method: 'POST', json: { kind: b.kind, params: b.params ?? {} } }), onSuccess: inv });
}
