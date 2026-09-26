// Printable client brief for one playbook: share before or after the demo.
import { Link, useParams } from 'react-router-dom';
import { Printer, Play } from 'lucide-react';
import { usePlaybook } from '@/api/client';
import { Page, Loading, ErrorBox, Badge, MockBadge } from '@/components/ui';
import { fmtDate } from '@/lib/format';
import { productById } from '@/products';

export default function BriefPage() {
  const { pid = '' } = useParams();
  const { data: pb, isLoading, error } = usePlaybook(pid);
  if (isLoading) return <Page title="Client brief"><Loading /></Page>;
  if (error || !pb) return <Page title="Client brief"><ErrorBox error={error} /></Page>;
  const b = pb.brief;
  const prod = productById(pb.product);
  const H = ({ children }: { children: React.ReactNode }) => <h2 className="mb-1.5 mt-5 text-[11px] font-semibold uppercase tracking-[.1em] text-accent-700">{children}</h2>;
  const UL = ({ items }: { items?: string[] }) => <ul className="list-disc space-y-1 pl-5 text-[13.5px] leading-relaxed text-ink-800">{(items ?? []).map((x) => <li key={x}>{x}</li>)}</ul>;
  return (
    <Page crumbs={<Link to={`${prod.base}/pipeline`} className="hover:underline">{prod.name} · Pipeline & mocks</Link>} title="Client brief"
      actions={<div className="flex gap-2 print:hidden">
        <Link to={`${prod.base}/pipeline/journey?pb=${pb.id}`} className="inline-flex h-8 items-center gap-1.5 rounded-md border border-line-strong px-3 text-[13px] font-medium hover:bg-ink-50"><Play className="size-3.5" />Open in player</Link>
        <button onClick={() => window.print()} className="inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white hover:bg-ink-800"><Printer className="size-3.5" />Print / save PDF</button>
      </div>}>
      <article className="mx-auto max-w-[860px] rounded-[var(--radius-card)] border border-line bg-surface p-8 shadow-[var(--shadow-card)] print:border-0 print:p-0 print:shadow-none">
        <div className="text-[11px] font-semibold uppercase tracking-[.12em] text-ink-500">Anaira Underwriting Control · {prod.name} · demo workflow brief</div>
        <h1 className="mt-1 text-[22px] font-semibold leading-tight text-ink-950">{pb.title}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[13px] text-ink-600">
          <span>{pb.account_name}</span>{pb.scenario && <Badge tone="dark">{pb.scenario}</Badge>}
          <span>· {pb.steps.length} steps · fictional demo data</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1">{pb.aspects.map((a) => <Badge key={a} tone="accent">{a}</Badge>)}</div>

        <H>Who it's for</H><p className="text-[13.5px] text-ink-800">{b.audience}</p>
        <H>The business problem</H><p className="text-[13.5px] leading-relaxed text-ink-800">{b.problem}</p>
        <H>What happens</H><UL items={b.story} />
        <H>Value demonstrated</H><p className="text-[13.5px] font-medium text-ink-900">{b.value}</p>

        <H>Step by step</H>
        <table className="dt w-full">
          <thead><tr><th>#</th><th>Stage</th><th>Step</th><th>What the presenter says</th>{pb.progress > 0 && <th>Result from the last run</th>}</tr></thead>
          <tbody>{pb.steps.map((s) => (
            <tr key={s.index} className="align-top">
              <td className="num">{s.index + 1}</td><td className="mono text-[11.5px]">{s.code}</td>
              <td className="text-[12.5px] font-medium">{s.label}</td><td className="text-[12px] text-ink-700">{s.say}</td>
              {pb.progress > 0 && <td className="text-[12px] text-ink-600">{s.result ?? '—'}</td>}
            </tr>
          ))}</tbody>
        </table>

        <div className="mt-5 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div><H><span className="inline-flex items-center gap-1.5"><Badge tone="ok">REAL</Badge> The product</span></H><UL items={b.real} /></div>
          <div><H><span className="inline-flex items-center gap-1.5"><MockBadge /> Stand-ins for carrier systems</span></H><UL items={b.mocked} /></div>
        </div>

        <H>What to point at</H><UL items={b.watch} />
        <H>Live facts {pb.progress > 0 ? `(after ${pb.progress} of ${pb.steps.length} steps, demo clock ${fmtDate(pb.clock)})` : '(before the run — play it to see the outcome)'}</H>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1 md:grid-cols-2">{pb.facts.map((f) => (
          <div key={f.label} className="grid grid-cols-[170px_1fr] gap-2 border-b border-line py-1 text-[12.5px]"><dt className="text-ink-500">{f.label}</dt><dd className="num text-ink-900">{f.value}</dd></div>
        ))}</dl>
        {!!b.questions?.length && <><H>Questions to ask the client</H><UL items={b.questions} /></>}
        <p className="mt-6 border-t border-line pt-3 text-[11.5px] text-ink-500">All names, documents and figures are fictional. Every step runs against the real engine; the carrier and broker systems it talks to are stand-ins with the same connector contract as production.</p>
      </article>
    </Page>
  );
}
