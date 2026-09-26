import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDataQuality, useMatchDecision } from '@/api/client';
import type { DataQualitySummary } from '@/api/types';
import { Page, Card, Stat, Badge, Button, Loading, ErrorBox, Empty, ScoreRing, cx } from '@/components/ui';
import { num, pct } from '@/lib/format';
import { Bar } from './common';
import { Info } from '@/help/Info';

export default function DataQualityPage() {
  const { data: d, isLoading, error } = useDataQuality();
  if (isLoading) return <Page title="Data quality"><Loading /></Page>;
  if (error || !d) return <Page title="Data quality"><ErrorBox error={error} /></Page>;
  const m = d.matching;
  const totalLoc = m.matched + m.new + m.deleted + m.ambiguous + m.merged + m.split;
  const segs = [
    { k: 'Matched', v: m.matched, c: 'bg-ok' }, { k: 'New', v: m.new, c: 'bg-info' }, { k: 'Deleted', v: m.deleted, c: 'bg-ink-400' },
    { k: 'Merged', v: m.merged, c: 'bg-accent-600' }, { k: 'Split', v: m.split, c: 'bg-[#7c4dcc]' }, { k: 'Ambiguous', v: m.ambiguous, c: 'bg-high' },
  ];
  return (
    <Page title="Data quality" actions={<Info id="dq.page" label="About this page" />} subtitle="Extraction confidence, location matching and impact-weighted gaps · scores weight each gap by modelled-loss share">
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Avg DQ score" value={d.avg_score.toFixed(0)} tone={d.avg_score < 75 ? 'high' : 'ok'} sub="AAL-weighted, 0–100" />
        <Stat label="Documents extracted" value={num(d.extraction.documents)} />
        <Stat label="Fields extracted" value={num(d.extraction.fields)} sub="each with a page/cell anchor" />
        <Stat label="Avg extraction confidence" value={pct(d.extraction.avg_confidence, 1)} />
        <Stat label="Human review queue" value={d.extraction.human_review_queue} tone={d.extraction.human_review_queue ? 'high' : 'ok'} />
      </div>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-5" title="Location matching across years" subtitle={`${num(totalLoc)} locations · prior SOV ↔ renewal SOV`}>
          <div className="flex h-3 overflow-hidden rounded-full">{segs.map((s) => s.v > 0 && <div key={s.k} className={s.c} style={{ width: `${(s.v / totalLoc) * 100}%` }} title={`${s.k} ${s.v}`} />)}</div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {segs.map((s) => <div key={s.k} className="flex items-center gap-2 text-[12px]"><span className={cx('size-2 rounded-sm', s.c)} /><span className="text-ink-600">{s.k}</span><span className="num ml-auto font-semibold text-ink-900">{s.v}</span></div>)}
          </div>
          <div className="mt-3 border-t border-line pt-2 text-[11.5px] text-ink-500">Matching uses loc no, geocode distance, name similarity and footprint overlap; renumbered SOVs, $000s scaling and totals rows are normalised before comparison.</div>
        </Card>
        <ReviewQueue d={d} className="col-span-12 xl:col-span-7" />
        <Card className="col-span-12" pad={false} title="Accounts ranked by data-quality score" subtitle="Lowest first · top gaps ordered by share of account AAL">
          <table className="dt">
            <thead><tr><th>Account</th><th>Score</th><th className="r">Missing</th><th className="r">Low conf.</th><th className="r">Stale</th><th className="r">Unmatched</th><th className="r">Conflicts</th><th>Top impact-weighted gaps</th></tr></thead>
            <tbody>
              {d.accounts.slice(0, 40).map((a) => (
                <tr key={a.account_id}>
                  <td><Link to={`/accounts/${a.account_id}/locations`} className="font-medium text-ink-900 hover:text-accent-700">{a.name}</Link></td>
                  <td><ScoreRing score={a.score} size={30} /></td>
                  <td className="num r">{a.missing_fields || '—'}</td><td className="num r">{a.low_confidence || '—'}</td><td className="num r">{a.stale_fields || '—'}</td>
                  <td className={cx('num r', a.unmatched_locations && 'text-high')}>{a.unmatched_locations || '—'}</td><td className={cx('num r', a.conflicts && 'text-high')}>{a.conflicts || '—'}</td>
                  <td className="max-w-[520px]">
                    {a.top_gaps.length === 0 ? <span className="text-ink-400">—</span> : a.top_gaps.slice(0, 3).map((g, i) => (
                      <div key={i} className="grid grid-cols-[1fr_60px_40px] items-center gap-2 text-[12px]">
                        <span className="truncate text-ink-700">{g.location_label} · <span className="mono text-[11px]">{g.field}</span> <span className="text-ink-400">— {g.reason}</span></span>
                        <Bar value={g.aal_weight} max={1} tone={g.aal_weight > 0.3 ? 'crit' : 'med'} /><span className="num text-right text-[11px] text-ink-500">{pct(g.aal_weight, 0)}</span>
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </Page>
  );
}

function ReviewQueue({ d, className }: { d: DataQualitySummary; className?: string }) {
  const mut = useMatchDecision();
  const [choice, setChoice] = useState<Record<string, string>>({});
  const KIND = { LOCATION_MATCH: { l: 'Location match', t: 'high' }, LOW_CONFIDENCE: { l: 'Low confidence', t: 'med' }, MAPPING: { l: 'Header mapping', t: 'info' } } as const;
  return (
    <Card className={className} pad={false} title="Human review queue" subtitle="Proposals below the auto-accept threshold — each decision is logged to the evidence ledger">
      {d.review_queue.length === 0 ? <Empty>Queue clear.</Empty> : (
        <div className="divide-y divide-line">
          {d.review_queue.map((r) => {
            const opt = choice[r.item_id] ?? r.options?.[0];
            return (
              <div key={r.item_id} className="px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2"><Badge tone={KIND[r.kind].t}>{KIND[r.kind].l}</Badge><span className="truncate text-[13px] font-medium text-ink-900">{r.label}</span></div>
                  <Link to={`/accounts/${r.account_id}/locations`} className="shrink-0 text-[11.5px] text-ink-500 hover:text-accent-700">{r.account_name}</Link>
                </div>
                <div className="mt-0.5 text-[12px] text-ink-600">{r.detail}</div>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  {r.options?.map((o) => (
                    <button key={o} onClick={() => setChoice({ ...choice, [r.item_id]: o })} className={cx('rounded-md border px-2 py-0.5 text-[11.5px]', opt === o ? 'border-accent-600 bg-accent-50 font-medium text-accent-700' : 'border-line-strong text-ink-700 hover:bg-ink-50')}>{o}</button>
                  ))}
                  <span className="flex-1" />
                  <Button size="sm" variant="ghost" disabled={mut.isPending} onClick={() => mut.mutate({ item_id: r.item_id, decision: 'REJECT' })}>Reject</Button>
                  <Button size="sm" variant="primary" loading={mut.isPending && mut.variables?.item_id === r.item_id} onClick={() => mut.mutate({ item_id: r.item_id, decision: 'CONFIRM', option: opt })}>Confirm</Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
