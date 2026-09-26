import { useState } from 'react';
import { Link } from 'react-router-dom';
import { FileSignature, Stamp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { AccountDetail, ContractCol, ContractDiffRow, Finding } from '@/api/types';
import { useBind, useContract, useIssue } from '@/api/client';
import { Card, Badge, Button, Loading, ErrorBox, SeverityPill, MockBadge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { usd, fmtDate } from '@/lib/format';
import { SectionLabel } from '../common';
import { Info } from '@/help/Info';

const COL_LABEL: Record<ContractCol, string> = { quote: 'Quote', binder: 'Binder', policy: 'Issued policy', endorsed: 'As endorsed' };
const GROUPS: ContractDiffRow['group'][] = ['Limits', 'Deductibles', 'Sublimits', 'Forms', 'Safeguards', 'Subjectivities', 'Premium'];

export default function ContractTab({ a }: { a: AccountDetail }) {
  const { data: c, isLoading, error } = useContract(a.account_id);
  const ev = useEvidence();
  if (isLoading) return <Loading />;
  if (error || !c) return <ErrorBox error={error} />;
  const cols = (['quote', 'binder', 'policy', 'endorsed'] as ContractCol[]).filter((k) => c.rows.some((r) => k in r.values));
  const mismatches = c.rows.filter((r) => r.result !== 'MATCH');
  const fById = (id: string | null) => (id ? a.findings.find((f) => f.finding_id === id) : undefined);
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 space-y-4 xl:col-span-8">
        <Card pad={false} title={<span className="inline-flex items-center gap-1.5">{`Contract integrity — ${c.term}`}<Info id="account.contract" /></span>} subtitle={<>Quote {c.quote_version} ↔ binder ↔ issued policy{cols.includes('endorsed') ? ' ↔ as endorsed' : ''} · click any cell to open the source at the anchor</>}
          actions={mismatches.length ? <Badge tone="crit"><AlertTriangle className="size-3" />{mismatches.length} mismatch{mismatches.length > 1 ? 'es' : ''}</Badge> : <Badge tone="ok"><CheckCircle2 className="size-3" />All fields match</Badge>}>
          <table className="dt">
            <thead><tr><th className="w-[26%]">Field</th>{cols.map((k) => <th key={k}>{COL_LABEL[k]}</th>)}<th>Result</th></tr></thead>
            {GROUPS.filter((g) => c.rows.some((r) => r.group === g)).map((g) => (
              <tbody key={g}>
                <tr><td colSpan={cols.length + 2} className="!bg-ink-50/60 !py-1"><SectionLabel>{g}</SectionLabel></td></tr>
                {c.rows.filter((r) => r.group === g).map((r) => {
                  const bad = r.result !== 'MATCH';
                  const first = cols.map((k) => r.values[k]).find((v) => v !== undefined);
                  const f = fById(r.finding_id);
                  return (
                    <tr key={r.field} className={cx(bad && 'bg-crit-bg/40')}>
                      <td className="font-medium text-ink-800">{r.label}</td>
                      {cols.map((k) => {
                        const v = r.values[k], an = r.anchors[k];
                        const differs = bad && v !== first;
                        return (
                          <td key={k}>
                            <button disabled={!an?.doc_id} onClick={() => an?.doc_id && ev.openDoc(an.doc_id, an)} title={an?.text ?? (an?.page ? `p.${an.page}` : undefined)}
                              className={cx('num rounded px-1 text-left text-[12.5px]', an?.doc_id && 'hover:bg-accent-50 hover:underline', differs ? 'bg-crit-bg font-semibold text-crit ring-1 ring-[#f6c5cc]' : v === null ? 'italic text-crit' : 'text-ink-900')}>
                              {v === null ? 'missing' : v === undefined ? '—' : v}
                              {an?.page && <span className="ml-1 text-[10px] font-normal text-ink-400">p.{an.page}</span>}
                            </button>
                          </td>
                        );
                      })}
                      <td>
                        {bad ? (
                          <button onClick={() => f && ev.openFinding(f)} className="text-left">
                            <Badge tone="crit">{r.result.toLowerCase()}</Badge>
                            {f && <div className="mt-0.5 max-w-[220px] text-[11px] leading-tight text-crit underline decoration-dotted underline-offset-2">{f.title}</div>}
                          </button>
                        ) : <Badge tone="ok">match</Badge>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            ))}
          </table>
        </Card>
        <BindIssue a={a} quotes={c.quotes} />
      </div>
      <div className="col-span-12 space-y-4 xl:col-span-4">
        <Card title="Endorsements" subtitle={c.term}>
          {c.endorsements.length === 0 ? <div className="text-[12px] text-ink-500">None.</div> : (
            <ol className="relative ml-1.5 border-l border-line">
              {c.endorsements.map((e) => (
                <li key={e.endt_id} className="mb-3 ml-3.5 last:mb-0">
                  <span className="absolute -left-[5px] mt-1.5 size-2.5 rounded-full border-2 border-surface bg-accent-600" />
                  <div className="num text-[11px] text-ink-500">{fmtDate(e.effective)} · <span className="mono">{e.endt_id}</span></div>
                  <div className="text-[12.5px] font-medium text-ink-900">{e.type}</div>
                  <div className="text-[12px] text-ink-600">{e.description}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-[11px]"><span className="num text-ink-500">Premium {e.premium_delta ? usd(e.premium_delta, { sign: true }) : '$0'}</span>{e.doc_id && <button onClick={() => ev.openDoc(e.doc_id!)} className="text-accent-700 hover:underline">open</button>}</div>
                </li>
              ))}
            </ol>
          )}
        </Card>
        <Card title={<span className="inline-flex items-center gap-1.5">Subjectivities<Info id="account.subjectivities" /></span>}>
          {c.subjectivities.length === 0 ? <div className="text-[12px] text-ink-500">None.</div> : c.subjectivities.map((s, i) => (
            <div key={i} className="flex items-start justify-between gap-2 border-b border-line py-2 last:border-0">
              <div><div className="text-[12.5px] text-ink-900">{s.text}</div><div className="num text-[11px] text-ink-500">due {fmtDate(s.due)}</div></div>
              <div className="text-right">
                <Badge tone={s.status === 'OPEN' ? (s.age_days > 30 ? 'crit' : 'med') : 'ok'}>{s.status.toLowerCase()}</Badge>
                {s.status === 'OPEN' && <div className={cx('num mt-0.5 text-[11px] font-semibold', s.age_days > 30 ? 'text-crit' : 'text-ink-600')}>{s.age_days} days open</div>}
              </div>
            </div>
          ))}
        </Card>
        <Card title={<span className="inline-flex items-center gap-1.5">Quote versions<Info id="account.quotes" /></span>} subtitle="Approvals are locked to the terms hash" pad={false}>
          <table className="dt">
            <thead><tr><th>Ver</th><th className="r">Premium</th><th>Hash</th><th>Status</th></tr></thead>
            <tbody>
              {c.quotes.map((q) => (
                <tr key={q.quote_id}>
                  <td><div className="font-medium">v{q.version}</div><div className="text-[10.5px] text-ink-400">{q.term} · {fmtDate(q.created_at)}</div></td>
                  <td className="num r">{usd(q.premium)}</td>
                  <td className="mono text-[11px] text-ink-600">{q.terms_hash}</td>
                  <td><Badge tone={q.status === 'BOUND' ? 'dark' : q.status === 'APPROVED' || q.status === 'ACCEPTED' ? 'ok' : q.status === 'SENT' ? 'accent' : q.status === 'REFERRED' ? 'info' : 'neutral'}>{q.status.toLowerCase()}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title={<span className="inline-flex items-center gap-1.5">Referrals<Info id="account.referrals" /></span>} pad={false}>
          {c.referrals.length === 0 ? <div className="p-4 text-[12px] text-ink-500">No referrals on this account.</div> : c.referrals.map((r) => (
            <Link key={r.referral_id} to={`/referrals?id=${r.referral_id}`} className="block border-b border-line px-4 py-2.5 last:border-0 hover:bg-ink-50">
              <div className="flex items-center justify-between"><span className="text-[12.5px] font-medium text-ink-900">L{r.required_level} · {r.requested_by}</span><Badge tone={r.status === 'APPROVED' ? 'ok' : r.status === 'INVALIDATED' || r.status === 'DECLINED' ? 'crit' : 'info'}>{r.status.toLowerCase()}</Badge></div>
              <div className="num text-[11px] text-ink-500">{fmtDate(r.requested_at)}{r.terms_hash && <> · hash <span className="mono">{r.terms_hash}</span></>}{r.approver && <> · {r.approver}</>}</div>
              {r.invalidated_reason && <div className="mt-1 rounded bg-crit-bg px-2 py-1 text-[11.5px] text-crit">{r.invalidated_reason}</div>}
            </Link>
          ))}
        </Card>
      </div>
    </div>
  );
}

function BindIssue({ a, quotes }: { a: AccountDetail; quotes: import('@/api/types').QuoteVersion[] }) {
  const bind = useBind(a.account_id), issue = useIssue(a.account_id);
  const [result, setResult] = useState<{ kind: 'bind' | 'issue'; doc: string; findings: Finding[] } | null>(null);
  const ev = useEvidence();
  const candidate = [...quotes].filter((q) => ['ACCEPTED', 'APPROVED', 'SENT', 'DRAFT'].includes(q.status)).sort((x, y) => (y.term > x.term ? 1 : y.term < x.term ? -1 : y.version - x.version))[0];
  const status = a.renewal.status;
  return (
    <Card title={<span className="inline-flex items-center gap-1.5">Bind & issue<Info id="account.bind_issue" /></span>} subtitle={<>Pass 3 runs on the final terms: authority re-checked, binder ↔ policy compared <MockBadge label="PAS mock" /></>}>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="primary" icon={<FileSignature className="size-3.5" />} disabled={!candidate || status === 'BOUND' || status === 'ISSUED'} loading={bind.isPending}
          onClick={() => candidate && bind.mutate({ quote_id: candidate.quote_id }, { onSuccess: (r) => setResult({ kind: 'bind', doc: r.binder_doc_id, findings: r.findings }) })}>
          Bind{candidate ? ` quote v${candidate.version} (${usd(candidate.premium)})` : ''}
        </Button>
        <Button icon={<Stamp className="size-3.5" />} disabled={status !== 'BOUND'} loading={issue.isPending}
          onClick={() => issue.mutate(undefined, { onSuccess: (r) => setResult({ kind: 'issue', doc: r.policy_doc_id, findings: r.findings }) })}>Issue policy</Button>
        {!candidate && <span className="text-[12px] text-ink-500">Save a renewal quote on the Pricing tab first.</span>}
        {(status === 'BOUND' || status === 'ISSUED') && <Badge tone="dark">{status.toLowerCase()}</Badge>}
      </div>
      {(bind.error || issue.error) && <div className="mt-3"><ErrorBox error={bind.error ?? issue.error} /></div>}
      {result && (
        <div className="anim-fade mt-3 rounded-lg border border-line p-3">
          <div className="mb-2 flex items-center justify-between text-[12.5px]">
            <span className="font-medium text-ink-900">{result.kind === 'bind' ? 'Binder generated' : 'Policy issued'} — {result.findings.length ? `${result.findings.length} contract-integrity finding${result.findings.length > 1 ? 's' : ''}` : 'Pass 3 clean'}</span>
            <button onClick={() => ev.openDoc(result.doc)} className="text-[12px] text-accent-700 hover:underline">Open document</button>
          </div>
          {result.findings.map((f) => (
            <button key={f.finding_id} onClick={() => ev.openFinding(f)} className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left hover:bg-ink-50">
              <SeverityPill s={f.severity} /><span className="text-[12.5px] text-ink-900">{f.title}</span><span className="ml-auto text-[11px] text-ink-500">{f.observed}</span>
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}
