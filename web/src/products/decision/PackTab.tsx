// Stage 1 — the decision pack, prepared before a human opens the file. Every value opens its evidence.
import { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, FileText, Send, ShieldQuestion, Search } from 'lucide-react';
import { Card, Badge, Button, Empty, ObsTypeChip, SeverityPill, cx } from '@/components/ui';
import { EvidenceLink, useEvidence } from '@/components/evidence';
import { usd, pct } from '@/lib/format';
import { Bar, SectionLabel } from '@/pages/common';
import { Info } from '@/help/Info';
import type { ObsType } from '@/api/types';
import { DRAFT_LABEL, useOrderInspection, useOverride, usePrerefer, useRequestInfo, useResolve, type CaseDetail, type Contradiction, type Facts, type Pack, type Side } from './api';
import { Cite } from './parts';

export default function PackTab({ c, onAct }: { c: CaseDetail; onAct: () => void }) {
  return <PackView pack={c.pack!} facts={c.facts!} c={c} onAct={onAct} />;
}

export function PackView({ pack, facts, c, onAct }: { pack: Pack; facts: Facts; c?: CaseDetail; onAct?: () => void }) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <Draft p={pack} c={c} onAct={onAct} className="col-span-12" />
      <Contradictions p={pack} caseId={c?.case_id} className="col-span-12 xl:col-span-7" />
      <MissingInfo p={pack} c={c} className="col-span-12 xl:col-span-5" />
      <Factors p={pack} c={c} className="col-span-12 xl:col-span-7" />
      <Authority p={pack} c={c} className="col-span-12 xl:col-span-5" />
      <PricingCard p={pack} className="col-span-12 xl:col-span-7" />
      <Terms p={pack} className="col-span-12 xl:col-span-5" />
      <FactsCard facts={facts} p={pack} className="col-span-12" />
      <Guidelines p={pack} className="col-span-12 xl:col-span-7" />
      <PortfolioCard p={pack} className="col-span-12 xl:col-span-5" />
    </div>
  );
}

function Title({ t, id }: { t: string; id: string }) {
  return <span className="inline-flex items-center gap-1.5">{t}<Info id={id} /></span>;
}

function Draft({ p, c, onAct, className }: { p: Pack; c?: CaseDetail; onAct?: () => void; className?: string }) {
  const d = p.draft;
  const tone = d.action === 'DECLINE' ? 'border-[#f6c5cc] bg-crit-bg/50' : d.action.startsWith('REFER') ? 'border-[#f5d2b8] bg-high-bg/50' : 'border-[#bfe3cd] bg-ok-bg/50';
  return (
    <Card className={className} title={<Title t="Draft recommendation" id="decision.draft" />} subtitle={`Prepared ${p.built_at} · ${p.evidence.facts} source-linked facts from ${p.evidence.documents} documents · the underwriter decides`}
      actions={c && onAct && !c.decision ? <Button size="sm" variant="primary" icon={<ArrowRight className="size-3.5" />} onClick={onAct}>Record intended action</Button> : undefined}>
      <div className="grid grid-cols-12 gap-4">
        <div className={cx('col-span-12 rounded-lg border p-3 lg:col-span-4', tone)}>
          <div className="text-[10.5px] font-medium uppercase tracking-wide text-ink-500">Draft action</div>
          <div className="text-[20px] font-semibold text-ink-950">{DRAFT_LABEL[d.action]}</div>
          <div className="text-[12.5px] text-ink-700">{d.why}</div>
          <div className="mt-2 text-[12px] text-ink-600">Suggested premium <span className="num font-semibold text-ink-900">{usd(d.premium_range[0], { compact: false })} – {usd(d.premium_range[1], { compact: false })}</span></div>
        </div>
        <div className="col-span-12 lg:col-span-5">
          <SectionLabel>Before the final decision</SectionLabel>
          {d.before_final.length === 0 ? <div className="flex items-center gap-1.5 text-[13px] text-ok"><CheckCircle2 className="size-4" />Nothing outstanding</div> :
            <ul className="space-y-1">{d.before_final.map((x) => <li key={x} className="flex gap-2 text-[12.5px] text-ink-800"><AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-high" />{x}</li>)}</ul>}
        </div>
        <div className="col-span-12 grid grid-cols-2 gap-2 text-[12px] lg:col-span-3">
          <div className="rounded-md border border-line p-2"><div className="text-ink-500">Evidence</div><div className="num text-[16px] font-semibold">{p.evidence.facts}</div><div className="text-[11px] text-ink-500">facts with anchors</div></div>
          <div className="rounded-md border border-line p-2"><div className="text-ink-500">Prep time</div><div className="num text-[16px] font-semibold">{p.prep.platform.toFixed(1)} h</div><div className="text-[11px] text-ink-500">vs {p.prep.manual.toFixed(1)} h manual</div></div>
          <div className="col-span-2 rounded-md border border-line p-2"><div className="text-ink-500">Sources</div><div className="text-[11.5px] text-ink-800">{p.evidence.sources.join(' · ')}</div></div>
        </div>
      </div>
    </Card>
  );
}

function SideBox({ s, label, winner }: { s: Side; label: string; winner?: boolean }) {
  const ev = useEvidence();
  return (
    <div className={cx('min-w-0 flex-1 rounded-md border p-2', winner ? 'border-accent-500 bg-accent-50/40' : 'border-line')}>
      <div className="flex items-center justify-between text-[10.5px] uppercase tracking-wide text-ink-500">{label}<ObsTypeChip t={s.obs_type as ObsType} /></div>
      <div className="num text-[17px] font-semibold text-ink-950"><EvidenceLink obsId={s.obs_id}>{s.value}</EvidenceLink></div>
      <div className="truncate text-[11.5px] text-ink-600" title={s.source}>{s.source}</div>
      {s.doc_id && <button onClick={() => ev.openDoc(s.doc_id!, s.anchor)} className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-accent-700 hover:underline"><FileText className="size-3" />Open at source</button>}
    </div>
  );
}

function Contradictions({ p, caseId, className }: { p: Pack; caseId?: string; className?: string }) {
  return (
    <Card className={className} title={<Title t="Contradictions between sources" id="decision.contradictions" />} subtitle="Same field, different values · each priced by re-rating on the other value">
      {p.contradictions.length === 0 ? <Empty>No contradictions — application, schedule, inspection and vendor data agree.</Empty> : (
        <div className="space-y-3">{p.contradictions.map((x) => <ContraRow key={x.contradiction_id} x={x} caseId={caseId} />)}</div>
      )}
    </Card>
  );
}

function ContraRow({ x, caseId }: { x: Contradiction; caseId?: string }) {
  const res = useResolve(caseId ?? '', x.contradiction_id);
  return (
    <div className="rounded-lg border border-line p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="text-[13px] font-semibold text-ink-900">{x.field_label} · {x.location} {x.material && <Badge tone="high">Material</Badge>}</div>
        <div className="text-[12px] text-ink-600">Rating impact <span className="num font-semibold text-ink-900">{usd(x.impact_usd, { compact: false })}</span></div>
      </div>
      <div className="flex gap-2">
        <SideBox s={x.resolved} label="Resolved by policy" winner />
        <SideBox s={x.other} label="Other source" />
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-ink-500">
        <span>Policy: {x.policy}</span>
        {x.status === 'RESOLVED' ? <span className="flex items-center gap-1 text-ok"><CheckCircle2 className="size-3.5" />Resolved by {x.resolution?.by}: {x.resolution?.choice}</span> : caseId && (
          <span className="flex gap-1.5">
            <Button size="sm" variant="primary" loading={res.isPending} onClick={() => res.mutate({ choice: 'resolved', note: 'Verified source governs' })}>Accept {x.resolved.value}</Button>
            <Button size="sm" loading={res.isPending} onClick={() => res.mutate({ choice: 'other', note: 'Underwriter determination' })}>Use {x.other.value}</Button>
          </span>
        )}
      </div>
    </div>
  );
}

function MissingInfo({ p, c, className }: { p: Pack; c?: CaseDetail; className?: string }) {
  const req = useRequestInfo(c?.case_id ?? '');
  const insp = useOrderInspection(c?.case_id ?? '');
  const open = p.missing.filter((m) => m.status === 'OPEN');
  const [sel, setSel] = useState<string[]>([]);
  const items = sel.length ? sel : open.map((m) => m.item);
  return (
    <Card className={className} title={<Title t="Missing information" id="decision.missing" />} subtitle={`Loss runs on file: ${p.loss_run_years} years`}
      actions={c && !c.decision ? <>
        <Button size="sm" icon={<Search className="size-3.5" />} loading={insp.isPending} onClick={() => insp.mutate({ scope: 'Verification survey' })}>Order inspection</Button>
        <Button size="sm" variant="primary" icon={<Send className="size-3.5" />} disabled={!items.length} loading={req.isPending} onClick={() => req.mutate({ items }, { onSuccess: () => setSel([]) })}>Request from broker</Button></> : undefined}>
      {p.missing.length === 0 ? <Empty>Nothing missing.</Empty> : (
        <ul className="space-y-1.5">{p.missing.map((m) => (
          <li key={m.item} className="flex items-start gap-2 text-[12.5px]">
            {c && m.status === 'OPEN' && <input type="checkbox" className="mt-1 accent-[var(--color-accent-600)]" checked={sel.includes(m.item)} onChange={() => setSel((s) => s.includes(m.item) ? s.filter((x) => x !== m.item) : [...s, m.item])} />}
            <span className="min-w-0 flex-1"><span className="font-medium text-ink-900">{m.item}</span>{m.blocking && <Badge tone="crit" className="ml-1.5">blocks bind</Badge>}<span className="block text-[11.5px] text-ink-500">{m.why}</span></span>
            <Badge tone={m.status === 'REQUESTED' ? 'info' : 'neutral'}>{m.status === 'REQUESTED' ? 'Requested' : 'Open'}</Badge>
          </li>
        ))}</ul>
      )}
      {c && c.requests.length > 0 && <div className="mt-3 border-t border-line pt-2 text-[11.5px] text-ink-500">{c.requests.map((r) => <div key={r.request_id}>{r.sent}: {r.items.join('; ')} — <span className={r.status === 'RECEIVED' ? 'text-ok' : ''}>{r.status === 'RECEIVED' ? 'received' : `due ${r.due}`}</span></div>)}</div>}
    </Card>
  );
}

function Factors({ p, c, className }: { p: Pack; c?: CaseDetail; className?: string }) {
  const ev = useEvidence();
  const ov = useOverride(c?.case_id ?? '');
  const [open, setOpen] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  return (
    <Card className={className} pad={false} title={<Title t="Material risk factors" id="decision.factors" />} subtitle="Rules and contradictions that fired on the pack · impact is premium-equivalent from re-rating">
      {p.factors.length === 0 ? <Empty>No material risk factors.</Empty> : (
        <div className="divide-y divide-line">{p.factors.map((f, i) => {
          const key = `${f.rule_id}|${f.subject_id ?? 'case'}`;
          const done = c?.overrides.find((o) => o.rule_id === f.rule_id && (o.subject_id ?? null) === (f.rule_id === 'DA.APPETITE.PROHIBITED' ? null : f.subject_id));
          return (
            <div key={i} className="px-4 py-2.5">
              <div className="flex items-start gap-2">
                <SeverityPill s={f.severity} />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium text-ink-900">{f.title} <span className="text-ink-500">· {f.subject}</span></div>
                  <div className="text-[12px] text-ink-600">{f.observed}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-3">
                    <Cite c={f.citation} />{f.rule_id && <span className="mono text-[10.5px] text-ink-400">{f.rule_id} · T{f.tier}</span>}
                    {f.evidence_obs_ids.length > 0 && <button onClick={() => ev.openObs(f.evidence_obs_ids[0])} className="text-[11.5px] font-medium text-accent-700 hover:underline">Evidence ({f.evidence_obs_ids.length})</button>}
                    {done && <Badge tone="med">Overridden by {done.by_name}: {done.reason}</Badge>}
                    {c && f.rule_id && !done && !c.decision && <button onClick={() => { setOpen(open === key ? null : key); setReason(''); }} className="text-[11.5px] text-ink-500 hover:text-ink-900">Override…</button>}
                  </div>
                  {open === key && (
                    <div className="mt-2 flex gap-2">
                      <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (required; cite the evidence it relies on)" className="h-7 flex-1 rounded-md border border-line-strong px-2 text-[12px] outline-none focus:border-accent-500" />
                      <Button size="sm" variant="primary" disabled={reason.trim().length < 8} loading={ov.isPending}
                        onClick={() => ov.mutate({ rule_id: f.rule_id, subject_id: f.rule_id === 'DA.APPETITE.PROHIBITED' ? null : f.subject_id, reason }, { onSuccess: () => setOpen(null) })}>Record override</Button>
                    </div>
                  )}
                </div>
                <span className="num text-[12.5px] font-semibold text-ink-900">{f.impact_usd ? usd(f.impact_usd) : ''}</span>
              </div>
            </div>
          );
        })}</div>
      )}
    </Card>
  );
}

function Authority({ p, c, className }: { p: Pack; c?: CaseDetail; className?: string }) {
  const pre = usePrerefer(c?.case_id ?? '');
  const need = p.requirements.some((r) => !r.within);
  const hasPre = c?.referrals.some((r) => r.kind === 'pre');
  return (
    <Card className={className} title={<Title t="Authority & referral requirements" id="decision.authority" />} subtitle={`New-business authority matrix · required level L${p.required_level}${c ? ` · ${c.underwriter} holds L${c.uw_level}` : ''}`}
      actions={c && need && !hasPre && !c.decision ? <Button size="sm" icon={<ShieldQuestion className="size-3.5" />} loading={pre.isPending} onClick={() => pre.mutate({ note: 'Pre-referral of the pack requirements before quoting' })}>Pre-refer</Button> : undefined}>
      <ul className="space-y-1.5">{p.requirements.map((r) => (
        <li key={r.requirement} className="flex items-start justify-between gap-2 text-[12.5px]">
          <span className="text-ink-800">{r.requirement}<span className="block text-[11px] text-ink-500">{r.source}</span></span>
          <Badge tone={r.within ? 'ok' : 'high'}>{r.within ? `L${r.level} · within` : `Refer L${r.level}`}</Badge>
        </li>
      ))}</ul>
      {pre.error && <div className="mt-2 text-[12px] text-crit">{(pre.error as Error).message}</div>}
      {c?.referrals.filter((r) => r.kind === 'pre').map((r) => (
        <div key={r.referral_id} className="mt-3 rounded-md border border-line bg-ink-50 px-3 py-2 text-[12px]">Pre-referral L{r.required_level}: <span className="font-medium">{r.status.toLowerCase()}</span>{r.approver && ` by ${r.approver}`}{r.envelope_text && ` · envelope: ${r.envelope_text}`}</div>
      ))}
    </Card>
  );
}

function PricingCard({ p, className }: { p: Pack; className?: string }) {
  const px = p.pricing;
  return (
    <Card className={className} title={<Title t="Pricing context" id="decision.pricing" />} subtitle={<>{px.model} + MockCat · <Badge tone="mock">MOCK rater</Badge></>}>
      <div className="mb-3 grid grid-cols-4 gap-2">
        {[['Technical', usd(px.technical, { compact: false })], ['Suggested range', `${usd(px.band_low)} – ${usd(px.band_high)}`], ['CAT AAL', usd(px.aal)], ['Prior / target', `${usd(px.prior_premium)} / ${usd(px.target_premium ?? px.bind_offer)}`]].map(([l, v]) => (
          <div key={l} className="rounded-md border border-line px-2.5 py-1.5"><div className="text-[10.5px] uppercase text-ink-500">{l}</div><div className="num text-[14px] font-semibold">{v}</div></div>
        ))}
      </div>
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-5">
          <SectionLabel>Components</SectionLabel>
          {px.components.map((x) => <div key={x.component} className="flex justify-between py-0.5 text-[12px]"><span className="text-ink-600">{x.component}</span><span className="num">{usd(x.value, { compact: false })}</span></div>)}
          <SectionLabel>Modifiers</SectionLabel>
          {px.modifiers.map((m) => <div key={m.label} className="flex justify-between py-0.5 text-[12px]"><span className="text-ink-600">{m.label}</span><span className="num">×{m.value.toFixed(3)}</span></div>)}
        </div>
        <div className="col-span-12 md:col-span-7">
          <SectionLabel>By location (rating factors)</SectionLabel>
          <table className="dt"><thead><tr><th>Location</th><th className="r">Base</th><th className="r">Const.</th><th className="r">Spr.</th><th className="r">Roof</th><th className="r">AAL</th></tr></thead>
            <tbody>{px.per_loc.map((l) => <tr key={l.location_uid}><td className="max-w-[160px] truncate">{l.label}</td><td className="num r">{l.base_rate.toFixed(3)}</td><td className="num r">{l.construction_factor}</td><td className={cx('num r', l.sprinkler_factor > 0.8 && 'text-high')}>{l.sprinkler_factor}</td><td className={cx('num r', l.roof_factor > 1 && 'text-high')}>{l.roof_factor}</td><td className="num r">{usd(l.aal)}</td></tr>)}</tbody></table>
        </div>
      </div>
    </Card>
  );
}

function Terms({ p, className }: { p: Pack; className?: string }) {
  const s = p.suggested;
  return (
    <Card className={className} title={<Title t="Suggested terms" id="decision.terms" />} subtitle="From the guidelines in force and the NB standards">
      {[['Action', 'Quote'], ['Premium', `${usd(p.draft.premium_range[0], { compact: false })} – ${usd(p.draft.premium_range[1], { compact: false })}`], ['Limit', `${usd(s.limit)} blanket`], ['AOP deductible', usd(s.aop, { compact: false })],
        ['Named storm', s.ns_pct ? `${pct(s.ns_pct, 0)} · min ${usd(s.ns_min ?? 0)}` : 'n/a'], ['Wind/hail', s.wh_pct ? pct(s.wh_pct, 0) : 'n/a'], ['Line', p.portfolio.max_line < 1 ? `≤ ${pct(p.portfolio.max_line, 0)} keeps the zone under threshold` : '100%']].map(([k, v]) => (
        <div key={k} className="flex justify-between border-b border-line py-1 text-[12.5px] last:border-0"><span className="text-ink-500">{k}</span><span className="num text-right text-ink-900">{v}</span></div>
      ))}
    </Card>
  );
}

function FactsCard({ facts, p, className }: { facts: Facts; p: Pack; className?: string }) {
  const [loc, setLoc] = useState(0);
  const L = facts.locations[loc];
  return (
    <Card className={className} pad={false} title={<Title t="Normalised risk facts & exposures" id="decision.facts" />} subtitle="Resolved value per field, its source and evidence type · click any value for all competing observations and the source document">
      <div className="grid grid-cols-12">
        <div className="col-span-12 border-r border-line p-3 lg:col-span-4">
          <SectionLabel>Submission</SectionLabel>
          {facts.account.map((f) => <FactRow key={f.field} f={f} />)}
          <SectionLabel>Classification evidence</SectionLabel>
          {p.classification.evidence.map((e) => <div key={e.obs_id} className="flex justify-between gap-2 py-0.5 text-[12px]"><EvidenceLink obsId={e.obs_id} className="truncate">{e.source}</EvidenceLink><span className="whitespace-nowrap text-ink-700">{e.class}</span></div>)}
          <div className="mt-1 text-[12px]">Governing class: <span className="font-semibold">{p.classification.label}</span></div>
        </div>
        <div className="col-span-12 p-3 lg:col-span-8">
          <div className="mb-2 flex flex-wrap gap-1">{facts.locations.map((l, i) => <button key={l.location_uid} onClick={() => setLoc(i)} className={cx('rounded-md border px-2 py-1 text-[12px]', i === loc ? 'border-ink-900 bg-ink-900 text-white' : 'border-line hover:bg-ink-50')}>{l.label} · {usd(l.tiv)}</button>)}</div>
          {L && <><div className="mb-2 text-[12px] text-ink-500">{L.address} · {L.occupancy}</div><div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">{L.facts.map((f) => <FactRow key={f.field} f={f} />)}</div></>}
        </div>
      </div>
    </Card>
  );
}

function FactRow({ f }: { f: Facts['account'][number] }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-line/70 py-1 text-[12px]">
      <span className="text-ink-500">{f.label}</span>
      <span className="flex min-w-0 items-center gap-1.5">
        {f.conflict && <AlertTriangle className="size-3 text-high" aria-label="sources disagree" />}
        <EvidenceLink obsId={f.obs_id} className="num max-w-[240px] truncate text-right text-ink-900">{f.value}</EvidenceLink>
        <ObsTypeChip t={f.obs_type as ObsType} />
        {f.sources > 1 && <span className="text-[10.5px] text-ink-400">{f.sources} src</span>}
      </span>
    </div>
  );
}

function Guidelines({ p, className }: { p: Pack; className?: string }) {
  const shown = p.guidelines.filter((g) => g.result !== 'N/A');
  return (
    <Card className={className} pad={false} title={<Title t="Applicable guidelines & appetite" id="decision.guidelines" />} subtitle="Rules evaluated on the pack, with citations to the carrier's guidelines and NB standards">
      <table className="dt"><thead><tr><th>Rule</th><th>Subject</th><th>Result</th><th>Citation</th></tr></thead>
        <tbody>{shown.map((g, i) => (
          <tr key={i}><td><div className="mono text-[11.5px] font-semibold">{g.rule_id}</div><div className="text-[11.5px] text-ink-500">{g.title}</div></td><td className="max-w-[180px] truncate text-[12px]">{g.subject}</td>
            <td><Badge tone={g.result === 'PASS' ? 'ok' : g.result === 'DECLINE' ? 'crit' : 'high'}>{g.result === 'PASS' ? 'Pass' : g.result.replace('_', ' ').toLowerCase()}</Badge></td><td><Cite c={g.citation} /></td></tr>
        ))}</tbody></table>
    </Card>
  );
}

function PortfolioCard({ p, className }: { p: Pack; className?: string }) {
  return (
    <Card className={className} title={<Title t="Portfolio context" id="decision.portfolio_case" />} subtitle="1-in-250 PML against zone capacity · in-force book + bound new business">
      {p.portfolio.zones.length === 0 ? <Empty>No location in a tracked CAT zone.</Empty> : p.portfolio.zones.map((z) => (
        <div key={z.zone_id} className="mb-3">
          <div className="flex justify-between text-[12.5px]"><span className="font-medium">{z.name} <span className="text-ink-400">· {z.peril}</span></span><span className={cx('num', z.util_after > 0.9 && 'font-semibold text-crit')}>{pct(z.util_before, 1)} → {pct(z.util_after, 1)}</span></div>
          <Bar value={z.after} max={z.threshold * 1.05} marker={z.threshold * 0.9} tone={z.util_after > 0.9 ? 'crit' : 'accent'} className="mt-1" />
          <div className="mt-1 text-[11.5px] text-ink-500">Adds {usd(z.increase)} PML{z.max_line < 1 && ` · a line of ${pct(z.max_line, 0)} or less stays under the 90% threshold`}</div>
        </div>
      ))}
    </Card>
  );
}
