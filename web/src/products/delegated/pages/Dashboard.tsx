// Monthly authority report across coverholders — the carrier's view of delegated business.
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Page, Card, Stat, Loading, ErrorBox, Badge, Select, cx } from '@/components/ui';
import { fmtDate, pct, usd, num } from '@/lib/format';
import { Info } from '@/help/Info';
import { CH_COLOR, MONTH, useOverview } from '../api';
import { ChLink, Grade, TrendChart, UtilBar } from '../parts';

export default function Dashboard() {
  const [month, setMonth] = useState<string | undefined>();
  const { data: o, isLoading, error } = useOverview(month);
  const nav = useNavigate();
  if (isLoading) return <Page title="Delegated authority"><Loading /></Page>;
  if (error || !o) return <Page title="Delegated authority"><ErrorBox error={error} /></Page>;
  const t = o.totals;
  const maxType = Math.max(1, ...o.types.map((x) => x.count));
  return (
    <Page title="Monthly authority report"
      subtitle={<>Northgate Specialty · {o.coverholders.length} coverholders · bordereau month <span className="num">{MONTH(o.month)}</span> · as of <span className="num">{fmtDate(o.as_of)}</span></>}
      actions={<><Info id="delegated.dashboard" label="About this page" />
        <Select value={o.month} onChange={(e) => setMonth(e.target.value)}>{o.months.map((m) => <option key={m} value={m}>{MONTH(m)}</option>)}</Select>
        <Link to="/delegated/breaches" className="inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white hover:bg-ink-800">Breach register <ArrowRight className="size-3.5" /></Link></>}>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label={<span className="inline-flex items-center gap-1.5">Policies checked<Info id="delegated.kpis" className="normal-case" /></span>} value={num(t.policies)} sub={`every bordereau line · ${MONTH(o.month)}`} />
        <Stat label="Within authority" value={pct(t.within_authority, 1)} tone={t.within_authority > 0.99 ? 'ok' : 'high'} sub={`${t.open_policies} policies still open`} />
        <Stat label="Policies with exceptions" value={t.with_exceptions} tone="crit" sub={`${pct(t.exception_rate, 1)} exception rate`} onClick={() => nav(`/delegated/breaches?month=${o.month}&status=all`)} />
        <Stat label="Premium tied to exceptions" value={usd(t.premium_tied)} tone="high" sub={`of ${usd(t.premium)} written`} />
        <Stat label="Commission discrepancy" value={`$${Math.round(t.commission).toLocaleString('en-US')}`} tone={t.commission ? 'crit' : 'ok'} sub="deducted above contract" onClick={() => nav('/delegated/breaches?family=commission&status=all')} />
        <Stat label="Missing referrals" value={t.missing_referrals} tone={t.missing_referrals ? 'crit' : 'ok'} sub="no valid approval located" onClick={() => nav('/delegated/breaches?family=referral&status=all')} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="$ at stake (open)" value={usd(o.at_stake)} sub={`${o.open_policies} policies · ${o.queries_open} queries awaiting reply`} />
        <Stat label="Aggregate warnings" value={o.aggregate_warnings} tone={o.aggregate_warnings ? 'crit' : 'ok'} sub="zones at or above warning level" onClick={() => nav('/delegated/aggregates')} />
        <Stat label="Unauthorised exposure prevented" value={usd(o.prevented.tiv)} tone="ok" sub={`${o.prevented.count} risks declined at referral · ${usd(o.corrected.exposure)} limit corrected`} />
        <Stat label="Correction turnaround" value={o.turnaround_days ? `${o.turnaround_days} days` : '—'} sub={`${o.corrected.count} exceptions resolved`} />
      </div>
      <div className="mt-4 grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-7" title={<span className="inline-flex items-center gap-1.5">Exception trend by month<Info id="delegated.trend" /></span>} subtitle="Share of bordereau lines with at least one authority exception, per coverholder">
          <TrendChart series={o.coverholders.map((c) => ({ key: c.id, label: c.short, points: c.trend }))} height={250} />
        </Card>
        <Card className="col-span-12 xl:col-span-5" title={<span className="inline-flex items-center gap-1.5">Authority exceptions by type<Info id="delegated.types" /></span>} subtitle={`${MONTH(o.month)} · click to filter the register`} pad={false}>
          <table className="dt">
            <thead><tr><th>Type</th><th className="r">Count</th><th className="w-[38%]" /></tr></thead>
            <tbody>{o.types.map((x) => (
              <tr key={x.family} className="cursor-pointer" onClick={() => nav(`/delegated/breaches?family=${x.family}&month=${o.month}&status=all`)}>
                <td className="text-[12.5px] text-ink-900">{x.label}</td><td className="num r font-semibold">{x.count}</td>
                <td><div className="flex h-2 overflow-hidden rounded-full bg-ink-100" style={{ width: `${(x.count / maxType) * 100}%` }}>{Object.entries(x.by_ch).map(([ch, n]) => <div key={ch} style={{ flex: n, background: CH_COLOR[ch] }} title={`${ch}: ${n}`} />)}</div></td>
              </tr>))}
              {o.types.length === 0 && <tr><td colSpan={3} className="text-center text-ink-400">No exceptions this month</td></tr>}
            </tbody>
          </table>
        </Card>
        <Card className="col-span-12" pad={false} title={<span className="inline-flex items-center gap-1.5">Coverholders<Info id="delegated.coverholders" /></span>} subtitle="Scorecard, latest month, open exceptions and capacity">
          <div className="overflow-x-auto">
            <table className="dt min-w-[1100px]">
              <thead><tr><th>Coverholder</th><th>Grade</th><th>Trend</th><th className="r">Latest month</th><th className="r">Within authority</th><th className="r">Open</th><th className="r">$ at stake</th><th>Top zone</th><th className="r">DQ</th><th className="r">Days late</th><th className="r">RARC</th></tr></thead>
              <tbody>{o.coverholders.map((c) => (
                <tr key={c.id} className="cursor-pointer" onClick={() => nav(`/delegated/coverholders/${c.id}`)}>
                  <td className="max-w-[280px]"><div className="flex items-center gap-1.5"><Badge tone="dark">{c.scenario}</Badge><ChLink id={c.id}>{c.name}</ChLink></div><div className="truncate text-[11px] text-ink-500">{c.title}</div></td>
                  <td><Grade g={c.grade} score={c.score} size="sm" /></td>
                  <td className="num whitespace-nowrap text-[12px]"><span className={cx(c.direction === 'deteriorating' ? 'text-crit' : c.direction === 'improving' ? 'text-ok' : 'text-ink-600')}>{c.trend.map((p) => pct(p.rate, 1)).join(' → ')}</span></td>
                  <td className="num r">{c.latest ? `${c.latest.with_exceptions}/${c.latest.policies}` : '—'}</td>
                  <td className="num r">{pct(c.within_authority, 1)}</td>
                  <td className="num r font-semibold">{c.open_exceptions || '—'}</td>
                  <td className="num r">{c.at_stake ? usd(c.at_stake) : '—'}</td>
                  <td className="w-[180px]">{c.top_zone && <div><div className="flex justify-between text-[11px]"><span className="truncate text-ink-600">{c.top_zone.name}</span><span className={cx('num font-medium', c.top_zone.util >= c.top_zone.warn ? 'text-crit' : 'text-ink-700')}>{pct(c.top_zone.util, 1)}</span></div><UtilBar util={c.top_zone.util} warn={c.top_zone.warn} /></div>}</td>
                  <td className={cx('num r', (c.dq_score ?? 100) < 85 ? 'text-high' : '')}>{c.dq_score?.toFixed(0) ?? '—'}</td>
                  <td className={cx('num r', c.avg_days_late > 0 ? 'text-crit' : 'text-ink-500')}>{c.avg_days_late || '—'}</td>
                  <td className={cx('num r', (c.rarc?.rarc ?? 0) < 0 ? 'text-crit' : 'text-ok')}>{c.rarc?.rarc != null ? pct(c.rarc.rarc, 1, true) : '—'}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Card>
        <Card className="col-span-12 xl:col-span-6" pad={false} title={<span className="inline-flex items-center gap-1.5">Aggregates vs thresholds<Info id="delegated.aggregates.card" /></span>} subtitle="In-force TIV by zone vs the limit in each BAA" actions={<Link to="/delegated/aggregates" className="text-[12px] font-medium text-accent-700 hover:underline">All zones →</Link>}>
          <table className="dt">
            <thead><tr><th>Zone</th><th>Coverholder</th><th className="r">In-force TIV</th><th className="w-[30%]">Utilisation</th><th>Status</th></tr></thead>
            <tbody>{o.zones.slice(0, 7).map((z) => (
              <tr key={z.ch + z.zone}>
                <td><div className="text-[12.5px] font-medium text-ink-900">{z.name}</div><div className="text-[11px] text-ink-500">{z.peril}</div></td>
                <td className="text-[12px]">{z.ch_name}</td><td className="num r">{usd(z.tiv)}</td>
                <td><div className="flex items-center gap-2"><UtilBar util={z.util} warn={z.warn} /><span className={cx('num w-12 text-right text-[12px] font-semibold', z.util >= z.warn ? 'text-crit' : 'text-ink-700')}>{pct(z.util, 1)}</span></div></td>
                <td><Badge tone={z.status === 'Open' ? (z.util >= z.warn ? 'crit' : 'neutral') : 'high'}>{z.util >= z.warn && z.status === 'Open' ? 'Above warning' : z.status}</Badge></td>
              </tr>))}</tbody>
          </table>
        </Card>
        <Card className="col-span-12 xl:col-span-6" pad={false} title={<span className="inline-flex items-center gap-1.5">Recent control activity<Info id="delegated.activity" /></span>} subtitle="Bordereaux, queries, responses, amendments">
          <div className="max-h-[330px] divide-y divide-line overflow-y-auto">
            {o.recent.map((e) => (
              <div key={e.event_id} className="flex items-start gap-3 px-4 py-2">
                <span className="num w-[80px] shrink-0 text-[12px] text-ink-500">{fmtDate(e.date)}</span>
                <span className="min-w-0 flex-1"><span className="block text-[12.5px] text-ink-900"><span className="font-medium">{e.ch_name}</span> · {e.title}</span><span className="block truncate text-[11.5px] text-ink-500">{e.detail}</span></span>
              </div>))}
          </div>
        </Card>
        {o.ledger.length > 0 && (
          <Card className="col-span-12" pad={false} title="Commission reconciliation — finance ledger (mock)">
            <table className="dt"><thead><tr><th>Entry</th><th>Date</th><th>Coverholder</th><th>Type</th><th className="r">Amount</th><th>Status</th></tr></thead>
              <tbody>{o.ledger.map((l) => <tr key={l.entry_id}><td className="mono text-[12px]">{l.entry_id}</td><td className="num">{fmtDate(l.date)}</td><td>{l.ch}</td><td>{l.type}</td><td className="num r">${l.amount.toLocaleString('en-US', { maximumFractionDigits: 2 })}</td><td><Badge tone={l.status === 'SETTLED' ? 'ok' : 'high'}>{l.status}</Badge></td></tr>)}</tbody></table>
          </Card>
        )}
      </div>
    </Page>
  );
}
