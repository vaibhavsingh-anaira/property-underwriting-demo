import { useState } from 'react';
import { FileText } from 'lucide-react';
import type { AccountDetail } from '@/api/types';
import { useCat } from '@/api/client';
import { Card, Badge, Loading, ErrorBox, Empty, MockBadge, Segmented, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { usd, pct, fmtDate } from '@/lib/format';
import { EpCurveChart } from '@/viewers/EpCurveChart';
import { Bar } from '../common';
import { Info } from '@/help/Info';

const SNAP_LABEL = { CURRENT: 'Current', AS_BOUND: 'As bound', RENEWAL_PROPOSED: 'Renewal proposed' } as const;

export default function CatTab({ a }: { a: AccountDetail }) {
  const { data, isLoading, error } = useCat(a.account_id);
  const ev = useEvidence();
  const [snap, setSnap] = useState<string | null>(null);
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data?.length) return <Card><Empty>No CAT run yet — account is outside the T-150 window.</Empty></Card>;
  const run = data.find((r) => r.run_id === snap) ?? data[0];
  const maxP = Math.max(...run.aal_by_peril.map((p) => p.aal), 1);
  const IMPACT_W = { HIGH: 3, MEDIUM: 2, LOW: 1 } as const;
  const dq = [...run.dq_flags].sort((x, y) => IMPACT_W[y.impact] - IMPACT_W[x.impact]);
  const locName = (uid: string) => a.locations.find((l) => l.location_uid === uid);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[12px] text-ink-600">
          <Info id="account.cat" label="About this tab" /><MockBadge label="MockCat" /><span>{run.vendor}</span><span className="text-ink-400">·</span><span className="mono">{run.model_version}</span><span className="text-ink-400">·</span><span>run {fmtDate(run.run_date)}</span><span className="text-ink-400">·</span><span>{run.basis}</span>
        </div>
        <Segmented value={run.run_id} onChange={setSnap} options={data.map((r) => ({ key: r.run_id, label: SNAP_LABEL[r.snapshot] }))} />
      </div>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 lg:col-span-4" title="Average annual loss" subtitle={run.perils.join(' · ')}>
          <div className="num text-[30px] font-semibold tracking-[-0.02em] text-ink-950">{usd(run.aal_total)}</div>
          <div className="mb-3 text-[12px] text-ink-500">AAL / expiring premium <span className="num font-medium text-ink-800">{pct(run.aal_total / a.policy.premium, 1)}</span></div>
          <div className="space-y-2">
            {run.aal_by_peril.map((p) => (
              <div key={p.peril} className="grid grid-cols-[120px_1fr_64px] items-center gap-2 text-[12px]">
                <span className="text-ink-700">{p.peril}</span><Bar value={p.aal} max={maxP} tone={p.peril === 'Named storm' ? 'high' : 'accent'} /><span className="num text-right font-medium">{usd(p.aal)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-3">
            {[['Exposure file (OED)', run.exposure_doc_id], ['Event loss table', run.elt_doc_id], ['EP curve', run.ep_doc_id]].filter(([, d]) => d).map(([l, d]) => (
              <button key={l} onClick={() => ev.openDoc(d!)} className="inline-flex items-center gap-1 rounded-md border border-line-strong px-2 py-1 text-[11.5px] text-ink-700 hover:bg-ink-50"><FileText className="size-3" />{l}</button>
            ))}
          </div>
        </Card>
        <Card className="col-span-12 lg:col-span-8" title="Exceedance probability" subtitle="OEP / AEP by return period (log scale) · prior runs overlaid">
          <EpCurveChart oep={run.oep} aep={run.aep} compare={data.filter((r) => r.run_id !== run.run_id).map((r) => ({ label: SNAP_LABEL[r.snapshot], oep: r.oep }))} height={280} />
          {data[0].compare.length > 0 && (
            <table className="dt mt-3">
              <thead><tr><th>Run</th><th className="r">AAL</th><th className="r">OEP 1-in-100</th><th className="r">OEP 1-in-250</th></tr></thead>
              <tbody>{data[0].compare.map((c) => <tr key={c.label}><td>{c.label}</td><td className="num r">{usd(c.aal_total)}</td><td className="num r">{usd(c.oep_100)}</td><td className="num r">{usd(c.oep_250)}</td></tr>)}</tbody>
            </table>
          )}
        </Card>
      </div>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-7" pad={false} title="CAT input vs resolved risk state" subtitle="What the model was run on vs what the evidence ledger says today">
          {run.input_mismatches.length === 0 ? <Empty>Model inputs match the resolved risk state.</Empty> : (
            <table className="dt">
              <thead><tr><th>Location</th><th>Field</th><th>CAT input</th><th>Resolved</th></tr></thead>
              <tbody>
                {run.input_mismatches.map((m, i) => {
                  const l = locName(m.location_uid);
                  return (
                    <tr key={i}>
                      <td>{l ? `Loc ${l.loc_no_current ?? l.loc_no_prior} · ${l.city}` : m.location_uid}</td>
                      <td className="font-medium text-ink-800">{m.field}</td>
                      <td><span className="rounded bg-crit-bg px-1.5 text-[12px] text-crit line-through decoration-crit/40">{m.cat_input}</span></td>
                      <td>
                        {l && ['Roof year', 'Occupancy', 'Construction', 'TIV'].includes(m.field)
                          ? <button onClick={() => ev.openObs(`ob-${l.location_uid}-${m.field === 'Roof year' ? 'roof' : m.field === 'Occupancy' ? 'occ' : m.field === 'Construction' ? 'const' : 'tiv'}`)} className="rounded bg-ok-bg px-1.5 text-[12px] font-medium text-ok hover:underline">{m.resolved}</button>
                          : <span className="rounded bg-ok-bg px-1.5 text-[12px] font-medium text-ok">{m.resolved}</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
        <Card className="col-span-12 xl:col-span-5" pad={false} title="Data-quality flags" subtitle="Weighted by modelled-loss impact">
          {dq.length === 0 ? <Empty>No flags.</Empty> : dq.map((f, i) => (
            <div key={i} className="flex items-start gap-2 border-b border-line px-4 py-2 last:border-0">
              <Badge tone={f.impact === 'HIGH' ? 'crit' : f.impact === 'MEDIUM' ? 'med' : 'low'}>{f.impact.toLowerCase()}</Badge>
              <div><div className="text-[12.5px] text-ink-900">{f.label} · <span className="mono text-[11.5px]">{f.field}</span></div><div className="text-[11.5px] text-ink-500">{f.issue}</div></div>
            </div>
          ))}
        </Card>
      </div>
      <Card pad={false} title="Location contribution" subtitle="Share of account AAL">
        <table className="dt">
          <thead><tr><th>Location</th><th className="r">TIV</th><th className="r">AAL</th><th className="r">Share</th><th className="w-[35%]" /><th className="r">AAL / TIV</th></tr></thead>
          <tbody>
            {run.location_contrib.map((l) => (
              <tr key={l.location_uid}>
                <td>{l.label}</td><td className="num r">{usd(l.tiv)}</td><td className="num r font-medium">{usd(l.aal)}</td><td className="num r">{pct(l.pct, 1)}</td>
                <td><Bar value={l.pct} max={1} tone={l.pct > 0.4 ? 'high' : 'accent'} /></td>
                <td className={cx('num r text-ink-500')}>{((l.aal / Math.max(1, l.tiv)) * 1e4).toFixed(2)} bp</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
