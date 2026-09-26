import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LayoutGrid, List, Search, X } from 'lucide-react';
import { useDocuments } from '@/api/client';
import type { DocumentMeta } from '@/api/types';
import { Page, Card, Input, Segmented, Badge, Loading, ErrorBox, Empty, MockBadge, cx } from '@/components/ui';
import { bytes, fmtDate, pct } from '@/lib/format';
import { FormatIcon, SectionLabel } from './common';
import { Info } from '@/help/Info';

type FacetKey = 'doc_type' | 'format' | 'source_channel' | 'account_name' | 'term';
const FACETS: { k: FacetKey; label: string }[] = [
  { k: 'doc_type', label: 'Type' }, { k: 'format', label: 'Format' }, { k: 'source_channel', label: 'Source channel' }, { k: 'term', label: 'Term' }, { k: 'account_name', label: 'Account' },
];
const val = (d: DocumentMeta, k: FacetKey) => (d[k] ?? (k === 'account_name' ? 'Reference / carrier' : '—')) as string;

export default function DocumentsPage() {
  const { data, isLoading, error } = useDocuments();
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [view, setView] = useState<'list' | 'grid'>('list');
  const [sel, setSel] = useState<Partial<Record<FacetKey, string>>>({});
  const filtered = useMemo(() => (data ?? []).filter((d) =>
    FACETS.every((f) => !sel[f.k] || val(d, f.k) === sel[f.k]) && (!q || `${d.title} ${d.filename} ${d.account_name ?? ''}`.toLowerCase().includes(q.toLowerCase()))), [data, sel, q]);
  const counts = (k: FacetKey) => {
    const base = (data ?? []).filter((d) => FACETS.every((f) => f.k === k || !sel[f.k] || val(d, f.k) === sel[f.k]));
    const m = new Map<string, number>(); base.forEach((d) => m.set(val(d, k), (m.get(val(d, k)) ?? 0) + 1));
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  };
  const shown = filtered.slice(0, 400);
  return (
    <Page title="Documents" subtitle={<>{data ? <span className="num">{data.length}</span> : '…'} documents across the book · every file watermarked SAMPLE · click to open with anchors and extracted fields</>}
      actions={<><Info id="documents.page" label="About this page" /><Segmented value={view} onChange={setView} options={[{ key: 'list', label: <List className="size-3.5" /> }, { key: 'grid', label: <LayoutGrid className="size-3.5" /> }]} /></>}>
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <div className="grid grid-cols-12 gap-4">
          <aside className="col-span-12 space-y-4 lg:col-span-3">
            <div className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-400" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Title, filename, account…" className="w-full pl-8" /></div>
            {FACETS.map((f) => {
              const c = counts(f.k);
              return (
                <div key={f.k}>
                  <SectionLabel right={sel[f.k] && <button onClick={() => setSel({ ...sel, [f.k]: undefined })} className="text-[11px] text-accent-700">clear</button>}>{f.label}</SectionLabel>
                  <div className={cx('space-y-0.5', f.k === 'account_name' && 'max-h-[260px] overflow-y-auto pr-1')}>
                    {c.slice(0, f.k === 'account_name' ? 200 : 14).map(([v, n]) => (
                      <button key={v} onClick={() => setSel({ ...sel, [f.k]: sel[f.k] === v ? undefined : v })}
                        className={cx('flex w-full items-center gap-2 rounded px-2 py-1 text-left text-[12px]', sel[f.k] === v ? 'bg-accent-50 font-medium text-ink-950' : 'text-ink-700 hover:bg-ink-50')}>
                        {f.k === 'format' && <FormatIcon f={v as DocumentMeta['format']} className="size-3.5" />}
                        <span className="flex-1 truncate">{f.k === 'format' ? v.toUpperCase() : v}</span><span className="num text-[11px] text-ink-400">{n}</span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </aside>
          <div className="col-span-12 lg:col-span-9">
            {Object.values(sel).some(Boolean) && (
              <div className="mb-2 flex flex-wrap gap-1.5">{Object.entries(sel).filter(([, v]) => v).map(([k, v]) => <Badge key={k} tone="accent">{v}<button onClick={() => setSel({ ...sel, [k]: undefined })}><X className="size-3" /></button></Badge>)}</div>
            )}
            {view === 'list' ? (
              <Card pad={false}>
                <table className="dt">
                  <thead><tr><th>Document</th><th>Type</th><th>Account</th><th>Term</th><th>Source</th><th>Received</th><th className="r">Size</th><th>Extraction</th></tr></thead>
                  <tbody>
                    {shown.map((d) => (
                      <tr key={d.doc_id} className="cursor-pointer" onClick={() => nav(`/documents/${d.doc_id}`)}>
                        <td className="max-w-[340px]"><div className="flex items-center gap-2"><FormatIcon f={d.format} /><div className="min-w-0"><div className="truncate font-medium text-ink-900">{d.title}</div><div className="mono truncate text-[10.5px] text-ink-400">{d.filename}</div></div></div></td>
                        <td className="text-ink-700">{d.doc_type}</td>
                        <td className="max-w-[180px] truncate">{d.account_id ? <Link onClick={(e) => e.stopPropagation()} to={`/accounts/${d.account_id}/documents`} className="text-ink-700 hover:text-accent-700">{d.account_name}</Link> : <span className="text-ink-400">Reference</span>}</td>
                        <td className="num text-ink-600">{d.term ?? '—'}</td>
                        <td className="text-[12px] text-ink-600">{d.source_channel.includes('mock') ? <MockBadge label={d.source_channel.replace(' (mock)', '')} /> : d.source_channel}</td>
                        <td className="num text-ink-600">{fmtDate(d.received_at)}</td>
                        <td className="num r text-ink-500">{bytes(d.size_bytes)}</td>
                        <td><Extraction d={d} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 && <Empty>No documents match.</Empty>}
              </Card>
            ) : (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
                {shown.map((d) => (
                  <button key={d.doc_id} onClick={() => nav(`/documents/${d.doc_id}`)} className="flex flex-col rounded-[var(--radius-card)] border border-line bg-surface p-3 text-left shadow-[var(--shadow-card)] hover:border-line-strong">
                    <div className="mb-3 flex h-20 items-center justify-center rounded-md bg-ink-50"><FormatIcon f={d.format} className="size-8" /></div>
                    <div className="line-clamp-2 text-[12.5px] font-medium text-ink-900">{d.title}</div>
                    <div className="mt-0.5 truncate text-[11px] text-ink-500">{d.account_name ?? 'Reference'} · {d.doc_type}</div>
                    <div className="mt-2 flex items-center justify-between"><span className="mono text-[10.5px] text-ink-400">{d.format.toUpperCase()} · {bytes(d.size_bytes)}</span><Extraction d={d} /></div>
                  </button>
                ))}
              </div>
            )}
            {filtered.length > shown.length && <div className="mt-2 text-center text-[12px] text-ink-500">Showing {shown.length} of {filtered.length} — refine with facets.</div>}
          </div>
        </div>
      )}
    </Page>
  );
}

function Extraction({ d }: { d: DocumentMeta }) {
  const e = d.extraction;
  if (!e || e.status === 'NOT_APPLICABLE') return <span className="text-[11px] text-ink-400">n/a</span>;
  if (e.status === 'PENDING') return <Badge tone="med">pending</Badge>;
  return <Badge tone={e.avg_confidence !== null && e.avg_confidence < 0.9 ? 'med' : 'ok'} title={`${e.fields} fields extracted`}>{e.fields} fields · {pct(e.avg_confidence, 0)}</Badge>;
}
