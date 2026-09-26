// Decision Assurance dashboard: what was prepared, what assurance found, what it corrected, and what the outcomes say.
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Page, Card, Stat, Loading, ErrorBox, Badge, cx } from '@/components/ui';
import { usd, pct, fmtDate } from '@/lib/format';
import { Bar } from '@/pages/common';
import { Info } from '@/help/Info';
import { useDashboard, VERDICT_LABEL, type Dashboard, type Verdict } from './api';

export default function DashboardPage() {
  const { data: d, isLoading, error } = useDashboard();
  if (isLoading) return <Page title="Decision assurance"><Loading /></Page>;
  if (error || !d) return <Page title="Decision assurance"><ErrorBox error={error} /></Page>;
  return (
    <Page title="Decision assurance" subtitle={<>Northgate new business · as of <span className="num">{fmtDate(d.as_of)}</span> · <span className="num">{d.prepared}</span> submissions prepared · <span className="num">{d.expected}</span> in the mailbox schedule</>}
      actions={<><Info id="decision.dashboard" label="About this page" /><Link to="/decision/cases" className="inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white hover:bg-ink-800">Open case queue <ArrowRight className="size-3.5" /></Link></>}>
      <Kpis d={d} />
      <div className="mt-4 grid grid-cols-12 gap-4">
        <Exposure d={d} className="col-span-12 xl:col-span-7" />
        <Mix d={d} className="col-span-12 xl:col-span-5" />
        <Funnel d={d} className="col-span-12 xl:col-span-7" />
        <Tiers d={d} className="col-span-12 xl:col-span-5" />
        <Issues d={d} className="col-span-12 xl:col-span-6" />
        <Feedback d={d} className="col-span-12 xl:col-span-6" />
        <ByUw d={d} className="col-span-12 xl:col-span-6" />
        <ByBroker d={d} className="col-span-12 xl:col-span-6" />
        <Portfolio d={d} className="col-span-12" />
      </div>
    </Page>
  );
}

function Kpis({ d }: { d: Dashboard }) {
  const nav = useNavigate();
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
      <Stat label={<span className="inline-flex items-center gap-1.5">Cases prepared<Info id="decision.kpis" className="normal-case" /></span>} value={d.prepared} sub={`${pct(d.auto_prepared / Math.max(1, d.prepared), 0)} auto-prepared`} onClick={() => nav('/decision/cases')} />
      <Stat label="Pass" value={d.verdicts.PASS} tone="ok" sub="latest verdict" />
      <Stat label="Pass with flags" value={d.verdicts.PASS_WITH_FLAGS} sub="conditions or flags" />
      <Stat label="Refer / hold" value={d.verdicts.REFER_HOLD} tone="crit" sub={`${d.first_verdicts.REFER_HOLD} on first action`} onClick={() => nav('/decision/referrals')} />
      <Stat label="Exposure corrected / prevented" value={usd(d.exposure.total)} tone="accent" sub={`${d.exposure.cases} cases · before commitment`} />
      <Stat label="Errors intercepted" value={d.errors_intercepted} tone="high" sub={`${d.commitments_changed} commitments changed`} />
      <Stat label="Prep hours saved" value={d.hours_saved.toFixed(0)} sub={`of ${d.hours_manual.toFixed(0)} h manual estimate`} />
      <Stat label="Median time to decision" value={d.median_days_to_decision === null ? '—' : `${d.median_days_to_decision} d`} sub={`${d.decided} decided`} />
    </div>
  );
}

function Exposure({ d, className }: { d: Dashboard; className?: string }) {
  const nav = useNavigate();
  const max = Math.max(1, ...d.exposure.by_case.map((x) => x.total));
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Material exposure corrected or prevented before commitment<Info id="decision.exposure" /></span>}
      subtitle="Premium-equivalent $: contradictions resolved on verified evidence · actions corrected or declined after assurance">
      <div className="mb-3 grid grid-cols-3 gap-2">
        {[['At preparation', d.exposure.preparation, 'Adverse contradictions resolved'], ['At assurance', d.exposure.assurance, 'Premium shortfall, terms, line, declines'], ['Loss avoided (outcome)', d.exposure.loss_avoided, 'Losses excluded by corrected terms']].map(([l, v, s]) => (
          <div key={String(l)} className="rounded-md border border-line px-3 py-2"><div className="text-[10.5px] uppercase tracking-wide text-ink-500">{l}</div><div className="num text-[17px] font-semibold text-ink-950">{usd(Number(v))}</div><div className="text-[11px] text-ink-500">{s}</div></div>
        ))}
      </div>
      <div className="space-y-1.5">
        {d.exposure.by_case.map((x) => (
          <button key={x.case_id} onClick={() => nav(`/decision/cases/${x.case_id}`)} className="grid w-full grid-cols-[210px_1fr_90px] items-center gap-3 rounded px-1 py-0.5 text-left text-[12px] hover:bg-ink-50">
            <span className="truncate text-ink-800">{x.scenario && <Badge tone="dark" className="mr-1">{x.scenario}</Badge>}{x.insured} <span className="text-ink-400">· {x.kind ?? 'preparation'}</span></span>
            <Bar value={x.total} max={max} tone="accent" />
            <span className="num text-right font-medium text-ink-900">{usd(x.total)}</span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function Mix({ d, className }: { d: Dashboard; className?: string }) {
  const tot = Math.max(1, d.verdicts.PASS + d.verdicts.PASS_WITH_FLAGS + d.verdicts.REFER_HOLD);
  const first = Math.max(1, d.first_verdicts.PASS + d.first_verdicts.PASS_WITH_FLAGS + d.first_verdicts.REFER_HOLD);
  const row = (label: string, v: Record<Verdict, number>, n: number) => (
    <div>
      <div className="mb-1 text-[12px] text-ink-600">{label}</div>
      <div className="flex h-6 overflow-hidden rounded-md">
        {(['PASS', 'PASS_WITH_FLAGS', 'REFER_HOLD'] as Verdict[]).map((k) => v[k] > 0 && (
          <div key={k} className={cx('flex items-center justify-center text-[11px] font-semibold text-white', k === 'PASS' ? 'bg-ok' : k === 'PASS_WITH_FLAGS' ? 'bg-med' : 'bg-crit')} style={{ width: `${(v[k] / n) * 100}%` }} title={`${VERDICT_LABEL[k]}: ${v[k]}`}>{v[k]}</div>
        ))}
      </div>
    </div>
  );
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Verdict mix<Info id="decision.mix" /></span>} subtitle="First intended action vs latest (after correction)">
      <div className="space-y-4">
        {row('First intended action', d.first_verdicts, first)}
        {row('Latest action', d.verdicts, tot)}
        <div className="flex gap-4 text-[11px] text-ink-500">{(['PASS', 'PASS_WITH_FLAGS', 'REFER_HOLD'] as Verdict[]).map((k) => <span key={k} className="flex items-center gap-1.5"><span className={cx('size-2 rounded-sm', k === 'PASS' ? 'bg-ok' : k === 'PASS_WITH_FLAGS' ? 'bg-med' : 'bg-crit')} />{VERDICT_LABEL[k]}</span>)}</div>
        <div className="grid grid-cols-3 gap-2 border-t border-line pt-3 text-[12px]">
          <div><div className="text-ink-500">Quoted</div><div className="num text-[15px] font-semibold">{d.quoted}</div></div>
          <div><div className="text-ink-500">Bound</div><div className="num text-[15px] font-semibold">{d.bound}</div></div>
          <div><div className="text-ink-500">Bound premium</div><div className="num text-[15px] font-semibold">{usd(d.bound_premium)}</div></div>
        </div>
      </div>
    </Card>
  );
}

function Funnel({ d, className }: { d: Dashboard; className?: string }) {
  const max = Math.max(1, d.funnel[0]?.count ?? 1);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Funnel through the ten stages<Info id="decision.funnel" /></span>} subtitle="Cases that reached each stage">
      <div className="space-y-1.5">
        {d.funnel.map((f) => (
          <Link key={f.code} to={`/decision/pipeline/${f.code}`} className="grid grid-cols-[200px_1fr_40px] items-center gap-3 text-[12px] hover:opacity-80">
            <span className="text-ink-700"><span className="mono mr-1.5 text-ink-400">{f.code}</span>{f.name}</span>
            <Bar value={f.count} max={max} tone={Number(f.code) >= 7 ? 'ink' : 'accent'} />
            <span className="num text-right font-medium">{f.count}</span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function Tiers({ d, className }: { d: Dashboard; className?: string }) {
  const t = d.tiers;
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Results by control tier<Info id="decision.tiers" /></span>} subtitle="Materiality-based control model, first assurance run per case">
      <div className="space-y-3 text-[12.5px]">
        {[['Tier 1 — deterministic', 'Authority, referral, deductible & limit thresholds, pricing deviation, prohibited classes, required documents', t.tier1.checks, t.tier1.fired, 'REAL'],
          ['Tier 2 — assurance model', 'Conflicting evidence, unusual risk, large limit, manuscript wording, override and rationale critique', t.tier2.checks, t.tier2.fired, 'STAND-IN']].map(([h, s, n, f, m]) => (
          <div key={String(h)} className="rounded-md border border-line p-3">
            <div className="flex items-center justify-between"><span className="font-semibold text-ink-900">{h}</span><Badge tone={m === 'REAL' ? 'ok' : 'mock'}>{m}</Badge></div>
            <div className="text-[11.5px] text-ink-500">{s}</div>
            <div className="mt-1.5 flex items-center gap-3"><Bar value={Number(f)} max={Math.max(1, Number(n))} tone="high" /><span className="num whitespace-nowrap text-ink-800">{f} fired / {n} checks</span></div>
          </div>
        ))}
        <div className="rounded-md border border-line p-3">
          <div className="font-semibold text-ink-900">Tier 3 — human judgement</div>
          <div className="text-[11.5px] text-ink-500">Material overrides, unresolved ambiguity, complex coverage, high severity, every final commitment</div>
          <div className="num mt-1 text-ink-800">{t.tier3.human_decisions} human decisions · {t.tier3.referrals} referrals</div>
        </div>
      </div>
    </Card>
  );
}

function Issues({ d, className }: { d: Dashboard; className?: string }) {
  const max = Math.max(1, ...d.top_issues.map((x) => x.cases));
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">Top issues surfaced<Info id="decision.issues" /></span>} subtitle="Rules that fired, by cases affected">
      <table className="dt">
        <thead><tr><th>Rule</th><th>Tier</th><th className="r">Cases</th><th className="r">$ at stake</th><th className="w-[22%]" /></tr></thead>
        <tbody>{d.top_issues.map((x) => (
          <tr key={x.rule_id}>
            <td><Link to={`/decision/rules/${x.rule_id}`} className="text-ink-900 hover:text-accent-700"><div className="mono text-[11.5px] font-semibold">{x.rule_id}</div><div className="text-[11.5px] text-ink-500">{x.title}</div></Link></td>
            <td>T{x.tier}</td><td className="num r">{x.cases}</td><td className="num r">{usd(x.impact_usd)}</td><td><Bar value={x.cases} max={max} tone="high" /></td>
          </tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

function Feedback({ d, className }: { d: Dashboard; className?: string }) {
  const f = d.feedback;
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">Override rate & outcome feedback<Info id="decision.feedback" /></span>} subtitle="Flags on committed cases, scored against losses six months after bind">
      <div className="grid grid-cols-4 gap-2 p-3">
        <div><div className="text-[10.5px] uppercase text-ink-500">Override rate</div><div className="num text-[16px] font-semibold">{pct(f.override_rate, 0)}</div><div className="text-[11px] text-ink-500">{f.overrides} of {f.flags} flags</div></div>
        <div><div className="text-[10.5px] uppercase text-ink-500">Outcome-confirmed</div><div className="num text-[16px] font-semibold">{f.confirmed}<span className="text-ink-400"> / {f.scored}</span></div><div className="text-[11px] text-ink-500">flags scored</div></div>
        <div><div className="text-[10.5px] uppercase text-ink-500">Loss ratio flagged</div><div className="num text-[16px] font-semibold text-crit">{pct(f.loss_ratio_flagged, 0)}</div><div className="text-[11px] text-ink-500">bound with flags</div></div>
        <div><div className="text-[10.5px] uppercase text-ink-500">Loss ratio clean</div><div className="num text-[16px] font-semibold text-ok">{pct(f.loss_ratio_clean, 0)}</div><div className="text-[11px] text-ink-500">{f.with_outcome} outcomes · {f.losses} losses</div></div>
      </div>
      <table className="dt">
        <thead><tr><th>Rule</th><th className="r">Fired</th><th className="r">Acted on</th><th className="r">Overridden, no loss</th><th className="r">Confirmed</th><th className="r">Precision</th></tr></thead>
        <tbody>{f.rules.filter((r) => r.fired).sort((a, b) => b.fired - a.fired).slice(0, 8).map((r) => (
          <tr key={r.rule_id}><td><Link to={`/decision/rules/${r.rule_id}`} className="mono text-[11.5px] text-ink-900 hover:text-accent-700">{r.rule_id}</Link></td><td className="num r">{r.fired}</td><td className="num r">{r.accepted}</td><td className="num r">{r.rejected}</td><td className="num r">{r.confirmed}</td>
            <td className={cx('num r font-semibold', r.precision !== null && r.precision < 0.6 && 'text-crit')}>{pct(r.precision, 0)}</td></tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

function ByUw({ d, className }: { d: Dashboard; className?: string }) {
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">By underwriter<Info id="decision.by_uw" /></span>} subtitle="First verdict on each underwriter's intended actions">
      <table className="dt">
        <thead><tr><th>Underwriter</th><th className="r">Cases</th><th className="r">Pass</th><th className="r">Flags</th><th className="r">Refer</th><th className="r">Overrides</th><th className="r">Avg dev.</th><th className="r">Bound</th></tr></thead>
        <tbody>{d.by_underwriter.map((u) => (
          <tr key={u.user_id}><td>{u.name} <span className="text-ink-400">L{u.level}</span></td><td className="num r">{u.cases}</td><td className="num r text-ok">{u.pass}</td><td className="num r">{u.flags}</td><td className="num r text-crit">{u.refer}</td><td className="num r">{u.overrides}</td>
            <td className={cx('num r', (u.avg_dev ?? 0) < -0.05 ? 'text-crit' : 'text-ink-800')}>{pct(u.avg_dev, 1, true)}</td><td className="num r">{u.bound}</td></tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

function ByBroker({ d, className }: { d: Dashboard; className?: string }) {
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">By broker and segment<Info id="decision.by_broker" /></span>} subtitle="Submission quality and hit ratio">
      <table className="dt">
        <thead><tr><th>Broker</th><th className="r">Cases</th><th className="r">Contradictions</th><th className="r">Missing</th><th className="r">Referred</th><th className="r">Hit ratio</th><th className="r">Bound premium</th></tr></thead>
        <tbody>{d.by_broker.map((b) => (
          <tr key={b.broker}><td className="whitespace-nowrap">{b.broker}</td><td className="num r">{b.cases}</td><td className="num r">{b.contradictions}</td><td className="num r">{b.missing}</td><td className="num r">{b.refer}</td><td className="num r">{pct(b.quoted ? b.bound / b.quoted : null, 0)}</td><td className="num r">{usd(b.premium)}</td></tr>
        ))}</tbody>
        <tbody>{d.by_segment.map((g) => (
          <tr key={g.segment} className="bg-ink-50/50"><td className="font-medium">{g.segment}</td><td className="num r">{g.cases}</td><td className="num r" colSpan={2}>{usd(g.tiv)} TIV</td><td className="num r">{g.refer}</td><td className="num r">{g.bound} bound</td><td className="num r">{usd(g.premium)}</td></tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

function Portfolio({ d, className }: { d: Dashboard; className?: string }) {
  const maxP = Math.max(1, ...d.portfolio.mix.map((m) => m.premium));
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Portfolio fit<Info id="decision.portfolio" /></span>} subtitle="Zone utilisation of 1-in-250 capacity: in-force book plus bound new business · bound mix by class">
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 space-y-2 lg:col-span-7">
          {d.portfolio.zones.map((z) => (
            <div key={z.zone_id} className="grid grid-cols-[190px_1fr_60px] items-center gap-3 text-[12px]">
              <span className="truncate text-ink-800">{z.name} <span className="text-ink-400">· {z.peril}</span></span>
              <Bar value={z.in_force + z.nb_bound} max={z.threshold * 1.05} marker={z.threshold * 0.9} tone={z.util > 0.9 ? 'crit' : z.util > 0.8 ? 'med' : 'accent'} />
              <span className={cx('num text-right font-medium', z.util > 0.9 && 'text-crit')}>{pct(z.util, 0)}</span>
            </div>
          ))}
          <div className="text-[11px] text-ink-500">Marker = 90% referral threshold (Guidelines §11.4). New business adds {usd(d.portfolio.zones.reduce((a, z) => a + z.nb_bound, 0))} PML.</div>
        </div>
        <div className="col-span-12 space-y-2 lg:col-span-5">
          {d.portfolio.mix.map((m) => (
            <div key={m.class} className="grid grid-cols-[170px_1fr_70px] items-center gap-3 text-[12px]"><span className="truncate">{m.class} <span className="text-ink-400">· {m.bound}</span></span><Bar value={m.premium} max={maxP} /><span className="num text-right">{usd(m.premium)}</span></div>
          ))}
        </div>
      </div>
    </Card>
  );
}
