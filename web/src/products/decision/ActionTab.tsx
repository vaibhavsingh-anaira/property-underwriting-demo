// Stage 2 — the underwriter's intended action, checked independently in real time; then the recorded assurance result.
import { useEffect, useMemo, useState } from 'react';
import { Send, ShieldCheck, User } from 'lucide-react';
import { Card, Badge, Button, Input, Select, Empty, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { usd, pct, fmtDate } from '@/lib/format';
import { SectionLabel } from '@/pages/common';
import { Info } from '@/help/Info';
import { usePreview, useRoute, useSubmitAction, type Action, type ActionInput, type Assurance, type CaseDetail, type Pack } from './api';
import { Cite, ResultBadge, VerdictBadge } from './parts';

export default function ActionTab({ c }: { c: CaseDetail }) {
  const route = useRoute(c.case_id);
  const done = ['BOUND', 'DECLINED', 'LOST'].includes(c.status);
  const pendingRef = c.referrals.some((r) => r.status === 'PENDING');
  return (
    <div className="grid grid-cols-12 gap-4">
      {!done && c.pack && <ActionForm c={c} className="col-span-12" />}
      {c.assurance ? (
        <>
          <div className="col-span-12 flex items-center justify-between">
            <div className="text-[13px] font-semibold text-ink-900">Recorded assurance — intended action v{c.assurance.action_version} ({c.assurance.action_type.toLowerCase()}), run {fmtDate(c.assurance.run_at)}</div>
            {c.assurance.verdict === 'REFER_HOLD' && !pendingRef && !done && <Button size="sm" variant="primary" loading={route.isPending} onClick={() => route.mutate({})}>Route: refer to L{Math.max(2, c.assurance.required_level)}</Button>}
          </div>
          {route.data && <div className="col-span-12 rounded-md bg-info-bg px-3 py-1.5 text-[12.5px] text-info">{route.data.message}</div>}
          {route.error && <div className="col-span-12 rounded-md bg-crit-bg px-3 py-1.5 text-[12.5px] text-crit">{(route.error as Error).message}</div>}
          <AssuranceView a={c.assurance} className="col-span-12" />
        </>
      ) : <Card className="col-span-12"><Empty>No intended action recorded yet.</Empty></Card>}
      <History c={c} className="col-span-12" />
    </div>
  );
}

export function defaults(pack: Pack, last?: Action | null): ActionInput {
  const s = pack.suggested;
  return last ? { type: last.type, premium: last.premium, aop: last.aop, limit: last.limit, line: last.line, ns_pct: last.ns_pct ?? null, ns_min: last.ns_min ?? null, wh_pct: last.wh_pct ?? null, manuscript: last.manuscript ?? null, rationale: last.rationale }
    : { type: 'QUOTE', premium: Math.round(pack.pricing.technical / 1000) * 1000, aop: s.aop, limit: s.limit, line: 1, ns_pct: s.ns_pct ?? null, ns_min: s.ns_min ?? null, wh_pct: s.wh_pct ?? null, manuscript: null, rationale: '' };
}

/** Intended action form with a live assurance preview (debounced). `preview` is injected so the sandbox can reuse it. */
export function ActionFields({ pack, init, onPreview, preview, footer }: { pack: Pack; init: ActionInput; onPreview: (a: ActionInput) => void; preview: Assurance | null | undefined; footer: (a: ActionInput) => React.ReactNode }) {
  const [a, setA] = useState<ActionInput>(init);
  const set = (k: keyof ActionInput, v: unknown) => setA((x) => ({ ...x, [k]: v }));
  const key = JSON.stringify(a);
  useEffect(() => { const t = setTimeout(() => onPreview({ ...a, limit: undefined }), 350); return () => clearTimeout(t); }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const num = (k: keyof ActionInput, label: string, step = 1000, scale = 1) => (
    <label className="text-[11.5px] text-ink-500">{label}
      <Input type="number" step={step} value={a[k] === null || a[k] === undefined ? '' : Number(a[k]) * scale} onChange={(e) => set(k, e.target.value === '' ? null : Number(e.target.value) / scale)} className="mt-0.5 w-full" />
    </label>
  );
  const dev = a.premium && preview ? a.premium / preview.technical - 1 : null;
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 space-y-3 lg:col-span-7">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <label className="text-[11.5px] text-ink-500">Action
            <Select value={a.type} onChange={(e) => set('type', e.target.value)} className="mt-0.5 w-full"><option value="QUOTE">Quote</option><option value="BIND">Bind</option></Select>
          </label>
          {num('premium', 'Premium ($)')}
          {num('aop', 'AOP deductible ($)', 5000)}
          {num('line', 'Line (%)', 5, 100)}
          {num('ns_pct', 'Named storm (%)', 0.5, 100)}
          {num('ns_min', 'Named storm minimum ($)', 10000)}
          {num('wh_pct', 'Wind/hail (%)', 0.5, 100)}
          <label className="text-[11.5px] text-ink-500">Manuscript wording
            <Select value={a.manuscript ?? ''} onChange={(e) => set('manuscript', e.target.value || null)} className="mt-0.5 w-full"><option value="">None</option><option value="full">Broker manuscript as drafted</option><option value="limited">Limited (sprinkler leakage only)</option></Select>
          </label>
        </div>
        <label className="block text-[11.5px] text-ink-500">Rationale / override reason
          <textarea value={a.rationale ?? ''} onChange={(e) => set('rationale', e.target.value)} rows={2} placeholder="Why this price and these terms" className="mt-0.5 w-full resize-none rounded-md border border-line-strong px-2.5 py-1.5 text-[13px] outline-none focus:border-accent-500" />
        </label>
        <div className="text-[12px] text-ink-500">Technical {usd(pack.pricing.technical, { compact: false })} · suggested {usd(pack.pricing.band_low)}–{usd(pack.pricing.band_high)}{dev !== null && <> · this premium is <span className={cx('num font-semibold', Math.abs(dev) > (preview?.permitted_dev ?? 1) ? 'text-crit' : 'text-ink-900')}>{pct(dev, 1, true)}</span> vs technical at these terms</>}</div>
        {footer({ ...a, limit: undefined })}
      </div>
      <div className="col-span-12 lg:col-span-5">
        <SectionLabel right={<Badge tone="accent">live</Badge>}>Assurance on this action (not recorded)</SectionLabel>
        {preview ? (
          <div className="rounded-lg border border-line p-3">
            <div className="mb-2 flex items-center justify-between"><VerdictBadge v={preview.verdict} large /><span className="text-[11.5px] text-ink-500">owner {preview.owner.name} (L{preview.owner.level})</span></div>
            <div className="grid grid-cols-5 gap-1">{preview.dimensions.map((d) => <div key={d.key} className="text-center"><div className="text-[10px] uppercase text-ink-500">{d.label}</div><ResultBadge r={d.result} /></div>)}</div>
            <ul className="mt-2 space-y-0.5">{preview.checks.filter((x) => x.result === 'FAIL' || x.result === 'FLAG' || x.result === 'CONDITION').slice(0, 6).map((x) => <li key={x.check_id} className="flex gap-1.5 text-[11.5px]"><ResultBadge r={x.result} /><span className="truncate text-ink-700" title={x.observed}>{x.title}</span></li>)}</ul>
          </div>
        ) : <div className="rounded-lg border border-dashed border-line p-4 text-[12px] text-ink-500">Checking…</div>}
      </div>
    </div>
  );
}

function ActionForm({ c, className }: { c: CaseDetail; className?: string }) {
  const prev = usePreview(c.case_id);
  const sub = useSubmitAction(c.case_id);
  const init = useMemo(() => defaults(c.pack!, c.actions.at(-1)), [c.pack, c.actions]);
  return (
    <Card className={className} title={<span className="inline-flex items-center gap-1.5">Intended action<Info id="decision.action" /></span>}
      subtitle={<>Quote or bind with premium, deductible, limit, line and wording · assurance re-runs as you type · recorded as the persona selected in the header</>}>
      <ActionFields key={c.actions.length} pack={c.pack!} init={init} preview={prev.data?.assurance} onPreview={(a) => prev.mutate(a)}
        footer={(a) => (
          <div className="flex items-center gap-2">
            <Button variant="primary" icon={<Send className="size-3.5" />} loading={sub.isPending} onClick={() => sub.mutate(a)}>Submit intended action</Button>
            {sub.error && <span className="text-[12px] text-crit">{(sub.error as Error).message}</span>}
            {prev.error && <span className="text-[12px] text-crit">{(prev.error as Error).message}</span>}
          </div>
        )} />
    </Card>
  );
}

export function AssuranceView({ a, className }: { a: Assurance; className?: string }) {
  const ev = useEvidence();
  const [tier, setTier] = useState<0 | 1 | 2>(0);
  const checks = a.checks.filter((x) => !tier || x.tier === tier);
  const border = a.verdict === 'PASS' ? 'border-[#bfe3cd]' : a.verdict === 'PASS_WITH_FLAGS' ? 'border-[#efdf9f]' : 'border-[#f6c5cc]';
  return (
    <div className={cx('space-y-4', className)}>
      <Card className={border} title={<span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-4" />Assurance result<Info id="decision.assurance" /></span>} subtitle={a.summary}>
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-3">
            <VerdictBadge v={a.verdict} large />
            <div className="mt-3 space-y-1 text-[12.5px]">
              <div className="flex justify-between"><span className="text-ink-500">Premium</span><span className="num">{usd(a.premium, { compact: false })}</span></div>
              <div className="flex justify-between"><span className="text-ink-500">Technical</span><span className="num">{usd(a.technical, { compact: false })}</span></div>
              <div className="flex justify-between"><span className="text-ink-500">Deviation</span><span className={cx('num font-semibold', Math.abs(a.deviation) > a.permitted_dev ? 'text-crit' : 'text-ink-900')}>{pct(a.deviation, 1, true)}</span></div>
              <div className="flex justify-between"><span className="text-ink-500">Permitted at L{a.uw_level}</span><span className="num">±{pct(a.permitted_dev, 0)}</span></div>
              <div className="flex justify-between"><span className="text-ink-500">Exposure flagged</span><span className="num">{usd(a.exposure_usd)}</span></div>
            </div>
            <div className="mt-3 rounded-md border border-line bg-ink-50 p-2 text-[12px]">
              <div className="flex items-center gap-1.5 font-semibold text-ink-900"><User className="size-3.5" />Decision owner</div>
              <div>{a.owner.name} · L{a.owner.level}</div><div className="text-ink-500">{a.owner.why}</div>
            </div>
          </div>
          <div className="col-span-12 lg:col-span-9">
            <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
              {a.dimensions.map((d) => (
                <div key={d.key} className={cx('rounded-md border p-2', d.result === 'FAIL' ? 'border-[#f6c5cc] bg-crit-bg/40' : d.result === 'FLAG' ? 'border-[#efdf9f] bg-med-bg/40' : 'border-[#bfe3cd] bg-ok-bg/40')}>
                  <div className="flex items-center justify-between"><span className="text-[12px] font-semibold text-ink-900">{d.label}</span><ResultBadge r={d.result} /></div>
                  <div className="mt-1 text-[11.5px] leading-snug text-ink-600">{d.summary}</div>
                  <div className="mt-1 text-[10.5px] text-ink-400">{d.checks} checks</div>
                </div>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-12 gap-3">
              <div className="col-span-12 md:col-span-7">
                <SectionLabel>Remaining conditions</SectionLabel>
                {a.conditions.length === 0 ? <div className="text-[12.5px] text-ink-500">None</div> : a.conditions.map((k, i) => (
                  <div key={i} className="flex items-start justify-between gap-2 py-0.5 text-[12.5px]"><span className="text-ink-800">{k.text}<span className="block text-[11px] text-ink-500">{k.due} · {k.source}</span></span><Badge tone={k.status === 'OPEN' ? 'med' : k.status === 'CLEARED' ? 'ok' : 'neutral'}>{k.status === 'TERM' ? 'term' : k.status.toLowerCase()}</Badge></div>
                ))}
              </div>
              <div className="col-span-12 md:col-span-5">
                <SectionLabel>Tier 3 — human judgement</SectionLabel>
                <ul className="list-disc pl-4 text-[12px] text-ink-700">{a.tier3.map((x) => <li key={x}>{x}</li>)}</ul>
              </div>
            </div>
          </div>
        </div>
      </Card>
      <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Checks<Info id="decision.checks" /></span>} subtitle={`${a.counts.tier1} tier-1 (deterministic) and ${a.counts.tier2} tier-2 (assurance-model stand-in) checks`}
        actions={<div className="flex gap-1">{([0, 1, 2] as const).map((t) => <button key={t} onClick={() => setTier(t)} className={cx('rounded px-2 py-0.5 text-[12px]', tier === t ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-100')}>{t ? `Tier ${t}` : 'All'}</button>)}</div>}>
        <table className="dt">
          <thead><tr><th>Result</th><th>Tier</th><th>Dimension</th><th>Check</th><th>Observed</th><th>Expected / note</th><th className="r">Impact</th></tr></thead>
          <tbody>{checks.map((x) => (
            <tr key={x.check_id} className={cx(x.result === 'PASS' && 'opacity-70')}>
              <td><ResultBadge r={x.result} />{x.level > 0 && x.result !== 'PASS' && <span className="ml-1 text-[10.5px] text-ink-500">L{x.level}</span>}</td>
              <td>T{x.tier}{x.tier === 2 && <Badge tone="mock" className="ml-1">model</Badge>}</td>
              <td className="text-[12px] capitalize">{x.dimension}</td>
              <td className="max-w-[240px]"><div className="text-[12.5px] font-medium text-ink-900">{x.title}</div><div className="text-[11px] text-ink-500">{x.subject} · <span className="mono">{x.rule_id}</span></div><Cite c={x.citation} /></td>
              <td className="max-w-[300px] text-[12px] text-ink-700">{x.observed}{x.evidence_obs_ids.length > 0 && <button onClick={() => ev.openObs(x.evidence_obs_ids[0])} className="ml-1 text-[11px] font-medium text-accent-700 hover:underline">evidence</button>}</td>
              <td className="max-w-[280px] text-[11.5px] text-ink-600">{x.note ?? x.expected}</td>
              <td className="num r">{x.impact_usd ? usd(x.impact_usd) : ''}</td>
            </tr>
          ))}</tbody>
        </table>
      </Card>
    </div>
  );
}

function History({ c, className }: { c: CaseDetail; className?: string }) {
  if (!c.actions.length) return null;
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">Intended actions and assurance runs<Info id="decision.history" /></span>}>
      <table className="dt">
        <thead><tr><th>Ver</th><th>Action</th><th className="r">Premium</th><th className="r">AOP</th><th className="r">Line</th><th>Wording</th><th>By</th><th>Date</th><th>Verdict</th><th>Rationale</th></tr></thead>
        <tbody>{c.actions.map((x) => {
          const r = [...c.assurances].reverse().find((y) => y.action_version === x.version);
          return (
            <tr key={x.action_id}><td>v{x.version}</td><td><Badge>{x.type}</Badge></td><td className="num r">{usd(x.premium, { compact: false })}</td><td className="num r">{usd(x.aop)}</td><td className="num r">{pct(x.line, 0)}</td>
              <td className="text-[12px]">{x.manuscript ?? '—'}</td><td className="text-[12px]">{x.by_name}</td><td className="num text-[12px]">{fmtDate(x.at)}</td><td><VerdictBadge v={r?.verdict} /></td><td className="max-w-[320px] truncate text-[12px] text-ink-600" title={x.rationale}>{x.rationale}</td></tr>
          );
        })}</tbody>
      </table>
    </Card>
  );
}
