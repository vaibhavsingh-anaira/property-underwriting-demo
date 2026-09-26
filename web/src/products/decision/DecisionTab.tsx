// Human final decision (referrals, commit / decline, quote → bind through the policy-admin stub) and outcome feedback.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, FileText, XCircle } from 'lucide-react';
import { useUsers } from '@/api/client';
import { Card, Badge, Button, Empty, MockBadge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { CitedText, SectionLabel } from '@/pages/common';
import { usd, fmtDate } from '@/lib/format';
import { Info } from '@/help/Info';
import { useBindCase, useDecideDaReferral, useFinalDecision, useMe, type CaseDetail, type Referral } from './api';
import { VerdictBadge } from './parts';

export default function DecisionTab({ c }: { c: CaseDetail }) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <Final c={c} className="col-span-12 xl:col-span-7" />
      <Outcome c={c} className="col-span-12 xl:col-span-5" />
      <Card className="col-span-12" pad={false} title={<span className="inline-flex items-center gap-1.5">Referrals<Info id="decision.referrals_case" /></span>} subtitle="Approvals are envelopes: they cover an action only within the approved minimums, line and wording">
        {c.referrals.length === 0 ? <Empty>No referrals on this case.</Empty> : <div className="divide-y divide-line">{c.referrals.map((r) => <ReferralCard key={r.referral_id} r={r} />)}</div>}
      </Card>
    </div>
  );
}

function Final({ c, className }: { c: CaseDetail; className?: string }) {
  const fin = useFinalDecision(c.case_id);
  const bind = useBindCase(c.case_id);
  const ev = useEvidence();
  const a = c.assurance;
  const me = useMe();
  const open = !['BOUND', 'DECLINED', 'LOST'].includes(c.status);
  const canCommit = open && a && a.verdict !== 'REFER_HOLD' && !c.quote;
  const msg = fin.data?.message ?? bind.data?.message;
  const err = (fin.error ?? bind.error) as Error | null;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Human final decision<Info id="decision.final" /></span>} subtitle="The underwriter remains the final decision owner; policy admin is a stand-in">
      {a && <div className="mb-3 flex flex-wrap items-center gap-2 text-[12.5px]"><VerdictBadge v={a.verdict} /> <span className="text-ink-700">Decision owner: <span className="font-semibold">{a.owner.name}</span> (L{a.owner.level}) — {a.owner.why}</span>{a.owner.user_id !== me && <Badge tone="info">switch persona to act</Badge>}</div>}
      {c.decision ? (
        <div className="rounded-md border border-line bg-ink-50 p-3 text-[12.5px]">
          <div className="font-semibold text-ink-900">{c.decision.decision === 'DECLINE' ? 'Declined' : c.decision.decision === 'BIND' ? 'Bound' : 'Quoted'} by {c.decision.by} (L{c.decision.level}) on {fmtDate(c.decision.at)}</div>
          {c.decision.note && <div className="text-ink-600">{c.decision.note}</div>}
        </div>
      ) : !a ? <Empty>Submit an intended action first.</Empty> : null}
      {c.quote && (
        <div className="mt-3 rounded-md border border-line p-3 text-[12.5px]">
          <div className="flex items-center justify-between"><span className="font-semibold">Quote {usd(c.quote.premium, { compact: false })} · {c.quote.status.toLowerCase().replace('_', ' ')}</span><span className="flex items-center gap-2"><MockBadge label="PAS MOCK" /><button onClick={() => ev.openDoc(c.quote!.doc_id)} className="inline-flex items-center gap-1 text-[12px] text-accent-700 hover:underline"><FileText className="size-3.5" />Quote PDF</button></span></div>
          <div className="text-ink-600">Read back by the extractor: {c.quote.readback.summary}</div>
          {c.quote.subjectivities.length > 0 && <><SectionLabel>Subjectivities (before bind)</SectionLabel>{c.quote.subjectivities.map((s) => <div key={s.text} className="flex items-start gap-1.5 py-0.5">{s.status === 'CLEARED' ? <CheckCircle2 className="mt-0.5 size-3.5 text-ok" /> : <XCircle className="mt-0.5 size-3.5 text-high" />}<span>{s.text}</span></div>)}</>}
        </div>
      )}
      {c.conditions.length > 0 && <div className="mt-3"><SectionLabel>Approval conditions</SectionLabel>{c.conditions.map((k) => (
        <div key={k.cond_id} className="flex items-start justify-between gap-2 py-0.5 text-[12.5px]"><span>{k.text}<span className="block text-[11px] text-ink-500">{k.source}</span></span>
          <span className="flex items-center gap-1.5">{k.evidence && <button onClick={() => ev.openDoc(k.evidence!)} className="text-[11px] text-accent-700 hover:underline">evidence</button>}<Badge tone={k.status === 'CLEARED' ? 'ok' : k.status === 'TERM' ? 'neutral' : 'med'}>{k.status === 'TERM' ? 'term of the action' : k.status.toLowerCase()}</Badge></span></div>
      ))}</div>}
      {c.bound && (
        <div className="mt-3 rounded-md border border-[#bfe3cd] bg-ok-bg/50 p-3 text-[12.5px]">
          <div className="flex items-center justify-between"><span className="font-semibold">Bound {fmtDate(c.bound.at)} at {usd(c.bound.premium, { compact: false })} · limit {usd(c.bound.limit)}{c.bound.line < 1 && ` (${Math.round(c.bound.line * 100)}% line)`}</span><button onClick={() => ev.openDoc(c.bound!.doc_id)} className="inline-flex items-center gap-1 text-[12px] text-accent-700 hover:underline"><FileText className="size-3.5" />Binder PDF</button></div>
          <div className="text-ink-600">Binder read back: {c.bound.readback.summary}</div>
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {canCommit && <Button variant="primary" loading={fin.isPending} onClick={() => fin.mutate({ decision: 'COMMIT' })}>{a!.action_type === 'BIND' ? 'Commit: bind' : 'Commit: issue quote'}</Button>}
        {open && c.quote?.status === 'ACCEPTED' && <Button variant="primary" loading={bind.isPending} onClick={() => bind.mutate({})}>Bind (assurance re-runs)</Button>}
        {open && !c.bound && <Button variant="danger" loading={fin.isPending} onClick={() => fin.mutate({ decision: 'DECLINE', note: 'Declined by the decision owner' })}>Decline</Button>}
        {c.quote?.status === 'SENT' && <span className="text-[12px] text-ink-500">Waiting for the broker (advance the clock from the header)</span>}
      </div>
      {msg && <div className="mt-2 rounded-md bg-ok-bg px-3 py-1.5 text-[12.5px] text-ok">{msg}</div>}
      {err && <div className="mt-2 rounded-md bg-crit-bg px-3 py-1.5 text-[12.5px] text-crit">{err.message}</div>}
    </Card>
  );
}

function Outcome({ c, className }: { c: CaseDetail; className?: string }) {
  const o = c.outcome;
  const ex = c.exposure_detail;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Outcome feedback<Info id="decision.outcome" /></span>} subtitle="Claims stub six months after bind · flags scored against what happened">
      <div className="mb-3 grid grid-cols-3 gap-2 text-[12px]">
        <div className="rounded-md border border-line p-2"><div className="text-ink-500">Corrected at prep</div><div className="num text-[15px] font-semibold">{usd(ex.preparation)}</div></div>
        <div className="rounded-md border border-line p-2"><div className="text-ink-500">At assurance</div><div className="num text-[15px] font-semibold">{usd(ex.assurance)}</div><div className="text-[10.5px] text-ink-500">{ex.kind ?? ''}</div></div>
        <div className="rounded-md border border-line p-2"><div className="text-ink-500">Loss avoided</div><div className="num text-[15px] font-semibold text-ok">{usd(ex.loss_avoided)}</div></div>
      </div>
      {!o ? <Empty>{c.bound ? 'Outcome review is scheduled six months after bind.' : 'No bound policy yet.'}</Empty> : (
        <div className="text-[12.5px]">
          <div className={cx('rounded-md border p-2.5', o.loss ? 'border-[#f5d2b8] bg-high-bg/50' : 'border-[#bfe3cd] bg-ok-bg/50')}>
            {o.loss ? <><div className="font-semibold">{o.loss.cause} loss {usd(o.loss.incurred, { compact: false })} · {o.loss.location}</div><div className="text-ink-600">{o.loss.desc} · {fmtDate(o.loss.dol)}</div>{o.loss.excluded && <div className="mt-1 font-medium text-ok">Excluded under the wording the assurance corrected.</div>}</> : <div className="font-semibold">Clean — no losses to {fmtDate(o.at)}</div>}
          </div>
          <SectionLabel>Flags on the commitment</SectionLabel>
          {c.feedback.map((f) => <div key={f.rule_id} className="flex items-center justify-between py-0.5"><span className="mono text-[11.5px]">{f.rule_id} <span className="text-ink-400">T{f.tier}{f.overridden ? ' · overridden' : ''}</span></span><Badge tone={f.outcome === 'CONFIRMED' ? 'crit' : 'neutral'}>{f.outcome === 'CONFIRMED' ? 'confirmed by loss' : 'not confirmed'}</Badge></div>)}
        </div>
      )}
    </Card>
  );
}

export function ReferralCard({ r, showCase }: { r: Referral; showCase?: boolean }) {
  const dec = useDecideDaReferral();
  const { data: users } = useUsers();
  const uid = useMe();
  const me = users?.find((u) => u.user_id === uid);
  const [conds, setConds] = useState('');
  const [note, setNote] = useState('');
  const can = r.status === 'PENDING' && (me?.authority_level ?? 0) >= r.required_level;
  return (
    <div className="grid grid-cols-12 gap-4 px-4 py-3">
      <div className="col-span-12 lg:col-span-7">
        <div className="mb-1 flex flex-wrap items-center gap-2 text-[12.5px]">
          <Badge tone={r.status === 'PENDING' ? 'info' : r.status === 'APPROVED' ? 'ok' : 'crit'}>{r.status.toLowerCase()}</Badge><Badge tone="dark">L{r.required_level}</Badge>{r.kind === 'pre' && <Badge>pre-referral</Badge>}
          {showCase && <Link to={r.href} className="font-medium text-accent-700 hover:underline">{r.scenario && `${r.scenario} · `}{r.insured}</Link>}
          <span className="text-ink-500">requested by {r.requested_by} · {fmtDate(r.requested_at)}</span>
        </div>
        <CitedText text={r.memo} className="text-[12.5px]" />
      </div>
      <div className="col-span-12 lg:col-span-5">
        {r.status !== 'PENDING' ? (
          <div className="rounded-md border border-line bg-ink-50 p-2.5 text-[12.5px]">
            <div className="font-semibold">{r.status === 'APPROVED' ? 'Approved' : 'Declined'} by {r.approver} (L{r.approver_level}) · {fmtDate(r.decided_at)}</div>
            {r.decision_note && <div className="text-ink-600">{r.decision_note}</div>}
            {r.envelope_text && <div className="mt-1">Envelope: <span className="font-medium">{r.envelope_text}</span></div>}
            {r.conditions.length > 0 && <ul className="mt-1 list-disc pl-4">{r.conditions.map((x) => <li key={x}>{x}</li>)}</ul>}
          </div>
        ) : (
          <div className="space-y-2">
            {!can && <div className="text-[12px] text-ink-500">Needs L{r.required_level}. Switch persona (top right) to an approver with that authority.</div>}
            <textarea value={conds} onChange={(e) => setConds(e.target.value)} rows={2} placeholder="Conditions, one per line (optional)" className="w-full resize-none rounded-md border border-line-strong px-2 py-1 text-[12px] outline-none focus:border-accent-500" disabled={!can} />
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Decision note" className="h-7 w-full rounded-md border border-line-strong px-2 text-[12px] outline-none focus:border-accent-500" disabled={!can} />
            <div className="flex gap-2">
              <Button size="sm" variant="primary" disabled={!can} loading={dec.isPending} onClick={() => dec.mutate({ rid: r.referral_id, decision: 'APPROVE', conditions: conds.split('\n'), note })}>Approve</Button>
              <Button size="sm" variant="danger" disabled={!can} loading={dec.isPending} onClick={() => dec.mutate({ rid: r.referral_id, decision: 'DECLINE', note })}>Decline</Button>
            </div>
            {dec.error && <div className="text-[12px] text-crit">{(dec.error as Error).message}</div>}
          </div>
        )}
      </div>
    </div>
  );
}
