import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, Save, Send, GitPullRequestArrow, RotateCcw, ShieldCheck, ShieldAlert } from 'lucide-react';
import type { AccountDetail, RarcResult, RarcTerms, QuoteVersion } from '@/api/types';
import { useContract, useCreateQuote, useCreateReferral, useRarc, useRarcWhatIf, useSendQuote, useUsers, getCurrentUserId } from '@/api/client';
import { Card, Button, Badge, Loading, ErrorBox, MockBadge, cx } from '@/components/ui';
import { usd, usdFull, pct, fmtDate } from '@/lib/format';
import { SectionLabel } from '../common';
import { Info } from '@/help/Info';

const k1 = (n: number) => `$${(n / 1000).toFixed(1)}K`;
const f3 = (n: number) => n.toFixed(3);

export default function PricingTab({ a }: { a: AccountDetail }) {
  const { data: base, isLoading, error } = useRarc(a.account_id);
  if (isLoading) return <Loading label="Rerunning technical model…" />;
  if (error || !base) return <Card><ErrorBox error={error ?? 'No pricing'} /></Card>;
  return <Workbench a={a} base={base} />;
}

function Workbench({ a, base }: { a: AccountDetail; base: RarcResult }) {
  const [premium, setPremium] = useState(base.proposed_premium);
  const [terms, setTerms] = useState<RarcTerms>(base.proposed_terms);
  const [brokerage, setBrokerage] = useState(base.net.brokerage_proposed);
  const whatIf = useRarcWhatIf(a.account_id);
  const dirty = premium !== base.proposed_premium || JSON.stringify(terms) !== JSON.stringify(base.proposed_terms) || brokerage !== base.net.brokerage_proposed;
  const t = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    if (!dirty) { whatIf.reset(); return; }
    clearTimeout(t.current);
    t.current = setTimeout(() => whatIf.mutate({ proposed_premium: premium, terms, brokerage }), 220);
    return () => clearTimeout(t.current);
  }, [premium, JSON.stringify(terms), brokerage]); // eslint-disable-line react-hooks/exhaustive-deps
  const r = dirty && whatIf.data ? whatIf.data : base;
  const reset = () => { setPremium(base.proposed_premium); setTerms(base.proposed_terms); setBrokerage(base.net.brokerage_proposed); };

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 space-y-4 xl:col-span-8">
        <Readout r={r} base={base} dirty={dirty} />
        <ModelRuns r={r} />
        <FactorChain r={r} />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card title={<span className="inline-flex items-center gap-1.5">Model drift<Info id="account.drift" /></span>} subtitle="Same exposure & terms, today's model vs as-priced">
            <div className="flex items-baseline gap-3"><span className="num text-[20px] font-semibold text-ink-950">{pct(r.model_drift.drift, 1, true)}</span><span className="text-[12px] text-ink-500">TP at bind <span className="num">{usdFull(r.model_drift.tp_at_bind)}</span> → today <span className="num">{usdFull(r.model_drift.tp_today_e0t0)}</span></span></div>
            <div className="mt-2 text-[12px] text-ink-500">Reported separately so model changes are not mistaken for rate. Model version held fixed across the three runs: <span className="mono text-ink-700">{r.model_version}</span>.</div>
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5">Gross vs net of acquisition cost<Info id="account.net" /></span>}>
            <div className="grid grid-cols-2 gap-3">
              <div><div className="text-[11px] uppercase tracking-wide text-ink-500">Gross RARC</div><div className={cx('num text-[20px] font-semibold', r.rarc < 0 ? 'text-crit' : 'text-ok')}>{pct(r.rarc, 1, true)}</div></div>
              <div><div className="text-[11px] uppercase tracking-wide text-ink-500">Net RARC</div><div className={cx('num text-[20px] font-semibold', r.net.rarc_net < 0 ? 'text-crit' : 'text-ok')}>{pct(r.net.rarc_net, 1, true)}</div></div>
            </div>
            <div className="mt-2 text-[12px] text-ink-500">Brokerage <span className="num">{pct(r.net.brokerage_expiring, 1)}</span> expiring → <span className="num font-medium text-ink-800">{pct(r.net.brokerage_proposed, 1)}</span> proposed.</div>
          </Card>
        </div>
      </div>
      <div className="col-span-12 xl:col-span-4">
        <div className="sticky top-14 space-y-4">
          <WhatIf a={a} base={base} r={r} premium={premium} setPremium={setPremium} terms={terms} setTerms={setTerms} brokerage={brokerage} setBrokerage={setBrokerage} dirty={dirty} reset={reset} pending={whatIf.isPending} />
        </div>
      </div>
    </div>
  );
}

function Readout({ r, base, dirty }: { r: RarcResult; base: RarcResult; dirty: boolean }) {
  const cells = [
    { l: 'Headline change', v: pct(r.headline_change, 1, true), s: `${usd(r.expiring_premium)} → ${usd(r.proposed_premium)}`, tone: 'text-ink-950', b: base.headline_change, x: r.headline_change },
    { l: 'Computed RARC', v: pct(r.rarc, 1, true), s: `vs expected ${k1(r.expected_premium)}`, tone: r.rarc < -0.05 ? 'text-crit' : r.rarc < 0 ? 'text-high' : 'text-ok', b: base.rarc, x: r.rarc },
    { l: 'Adequacy', v: pct(r.adequacy, 1), s: `of TP(E1,T1) ${usd(r.tp_e1_t1)} · floor ${pct(r.adequacy_floor, 0)}`, tone: r.adequacy < r.adequacy_floor ? 'text-crit' : r.adequacy < 1 ? 'text-med' : 'text-ok', b: base.adequacy, x: r.adequacy },
  ];
  const rateGiven = r.rarc < 0;
  return (
    <Card pad={false}>
      <div className="grid grid-cols-2 divide-x divide-line md:grid-cols-4">
        {cells.map((c) => (
          <div key={c.l} className="px-4 py-3">
            <div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">{c.l}</div>
            <div className={cx('num mt-0.5 text-[28px] font-semibold tracking-[-0.02em]', c.tone)}>{c.v}</div>
            <div className="num text-[11.5px] text-ink-500">{c.s}</div>
            {dirty && Math.abs(c.x - c.b) > 0.0005 && <div className="num mt-0.5 text-[11px] text-ink-400">was {c.l === 'Adequacy' ? pct(c.b, 1) : pct(c.b, 1, true)}</div>}
          </div>
        ))}
        <div className={cx('px-4 py-3', r.required_authority_level > 1 ? 'bg-high-bg/50' : 'bg-ok-bg/50')}>
          <div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">Authority required</div>
          <div className="mt-0.5 flex items-center gap-2"><span className="num text-[28px] font-semibold text-ink-950">L{r.required_authority_level}</span>{r.required_authority_level > 1 ? <ShieldAlert className="size-5 text-high" /> : <ShieldCheck className="size-5 text-ok" />}</div>
          <ul className="mt-0.5 space-y-0.5 text-[11px] leading-snug text-ink-600">{r.authority_reasons.map((x) => <li key={x}>· {x}</li>)}</ul>
        </div>
      </div>
      <div className="border-t border-line bg-ink-50/60 px-4 py-2.5 text-[13.5px] text-ink-800">
        The account looks like it's <span className="num font-semibold">{pct(r.headline_change, 1, true)}</span>, but on a like-for-like basis you're {rateGiven ? 'giving' : 'gaining'} <span className={cx('num font-semibold', rateGiven ? 'text-crit' : 'text-ok')}>{pct(Math.abs(r.rarc), 1)}</span> of rate.{' '}
        {r.adequacy >= r.adequacy_floor ? <>It's still within adequacy{r.adequacy < r.adequacy_floor + 0.01 ? ", and you're at the floor" : ''}.</> : <span className="font-medium text-crit">It's below the {pct(r.adequacy_floor, 0)} adequacy floor.</span>}
        <span className="ml-2 text-[11px] text-ink-500">Method: {r.method === 'model_rerun' ? 'carrier rater rerun ×3' : 'exposure-elasticity fallback (lower confidence)'} <MockBadge label="rater-stub" /></span>
        <Info id="account.pricing" label="About this tab" className="ml-2 align-middle" />
      </div>
    </Card>
  );
}

function ModelRuns({ r }: { r: RarcResult }) {
  const cols = [
    { k: 'e0t0' as const, t: 'TP(E0,T0)', s: 'Expiring exposure · expiring terms', tiv: r.tiv_expiring, total: r.tp_e0_t0 },
    { k: 'e1t0' as const, t: 'TP(E1,T0)', s: 'Renewal exposure · expiring terms', tiv: r.tiv_renewal, total: r.tp_e1_t0 },
    { k: 'e1t1' as const, t: 'TP(E1,T1)', s: 'Renewal exposure · proposed terms', tiv: r.tiv_renewal, total: r.tp_e1_t1 },
  ];
  return (
    <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Three technical-model runs<Info id="account.rarc_runs" /></span>} subtitle="Controlled snapshots — only one variable moves between adjacent columns">
      <table className="dt">
        <thead>
          <tr><th>Component</th>{cols.map((c) => <th key={c.k} className="r"><div className="mono text-[11.5px] normal-case text-ink-900">{c.t}</div><div className="text-[10px] normal-case tracking-normal text-ink-400">{c.s}</div></th>)}<th className="r">Δ exposure</th><th className="r">Δ terms</th></tr>
        </thead>
        <tbody>
          {r.breakdown.map((row) => (
            <tr key={row.component}>
              <td className="text-ink-700">{row.component}</td>
              <td className="num r">{usdFull(row.e0t0)}</td><td className="num r">{usdFull(row.e1t0)}</td>
              <td className={cx('num r', row.e1t1 !== row.e1t0 && 'font-semibold text-accent-700')}>{usdFull(row.e1t1)}</td>
              <td className={cx('num r text-[12px]', row.e1t0 - row.e0t0 > 0 ? 'text-high' : 'text-ink-400')}>{row.e1t0 === row.e0t0 ? '—' : (row.e1t0 > row.e0t0 ? '+' : '−') + usd(Math.abs(row.e1t0 - row.e0t0))}</td>
              <td className={cx('num r text-[12px]', row.e1t1 < row.e1t0 ? 'text-ok' : row.e1t1 > row.e1t0 ? 'text-high' : 'text-ink-400')}>{row.e1t1 === row.e1t0 ? '—' : (row.e1t1 > row.e1t0 ? '+' : '−') + usd(Math.abs(row.e1t1 - row.e1t0))}</td>
            </tr>
          ))}
          <tr className="font-semibold">
            <td className="!border-t-2 !border-t-ink-200 text-ink-950">Technical premium</td>
            {cols.map((c) => <td key={c.k} className="num r !border-t-2 !border-t-ink-200 text-[14px] text-ink-950">{usdFull(c.total)}</td>)}
            <td className="num r !border-t-2 !border-t-ink-200 text-[12px] text-ink-600">× {f3(r.exposure_factor)}</td>
            <td className="num r !border-t-2 !border-t-ink-200 text-[12px] text-ink-600">× {f3(r.terms_factor)}</td>
          </tr>
          <tr><td className="text-[11px] text-ink-500">TIV</td>{cols.map((c) => <td key={c.k} className="num r text-[11px] text-ink-500">{usd(c.tiv)}</td>)}<td /><td /></tr>
        </tbody>
      </table>
    </Card>
  );
}

function FactorChain({ r }: { r: RarcResult }) {
  const Box = ({ l, v, s, strong }: { l: string; v: string; s?: string; strong?: boolean }) => (
    <div className={cx('rounded-lg border px-3 py-2 text-center', strong ? 'border-ink-900 bg-ink-900 text-white' : 'border-line bg-surface')}>
      <div className={cx('text-[10.5px] uppercase tracking-wide', strong ? 'text-ink-300' : 'text-ink-500')}>{l}</div>
      <div className="num text-[17px] font-semibold">{v}</div>
      {s && <div className={cx('mono text-[10px]', strong ? 'text-ink-300' : 'text-ink-400')}>{s}</div>}
    </div>
  );
  const Op = ({ c }: { c: string }) => <span className="text-[18px] font-light text-ink-400">{c}</span>;
  return (
    <Card title={<span className="inline-flex items-center gap-1.5">Expected premium — factor chain<Info id="account.factor_chain" /></span>} subtitle="Lloyd's PMDR method, with adjustments computed from the model rather than typed in">
      <div className="flex flex-wrap items-center gap-2.5">
        <Box l="Expiring" v={k1(r.expiring_premium)} />
        <Op c="×" /><Box l="Exposure factor" v={f3(r.exposure_factor)} s="E1T0 / E0T0" />
        <Op c="×" /><Box l="Terms factor" v={f3(r.terms_factor)} s="E1T1 / E1T0" />
        <Op c="=" /><Box l="Expected" v={k1(r.expected_premium)} strong />
        <ArrowRight className="mx-1 size-4 text-ink-400" />
        <Box l="Proposed" v={k1(r.proposed_premium)} />
        <Op c="→" />
        <div className="rounded-lg border border-line px-3 py-2">
          <div className="text-[10.5px] uppercase tracking-wide text-ink-500">RARC = proposed ÷ expected − 1</div>
          <div className={cx('num text-[17px] font-semibold', r.rarc < 0 ? 'text-crit' : 'text-ok')}>{pct(r.rarc, 1, true)}</div>
        </div>
      </div>
      <div className="mt-3 text-[12px] text-ink-500">Price deviation vs technical <span className="num font-medium text-ink-800">{pct(r.price_deviation, 1, true)}</span> · adequacy = proposed ÷ TP(E1,T1) = <span className="num">{k1(r.proposed_premium)} ÷ {k1(r.tp_e1_t1)}</span> = <span className="num font-medium text-ink-800">{pct(r.adequacy, 1)}</span></div>
    </Card>
  );
}

function WhatIf({ a, base, r, premium, setPremium, terms, setTerms, brokerage, setBrokerage, dirty, reset, pending }: {
  a: AccountDetail; base: RarcResult; r: RarcResult; premium: number; setPremium: (n: number) => void; terms: RarcTerms; setTerms: (t: RarcTerms) => void;
  brokerage: number; setBrokerage: (n: number) => void; dirty: boolean; reset: () => void; pending: boolean;
}) {
  const { data: contract } = useContract(a.account_id);
  const { data: users } = useUsers();
  const meUser = users?.find((u) => u.user_id === getCurrentUserId());
  const create = useCreateQuote(a.account_id), refer = useCreateReferral(a.account_id), send = useSendQuote(a.account_id);
  const [memoOpen, setMemoOpen] = useState(false);
  const [note, setNote] = useState('');
  const [msg, setMsg] = useState<{ tone: 'ok' | 'crit'; text: string } | null>(null);
  const current = useMemo(() => (contract?.quotes ?? []).filter((q) => q.term !== contract?.term || !['BOUND'].includes(q.status)).sort((x, y) => y.version - x.version), [contract]);
  const latest: QuoteVersion | undefined = current[0];
  const matchesLatest = latest && latest.premium === premium && JSON.stringify(latest.terms) === JSON.stringify(terms);
  const lo = Math.round(base.expiring_premium * 0.85 / 1000) * 1000, hi = Math.round(base.expiring_premium * 1.35 / 1000) * 1000;
  const set = (p: Partial<RarcTerms>) => setTerms({ ...terms, ...p });
  const flash = (tone: 'ok' | 'crit', text: string) => { setMsg({ tone, text }); setTimeout(() => setMsg(null), 6000); };
  const save = () => create.mutateAsync({ premium, terms });
  const doRefer = async () => {
    try { const q = matchesLatest ? latest! : await save(); const ref = await refer.mutateAsync({ quote_id: q.quote_id, note }); setMemoOpen(false); flash('ok', `Referred to L${ref.required_level} — approval will be locked to terms hash ${q.terms_hash}`); }
    catch (e) { flash('crit', (e as Error).message); }
  };
  const doSend = async () => {
    try { const q = matchesLatest ? latest! : await save(); await send.mutateAsync(q.quote_id); flash('ok', `Quote v${q.version} sent to ${a.broker}`); }
    catch (e) { flash('crit', (e as Error).message); }
  };
  const memo = `Requesting approval of ${usdFull(premium)}${terms.named_storm_ded_pct !== null ? ` at a ${(terms.named_storm_ded_pct * 100).toFixed(1)}% named-storm deductible` : ''}. Headline ${pct(r.headline_change, 1, true)}, RARC ${pct(r.rarc, 1, true)}, adequacy ${pct(r.adequacy, 1)}. ${r.authority_reasons.join('; ')}.`;
  const over = meUser && r.required_authority_level > meUser.authority_level;

  return (
    <Card title={<span className="inline-flex items-center gap-1.5">What-if<Info id="account.whatif" /></span>} subtitle="Live recompute on the same three model runs" actions={dirty ? <Button size="sm" variant="ghost" icon={<RotateCcw className="size-3" />} onClick={reset}>Reset</Button> : <Badge>baseline: broker counter</Badge>}>
      <div className="space-y-4">
        <div>
          <div className="mb-1 flex items-baseline justify-between"><SectionLabel>Proposed premium</SectionLabel>{pending && <span className="text-[11px] text-ink-400">recomputing…</span>}</div>
          <div className="flex items-center gap-2">
            <span className="text-ink-400">$</span>
            <input type="number" step={1000} value={premium} onChange={(e) => setPremium(Math.max(0, +e.target.value))} className="num h-8 w-32 rounded-md border border-line-strong px-2 text-[14px] font-semibold outline-none focus:border-accent-500" />
            <span className="num text-[12px] text-ink-500">{pct(premium / base.expiring_premium - 1, 1, true)} vs expiring</span>
          </div>
          <input type="range" min={lo} max={hi} step={1000} value={premium} onChange={(e) => setPremium(+e.target.value)} className="mt-2 w-full accent-[var(--color-accent-600)]" />
          <div className="num flex justify-between text-[10.5px] text-ink-400"><span>{usd(lo)}</span><span>expected {k1(r.expected_premium)} · TP {usd(r.tp_e1_t1)}</span><span>{usd(hi)}</span></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {terms.named_storm_ded_pct !== null && (
            <Field label="Named-storm ded %" hint={terms.named_storm_ded_pct < 0.03 ? 'below 3% floor' : 'floor 3%'} warn={terms.named_storm_ded_pct < 0.03}>
              <select value={terms.named_storm_ded_pct} onChange={(e) => set({ named_storm_ded_pct: +e.target.value })} className="h-8 w-full rounded-md border border-line-strong px-2 text-[13px]">
                {[0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05].map((v) => <option key={v} value={v}>{(v * 100).toFixed(1)}% per location</option>)}
              </select>
            </Field>
          )}
          {terms.named_storm_ded_min !== null && (
            <Field label="NS minimum">
              <select value={terms.named_storm_ded_min} onChange={(e) => set({ named_storm_ded_min: +e.target.value })} className="h-8 w-full rounded-md border border-line-strong px-2 text-[13px]">
                {[50_000, 100_000, 250_000, 500_000].map((v) => <option key={v} value={v}>{usd(v)}</option>)}
              </select>
            </Field>
          )}
          <Field label="AOP deductible">
            <select value={terms.aop_deductible} onChange={(e) => set({ aop_deductible: +e.target.value })} className="h-8 w-full rounded-md border border-line-strong px-2 text-[13px]">
              {[10_000, 25_000, 50_000, 100_000, 250_000, 500_000].map((v) => <option key={v} value={v}>{usd(v)}</option>)}
            </select>
          </Field>
          {terms.bi_sublimit !== null && (
            <Field label="BI sublimit">
              <select value={terms.bi_sublimit} onChange={(e) => set({ bi_sublimit: +e.target.value })} className="h-8 w-full rounded-md border border-line-strong px-2 text-[13px]">
                {[...new Set([2e6, 5e6, 10e6, 15e6, 25e6, base.expiring_terms.bi_sublimit ?? 0, terms.bi_sublimit])].filter(Boolean).sort((x, y) => x - y).map((v) => <option key={v} value={v}>{usd(v)}</option>)}
              </select>
            </Field>
          )}
          <Field label="Brokerage">
            <select value={brokerage} onChange={(e) => setBrokerage(+e.target.value)} className="h-8 w-full rounded-md border border-line-strong px-2 text-[13px]">
              {[...new Set([0.1, 0.125, 0.15, 0.175, 0.2, 0.25, brokerage])].sort().map((v) => <option key={v} value={v}>{pct(v, 1)}</option>)}
            </select>
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-lg bg-ink-50 p-2.5 text-center">
          <Mini l="RARC" v={pct(r.rarc, 1, true)} tone={r.rarc < -0.05 ? 'text-crit' : r.rarc < 0 ? 'text-high' : 'text-ok'} />
          <Mini l="Adequacy" v={pct(r.adequacy, 1)} tone={r.adequacy < r.adequacy_floor ? 'text-crit' : r.adequacy < 1 ? 'text-med' : 'text-ok'} />
          <Mini l="Authority" v={`L${r.required_authority_level}`} tone={over ? 'text-high' : 'text-ok'} />
        </div>
        {meUser && <div className={cx('text-[12px]', over ? 'text-high' : 'text-ok')}>{over ? `You are L${meUser.authority_level} — these terms need L${r.required_authority_level}. Refer before sending.` : `Within your authority (L${meUser.authority_level}).`}</div>}
        <div className="flex flex-wrap gap-2">
          <Button icon={<Save className="size-3.5" />} loading={create.isPending && !refer.isPending && !send.isPending} disabled={!!matchesLatest} onClick={() => save().then((q) => flash('ok', `Saved quote v${q.version} · hash ${q.terms_hash}`)).catch((e) => flash('crit', e.message))}>Save as quote version</Button>
          <Button icon={<GitPullRequestArrow className="size-3.5" />} onClick={() => { setNote(''); setMemoOpen((o) => !o); }}>Refer</Button>
          <Button variant="primary" icon={<Send className="size-3.5" />} loading={send.isPending} onClick={doSend}>Send to broker</Button>
        </div>
        {memoOpen && (
          <div className="rounded-lg border border-line p-3">
            <SectionLabel>Referral memo (pre-filled · findings cited automatically)</SectionLabel>
            <div className="mb-2 rounded bg-ink-50 p-2 text-[12px] leading-relaxed text-ink-700">{memo}</div>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} placeholder="Add your rationale (retention, broker relationship, conditions offered)…" className="w-full resize-none rounded-md border border-line-strong px-2 py-1.5 text-[12px] outline-none focus:border-accent-500" />
            <div className="mt-2 flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={() => setMemoOpen(false)}>Cancel</Button><Button size="sm" variant="primary" loading={refer.isPending} onClick={doRefer}>Submit referral</Button></div>
          </div>
        )}
        {msg && <div className={cx('anim-fade rounded-md px-3 py-2 text-[12px]', msg.tone === 'ok' ? 'bg-ok-bg text-ok' : 'bg-crit-bg text-crit')}>{msg.text}</div>}
        {current.length > 0 && (
          <div>
            <SectionLabel>Quote versions</SectionLabel>
            <div className="space-y-1">
              {current.slice(0, 5).map((q) => (
                <div key={q.quote_id} className="flex items-center justify-between gap-2 rounded-md border border-line px-2 py-1.5 text-[12px]">
                  <span className="font-medium text-ink-900">v{q.version} <span className="text-ink-400">{q.term}</span></span>
                  <span className="num">{usd(q.premium)}</span>
                  <span className="num text-ink-500">{pct(q.rarc, 1, true)}</span>
                  <span className="mono text-[10.5px] text-ink-400">{q.terms_hash}</span>
                  <Badge tone={q.status === 'APPROVED' || q.status === 'ACCEPTED' ? 'ok' : q.status === 'SENT' ? 'accent' : q.status === 'REFERRED' ? 'info' : 'neutral'}>{q.status.toLowerCase()}</Badge>
                </div>
              ))}
            </div>
            <div className="mt-1 text-[10.5px] text-ink-400">Last saved {fmtDate(current[0].created_at)} by {current[0].created_by}</div>
          </div>
        )}
      </div>
    </Card>
  );
}

function Field({ label, children, hint, warn }: { label: string; children: React.ReactNode; hint?: string; warn?: boolean }) {
  return <label className="block"><div className="mb-1 flex justify-between text-[11px] text-ink-500"><span>{label}</span>{hint && <span className={cx(warn ? 'font-medium text-crit' : 'text-ink-400')}>{hint}</span>}</div>{children}</label>;
}
function Mini({ l, v, tone }: { l: string; v: string; tone: string }) {
  return <div><div className="text-[10px] uppercase tracking-wide text-ink-500">{l}</div><div className={cx('num text-[18px] font-semibold', tone)}>{v}</div></div>;
}
