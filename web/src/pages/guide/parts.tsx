// Building blocks for every product's "Start here" guide, so all three read the same way.
import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { usePlaybooks } from '@/api/client';
import { productById, PRODUCTS, type ProductId } from '@/products';

/** Every non-lifecycle playbook of a product: who it is for, what it shows, play / brief links. */
export function PlaybookTable({ product = 'renewal' }: { product?: ProductId }) {
  const base = productById(product).base;
  const { data } = usePlaybooks(product);
  const flows = (data ?? []).filter((p) => !p.id.startsWith('lifecycle-'));
  return (
    <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line bg-surface">
      <table className="dt">
        <thead><tr><th>Workflow</th><th>Best for</th><th>Shows</th><th /></tr></thead>
        <tbody>{flows.map((p) => (
          <tr key={p.id} className="align-top">
            <td><div className="text-[12.5px] font-medium text-ink-900">{p.title}</div><div className="text-[11.5px] text-ink-500">{p.scenario} · {p.account_name} · {p.steps.length} steps</div></td>
            <td className="text-[12px] text-ink-700">{p.brief?.audience}</td>
            <td className="text-[12px] text-ink-600">{p.brief?.value}</td>
            <td className="whitespace-nowrap text-[12px]">
              <Link to={`${base}/pipeline/journey?pb=${p.id}`} className="font-medium text-accent-700 hover:underline">Play</Link>{' · '}
              <Link to={`${base}/pipeline/brief/${p.id}`} className="inline-flex items-center gap-0.5 font-medium text-accent-700 hover:underline"><FileText className="size-3" />Brief</Link>
            </td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}


/** The three products on one core — shown at the top of every guide. */
export function ProductsStrip({ current }: { current: ProductId }) {
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
      {PRODUCTS.map((p) => (
        <Link key={p.id} to={`${p.base}/guide`} className={`rounded-md border p-3 transition hover:border-accent-500 ${p.id === current ? 'border-accent-500 bg-accent-50' : 'border-line bg-surface'}`}>
          <div className="flex items-center gap-2"><span className="mono rounded bg-ink-900 px-1.5 text-[10.5px] font-bold text-white">{p.number}</span><span className="text-[13px] font-semibold text-ink-950">{p.name}</span></div>
          <div className="mt-1 text-[12px] text-ink-600">{p.tagline}</div>
          {p.id === current && <div className="mt-1 text-[11px] font-medium text-accent-700">You are here</div>}
        </Link>
      ))}
    </div>
  );
}

export function S({ id, h, children }: { id: string; h: string; children: React.ReactNode }) {
  return <section id={id} className="scroll-mt-4"><h2 className="mb-2 text-[18px] font-semibold text-ink-950">{h}</h2>{children}</section>;
}
export function H3({ children }: { children: React.ReactNode }) { return <h3 className="mb-1 mt-3 text-[13px] font-semibold uppercase tracking-[.06em] text-ink-600">{children}</h3>; }
export function P({ children, className }: { children: React.ReactNode; className?: string }) { return <p className={`mb-2 text-[14px] leading-relaxed text-ink-800 ${className ?? ''}`}>{children}</p>; }
export function UL({ items }: { items: React.ReactNode[] }) { return <ul className="mb-2 list-disc space-y-1 pl-5 text-[13.5px] leading-relaxed text-ink-800">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>; }
export function Ol({ items }: { items: React.ReactNode[] }) { return <ol className="mb-2 list-decimal space-y-1 pl-5 text-[13.5px] leading-relaxed text-ink-800">{items.map((x, i) => <li key={i}>{x}</li>)}</ol>; }
export function Code({ children }: { children: React.ReactNode }) { return <code className="mono rounded bg-ink-100 px-1 py-0.5 text-[12px]">{children}</code>; }
export function L({ to, children }: { to: string; children: React.ReactNode }) { return <Link to={to} className="font-medium text-accent-700 hover:underline">{children}</Link>; }
export function Box({ title, items, tone }: { title: React.ReactNode; items: string[]; tone: 'ok' | 'mock' }) {
  return (
    <div className={`rounded-[var(--radius-card)] border p-3 ${tone === 'ok' ? 'border-[#bfe3cd] bg-ok-bg/40' : 'border-line bg-surface'}`}>
      <div className="mb-1.5 flex items-center gap-1.5 text-[13px] font-semibold text-ink-900">{title}</div>
      <UL items={items} />
    </div>
  );
}

/** Sticky table of contents with quick links, left column of every guide. */
export function GuideToc({ toc, links }: { toc: readonly (readonly [string, string])[]; links: React.ReactNode }) {
  return (
    <nav className="col-span-12 lg:col-span-3">
      <div className="sticky top-4 rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)]">
        <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.1em] text-ink-500">On this page</div>
        {toc.map(([id, l], i) => <a key={id} href={`#${id}`} className="block rounded px-2 py-1 text-[13px] text-ink-700 hover:bg-ink-50 hover:text-ink-950"><span className="num mr-1.5 text-ink-400">{i + 1}</span>{l}</a>)}
        <div className="mt-3 space-y-1.5 border-t border-line pt-3">{links}</div>
      </div>
    </nav>
  );
}

/** Glossary grid. */
export function Glossary({ items }: { items: [string, string][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
      {items.map(([t, d]) => <div key={t} className="border-b border-line py-1.5"><dt className="text-[13px] font-semibold text-ink-900">{t}</dt><dd className="text-[12.5px] text-ink-600">{d}</dd></div>)}
    </dl>
  );
}
