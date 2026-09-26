import { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, AlertTriangle } from 'lucide-react';
import { useBook } from '@/api/client';
import type { BookSummary } from '@/api/types';
import { Page, Card, Stat, Loading, ErrorBox, Badge, cx } from '@/components/ui';
import { usd, pct, fmtDate, num, ACTION_LABEL } from '@/lib/format';
import { GeoMap, type MapPoint } from '@/viewers/GeoMap';
import { Bar, SectionLabel } from './common';
import { Info } from '@/help/Info';

export default function BookPage() {
  const { data: b, isLoading, error } = useBook();
  if (isLoading) return <Page title="Renewal book"><Loading /></Page>;
  if (error || !b) return <Page title="Renewal book"><ErrorBox error={error} /></Page>;
  return (
    <Page title="Renewal book"
      subtitle={<>{b.carrier} · as of <span className="num">{fmtDate(b.as_of)}</span> · <span className="num">{b.renewals}</span> renewals · <span className="num">{num(b.locations)}</span> locations · <span className="num">{usd(b.tiv)}</span> TIV · <span className="num">{usd(b.premium_expiring)}</span> expiring premium</>}
      actions={<><Info id="book.page" label="About this page" /><Link to="/renewals" className="inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white hover:bg-ink-800">Open renewal queue <ArrowRight className="size-3.5" /></Link></>}>
      <Kpis b={b} />
      <div className="mt-4 grid grid-cols-12 gap-4">
        <DollarPipeline b={b} className="col-span-12 xl:col-span-7" />
        <RarcInsight b={b} className="col-span-12 xl:col-span-5" />
        <AdequacyHist b={b} className="col-span-12 lg:col-span-6 xl:col-span-4" />
        <ByMonth b={b} className="col-span-12 lg:col-span-6 xl:col-span-4" />
        <ByAction b={b} className="col-span-12 xl:col-span-4" />
        <ByFamily b={b} className="col-span-12 lg:col-span-6 xl:col-span-4" />
        <ByUnderwriter b={b} className="col-span-12 lg:col-span-6 xl:col-span-4" />
        <ByBroker b={b} className="col-span-12 xl:col-span-4" />
        <Accumulation b={b} className="col-span-12" />
      </div>
    </Page>
  );
}

function Kpis({ b }: { b: BookSummary }) {
  const nav = useNavigate();
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Stat label={<span className="inline-flex items-center gap-1.5">Renewals analysed<Info id="book.kpis" className="normal-case" /></span>} value={b.renewals} sub={`${fmtDate(b.by_month[0]?.month + '-01')} – ${fmtDate(b.by_month.at(-1)?.month + '-28').replace(/\d+, /, '')}`} onClick={() => nav('/renewals')} />
      <Stat label="Fast-tracked" value={b.fast_track} tone="ok" sub={`${pct(b.fast_track / b.renewals, 0)} of book · one-click confirm`} onClick={() => nav('/renewals?status=FAST_TRACK')} />
      <Stat label="Material action" value={b.material_action} tone="crit" sub="Findings above materiality" onClick={() => nav('/renewals?status=ACTION_REQUIRED')} />
      <Stat label="Not started" value={b.not_started} sub="Outside T-150 window" onClick={() => nav('/renewals?status=NOT_STARTED')} />
      <Stat label="Inadequacy identified" value={usd(b.pipeline.identified)} tone="high" sub={`${usd(b.pipeline.corrected)} corrected so far`} />
      <Stat label="Computed book RARC" value={pct(b.rarc_computed, 1, true)} tone={b.rarc_computed < 0 ? 'crit' : 'ok'} sub={<>reported <span className="num">{pct(b.rarc_reported, 1, true)}</span></>} />
    </div>
  );
}

function DollarPipeline({ b, className }: { b: BookSummary; className?: string }) {
  const steps = [
    { k: 'Identified', v: b.pipeline.identified, d: 'Platform findings with $ impact', tone: 'bg-ink-700' },
    { k: 'Validated', v: b.pipeline.validated, d: 'Accepted by underwriter (reason-coded)', tone: 'bg-accent-700' },
    { k: 'Approved', v: b.pipeline.approved, d: 'Within authority or senior-approved', tone: 'bg-accent-600' },
    { k: 'Corrected', v: b.pipeline.corrected, d: 'Actually bound / endorsed', tone: 'bg-ok' },
  ];
  const max = steps[0].v || 1;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Dollar pipeline<Info id="book.pipeline" /></span>} subtitle="Potential premium inadequacy and control exposure, from finding to correction">
      <div className="space-y-3">
        {steps.map((s, i) => (
          <div key={s.k} className="grid grid-cols-[92px_1fr_150px] items-center gap-3">
            <div>
              <div className="text-[13px] font-medium text-ink-900">{s.k}</div>
              <div className="text-[11px] leading-tight text-ink-500">{s.d}</div>
            </div>
            <div className="relative flex h-8 items-center rounded-md bg-ink-50">
              <div className={cx('flex h-full items-center rounded-md px-2.5 text-[12px] font-semibold text-white transition-all', s.tone)} style={{ width: `${Math.max(0.6, (s.v / max) * 100)}%` }}>
                {s.v / max >= 0.18 && <span className="num">{usd(s.v)}</span>}
              </div>
              {s.v / max < 0.18 && <span className="num ml-2 text-[12px] font-semibold text-ink-900">{usd(s.v)}</span>}
            </div>
            <div className="num text-right text-[12px] text-ink-500">
              {i === 0 ? '100%' : <><span className="font-semibold text-ink-900">{pct(s.v / steps[i - 1].v, 0)}</span> of {steps[i - 1].k.toLowerCase()}</>}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-[12px] text-ink-500">
        <span>Leakage still open: <span className="num font-semibold text-crit">{usd(b.pipeline.identified - b.pipeline.corrected)}</span> · conversion identified → corrected <span className="num font-semibold text-ink-900">{pct(b.pipeline.corrected / b.pipeline.identified, 0)}</span></span>
        <Link to="/renewals?status=ACTION_REQUIRED" className="font-medium text-accent-700 hover:underline">Work the open findings →</Link>
      </div>
    </Card>
  );
}

function RarcInsight({ b, className }: { b: BookSummary; className?: string }) {
  const gap = b.rarc_reported - b.rarc_computed;
  const lo = Math.min(-0.04, b.rarc_computed - 0.01), hi = Math.max(0.06, b.rarc_reported + 0.01);
  const x = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Real rate change — computed vs reported<Info id="book.rarc" /></span>} subtitle="Premium-weighted RARC across renewals with a technical rerun">
      <div className="text-[15px] leading-snug text-ink-800">
        Underwriters report <span className="num font-semibold text-ink-950">{pct(b.rarc_reported, 1, true)}</span>; like-for-like it's{' '}
        <span className={cx('num font-semibold', b.rarc_computed < 0 ? 'text-crit' : 'text-ok')}>{pct(b.rarc_computed, 1, true)}</span>.
      </div>
      <div className="mt-1 text-[12px] text-ink-500">A <span className="num font-medium text-ink-800">{(gap * 100).toFixed(1)} pt</span> gap. Computed by rerunning the rater on E0/T0, E1/T0 and E1/T1 for every account — traceable to each account's three model runs.</div>
      <div className="relative mt-6 h-12">
        <div className="absolute inset-x-0 top-5 h-2 rounded-full bg-gradient-to-r from-crit-bg via-ink-50 to-ok-bg" />
        <div className="absolute top-3 h-6 w-px bg-ink-400" style={{ left: x(0) }} />
        <div className="num absolute top-9 -translate-x-1/2 text-[10px] text-ink-400" style={{ left: x(0) }}>0%</div>
        {[{ v: b.rarc_computed, l: 'Computed', c: 'bg-crit' }, { v: b.rarc_reported, l: 'Reported', c: 'bg-ink-500' }].map((m) => (
          <div key={m.l} className="absolute top-0 -translate-x-1/2 text-center" style={{ left: x(m.v) }}>
            <div className="whitespace-nowrap text-[10px] font-medium text-ink-600">{m.l}</div>
            <div className={cx('mx-auto mt-0.5 size-3.5 rounded-full border-2 border-white shadow', m.c)} />
          </div>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
        {b.by_underwriter.map((u) => (
          <Link key={u.user_id} to={`/renewals?uw=${u.user_id}`} className="flex items-center justify-between rounded-md border border-line px-2 py-1.5 hover:bg-ink-50">
            <span className="truncate text-ink-700">{u.name}</span><span className={cx('num font-medium', u.avg_rarc < 0 ? 'text-crit' : 'text-ok')}>{pct(u.avg_rarc, 1, true)}</span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function AdequacyHist({ b, className }: { b: BookSummary; className?: string }) {
  const max = Math.max(...b.adequacy_hist.map((h) => h.count), 1);
  const below = b.adequacy_hist.filter((h) => h.bucket.startsWith('<') || h.bucket.startsWith('85') || h.bucket.startsWith('90'));
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Adequacy distribution<Info id="book.adequacy" /></span>} subtitle="Proposed ÷ technical premium TP(E1,T1) · floor 95%">
      <div className="flex h-[150px] items-end gap-1.5">
        {b.adequacy_hist.map((h) => {
          const bad = below.includes(h);
          return (
            <div key={h.bucket} className="group flex flex-1 flex-col items-center justify-end" title={`${h.count} accounts · ${usd(h.premium)} premium`}>
              <div className="num mb-1 text-[11px] font-medium text-ink-700">{h.count}</div>
              <div className={cx('w-full rounded-t-[3px]', bad ? 'bg-crit/80' : h.bucket.startsWith('95') ? 'bg-med' : 'bg-accent-600')} style={{ height: `${(h.count / max) * 110}px` }} />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex gap-1.5 border-t border-line pt-1">{b.adequacy_hist.map((h) => <div key={h.bucket} className="num flex-1 text-center text-[10px] text-ink-500">{h.bucket}</div>)}</div>
      <div className="mt-3 text-[12px] text-ink-600">
        <span className="num font-semibold text-crit">{below.reduce((a, h) => a + h.count, 0)}</span> accounts below floor, carrying <span className="num font-semibold text-ink-900">{usd(below.reduce((a, h) => a + h.premium, 0))}</span> expiring premium.
      </div>
    </Card>
  );
}

function ByMonth({ b, className }: { b: BookSummary; className?: string }) {
  const max = Math.max(...b.by_month.map((m) => m.renewals), 1);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Renewals by expiry month<Info id="book.months" /></span>} subtitle="Fast-track vs action required">
      <div className="flex h-[150px] items-end gap-3">
        {b.by_month.map((m) => (
          <div key={m.month} className="flex flex-1 flex-col items-center justify-end" title={`${m.renewals} renewals · ${usd(m.premium)}`}>
            <div className="num mb-1 text-[11px] font-medium text-ink-700">{m.renewals}</div>
            <div className="flex w-full flex-col overflow-hidden rounded-t-[3px]" style={{ height: `${(m.renewals / max) * 110}px` }}>
              <div className="bg-high" style={{ flex: m.action }} />
              <div className="bg-ok/70" style={{ flex: m.fast_track }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-3 border-t border-line pt-1">{b.by_month.map((m) => <div key={m.month} className="flex-1 text-center text-[10px] text-ink-500">{new Date(m.month + '-01T00:00:00').toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}</div>)}</div>
      <div className="mt-3 flex gap-4 text-[11px] text-ink-500">
        <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-high" />Action</span>
        <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-ok/70" />Fast-track</span>
      </div>
    </Card>
  );
}

function ByAction({ b, className }: { b: BookSummary; className?: string }) {
  const max = Math.max(...b.by_action.map((a) => a.count), 1);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Recommended actions<Info id="book.actions" /></span>} subtitle="Accounts can carry several">
      <div className="space-y-2">
        {b.by_action.map((a) => (
          <div key={a.action} className="grid grid-cols-[130px_1fr_40px] items-center gap-2 text-[12px]">
            <span className="text-ink-700">{ACTION_LABEL[a.action]}</span>
            <Bar value={a.count} max={max} tone={a.action === 'MAINTAIN' ? 'ok' : a.action === 'NON_RENEW' ? 'crit' : 'accent'} />
            <span className="num text-right font-medium text-ink-900">{a.count}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ByFamily({ b, className }: { b: BookSummary; className?: string }) {
  const max = Math.max(...b.by_family.map((f) => f.impact_usd), 1);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Exceptions by rule family<Info id="book.families" /></span>} subtitle="Open material findings · click to filter the queue" pad={false}>
      <table className="dt">
        <thead><tr><th>Family</th><th className="r">Findings</th><th className="r">$ at stake</th><th className="w-[30%]" /></tr></thead>
        <tbody>
          {b.by_family.slice(0, 10).map((f) => (
            <tr key={f.family} className="cursor-pointer">
              <td><Link to={`/renewals?family=${f.family}`} className="text-ink-900 hover:text-accent-700">{f.label}</Link></td>
              <td className="num r">{f.count}</td>
              <td className="num r font-medium">{usd(f.impact_usd)}</td>
              <td><Bar value={f.impact_usd} max={max} tone="high" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function ByUnderwriter({ b, className }: { b: BookSummary; className?: string }) {
  const total = b.by_underwriter.reduce((a, u) => a + u.pricing_deviations, 0) || 1;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Exceptions by underwriter<Info id="book.underwriters" /></span>} subtitle="Pricing deviation = RARC < −5% or adequacy < 95%" pad={false}>
      <table className="dt">
        <thead><tr><th>Underwriter</th><th className="r">Accts</th><th className="r">$ at stake</th><th className="r">Pricing dev.</th><th className="r">Avg RARC</th></tr></thead>
        <tbody>
          {b.by_underwriter.map((u) => {
            const share = u.pricing_deviations / total;
            const outlier = share >= 0.35;
            return (
              <tr key={u.user_id}>
                <td><Link to={`/renewals?uw=${u.user_id}`} className="text-ink-900 hover:text-accent-700">{u.name}</Link>{outlier && <Badge tone="crit" className="ml-1.5"><AlertTriangle className="size-3" />outlier</Badge>}</td>
                <td className="num r">{u.accounts}</td>
                <td className="num r">{usd(u.impact_usd)}</td>
                <td className={cx('num r', outlier && 'font-semibold text-crit')}>{u.pricing_deviations} <span className="text-ink-400">· {pct(share, 0)}</span></td>
                <td className={cx('num r', u.avg_rarc < 0 ? 'text-crit' : 'text-ok')}>{pct(u.avg_rarc, 1, true)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {b.by_underwriter.some((u) => u.pricing_deviations / total >= 0.35) && (
        <div className="border-t border-line px-4 py-2.5 text-[12px] text-ink-600">
          {(() => { const o = [...b.by_underwriter].sort((x, y) => y.pricing_deviations - x.pricing_deviations)[0]; return <><span className="font-semibold text-ink-900">{o.name}</span> holds <span className="num font-semibold text-crit">{pct(o.pricing_deviations / total, 0)}</span> of the book's pricing deviations on {pct(o.accounts / b.renewals, 0)} of accounts.</>; })()}
        </div>
      )}
    </Card>
  );
}

function ByBroker({ b, className }: { b: BookSummary; className?: string }) {
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">By broker<Info id="book.brokers" /></span>} subtitle="Premium, $ at stake and average RARC" pad={false}>
      <table className="dt">
        <thead><tr><th>Broker</th><th className="r">Accts</th><th className="r">Premium</th><th className="r">$ at stake</th><th className="r">Avg RARC</th></tr></thead>
        <tbody>
          {b.by_broker.map((x) => (
            <tr key={x.broker}>
              <td><Link to={`/renewals?broker=${encodeURIComponent(x.broker)}`} className="text-ink-900 hover:text-accent-700">{x.broker}</Link></td>
              <td className="num r">{x.accounts}</td>
              <td className="num r">{usd(x.premium)}</td>
              <td className="num r">{usd(x.impact_usd)}</td>
              <td className={cx('num r', x.avg_rarc < -0.02 ? 'text-crit' : x.avg_rarc < 0 ? 'text-high' : 'text-ok')}>{pct(x.avg_rarc, 1, true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Accumulation({ b, className }: { b: BookSummary; className?: string }) {
  const nav = useNavigate();
  const zones = [...b.accumulation].sort((x, y) => y.utilization - x.utilization);
  const hot = zones.filter((z) => z.utilization > 0.9);
  const points = useMemo<MapPoint[]>(() => zones.flatMap((z) => z.accounts.slice(0, 6).map((a, i) => ({ id: `${z.zone_id}:${a.account_id}`, lat: z.lat + Math.sin(i * 2.1) * 0.12, lon: z.lon + Math.cos(i * 2.1) * 0.16, label: a.name, sublabel: `${z.name} · ${usd(a.contribution)} PML`, value: a.contribution, severity: z.utilization > 0.9 ? 'HIGH' as const : null }))), [zones]);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Accumulation — post-renewal zone utilisation<Info id="book.accumulation" /></span>} subtitle="If every renewal binds as proposed" actions={<Link to="/portfolio" className="text-[12px] font-medium text-accent-700 hover:underline">Portfolio view →</Link>} pad={false}>
      <div className="grid grid-cols-12">
        <div className="col-span-12 lg:col-span-7"><GeoMap points={points} zones={b.accumulation} height={340} fitTo="us" onSelect={(id) => nav(`/accounts/${id.split(':')[1]}`)} /></div>
        <div className="col-span-12 border-l border-line p-4 lg:col-span-5">
          {hot.length > 0 && (
            <div className="mb-3 rounded-md border border-[#f6c5cc] bg-crit-bg px-3 py-2 text-[12px] text-crit">
              <AlertTriangle className="mr-1 inline size-3.5" />
              {hot.map((z) => <span key={z.zone_id}><span className="font-semibold">{z.name}</span> at <span className="num font-semibold">{pct(z.utilization, 0)}</span> after renewal — {z.accounts.slice(0, 3).map((a) => a.name).join(', ')} drive the increase. </span>)}
            </div>
          )}
          <SectionLabel>Zones</SectionLabel>
          <div className="space-y-2">
            {zones.slice(0, 8).map((z) => (
              <div key={z.zone_id} className="grid grid-cols-[1fr_120px_44px] items-center gap-2 text-[12px]">
                <span className="truncate text-ink-800">{z.name} <span className="text-ink-400">· {z.peril}</span></span>
                <Bar value={z.post_renewal} max={z.threshold * 1.05} marker={z.threshold * 0.9} tone={z.utilization > 0.9 ? 'crit' : z.utilization > 0.8 ? 'med' : 'accent'} />
                <span className={cx('num text-right font-medium', z.utilization > 0.9 ? 'text-crit' : 'text-ink-800')}>{pct(z.utilization, 0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
