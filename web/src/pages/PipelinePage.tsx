import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail, MessageSquare, Globe, RefreshCw, Play } from 'lucide-react';
import { useDemoState, useMockSystems, useOutbox, usePipeline, usePipelineGroups, usePlaybooks, useSetInjection } from '@/api/client';
import { useProduct } from '@/products';
import type { PipelineStage } from '@/api/types';
import { Page, Card, Badge, MockBadge, Loading, ErrorBox, Empty, cx } from '@/components/ui';
import { fmtDate, num, titleCase } from '@/lib/format';
import { Info } from '@/help/Info';


export default function PipelinePage() {
  const product = useProduct();
  const { data: stages, isLoading, error } = usePipeline(product.id);
  const { data: GROUPS = [] } = usePipelineGroups(product.id);
  return (
    <Page title={`Pipeline & mocks · ${product.name}`} subtitle={`The ${stages?.length ?? ''}-stage lifecycle end to end · REAL = our product · MOCK = stand-in for a carrier, broker or coverholder system, behind the production connector contract`}
      actions={<Info id="pipeline.page" label="About this page" />}>
      {isLoading ? <Loading /> : error || !stages ? <ErrorBox error={error} /> : (
        <>
          <PlaybookGallery />
          <div className="mb-3 flex items-center gap-3 text-[12px] text-ink-500">
            <span className="flex items-center gap-1.5"><Badge tone="ok">REAL</Badge>{stages.filter((s) => s.mode === 'REAL').length}</span>
            {stages.some((s) => s.mode === 'BASIC') && <span className="flex items-center gap-1.5"><Badge tone="info">BASIC</Badge>{stages.filter((s) => s.mode === 'BASIC').length}</span>}
            <span className="flex items-center gap-1.5"><MockBadge />{stages.filter((s) => s.mode === 'MOCK').length}</span>
            <span className="ml-auto flex items-center gap-1"><RefreshCw className="size-3" />The last stage feeds outcomes back into the first</span>
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
            {GROUPS.map((g, gi) => (
              <div key={g} className="relative">
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[.06em] text-ink-700">{g}</span>
                  {gi < GROUPS.length - 1 && <ArrowRight className="hidden size-3.5 text-ink-300 lg:block" />}
                </div>
                <div className="space-y-2">
                  {stages.filter((s) => s.group === g).map((s) => <StageCard key={s.code} s={s} />)}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-5 grid grid-cols-12 gap-4">
            <MockConsole className="col-span-12 xl:col-span-7" />
            <Outbox className="col-span-12 xl:col-span-5" />
          </div>
        </>
      )}
    </Page>
  );
}

function StageCard({ s }: { s: PipelineStage }) {
  const product = useProduct();
  return (
    <Link to={product.to(`/pipeline/${s.code}`)} className={cx('group block rounded-[var(--radius-card)] border bg-surface p-3 shadow-[var(--shadow-card)] transition hover:-translate-y-px hover:border-accent-500 hover:shadow-[var(--shadow-pop)]', s.mode === 'REAL' ? 'border-accent-100' : 'border-line')}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={cx('mono flex size-6 items-center justify-center rounded-md text-[10.5px] font-semibold', s.mode === 'REAL' ? 'bg-accent-600 text-white' : 'bg-ink-100 text-ink-700')}>{s.code}</span>
          <span className="text-[13px] font-semibold text-ink-900">{s.name}</span>
        </div>
        {s.mode === 'MOCK' ? <MockBadge /> : <Badge tone={s.mode === 'REAL' ? 'ok' : 'info'}>{s.mode}</Badge>}
      </div>
      <div className="mt-1 text-[12px] font-medium text-ink-700">{s.component}{s.port && <span className="mono ml-1 text-[10.5px] font-normal text-ink-400">· {s.port}</span>}</div>
      <div className="mt-0.5 text-[11.5px] leading-snug text-ink-500">{s.description}</div>
      {s.counts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 border-t border-line pt-1.5">
          {s.counts.map((c) => <span key={c.label} className="text-[11px] text-ink-500"><span className="num font-semibold text-ink-900">{num(c.value)}</span> {c.label}</span>)}
        </div>
      )}
      <div className="mt-2 flex items-center gap-1 text-[11.5px] font-medium text-accent-700 opacity-70 group-hover:opacity-100">Open workspace <ArrowRight className="size-3" /></div>
    </Link>
  );
}

function MockConsole({ className }: { className?: string }) {
  const product = useProduct();
  const { data, isLoading } = useMockSystems(product.id);
  const { data: demo } = useDemoState();
  const setInj = useSetInjection();
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">Mock systems console<Info id="pipeline.mocks" /></span>} subtitle="Same connector contract as production — swapping in the real system is configuration">
      {isLoading ? <Loading /> : (
        <table className="dt">
          <thead><tr><th>Port</th><th>Mock</th><th>Stands in for</th><th>Status</th><th className="r">Records</th><th>Last sync</th></tr></thead>
          <tbody>
            {data?.map((m) => (
              <tr key={m.port}>
                <td className="mono text-[11.5px] font-medium">{m.port}</td><td>{m.name}</td><td className="text-ink-600">{m.stands_in_for}</td>
                <td><span className="flex items-center gap-1.5 text-[12px] text-ok"><span className="size-1.5 rounded-full bg-ok" />{m.status}</span></td>
                <td className="num r">{num(m.records)}</td><td className="num text-[12px] text-ink-500">{new Date(m.last_sync).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {demo && product.id === 'renewal' && (
        <div className="border-t border-line px-4 py-3">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">Fault injection</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(demo.injections).map(([k, v]) => (
              <label key={k} className={cx('flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1 text-[12px]', v ? 'border-[#efd98f] bg-med-bg text-[#8a6100]' : 'border-line-strong text-ink-600')}>
                <input type="checkbox" checked={v} disabled={setInj.isPending} onChange={(e) => setInj.mutate({ [k]: e.target.checked })} className="accent-[var(--color-med)]" />
                {titleCase(k)}
              </label>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function Outbox({ className }: { className?: string }) {
  const product = useProduct();
  const { data, isLoading } = useOutbox(product.id);
  const [open, setOpen] = useState<string | null>(null);
  const Icon = { email: Mail, broker_portal: Globe, in_app: MessageSquare };
  return (
    <Card className={className} pad={false} title={<span className="inline-flex items-center gap-1.5">Mock outbox<Info id="pipeline.outbox" /></span>} subtitle="Broker data requests, referral notifications, notice alerts — nothing leaves the demo tenant">
      {isLoading ? <Loading /> : !data?.length ? <Empty>No messages.</Empty> : (
        <div className="max-h-[520px] divide-y divide-line overflow-y-auto">
          {data.map((m) => {
            const I = Icon[m.channel];
            return (
              <button key={m.message_id} onClick={() => setOpen(open === m.message_id ? null : m.message_id)} className="block w-full px-4 py-2.5 text-left hover:bg-ink-50">
                <div className="flex items-center gap-2">
                  <I className="size-3.5 shrink-0 text-ink-400" />
                  <span className="truncate text-[12.5px] font-medium text-ink-900">{m.subject}</span>
                  <span className="num ml-auto shrink-0 text-[11px] text-ink-400">{fmtDate(m.at.slice(0, 10))}</span>
                </div>
                <div className="ml-5 truncate text-[11.5px] text-ink-500">to {m.to} · {m.channel.replace('_', ' ')}</div>
                {open === m.message_id && (
                  <div className="ml-5 mt-1.5 whitespace-pre-wrap rounded bg-ink-50 p-2 text-[12px] text-ink-700">
                    {m.body}
                    {(m.href || m.account_id) && <div className="mt-1"><Link onClick={(e) => e.stopPropagation()} to={m.href ?? `/accounts/${m.account_id}`} className="text-accent-700 hover:underline">Open →</Link></div>}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function PlaybookGallery() {
  const product = useProduct();
  const { data } = usePlaybooks(product.id);
  const flows = (data ?? []).filter((p) => !p.id.startsWith('lifecycle-'));
  const life = (data ?? []).find((p) => p.id.startsWith('lifecycle-'));
  return (
    <div className="mb-5">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1.5 text-[14px] font-semibold text-ink-950">Workflow playbooks<Info id="pipeline.playbooks" /></div>
          <div className="text-[12px] text-ink-500">Each walks one account through the pipeline against the real engine and the mocks · autoplay with pause, resume, stop and single-step</div>
        </div>
        {life && <Link to={product.to(`/pipeline/journey?pb=${life.id}`)} className="text-[12px] font-medium text-accent-700 hover:underline">All {life.steps.length} stages for any {product.subjectLabel.toLowerCase()} →</Link>}
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {flows.map((p) => (
          <div key={p.id} className="group flex flex-col rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)] transition hover:border-accent-500">
            <div className="flex items-start justify-between gap-2">
              <div className="text-[13px] font-semibold leading-snug text-ink-950">{p.title}</div>
              <Badge tone="dark">{p.scenario}</Badge>
            </div>
            <div className="mt-0.5 text-[12px] text-ink-500">{p.account_name} · {p.steps.length} steps · stages {[...new Set(p.steps.map((s) => s.code))].sort().join(' ')}</div>
            {p.brief?.problem && <div className="mt-2 text-[12px] leading-snug text-ink-700">{p.brief.problem}</div>}
            {p.brief?.audience && <div className="mt-1 text-[11.5px] text-ink-500">For: {p.brief.audience}</div>}
            <div className="mt-2 flex flex-wrap gap-1">{p.aspects.map((a) => <Badge key={a} tone="accent">{a}</Badge>)}</div>
            <div className="mt-auto flex gap-2 pt-3">
              <Link to={product.to(`/pipeline/journey?pb=${p.id}&autoplay=1`)} className="inline-flex h-7 items-center gap-1.5 rounded-md bg-accent-600 px-2.5 text-[12px] font-semibold text-white hover:bg-accent-700"><Play className="size-3" />Autoplay</Link>
              <Link to={product.to(`/pipeline/journey?pb=${p.id}`)} className="inline-flex h-7 items-center rounded-md border border-line-strong px-2.5 text-[12px] font-medium text-ink-800 hover:bg-ink-50">Step through</Link>
              <Link to={product.to(`/pipeline/brief/${p.id}`)} className="ml-auto inline-flex h-7 items-center rounded-md px-1.5 text-[12px] font-medium text-accent-700 hover:underline">Client brief</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
