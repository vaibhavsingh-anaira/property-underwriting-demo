// Right slide-over for evidence: an observation (with all competing observations for the field,
// resolution policy, conflict flag, and an inline source preview at the anchor) or a finding.
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, Crown, AlertTriangle, Scale, Maximize2, Database, ShieldCheck, ShieldAlert, ChevronRight, FileText } from 'lucide-react';
import type { Anchor, Finding, Observation } from '@/api/types';
import { useDocument, useObservation } from '@/api/client';
import { useEvidence } from '@/components/evidence';
import { Badge, Button, cx, ErrorBox, Loading, MockBadge, ObsTypeChip, SeverityPill } from '@/components/ui';
import { fmtDate, usd } from '@/lib/format';
import { DocumentViewer, ConfidenceBar } from '@/viewers/DocumentViewer';
import { anchorSummary } from '@/viewers/util';
import { Info } from '@/help/Info';

export function EvidenceDrawer() {
  const ev = useEvidence();
  const t = ev.target;
  useEffect(() => {
    if (!t) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !ev.doc) ev.closeDrawer(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [t, ev]);
  if (!t) return null;
  return (
    <div className="fixed inset-0 z-40">
      <div className="anim-fade absolute inset-0 bg-ink-950/20" onClick={ev.closeDrawer} />
      <aside className="anim-slide-in absolute right-0 top-0 flex h-full w-[560px] max-w-[100vw] flex-col border-l border-line bg-surface shadow-[var(--shadow-pop)]">
        <div className="flex h-11 shrink-0 items-center justify-between border-b border-line px-4">
          <div className="flex items-center gap-2 text-[12px] font-medium uppercase tracking-[.05em] text-ink-500">
            {t.kind === 'obs' ? <><Database className="size-3.5" />Evidence</> : <><Scale className="size-3.5" />Finding</>}
            <Info id="app.evidence" className="normal-case tracking-normal" />
          </div>
          <button onClick={ev.closeDrawer} title="Close (Esc)" className="rounded-md p-1 text-ink-500 hover:bg-ink-100 hover:text-ink-900"><X className="size-4" /></button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {t.kind === 'obs' ? <ObsPanel key={t.obsId} obsId={t.obsId} /> : <FindingPanel key={t.finding.finding_id} f={t.finding} />}
        </div>
      </aside>
    </div>
  );
}

// ------------------------------------------------------------------ observation
function ObsPanel({ obsId }: { obsId: string }) {
  const { data, error, isLoading } = useObservation(obsId);
  const [selId, setSelId] = useState(obsId);
  if (error) return <div className="p-4"><ErrorBox error={error} /></div>;
  if (isLoading || !data) return <Loading label="Loading evidence…" />;
  const { observation, field } = data;
  const all = field.observations.length ? field.observations : [observation];
  const sel = all.find((o) => o.obs_id === selId) ?? observation;
  const winnerId = field.resolved_obs_id;
  const winner = all.find((o) => o.obs_id === winnerId);
  const sorted = [...all].sort((a, b) => Number(b.obs_id === winnerId) - Number(a.obs_id === winnerId) || b.recorded_at.localeCompare(a.recorded_at));

  return (
    <div className="pb-6">
      <div className="px-5 pb-4 pt-4">
        <div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">{field.label}</div>
        <div className="mt-0.5 text-[13px] text-ink-600">{observation.subject_label}</div>
        <div className="mt-2 flex items-center gap-3">
          <span className="num text-[28px] font-semibold leading-none tracking-[-0.02em] text-ink-950">{field.value_display}</span>
          {winner && <ObsTypeChip t={winner.obs_type} withLabel />}
        </div>
        <div className="mt-3 rounded-lg border border-line bg-ink-50 px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-ink-600"><Scale className="size-3.5" />Resolution policy <span className="mono text-ink-500">{field.policy}</span></div>
          <div className="mt-1 text-[12.5px] leading-snug text-ink-800">{field.policy_explainer}</div>
        </div>
        {field.conflict && (
          <div className="mt-2 flex items-start gap-2 rounded-lg border border-[#f5d2b8] bg-high-bg px-3 py-2 text-[12.5px] text-high">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <div><span className="font-semibold">Conflicting sources.</span> <span className="text-ink-700">{new Set(all.map((o) => o.value_display)).size} distinct values across {all.length} observations — the winner is chosen by policy, not recency.</span></div>
          </div>
        )}
      </div>

      <div className="border-y border-line bg-ink-50/60 px-5 py-1.5 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">All observations ({all.length})</div>
      <div className="divide-y divide-line">
        {sorted.map((o) => <ObsRow key={o.obs_id} o={o} winner={o.obs_id === winnerId} selected={o.obs_id === sel.obs_id} onClick={() => setSelId(o.obs_id)} />)}
      </div>

      <div className="px-5 pt-4">
        <SourcePreview o={sel} />
      </div>
    </div>
  );
}

function ObsRow({ o, winner, selected, onClick }: { o: Observation; winner: boolean; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={cx('relative flex w-full items-start gap-3 px-5 py-2.5 text-left transition-colors', selected ? 'bg-accent-50' : 'hover:bg-ink-50')}>
      {selected && <span className="absolute inset-y-0 left-0 w-[3px] bg-accent-500" />}
      <span className="pt-0.5"><ObsTypeChip t={o.obs_type} /></span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className={cx('num text-[14px] font-semibold', winner ? 'text-ink-950' : 'text-ink-700')}>{o.value_display}{o.unit ? <span className="ml-1 text-[11px] font-normal text-ink-500">{o.unit}</span> : null}</span>
          <span className="flex shrink-0 items-center gap-1.5">
            {winner && <Badge tone="accent"><Crown className="size-3" />Winner</Badge>}
            {o.verification_status === 'VERIFIED' && <Badge tone="ok"><ShieldCheck className="size-3" />Verified</Badge>}
            {o.verification_status === 'DISPUTED' && <Badge tone="high"><ShieldAlert className="size-3" />Disputed</Badge>}
            {o.verification_status === 'SUPERSEDED' && <Badge>Superseded</Badge>}
          </span>
        </span>
        <span className="mt-0.5 block truncate text-[12px] text-ink-700">{o.source_label}<span className="text-ink-400"> · {o.source_family}</span></span>
        <span className="mt-1 flex items-center gap-3 text-[11px] text-ink-500">
          <ConfidenceBar value={o.confidence} />
          <span className="num">Recorded {fmtDate(o.recorded_at)}</span>
          <span className="truncate text-ink-400">{anchorSummary(o.anchor)}</span>
        </span>
      </span>
    </button>
  );
}

function SourcePreview({ o }: { o: Observation }) {
  const ev = useEvidence();
  const a = o.anchor;
  const docId = a?.doc_id ?? null;
  const { data: doc } = useDocument(docId);
  if (!a) return <div className="rounded-lg border border-dashed border-line-strong px-4 py-5 text-center text-[12.5px] text-ink-500">No source anchor — {o.obs_type === 'D' ? 'derived by the platform from other observations' : 'value recorded without a document reference'}.</div>;
  if (!docId) return <RecordCard o={o} a={a} />;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">Source · {anchorSummary(a)}</div>
          <div className="mt-0.5 flex items-center gap-1.5 truncate text-[13px] font-medium text-ink-900"><FileText className="size-3.5 shrink-0 text-ink-400" /><span className="truncate">{doc?.title ?? o.source_label}</span></div>
        </div>
        <Button size="sm" icon={<Maximize2 className="size-3.5" />} onClick={() => ev.openDoc(docId, a)}>Open full document</Button>
      </div>
      {a.text && <div className="mb-2 rounded-md border-l-2 border-accent-500 bg-accent-50 px-3 py-1.5 text-[12.5px] italic text-ink-700">“{a.text}”</div>}
      <div className="overflow-hidden rounded-lg border border-line">
        <DocumentViewer key={o.obs_id} docId={docId} anchor={a} compact height={420} />
      </div>
    </div>
  );
}

function RecordCard({ o, a }: { o: Observation; a: Anchor }) {
  const sys = a.system ?? o.vendor ?? (a.kind === 'vendor' ? 'Vendor' : 'System');
  const rows: [string, unknown][] = [
    ['system', sys], ['record_id', a.record_id], ['path', a.path], ['field', o.field_code], ['value', o.value],
    ['vendor', o.vendor], ['model_version', o.model_version], ['valid_from', o.valid_from], ['recorded_at', o.recorded_at],
  ];
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">
        <Database className="size-3.5" />{a.kind === 'vendor' ? 'Vendor payload' : 'System record'}
        {String(sys).includes('(mock)') && <MockBadge />}
      </div>
      <div className="mono overflow-x-auto rounded-lg border border-line bg-ink-950 px-4 py-3 text-[12px] leading-[20px] text-ink-200">
        <div className="text-ink-500">{'{'}</div>
        {rows.filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v], i, arr) => (
          <div key={k} className="pl-4">
            <span className="text-accent-100">"{k}"</span><span className="text-ink-500">: </span>
            <span className={typeof v === 'number' ? 'text-[#9ab8ff]' : typeof v === 'boolean' ? 'text-[#c9a7ff]' : 'text-[#a7e3bf]'}>{typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}</span>
            {i < arr.length - 1 && <span className="text-ink-500">,</span>}
          </div>
        ))}
        <div className="text-ink-500">{'}'}</div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ finding
function FindingPanel({ f }: { f: Finding }) {
  const ev = useEvidence();
  return (
    <div className="pb-6">
      <div className="px-5 pb-4 pt-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityPill s={f.severity} />
          <Badge tone="dark">{f.outcome.replace(/_/g, ' ')}</Badge>
          <Badge>{f.status}</Badge>
          {f.material && <Badge tone="crit">Material</Badge>}
        </div>
        <h2 className="mt-2 text-[17px] font-semibold leading-snug tracking-[-0.01em] text-ink-950">{f.title}</h2>
        <div className="mt-0.5 text-[12.5px] text-ink-500">{f.subject_label}</div>
        {f.description && <p className="mt-2 text-[13px] leading-relaxed text-ink-700">{f.description}</p>}

        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-[#f6c5cc] bg-crit-bg/60 px-3 py-2">
            <div className="text-[10.5px] font-medium uppercase tracking-[.05em] text-crit">Observed</div>
            <div className="num mt-0.5 text-[14px] font-semibold text-ink-950">{f.observed}</div>
          </div>
          <div className="rounded-lg border border-line bg-ink-50 px-3 py-2">
            <div className="text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-500">Expected</div>
            <div className="num mt-0.5 text-[14px] font-semibold text-ink-950">{f.expected}</div>
          </div>
        </div>

        <div className="mt-3 divide-y divide-line rounded-lg border border-line text-[12.5px]">
          <Row k="Impact"><span className="num font-semibold text-ink-950">{usd(f.impact_usd)}</span><span className="ml-1.5 text-ink-500">{f.impact_method}</span></Row>
          <Row k="Confidence"><ConfidenceBar value={f.confidence} /></Row>
          <Row k="Rule"><Link to={`/rules/${f.rule_id}`} className="mono text-[12px] text-accent-700 hover:underline">{f.rule_id}</Link><span className="ml-1 text-ink-500">v{f.rule_version}</span></Row>
          <Row k="Source">{f.source}</Row>
          <Row k="Raised"><span className="num">{fmtDate(f.created_at)}</span><span className="ml-1.5 text-ink-500">· pass {f.pass}</span></Row>
          {f.disposition && <Row k="Disposition">{f.disposition.decision} · {f.disposition.reason_code.replace(/_/g, ' ')} <span className="text-ink-500">— {f.disposition.actor}, {fmtDate(f.disposition.at)}</span></Row>}
        </div>

        {f.critique && (
          <div className={cx('mt-3 rounded-lg border px-3 py-2 text-[12.5px]', f.critique.verdict === 'UPHELD' ? 'border-[#bfe3cd] bg-ok-bg' : 'border-[#efdf9f] bg-med-bg')}>
            <div className={cx('flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[.05em]', f.critique.verdict === 'UPHELD' ? 'text-ok' : 'text-med')}>
              {f.critique.verdict === 'UPHELD' ? <ShieldCheck className="size-3.5" /> : <ShieldAlert className="size-3.5" />}Critique · {f.critique.verdict.toLowerCase()}
            </div>
            <div className="mt-0.5 text-ink-800">{f.critique.note}</div>
          </div>
        )}
      </div>

      <div className="border-y border-line bg-ink-50/60 px-5 py-1.5 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">Evidence ({f.evidence_obs_ids.length + f.conflicting_obs_ids.length})</div>
      <div className="divide-y divide-line">
        {f.evidence_obs_ids.map((id) => <EvidenceRow key={id} obsId={id} onOpen={() => ev.openObs(id)} />)}
        {f.conflicting_obs_ids.map((id) => <EvidenceRow key={'c' + id} obsId={id} conflict onOpen={() => ev.openObs(id)} />)}
        {f.evidence_obs_ids.length + f.conflicting_obs_ids.length === 0 && <div className="px-5 py-4 text-[12.5px] text-ink-500">No linked observations.</div>}
      </div>
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return <div className="flex items-baseline gap-3 px-3 py-1.5"><span className="w-[84px] shrink-0 text-[11.5px] text-ink-500">{k}</span><span className="min-w-0 flex-1 text-ink-900">{children}</span></div>;
}

function EvidenceRow({ obsId, conflict, onOpen }: { obsId: string; conflict?: boolean; onOpen: () => void }) {
  const { data, error } = useObservation(obsId);
  const o = data?.observation;
  return (
    <button onClick={onOpen} className="group flex w-full items-center gap-3 px-5 py-2.5 text-left hover:bg-ink-50">
      {o ? <ObsTypeChip t={o.obs_type} /> : <span className="size-[18px] rounded bg-ink-100" />}
      <span className="min-w-0 flex-1">
        {error ? <span className="text-[12px] text-crit">Could not load {obsId}</span> : !o ? <span className="block h-3 w-40 animate-pulse rounded bg-ink-100" /> : (
          <>
            <span className="flex items-baseline gap-2">
              <span className="truncate text-[12.5px] text-ink-600">{o.field_label}</span>
              <span className="num text-[13px] font-semibold text-ink-950">{o.value_display}</span>
              {conflict && <Badge tone="high">conflict</Badge>}
            </span>
            <span className="block truncate text-[11.5px] text-ink-500">{o.subject_label} · {o.source_label} · {anchorSummary(o.anchor)}</span>
          </>
        )}
      </span>
      <ChevronRight className="size-4 shrink-0 text-ink-300 group-hover:text-ink-600" />
    </button>
  );
}
