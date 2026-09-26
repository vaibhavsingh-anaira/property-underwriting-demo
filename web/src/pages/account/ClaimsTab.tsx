import { Link2, AlertTriangle } from 'lucide-react';
import type { AccountDetail } from '@/api/types';
import { useClaimsEngineering } from '@/api/client';
import { Card, Badge, Loading, ErrorBox, Stat, SeverityPill, Empty, MockBadge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { usd, pct, fmtDate } from '@/lib/format';
import { Bar } from '../common';
import { Info } from '@/help/Info';

export default function ClaimsTab({ a }: { a: AccountDetail }) {
  const { data: c, isLoading, error } = useClaimsEngineering(a.account_id);
  const ev = useEvidence();
  if (isLoading) return <Loading />;
  if (error || !c) return <ErrorBox error={error} />;
  const s = c.summary;
  const cat = c.claims.filter((x) => x.cat_event).reduce((t, x) => t + x.incurred, 0);
  const attr = s.incurred_5y - cat;
  const maxC = Math.max(...s.by_cause.map((b) => b.incurred), 1);
  const recLinked = new Set(c.claims.map((x) => x.linked_recommendation).filter(Boolean));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Claims · 5 years" value={s.count_5y} />
        <Stat label="Incurred · 5 years" value={usd(s.incurred_5y)} />
        <Stat label="Loss ratio · 5 years" value={pct(s.loss_ratio_5y, 1)} tone={s.loss_ratio_5y > 0.6 ? 'crit' : s.loss_ratio_5y > 0.45 ? 'high' : 'ok'} />
        <Stat label="CAT vs attritional" value={<span className="text-[18px]">{usd(cat)} <span className="text-ink-400">/</span> {usd(attr)}</span>} sub={s.incurred_5y ? `${pct(cat / s.incurred_5y, 0)} CAT` : undefined} />
        <Stat label="Recommendations open" value={c.recommendations.filter((r) => r.status === 'OPEN' || r.status === 'IN_PROGRESS').length} tone={c.recommendations.some((r) => r.days_overdue > 0 && r.status !== 'VERIFIED_CLOSED') ? 'high' : undefined} sub={`${c.recommendations.filter((r) => r.days_overdue > 0 && r.status !== 'VERIFIED_CLOSED' && r.status !== 'CLOSED').length} overdue`} />
      </div>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 lg:col-span-4" title="Incurred by cause">
          {s.by_cause.length === 0 ? <Empty>No losses in 5 years.</Empty> : s.by_cause.map((b) => (
            <div key={b.cause} className="mb-2 grid grid-cols-[110px_1fr_70px] items-center gap-2 text-[12px]">
              <span className="text-ink-700">{b.cause} <span className="text-ink-400">×{b.count}</span></span><Bar value={b.incurred} max={maxC} tone={b.count > 1 ? 'high' : 'accent'} /><span className="num text-right font-medium">{usd(b.incurred)}</span>
            </div>
          ))}
        </Card>
        <Card className="col-span-12 lg:col-span-8" pad={false} title={<span className="inline-flex items-center gap-1.5">Claims<Info id="account.claims" /></span>} subtitle={<>Claims system <MockBadge /></>}>
          <table className="dt">
            <thead><tr><th>Claim</th><th>Date of loss</th><th>Location</th><th>Cause</th><th className="r">Paid</th><th className="r">Reserve</th><th className="r">Incurred</th><th>Status</th><th>Linked rec.</th></tr></thead>
            <tbody>
              {c.claims.map((x) => (
                <tr key={x.claim_id} title={x.description}>
                  <td className="mono text-[11.5px]">{x.claim_id}</td><td className="num">{fmtDate(x.date_of_loss)}</td><td>{x.location_label}</td>
                  <td>{x.cause}{x.cat_event && <Badge tone="info" className="ml-1">{x.cat_event}</Badge>}</td>
                  <td className="num r">{usd(x.paid)}</td><td className="num r">{usd(x.reserve)}</td><td className="num r font-semibold">{usd(x.incurred)}</td>
                  <td><Badge tone={x.status === 'OPEN' ? 'high' : 'neutral'}>{x.status.toLowerCase()}</Badge></td>
                  <td>{x.linked_recommendation ? <Badge tone="crit"><Link2 className="size-3" />{x.linked_recommendation}</Badge> : <span className="text-ink-400">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {c.claims.length === 0 && <Empty>No claims.</Empty>}
        </Card>
      </div>
      <Card pad={false} title="Recommendation register" subtitle={<>Engineering system <MockBadge /> · closures without evidence are flagged</>}>
        <table className="dt">
          <thead><tr><th>Rec</th><th>Location</th><th>Recommendation</th><th>Severity</th><th>Due</th><th className="r">Overdue</th><th>Status</th><th>Evidence</th></tr></thead>
          <tbody>
            {c.recommendations.map((r) => {
              const noEvidence = r.status === 'CLOSED' && !r.completion_evidence;
              return (
                <tr key={r.rec_id} className={cx(noEvidence && 'bg-crit-bg/40')}>
                  <td className="mono text-[11.5px] font-medium">{r.rec_id}{recLinked.has(r.rec_id) && <Link2 className="ml-1 inline size-3 text-crit" />}</td>
                  <td>{r.location_label}</td>
                  <td className="max-w-[380px]">{r.description}<div className="text-[11px] text-ink-500">{r.category} · raised {fmtDate(r.raised)}{r.bind_condition && <Badge tone="dark" className="ml-1.5">bind condition</Badge>}</div></td>
                  <td><SeverityPill s={r.severity} /></td>
                  <td className="num">{fmtDate(r.due)}</td>
                  <td className={cx('num r', r.days_overdue > 0 && r.status !== 'VERIFIED_CLOSED' ? 'font-semibold text-crit' : 'text-ink-400')}>{r.days_overdue > 0 && r.status !== 'VERIFIED_CLOSED' ? `${r.days_overdue}d` : '—'}</td>
                  <td><Badge tone={r.status === 'VERIFIED_CLOSED' ? 'ok' : noEvidence ? 'crit' : r.status === 'OPEN' ? 'high' : 'neutral'}>{r.status.replace('_', ' ').toLowerCase()}</Badge></td>
                  <td className="max-w-[260px] text-[12px]">
                    {noEvidence ? <span className="flex items-center gap-1 font-medium text-crit"><AlertTriangle className="size-3.5" />Closed without evidence</span> : r.completion_evidence ?? <span className="text-ink-400">—</span>}
                    {r.doc_id && <button onClick={() => ev.openDoc(r.doc_id!)} className="ml-1 text-accent-700 hover:underline">survey</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <Card pad={false} title="Surveys">
        <table className="dt">
          <thead><tr><th>Survey</th><th>Location</th><th>Date</th><th>Engineer</th><th /></tr></thead>
          <tbody>{c.surveys.map((s2) => <tr key={s2.survey_id}><td className="mono text-[11.5px]">{s2.survey_id}</td><td>{s2.location_label}</td><td className="num">{fmtDate(s2.date)}</td><td>{s2.engineer}</td><td className="r">{s2.doc_id ? <button onClick={() => ev.openDoc(s2.doc_id!)} className="text-[12px] text-accent-700 hover:underline">Open report</button> : <span className="text-[12px] text-ink-400">not on file</span>}</td></tr>)}</tbody>
        </table>
      </Card>
      {a.findings.some((f) => f.family === 'claims' || f.family === 'engineering') && <div className="text-[12px] text-ink-500">Related findings are on the Overview tab under Loss experience and Engineering recommendations.</div>}
    </div>
  );
}
