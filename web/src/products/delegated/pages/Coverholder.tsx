// One coverholder: authority (source-linked), scorecard, trend, bordereaux, breaches, aggregates, claims, queries, RARC.
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Send, Receipt, ClipboardCheck, FileText, FilePen, ShieldAlert } from 'lucide-react';
import { Page, Card, Loading, ErrorBox, Badge, Button, Tabs, Empty, cx } from '@/components/ui';
import { fmtDate, pct, usd } from '@/lib/format';
import { Info } from '@/help/Info';
import { useEvidence } from '@/components/evidence';
import { useCoverholder, useDaAction, MONTH, type ChDetail } from '../api';
import { Grade, Mini, Src, StatusPill, TrendChart, UtilBar, money } from '../parts';
import { PolicyDrawer } from '../PolicyDrawer';

type Tab = 'overview' | 'authority' | 'bordereaux' | 'breaches' | 'aggregates' | 'claims' | 'queries' | 'rarc';

export default function Coverholder() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get('tab') as Tab) || 'overview';
  const { data: c, isLoading, error } = useCoverholder(id);
  const act = useDaAction();
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  if (isLoading) return <Page title="Coverholder"><Loading /></Page>;
  if (error || !c) return <Page title="Coverholder"><ErrorBox error={error} /></Page>;
  const run = (path: string, body?: unknown) => act.mutate({ path: `coverholders/${c.id}/${path}`, body }, { onSuccess: (r) => setMsg({ ok: true, t: r.message }), onError: (e) => setMsg({ ok: false, t: (e as Error).message }) });
  const openQ = c.register.filter((r) => r.checks.some((x) => x.status === 'OPEN') && r.subject_type === 'policy').length;
  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'overview', label: 'Overview' }, { key: 'authority', label: 'Authority' }, { key: 'bordereaux', label: 'Bordereaux', count: c.bordereaux.length },
    { key: 'breaches', label: 'Breach register', count: c.register.filter((r) => r.open).length }, { key: 'aggregates', label: 'Aggregates' },
    { key: 'claims', label: 'Claims', count: c.claims.length }, { key: 'queries', label: 'Queries & actions', count: c.queries.length }, { key: 'rarc', label: 'RARC' },
  ];
  return (
    <Page title={<span className="flex items-center gap-2"><Badge tone="dark">{c.scenario}</Badge>{c.name}</span>}
      crumbs={<Link to="/delegated/coverholders" className="hover:underline">Coverholders</Link>}
      subtitle={<>{c.program} · {c.agreement} · UMR <span className="mono">{c.umr}</span> · PIN {c.pin} · {c.contact} · placed by {c.broker}</>}
      actions={<><Info id="delegated.coverholder.page" label="About this page" /><Grade g={c.grade} score={c.score} /></>}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button size="sm" variant="primary" icon={<Send className="size-3.5" />} disabled={!openQ} loading={act.isPending} onClick={() => run('query', {})}>Query open exceptions{openQ ? ` (${openQ})` : ''}</Button>
        <Button size="sm" icon={<Receipt className="size-3.5" />} disabled={!c.commission_open} onClick={() => run('commission')}>Commission reconciliation</Button>
        <Button size="sm" icon={<ClipboardCheck className="size-3.5" />} onClick={() => run('audit')}>Request audit</Button>
        <Button size="sm" icon={<FileText className="size-3.5" />} onClick={() => run('report', {})}>Issue authority report</Button>
        {(c.id === 'ch_northfield' || c.id === 'ch_meridian') && <Button size="sm" icon={<FilePen className="size-3.5" />} onClick={() => run('amend')}>{c.id === 'ch_northfield' ? 'Amend: capacity increase' : 'Amend: tighten authority'}</Button>}
        <Info id="delegated.actions" />
        {msg && <span className={cx('text-[12px]', msg.ok ? 'text-ok' : 'text-crit')}>{msg.t}</span>}
      </div>
      <Tabs value={tab} onChange={(k) => { const n = new URLSearchParams(sp); n.set('tab', k); setSp(n, { replace: true }); }} tabs={tabs} />
      <div className="mt-4">
        {tab === 'overview' && <Overview c={c} onOpen={setOpen} />}
        {tab === 'authority' && <Authority c={c} />}
        {tab === 'bordereaux' && <Bdx c={c} />}
        {tab === 'breaches' && <Register c={c} onOpen={setOpen} />}
        {tab === 'aggregates' && <Aggs c={c} run={run} />}
        {tab === 'claims' && <Claims c={c} onOpen={setOpen} />}
        {tab === 'queries' && <Queries c={c} />}
        {tab === 'rarc' && <RarcTab c={c} />}
      </div>
      <PolicyDrawer k={open} onClose={() => setOpen(null)} />
    </Page>
  );
}

function Overview({ c, onOpen }: { c: ChDetail; onOpen: (k: string) => void }) {
  const r = c.reports[c.reports.length - 1];
  const sc = c.scorecard;
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 grid grid-cols-2 gap-2 md:grid-cols-6">
        <Mini label="Within authority" value={pct(sc.within_authority, 1)} tone={sc.within_authority > 0.995 ? 'ok' : 'high'} />
        <Mini label="Latest month" value={r ? `${r.with_exceptions}/${r.policies} · ${pct(r.exception_rate, 1)}` : '—'} tone={r?.with_exceptions ? 'crit' : 'ok'} />
        <Mini label="Premium tied" value={usd(r?.premium_tied ?? 0)} />
        <Mini label="Commission discrepancy" value={`$${(r?.commission_discrepancy ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`} tone={r?.commission_discrepancy ? 'crit' : undefined} />
        <Mini label="Missing referrals" value={r?.missing_referrals ?? 0} tone={r?.missing_referrals ? 'crit' : 'ok'} />
        <Mini label="Correction turnaround" value={sc.turnaround_days ? `${sc.turnaround_days} d` : '—'} />
      </div>
      <Card className="col-span-12 xl:col-span-7" title={<span className="inline-flex items-center gap-1.5">Exception trend<Info id="delegated.trend" /></span>} subtitle={`Direction: ${sc.direction}`}>
        <TrendChart series={[{ key: c.id, label: c.short, points: sc.trend }]} height={210} />
      </Card>
      <Card className="col-span-12 xl:col-span-5" title={<span className="inline-flex items-center gap-1.5">Scorecard<Info id="delegated.scorecard" /></span>} subtitle="0–100 per component; weights 35 / 20 / 15 / 15 / 15">
        <div className="space-y-2">
          {Object.entries(sc.components).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[110px_1fr_40px] items-center gap-2 text-[12.5px]">
              <span className="capitalize text-ink-700">{k.replace('_', ' ')}</span>
              <div className="h-2 rounded-full bg-ink-100"><div className={cx('h-2 rounded-full', v >= 85 ? 'bg-ok' : v >= 65 ? 'bg-med' : 'bg-crit')} style={{ width: `${v}%` }} /></div>
              <span className="num text-right font-medium">{Math.round(v)}</span>
            </div>))}
          <div className="border-t border-line pt-2 text-[12px] text-ink-600">DQ {sc.dq_score?.toFixed(0) ?? '—'} · on time {pct(sc.on_time, 0)} · avg {sc.avg_days_late} days late · incurred ÷ written {sc.loss_ratio != null ? pct(sc.loss_ratio, 1) : '—'} · GWP {usd(sc.gwp)}</div>
        </div>
      </Card>
      {r && (
        <Card className="col-span-12 xl:col-span-6" pad={false} title={<span className="inline-flex items-center gap-1.5">Authority report · {MONTH(r.month)}<Info id="delegated.report" /></span>}>
          <table className="dt"><thead><tr><th>Exceptions by type</th><th className="r">Count</th><th className="r">Open</th><th className="r">Premium tied</th></tr></thead>
            <tbody>{r.types.map((t) => <tr key={t.family}><td>{t.label}</td><td className="num r">{t.count}</td><td className="num r">{t.open}</td><td className="num r">{usd(t.premium_tied)}</td></tr>)}
              {r.types.length === 0 && <tr><td colSpan={4} className="text-center text-ink-400">No exceptions</td></tr>}</tbody></table>
          <div className="border-t border-line px-4 py-2"><div className="text-[11px] font-semibold uppercase text-ink-500">Recommended</div><ul className="list-disc pl-4 text-[12.5px] text-ink-800">{(r.recommendations.length ? r.recommendations : ['No action required']).map((x) => <li key={x}>{x}</li>)}</ul></div>
        </Card>
      )}
      <Card className="col-span-12 xl:col-span-6" pad={false} title="Open items" subtitle="Click for the side-by-side result">
        <div className="max-h-[340px] divide-y divide-line overflow-y-auto">
          {c.register.filter((x) => x.open).map((x) => (
            <button key={x.key} onClick={() => onOpen(x.key)} className="flex w-full items-start gap-2 px-4 py-2 text-left hover:bg-ink-50">
              <StatusPill s={x.status} />
              <span className="min-w-0 flex-1"><span className="block truncate text-[12.5px] font-medium text-ink-900">{x.insured} <span className="mono text-[11px] text-ink-500">{x.certificate_ref}</span></span>
                <span className="block truncate text-[11.5px] text-ink-500">{x.checks.filter((k) => k.status !== 'AUTHORISED').map((k) => k.check).join(' · ')}</span></span>
              <span className="num text-[12px] font-semibold">{x.impact_usd ? usd(x.impact_usd) : ''}</span>
            </button>))}
          {!c.register.some((x) => x.open) && <Empty>Nothing open.</Empty>}
        </div>
      </Card>
      <Card className="col-span-12" pad={false} title="Activity" subtitle="Audit trail for this coverholder">
        <div className="max-h-[300px] divide-y divide-line overflow-y-auto">
          {c.timeline.map((e) => <div key={e.event_id} className="flex gap-3 px-4 py-1.5 text-[12.5px]"><span className="num w-[84px] shrink-0 text-ink-500">{fmtDate(e.date)}</span><span className="min-w-0 flex-1"><span className="text-ink-900">{e.title}</span> <span className="text-ink-500">— {e.detail}</span></span><span className="text-[11.5px] text-ink-400">{e.actor}</span>{e.doc_id && <Src docId={e.doc_id} label="doc" />}</div>)}
        </div>
      </Card>
    </div>
  );
}

function Authority({ c }: { c: ChDetail }) {
  const a = c.authority;
  const T = ({ title, info, children }: { title: string; info?: string; children: React.ReactNode }) => <Card pad={false} title={<span className="inline-flex items-center gap-1.5">{title}{info && <Info id={info} />}</span>}>{children}</Card>;
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 xl:col-span-5 space-y-4">
        <T title={`Authority in force · v${a.version}`} info="delegated.authority">
          <table className="dt"><tbody>{a.kv.map((k) => <tr key={k.key}><td className="text-[12px] text-ink-500">{k.label}</td><td className="num text-[12.5px] font-medium">{k.value}</td><td className="r"><Src anchor={k.anchor} kind="clause" /></td></tr>)}</tbody></table>
        </T>
        <T title="Versions (agreement + endorsements)" info="delegated.versions">
          <div className="divide-y divide-line">{a.versions.map((v) => (
            <div key={v.version} className="px-4 py-2">
              <div className="flex items-center justify-between"><span className="text-[12.5px] font-medium text-ink-900">v{v.version} · {v.title}</span><span className="flex items-center gap-2"><Badge tone={v.in_force ? 'ok' : 'neutral'}>{v.in_force ? 'in force' : 'scheduled'}</Badge><Src docId={v.doc_id} kind="clause" label="PDF" /></span></div>
              <div className="text-[11.5px] text-ink-500">Effective {fmtDate(v.effective)} · issued {fmtDate(v.issued)} · {v.terms} terms read</div>
              {v.changes.map((ch) => <div key={ch.label} className="text-[12px] text-ink-700">{ch.label}: <span className="text-ink-500 line-through">{ch.from}</span> → <span className="font-medium">{ch.to}</span></div>)}
            </div>))}</div>
        </T>
        <T title="Exclusions — prohibited risks"><table className="dt"><tbody>{a.prohibited.map((p) => <tr key={p.code}><td className="mono text-[12px]">{p.code}</td><td>{p.label}</td><td className="r"><Src anchor={p.anchor} kind="clause" /></td></tr>)}</tbody></table></T>
      </div>
      <div className="col-span-12 xl:col-span-7 space-y-4">
        <T title="Schedule of classes and rating" info="delegated.rating">
          <table className="dt"><thead><tr><th>Code</th><th>Class</th><th className="r">Base rate / $100</th><th>Status</th><th /></tr></thead>
            <tbody>{a.classes.map((k) => <tr key={k.code}><td className="mono text-[12px]">{k.code}</td><td>{k.label}</td><td className="num r">{k.rate.toFixed(3)}</td><td><Badge tone={k.status === 'Referral' ? 'high' : 'ok'}>{k.status}</Badge></td><td className="r"><Src anchor={k.anchor} kind="clause" /></td></tr>)}</tbody></table>
          <div className="grid grid-cols-3 gap-4 border-t border-line p-3 text-[12px]">
            <div><div className="mb-1 font-semibold text-ink-600">Construction factor</div>{a.construction.map((x) => <div key={x.iso} className="flex justify-between"><span>ISO {x.iso}</span><span className="num">{x.factor.toFixed(2)}</span></div>)}</div>
            <div><div className="mb-1 font-semibold text-ink-600">Deductible factor</div>{a.ded_factors.map((x) => <div key={x.deductible} className="flex justify-between"><span>{usd(x.deductible)}</span><span className="num">{x.factor.toFixed(2)}</span></div>)}</div>
            <div><div className="mb-1 font-semibold text-ink-600">Minimum AOP deductible</div>{a.min_aop.map((x) => <div key={x.from} className="flex items-center justify-between gap-1"><span>{usd(x.from)}{x.to ? `–${usd(x.to)}` : '+'}</span><span className="num font-medium">{usd(x.min)}</span><Src anchor={x.anchor} kind="clause" label="p" /></div>)}</div>
          </div>
        </T>
        <T title="Territories">
          <table className="dt"><thead><tr><th>State</th><th>County</th><th>Tier</th><th className="r">Factor</th><th>Status</th><th /></tr></thead>
            <tbody>{a.territories.map((t) => <tr key={t.key}><td>{t.state}</td><td>{t.county}</td><td>{t.tier}</td><td className="num r">{t.factor?.toFixed(2) ?? '—'}</td><td><Badge tone={t.status === 'Excluded' ? 'crit' : 'ok'}>{t.status}</Badge></td><td className="r"><Src anchor={t.anchor} kind="clause" /></td></tr>)}</tbody></table>
        </T>
      </div>
    </div>
  );
}

function Bdx({ c }: { c: ChDetail }) {
  const ev = useEvidence();
  return (
    <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Bordereaux received<Info id="delegated.bordereaux" /></span>} actions={<Link to={`/delegated/bordereaux?ch=${c.id}`} className="text-[12px] font-medium text-accent-700 hover:underline">Mapping & validation →</Link>}>
      <table className="dt"><thead><tr><th>Period</th><th>Type</th><th>File</th><th>Received</th><th className="r">Days late</th><th className="r">Rows</th><th className="r">Mapping</th><th className="r">DQ</th><th className="r">Issues</th><th /></tr></thead>
        <tbody>{c.bordereaux.map((b) => (
          <tr key={b.doc_id} className={cx(b.superseded_by && 'opacity-50')}>
            <td>{MONTH(b.month)}</td><td><Badge tone={b.correction ? 'accent' : 'neutral'}>{b.correction ? (b.replaces ? 'resubmission' : 'correction') : b.kind}</Badge></td>
            <td className="max-w-[300px] truncate text-[12.5px]">{b.title}{b.superseded_by && <span className="ml-1 text-[11px] text-ink-400">(superseded)</span>}</td>
            <td className="num">{fmtDate(b.received)}</td><td className={cx('num r', b.days_late ? 'font-semibold text-crit' : 'text-ink-400')}>{b.days_late || '—'}</td>
            <td className="num r">{b.rows}</td><td className="num r">{pct(b.mapping_confidence, 0)}</td><td className={cx('num r', b.dq_score < 85 ? 'text-high' : '')}>{b.dq_score.toFixed(0)}</td><td className="num r">{b.issues}</td>
            <td className="r"><button onClick={() => ev.openDoc(b.doc_id)} className="text-[12px] font-medium text-accent-700 hover:underline">Open</button></td>
          </tr>))}</tbody></table>
    </Card>
  );
}

function Register({ c, onOpen }: { c: ChDetail; onOpen: (k: string) => void }) {
  return (
    <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Breach register<Info id="delegated.breaches" /></span>} subtitle="Every policy with an exception, including resolved and ratified">
      <table className="dt"><thead><tr><th>Month</th><th>Policy / subject</th><th>Exceptions</th><th>Status</th><th className="r">Premium tied</th><th className="r">$ at stake</th></tr></thead>
        <tbody>{c.register.map((r) => (
          <tr key={r.key} className="cursor-pointer" onClick={() => onOpen(r.key)}>
            <td className="whitespace-nowrap">{MONTH(r.month)}</td>
            <td><div className="text-[12.5px] font-medium text-ink-900">{r.insured}</div><div className="mono text-[11px] text-ink-500">{r.certificate_ref} · {r.txn ?? r.subject_type}</div></td>
            <td className="max-w-[420px] text-[12px] text-ink-700">{r.checks.filter((k) => k.status !== 'AUTHORISED').map((k) => `${k.check}: ${k.written} vs ${k.authority}`).join(' · ')}</td>
            <td><StatusPill s={r.status} /></td><td className="num r">{usd(r.premium_tied)}</td><td className="num r font-semibold">{r.impact_usd ? usd(r.impact_usd) : '—'}</td>
          </tr>))}</tbody></table>
    </Card>
  );
}

function Aggs({ c, run }: { c: ChDetail; run: (p: string, b?: unknown) => void }) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12 xl:col-span-8" pad={false} title={<span className="inline-flex items-center gap-1.5">Zone aggregates vs the BAA<Info id="delegated.aggregates" /></span>} subtitle="Exposure return (30 Apr) + every bordereau movement · zones from the CAT feed (mock)">
        <table className="dt"><thead><tr><th>Zone</th><th>Peril</th><th className="r">Opening</th><th className="r">Movement</th><th className="r">In-force TIV</th><th className="r">Limit</th><th className="w-[22%]">Utilisation</th><th>Status</th><th /></tr></thead>
          <tbody>{c.aggregates.map((z) => (
            <tr key={z.zone}>
              <td><span className="font-medium">{z.name}</span> <span className="mono text-[11px] text-ink-400">{z.zone}</span></td><td className="text-[12px]">{z.peril}</td>
              <td className="num r">{usd(z.opening)}</td><td className="num r">{usd(z.movement, { sign: true })}</td><td className="num r font-medium">{usd(z.tiv)}</td><td className="num r">{usd(z.limit)} <Src anchor={z.anchor} kind="clause" label="p" /></td>
              <td><div className="flex items-center gap-2"><UtilBar util={z.util} warn={z.warn} /><span className={cx('num w-12 text-right text-[12px] font-semibold', z.util >= z.warn ? 'text-crit' : '')}>{pct(z.util, 1)}</span></div></td>
              <td><Badge tone={z.status !== 'Open' ? 'high' : z.util >= z.warn ? 'crit' : 'neutral'}>{z.status !== 'Open' ? z.status : z.util >= z.warn ? 'Above warning' : 'Open'}</Badge></td>
              <td className="r">{z.status === 'Open' && z.util >= z.warn - 0.05 && <Button size="sm" icon={<ShieldAlert className="size-3.5" />} onClick={() => run('restrict', { zone: z.zone, mode: 'Refer' })}>Refer new business</Button>}</td>
            </tr>))}</tbody></table>
      </Card>
      <Card className="col-span-12 xl:col-span-4" title="Utilisation by month end" subtitle="Top zones">
        <table className="dt"><thead><tr><th>Month</th>{c.aggregates.slice(0, 3).map((z) => <th key={z.zone} className="r">{z.zone}</th>)}</tr></thead>
          <tbody>{c.zone_history.map((h) => <tr key={h.month}><td>{MONTH(h.month)}</td>{c.aggregates.slice(0, 3).map((z) => <td key={z.zone} className={cx('num r', (h.zones[z.zone] ?? 0) >= z.warn ? 'font-semibold text-crit' : '')}>{pct(h.zones[z.zone], 1)}</td>)}</tr>)}</tbody></table>
        <div className="mt-3 text-[12px] text-ink-600">GPI: {usd(c.capacity.ytd)} YTD · projected {usd(c.capacity.projected)} vs {usd(c.capacity.limit)} ({pct(c.capacity.util, 0)})</div>
        {c.restrictions.map((r) => <div key={r.doc_id} className="mt-2 rounded-md bg-high-bg px-2 py-1.5 text-[12px] text-high">{r.name}: {r.mode.toLowerCase()} from {fmtDate(r.effective)} (at {pct(r.util_at_issue, 1)}) <Src docId={r.doc_id} kind="clause" label="endorsement" /></div>)}
        {c.prevented.length > 0 && <div className="mt-2 text-[12px] text-ok">{c.prevented.length} risks declined at the referral desk — {money(c.prevented.reduce((a, p) => a + p.tiv, 0))} TIV never bound</div>}
      </Card>
    </div>
  );
}

function Claims({ c, onOpen }: { c: ChDetail; onOpen: (k: string) => void }) {
  return (
    <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Claims bordereau — latest snapshot<Info id="delegated.claims" /></span>} subtitle={`Incurred ${usd(c.claims.reduce((a, x) => a + x.incurred, 0))} · incurred ÷ written ${c.scorecard.loss_ratio != null ? pct(c.scorecard.loss_ratio, 1) : '—'}`}>
      <table className="dt"><thead><tr><th>Claim</th><th>Insured</th><th>Loss</th><th>Cause</th><th className="r">Paid</th><th className="r">Reserve</th><th className="r">Incurred</th><th className="r">Movement</th><th className="r">Days to carrier</th><th>Exceptions</th><th /></tr></thead>
        <tbody>{c.claims.map((x) => (
          <tr key={x.claim_ref} className={cx(x.exceptions.length && 'cursor-pointer')} onClick={() => x.exceptions.length && onOpen(`${c.id}|${x.certificate_ref}`)}>
            <td className="mono text-[12px]">{x.claim_ref}</td><td className="text-[12.5px]">{x.insured_name}<div className="mono text-[11px] text-ink-500">{x.certificate_ref}</div></td>
            <td className="num">{fmtDate(x.date_of_loss)}</td><td className="text-[12px]">{x.cause}</td><td className="num r">{usd(x.paid)}</td><td className="num r">{usd(x.reserve)}</td><td className="num r font-semibold">{usd(x.incurred)}</td>
            <td className={cx('num r', x.incurred_change > 0 ? 'text-crit' : '')}>{x.incurred_change ? usd(x.incurred_change, { sign: true }) : '—'}</td><td className="num r">{x.days_to_carrier ?? '—'}</td>
            <td className="max-w-[240px] text-[11.5px] text-crit">{x.exceptions.map((e) => e.title).join(' · ')}</td><td className="r"><Src anchor={x.anchor} /></td>
          </tr>))}</tbody></table>
    </Card>
  );
}

function Queries({ c }: { c: ChDetail }) {
  const ev = useEvidence();
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12 xl:col-span-7" pad={false} title={<span className="inline-flex items-center gap-1.5">Queries and coverholder responses<Info id="delegated.queries" /></span>}>
        <div className="divide-y divide-line">{c.queries.map((q) => (
          <div key={q.query_id} className="px-4 py-2.5">
            <div className="flex items-center justify-between"><span className="text-[13px] font-medium text-ink-900"><span className="mono">{q.query_id}</span> · {q.kind.replace('_', ' ')} · {q.items.length} item(s)</span><Badge tone={q.status === 'SENT' ? 'high' : 'ok'}>{q.status}</Badge></div>
            <div className="text-[11.5px] text-ink-500">Sent {fmtDate(q.created)} by {q.by} · due {fmtDate(q.due)}{q.responded ? ` · replied ${fmtDate(q.responded)}` : ''}</div>
            {q.summary && <div className="mt-1 text-[12px] text-ink-700">{Object.entries(q.summary).filter(([, v]) => v).map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(' · ')}</div>}
            <div className="mt-1 flex gap-2"><button onClick={() => ev.openDoc(q.doc_id)} className="text-[12px] font-medium text-accent-700 hover:underline">Query email</button>{q.response && <button onClick={() => ev.openDoc(q.response!)} className="text-[12px] font-medium text-accent-700 hover:underline">Response email</button>}</div>
          </div>))}
          {c.queries.length === 0 && <Empty>No queries yet.</Empty>}</div>
      </Card>
      <div className="col-span-12 space-y-4 xl:col-span-5">
        <Card pad={false} title="Finance ledger (mock)">
          <table className="dt"><tbody>{c.ledger.map((l) => <tr key={l.entry_id}><td className="mono text-[12px]">{l.entry_id}</td><td>{fmtDate(l.date)}</td><td className="num r">${l.amount.toLocaleString('en-US', { maximumFractionDigits: 2 })}</td><td><Badge tone={l.status === 'SETTLED' ? 'ok' : 'high'}>{l.status}</Badge></td><td><Src docId={l.doc_id} kind="clause" label="PDF" /></td></tr>)}
            {c.ledger.length === 0 && <tr><td className="text-center text-ink-400">No debit notes</td></tr>}</tbody></table>
        </Card>
        <Card pad={false} title="Audits, reports and amendments">
          <div className="divide-y divide-line text-[12.5px]">
            {c.audits.map((a) => <div key={a.audit_id} className="flex items-center justify-between px-4 py-2"><span>{a.audit_id} · visit {fmtDate(a.visit)} · {a.findings ? a.findings.rating : a.status.toLowerCase()}</span>{a.doc_id && <Src docId={a.doc_id} kind="clause" label="report" />}</div>)}
            {c.issued_reports.map((r) => <div key={r.report_id} className="flex items-center justify-between px-4 py-2"><span>{r.report_id} · authority report {MONTH(r.month)}</span><Src docId={r.doc_id} kind="clause" label="PDF" /></div>)}
            {c.amendments.map((a) => <div key={a.doc_id} className="flex items-center justify-between px-4 py-2"><span>Endorsement No. {a.number} · {a.note || a.kind} · effective {fmtDate(a.effective)}</span><Src docId={a.doc_id} kind="clause" label="PDF" /></div>)}
            {!c.audits.length && !c.issued_reports.length && !c.amendments.length && <Empty>None yet.</Empty>}
          </div>
        </Card>
        <Card pad={false} title="Referral system (mock) — latest requests">
          <div className="max-h-[260px] overflow-y-auto"><table className="dt"><tbody>{c.referrals.slice(0, 40).map((r) => <tr key={r.ref}><td className="mono text-[11.5px]">{r.ref}</td><td className="text-[12px]">{r.insured}</td><td>{fmtDate(r.decided)}</td><td><Badge tone={r.status === 'APPROVED' ? 'ok' : 'crit'}>{r.status}</Badge></td></tr>)}</tbody></table></div>
        </Card>
      </div>
    </div>
  );
}

function RarcTab({ c }: { c: ChDetail }) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12" pad={false} title={<span className="inline-flex items-center gap-1.5">Quarterly RARC from bordereaux<Info id="delegated.rarc" /></span>} subtitle="Renewal lines only · weighted by expiring premium">
        <table className="dt"><thead><tr><th>Quarter</th><th className="r">Renewals used</th><th className="r">Expiring premium</th><th className="r">Renewal premium</th><th className="r">Expected (like-for-like)</th><th className="r">Headline</th><th className="r">TIV change</th><th className="r">RARC</th><th className="r">Rate / $100 TIV</th><th className="r">Rate on line</th></tr></thead>
          <tbody>{c.rarc_detail.quarters.map((q) => (
            <tr key={q.quarter}><td>{q.label}</td><td className="num r">{q.used} of {q.renewals}{q.excluded ? ` (${q.excluded} excluded)` : ''}</td><td className="num r">{usd(q.expiring_premium)}</td><td className="num r">{usd(q.renewal_premium)}</td><td className="num r">{usd(q.expected_premium)}</td>
              <td className="num r">{pct(q.headline, 1, true)}</td><td className="num r">{pct(q.exposure_change, 1, true)}</td><td className={cx('num r font-semibold', (q.rarc ?? 0) < 0 ? 'text-crit' : 'text-ok')}>{pct(q.rarc, 1, true)}</td>
              <td className="num r">{q.rate_on_tiv_prior?.toFixed(3)} → {q.rate_on_tiv?.toFixed(3)}</td><td className="num r">{pct(q.rate_on_line, 2)}</td></tr>))}</tbody></table>
        <div className="border-t border-line px-4 py-3 text-[12.5px] leading-relaxed text-ink-700"><span className="font-semibold">Method.</span> {c.rarc_detail.method}</div>
      </Card>
      <Card className="col-span-12" pad={false} title="By month">
        <table className="dt"><thead><tr><th>Month</th><th className="r">Renewals</th><th className="r">Headline</th><th className="r">RARC</th></tr></thead>
          <tbody>{c.rarc_detail.quarters.flatMap((q) => q.by_month).map((m) => <tr key={m.month}><td>{MONTH(m.month)}</td><td className="num r">{m.renewals}</td><td className="num r">{pct(m.headline, 1, true)}</td><td className={cx('num r', (m.rarc ?? 0) < 0 ? 'text-crit' : 'text-ok')}>{pct(m.rarc, 1, true)}</td></tr>)}</tbody></table>
      </Card>
    </div>
  );
}
