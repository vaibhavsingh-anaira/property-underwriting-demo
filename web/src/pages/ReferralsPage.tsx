import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Lock, ShieldAlert, ShieldCheck, XCircle, CheckCircle2, AlertTriangle } from 'lucide-react';
import { getCurrentUserId, useAccount, useDecideReferral, useReferrals, useUsers } from '@/api/client';
import type { Referral } from '@/api/types';
import { Page, Card, Badge, Button, Segmented, Loading, ErrorBox, Empty, cx } from '@/components/ui';
import { fmtDate, usd } from '@/lib/format';
import { CitedText, ScenarioChip, SectionLabel, StatusBadge } from './common';
import { Info } from '@/help/Info';

type F = 'PENDING' | 'ALL' | 'INVALIDATED' | 'DECIDED';
const TONE = { PENDING: 'info', APPROVED: 'ok', DECLINED: 'neutral', INVALIDATED: 'crit' } as const;

export default function ReferralsPage() {
  const { data, isLoading, error } = useReferrals();
  const [sp, setSp] = useSearchParams();
  const [f, setF] = useState<F>('PENDING');
  const list = useMemo(() => (data ?? []).filter((r) => f === 'ALL' || (f === 'DECIDED' ? r.status === 'APPROVED' || r.status === 'DECLINED' : r.status === f)).sort((a, b) => b.required_level - a.required_level || b.requested_at.localeCompare(a.requested_at)), [data, f]);
  const selId = sp.get('id') ?? list[0]?.referral_id;
  const sel = data?.find((r) => r.referral_id === selId) ?? list[0];
  const count = (s: Referral['status']) => data?.filter((r) => r.status === s).length ?? 0;
  return (
    <Page title="Referrals" actions={<Info id="referrals.page" label="About this page" />} subtitle="Senior underwriting inbox · approvals are locked to the hash of the terms they approve">
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <div className="grid grid-cols-12 gap-4">
          <Card className="col-span-12 lg:col-span-4" pad={false}
            title={<Segmented value={f} onChange={setF} options={[{ key: 'PENDING', label: `Pending ${count('PENDING')}` }, { key: 'INVALIDATED', label: `Invalidated ${count('INVALIDATED')}` }, { key: 'DECIDED', label: 'Decided' }, { key: 'ALL', label: 'All' }]} />}>
            <div className="max-h-[calc(100vh-220px)] overflow-y-auto">
              {list.map((r) => (
                <button key={r.referral_id} onClick={() => setSp({ id: r.referral_id }, { replace: true })}
                  className={cx('block w-full border-b border-line px-4 py-2.5 text-left last:border-0', sel?.referral_id === r.referral_id ? 'bg-accent-50' : 'hover:bg-ink-50')}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[13px] font-medium text-ink-900">{r.account_name}</span>
                    <span className="flex shrink-0 items-center gap-1"><Badge tone="dark">L{r.required_level}</Badge><Badge tone={TONE[r.status]}>{r.status.toLowerCase()}</Badge></span>
                  </div>
                  <div className="truncate text-[11.5px] text-ink-500">{r.reasons[0]}</div>
                  <div className="num text-[11px] text-ink-400">{r.requested_by} · {fmtDate(r.requested_at)}</div>
                </button>
              ))}
              {list.length === 0 && <Empty>Inbox zero.</Empty>}
            </div>
          </Card>
          <div className="col-span-12 lg:col-span-8">{sel ? <Detail key={sel.referral_id} r={sel} /> : <Card><Empty>Select a referral.</Empty></Card>}</div>
        </div>
      )}
    </Page>
  );
}

function Detail({ r }: { r: Referral }) {
  const { data: a } = useAccount(r.account_id);
  const { data: users } = useUsers();
  const me = users?.find((u) => u.user_id === getCurrentUserId());
  const decide = useDecideReferral();
  const [conditions, setConditions] = useState('');
  const canDecide = !!me && me.authority_level >= r.required_level;
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              {a && <ScenarioChip s={a.scenario} />}
              <Link to={`/accounts/${r.account_id}`} className="text-[18px] font-semibold text-ink-950 hover:text-accent-700">{r.account_name}</Link>
              {a && <StatusBadge s={a.renewal.status} />}
            </div>
            <div className="mt-0.5 text-[12px] text-ink-500">Requested by {r.requested_by} · {fmtDate(r.requested_at)}{r.quote_id && <> · quote <span className="mono">{r.quote_id}</span></>}</div>
            {a && <div className="mt-1 text-[12px] text-ink-600">{a.policy.policy_no} · expiring {usd(a.policy.premium)} · {a.broker} · T-{a.renewal.days_to_expiry}</div>}
          </div>
          <div className="flex items-stretch gap-2">
            <div className="rounded-lg border border-line px-3 py-2 text-center"><div className="text-[10.5px] uppercase tracking-wide text-ink-500">Required</div><div className="num text-[22px] font-semibold text-ink-950">L{r.required_level}</div></div>
            <div className={cx('rounded-lg border px-3 py-2 text-center', canDecide ? 'border-[#bfe3cd] bg-ok-bg' : 'border-[#f5d2b8] bg-high-bg')}>
              <div className="text-[10.5px] uppercase tracking-wide text-ink-500">Your level</div>
              <div className="flex items-center justify-center gap-1"><span className="num text-[22px] font-semibold text-ink-950">L{me?.authority_level ?? '–'}</span>{canDecide ? <ShieldCheck className="size-4 text-ok" /> : <ShieldAlert className="size-4 text-high" />}</div>
            </div>
            {r.terms_hash && <div className="rounded-lg border border-line px-3 py-2 text-center"><div className="flex items-center justify-center gap-1 text-[10.5px] uppercase tracking-wide text-ink-500"><Lock className="size-3" />Terms hash</div><div className="mono mt-1 text-[14px] font-semibold text-ink-900">{r.terms_hash}</div></div>}
          </div>
        </div>
        {r.status === 'INVALIDATED' && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-[#f6c5cc] bg-crit-bg px-3 py-2 text-[12.5px] text-crit">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <div><div className="font-semibold">Approval invalidated — terms changed after approval</div><div>{r.invalidated_reason}</div>{r.approver && <div className="text-[11.5px] opacity-80">Originally approved by {r.approver} on {fmtDate(r.decided_at)}{r.conditions && ` · conditions: ${r.conditions}`}</div>}</div>
          </div>
        )}
        {(r.status === 'APPROVED' || r.status === 'DECLINED') && (
          <div className={cx('mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-[12.5px]', r.status === 'APPROVED' ? 'bg-ok-bg text-ok' : 'bg-ink-100 text-ink-700')}>
            {r.status === 'APPROVED' ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
            {r.status === 'APPROVED' ? 'Approved' : 'Declined'} by {r.approver} on {fmtDate(r.decided_at)}{r.conditions && <> · conditions: {r.conditions}</>}{r.status === 'APPROVED' && r.terms_hash && <> · valid only for hash <span className="mono">{r.terms_hash}</span></>}
          </div>
        )}
      </Card>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-8" title="Referral memo" subtitle="Pre-filled from the integrity record · citations open the evidence">
          <CitedText text={r.memo} findings={a?.findings} />
          <div className="mt-4"><SectionLabel>Why a referral is required</SectionLabel>
            <ul className="space-y-1">{r.reasons.map((x) => <li key={x} className="flex gap-2 text-[12.5px] text-ink-700"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-high" />{x}</li>)}</ul>
          </div>
        </Card>
        <div className="col-span-12 space-y-4 xl:col-span-4">
          {a && (
            <Card title="Account at a glance">
              <div className="space-y-1 text-[12.5px]">
                {a.deltas.slice(0, 5).map((d) => <div key={d.key} className="flex items-start justify-between gap-2 border-b border-line py-1 last:border-0"><span className="text-ink-500">{d.title}</span><span className={cx('text-right font-medium', d.status === 'ACTION' ? 'text-crit' : d.status === 'WATCH' ? 'text-med' : 'text-ok')}>{d.headline}</span></div>)}
              </div>
              <div className="mt-2 text-[11.5px] text-ink-500">{a.findings.filter((x) => x.material).length} material findings · {usd(a.findings.filter((x) => x.material && x.status !== 'REJECTED').reduce((s, x) => s + x.impact_usd, 0))} at stake · integrity {a.renewal.integrity_score}</div>
              <Link to={`/accounts/${a.account_id}/pricing`} className="mt-2 inline-block text-[12px] font-medium text-accent-700 hover:underline">Open RARC workbench →</Link>
            </Card>
          )}
          {r.status === 'PENDING' && (
            <Card title="Decision">
              {!canDecide && <div className="mb-2 rounded-md bg-high-bg px-2.5 py-1.5 text-[12px] text-high">Your authority (L{me?.authority_level}) is below the required L{r.required_level}. Switch persona to decide.</div>}
              <textarea value={conditions} onChange={(e) => setConditions(e.target.value)} rows={3} placeholder="Conditions (optional) — e.g. 3% named-storm deductible; re-survey Reno before bind"
                className="mb-2 w-full resize-none rounded-md border border-line-strong px-2 py-1.5 text-[12.5px] outline-none focus:border-accent-500" />
              <div className="flex gap-2">
                <Button variant="primary" className="flex-1" disabled={!canDecide} loading={decide.isPending && decide.variables?.decision === 'APPROVE'} onClick={() => decide.mutate({ referral_id: r.referral_id, decision: 'APPROVE', conditions: conditions || undefined })}>Approve{conditions ? ' with conditions' : ''}</Button>
                <Button variant="danger" disabled={!canDecide} loading={decide.isPending && decide.variables?.decision === 'DECLINE'} onClick={() => decide.mutate({ referral_id: r.referral_id, decision: 'DECLINE', conditions: conditions || undefined })}>Decline</Button>
              </div>
              {r.terms_hash && <div className="mt-2 text-[11px] text-ink-500">Approval will be locked to terms hash <span className="mono">{r.terms_hash}</span>. Any later change to premium or terms invalidates it.</div>}
              {decide.error && <div className="mt-2"><ErrorBox error={decide.error} /></div>}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
