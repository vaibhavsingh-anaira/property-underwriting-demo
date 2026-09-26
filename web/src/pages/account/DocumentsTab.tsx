import { useMemo, useState } from 'react';
import type { AccountDetail } from '@/api/types';
import { Card, Badge, Empty, MockBadge, cx } from '@/components/ui';
import { bytes, fmtDate } from '@/lib/format';
import { DocumentViewer } from '@/viewers/DocumentViewer';
import { FormatIcon, SectionLabel } from '../common';
import { Info } from '@/help/Info';

const MOCK_CH = ['PAS (mock)', 'Claims (mock)', 'Engineering (mock)', 'Vendor (mock)', 'CAT (mock)'];

export default function DocumentsTab({ a }: { a: AccountDetail }) {
  const [sel, setSel] = useState<string | null>(a.documents[0]?.doc_id ?? null);
  const groups = useMemo(() => {
    const byTerm = new Map<string, Map<string, typeof a.documents>>();
    for (const d of a.documents) {
      const t = d.term ?? 'Reference';
      const m = byTerm.get(t) ?? new Map();
      m.set(d.doc_type, [...(m.get(d.doc_type) ?? []), d]);
      byTerm.set(t, m);
    }
    return [...byTerm.entries()].sort((x, y) => y[0].localeCompare(x[0]));
  }, [a.documents]);
  if (!a.documents.length) return <Card><Empty>No documents.</Empty></Card>;
  return (
    <div className="grid grid-cols-12 gap-4">
      <Card className="col-span-12 lg:col-span-4" pad={false} title={<span className="inline-flex items-center gap-1.5">{`${a.documents.length} documents`}<Info id="account.documents" /></span>} subtitle="Grouped by term and type">
        <div className="max-h-[calc(100vh-260px)] overflow-y-auto py-1">
          {groups.map(([term, types]) => (
            <div key={term} className="px-2 pb-2">
              <div className="px-2 pt-2"><SectionLabel>{term}</SectionLabel></div>
              {[...types.entries()].map(([type, docs]) => (
                <div key={type}>
                  <div className="px-2 pb-0.5 pt-1 text-[11px] text-ink-400">{type}</div>
                  {docs.map((d) => (
                    <button key={d.doc_id} onClick={() => setSel(d.doc_id)} className={cx('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left', sel === d.doc_id ? 'bg-accent-50' : 'hover:bg-ink-50')}>
                      <FormatIcon f={d.format} />
                      <span className="min-w-0 flex-1"><span className="block truncate text-[12.5px] text-ink-900">{d.title}</span><span className="num block truncate text-[10.5px] text-ink-400">{d.format.toUpperCase()} · {bytes(d.size_bytes)} · {fmtDate(d.received_at)} · {d.source_channel}</span></span>
                      {MOCK_CH.includes(d.source_channel) && <MockBadge />}
                      {d.extraction?.status === 'EXTRACTED' && <Badge tone="accent" title={`${d.extraction.fields} fields`}>{d.extraction.fields}</Badge>}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      </Card>
      <div className="col-span-12 overflow-hidden rounded-[var(--radius-card)] border border-line lg:col-span-8">
        {sel ? <DocumentViewer key={sel} docId={sel} height="calc(100vh - 200px)" /> : <Empty>Select a document.</Empty>}
      </div>
    </div>
  );
}
