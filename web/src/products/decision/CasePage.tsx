// The case page: Stage 1 decision pack, Stage 2 intended action and assurance, human final decision, outcome.
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronRight, Clock, FastForward, FileText } from 'lucide-react';
import { useAdvance } from '@/api/client';
import { Tabs, Loading, ErrorBox, Badge, Button, Card, Empty, Segmented, MockBadge, cx } from '@/components/ui';
import { usd, pct, fmtDate } from '@/lib/format';
import { useEvidence } from '@/components/evidence';
import { DocumentViewer } from '@/viewers/DocumentViewer';
import { FormatIcon } from '@/pages/common';
import { Info } from '@/help/Info';
import { DRAFT_LABEL, STAGES, STATUS_LABEL, useCase, type CaseDetail } from './api';
import { StageDots, VerdictBadge } from './parts';
import PackTab from './PackTab';
import ActionTab from './ActionTab';
import DecisionTab from './DecisionTab';

type TabKey = 'pack' | 'action' | 'decision' | 'documents' | 'timeline';

export default function CasePage() {
  const { id } = useParams();
  const { data: c, isLoading, error } = useCase(id);
  const [tab, setTab] = useState<TabKey | null>(null);
  if (isLoading) return <Loading label="Loading case…" />;
  if (error || !c) return <div className="p-6"><ErrorBox error={error ?? 'Case not found'} /></div>;
  const t: TabKey = tab ?? (c.decision ? 'decision' : c.actions.length ? 'action' : 'pack');
  return (
    <div className="min-h-full">
      <Header c={c} />
      <div className="sticky top-0 z-10 border-b border-line bg-surface/95 px-6 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center gap-4">
          <Tabs className="border-b-0" value={t} onChange={setTab} tabs={[
            { key: 'pack', label: 'Stage 1 · Decision pack', count: c.pack ? c.pack.factors.length : undefined },
            { key: 'action', label: 'Stage 2 · Intended action & assurance', count: c.assurances.length || undefined },
            { key: 'decision', label: 'Final decision & outcome' },
            { key: 'documents', label: 'Documents', count: c.documents.length },
            { key: 'timeline', label: 'Timeline' },
          ]} />
        </div>
      </div>
      <div className="mx-auto w-full max-w-[1600px] px-6 py-5">
        {!c.received ? <NotYet c={c} /> : (
          <>
            {t === 'pack' && c.pack && <PackTab c={c} onAct={() => setTab('action')} />}
            {t === 'action' && <ActionTab c={c} />}
            {t === 'decision' && <DecisionTab c={c} />}
            {t === 'documents' && <Docs c={c} />}
            {t === 'timeline' && <Timeline c={c} />}
          </>
        )}
      </div>
    </div>
  );
}

function Header({ c }: { c: CaseDetail }) {
  const adv = useAdvance();
  const next = c.pending[0];
  return (
    <div className="border-b border-line bg-surface px-6 pb-4 pt-4">
      <div className="mx-auto max-w-[1600px]">
        <div className="mb-1 flex items-center gap-1 text-[12px] text-ink-500"><Link to="/decision/cases" className="hover:text-ink-800">Case queue</Link><ChevronRight className="size-3" /><span className="text-ink-700">{c.short}</span></div>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-[22px] font-semibold tracking-[-0.015em] text-ink-950">{c.insured}</h1>
              <Badge tone={c.status === 'BOUND' ? 'dark' : c.status === 'DECLINED' || c.status === 'HOLD' ? 'crit' : 'neutral'}>{STATUS_LABEL[c.status] ?? c.status}</Badge>
              {c.scenario && <span className="flex items-center gap-1.5"><Badge tone="dark">{c.scenario}</Badge><span className="text-[12px] text-ink-600">{c.title}</span></span>}
              <Info id="decision.case" label="About this page" />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[12px] text-ink-600">
              <span>New business · effective <span className="num text-ink-900">{fmtDate(c.effective)}</span></span>
              <span>Broker <span className="text-ink-900">{c.broker}</span> <span className="text-ink-400">({c.contact})</span></span>
              <span>UW <span className="text-ink-900">{c.underwriter}</span> · L{c.uw_level}</span>
              <span>{c.segment} · {c.class_label ?? '—'} · {c.state}</span>
              {c.tiv !== null && <span>TIV <span className="num text-ink-900">{usd(c.tiv)}</span></span>}
              {c.quote_by && <span>Terms needed by <span className="num text-ink-900">{fmtDate(c.quote_by)}</span></span>}
            </div>
            <div className="mt-3 flex items-center gap-3"><StageDots n={c.stage} /><span className="text-[12px] text-ink-600">Stage {c.stage || 0} of 10{c.stage ? ` · ${STAGES[c.stage - 1]}` : ''}</span></div>
          </div>
          <div className="flex shrink-0 items-stretch gap-3">
            <Box label="Technical">{c.technical ? <span className="num text-[15px] font-semibold">{usd(c.technical, { compact: false })}</span> : '—'}</Box>
            <Box label="Draft">{c.draft ? <span className="text-[13px] font-medium">{DRAFT_LABEL[c.draft]}</span> : '—'}</Box>
            <Box label="Intended">{c.premium ? <><span className="num text-[15px] font-semibold">{usd(c.premium, { compact: false })}</span> <span className="num text-[11px] text-ink-500">{pct(c.deviation, 1, true)}</span></> : '—'}</Box>
            <Box label="Verdict"><VerdictBadge v={c.verdict} large /></Box>
          </div>
        </div>
        {next && (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-line bg-ink-50 px-3 py-1.5 text-[12px]">
            <Clock className="size-3.5 text-ink-500" /><span className="text-ink-700">Next for this case: <span className="font-medium text-ink-900">{next.title}</span> on <span className="num">{fmtDate(next.date)}</span></span><MockBadge />
            <Button size="sm" className="ml-auto" icon={<FastForward className="size-3.5" />} loading={adv.isPending} onClick={() => adv.mutate({ to: next.date })}>Advance clock to {fmtDate(next.date)}</Button>
          </div>
        )}
      </div>
    </div>
  );
}

function Box({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="rounded-lg border border-line px-3 py-2"><div className="mb-0.5 text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-500">{label}</div>{children}</div>;
}

function NotYet({ c }: { c: CaseDetail }) {
  return <Card><Empty>The broker's submission arrives on {fmtDate(c.expected)} (mailbox stub). Advance the demo clock to receive it; it is parsed and the decision pack prepared automatically.</Empty></Card>;
}

function Docs({ c }: { c: CaseDetail }) {
  const [sel, setSel] = useState<string | null>(c.documents[0]?.doc_id ?? null);
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12 lg:col-span-4" pad={false} title={<span className="inline-flex items-center gap-1.5">{c.documents.length} documents<Info id="decision.documents" /></span>} subtitle="Submission, broker replies, vendor stubs, policy admin">
        <div className="max-h-[calc(100vh-260px)] overflow-y-auto py-1">
          {c.documents.map((d) => (
            <button key={d.doc_id} onClick={() => setSel(d.doc_id)} className={cx('flex w-full items-center gap-2 px-3 py-1.5 text-left', sel === d.doc_id ? 'bg-accent-50' : 'hover:bg-ink-50')}>
              <FormatIcon f={d.format} />
              <span className="min-w-0 flex-1"><span className="block truncate text-[12.5px] text-ink-900">{d.title}</span><span className="block truncate text-[10.5px] text-ink-400">{d.doc_type} · {fmtDate(d.received_at)} · {d.source_channel}</span></span>
              {d.source_channel.includes('mock') && <MockBadge />}
              {d.extraction?.status === 'EXTRACTED' && <Badge tone="accent">{d.extraction.fields}</Badge>}
            </button>
          ))}
        </div>
      </Card>
      <div className="col-span-12 overflow-hidden rounded-[var(--radius-card)] border border-line lg:col-span-8">{sel ? <DocumentViewer key={sel} docId={sel} height="calc(100vh - 200px)" /> : <Empty>Select a document.</Empty>}</div>
    </div>
  );
}

function Timeline({ c }: { c: CaseDetail }) {
  const ev = useEvidence();
  const [k, setK] = useState<'all' | 'user' | 'engine' | 'mock' | 'document'>('all');
  const evs = c.timeline.filter((e) => k === 'all' || e.kind === k);
  return (
    <Card title={<span className="inline-flex items-center gap-1.5">Timeline & audit trail<Info id="decision.timeline" /></span>} subtitle="Every document, engine run, stand-in event and human decision, with its stage"
      actions={<Segmented value={k} onChange={setK} options={[{ key: 'all', label: 'All' }, { key: 'user', label: 'Human' }, { key: 'engine', label: 'Engine' }, { key: 'mock', label: 'Stand-ins' }, { key: 'document', label: 'Documents' }]} />}>
      <ol className="relative ml-3 border-l border-line">
        {evs.map((e) => (
          <li key={e.event_id} className="relative mb-3 ml-5">
            <span className={cx('absolute -left-[27px] top-1 size-3 rounded-full ring-4 ring-surface', e.kind === 'user' ? 'bg-ink-800' : e.kind === 'engine' ? 'bg-accent-600' : e.kind === 'mock' ? 'bg-med' : 'bg-info')} />
            <div className="flex flex-wrap items-center gap-2 text-[12px]"><span className="num text-ink-500">{fmtDate(e.date)}</span><span className="mono rounded bg-ink-100 px-1.5 text-[10.5px] font-semibold">{e.stage} · {STAGES[Number(e.stage) - 1]}</span>{e.kind === 'mock' && <MockBadge />}<span className="text-ink-500">{e.actor}</span></div>
            <div className="text-[13px] font-medium text-ink-900">{e.title}</div>
            <div className="text-[12.5px] text-ink-600">{e.detail}</div>
            {e.doc_id && <button onClick={() => ev.openDoc(e.doc_id!)} className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-info hover:underline"><FileText className="size-3" />document</button>}
          </li>
        ))}
      </ol>
    </Card>
  );
}
