import { useState } from 'react';
import { FileText, Cpu, User, Server, Boxes } from 'lucide-react';
import type { AccountDetail, TimelineEvent } from '@/api/types';
import { Card, Segmented, MockBadge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { fmtDate } from '@/lib/format';
import { Info } from '@/help/Info';

const KIND: Record<TimelineEvent['kind'], { icon: typeof FileText; color: string; label: string }> = {
  document: { icon: FileText, color: 'bg-info', label: 'Document' },
  engine: { icon: Cpu, color: 'bg-accent-600', label: 'Engine' },
  user: { icon: User, color: 'bg-ink-800', label: 'User' },
  system: { icon: Server, color: 'bg-ink-500', label: 'System' },
  mock: { icon: Boxes, color: 'bg-med', label: 'Mock system' },
};
const STAGE: Record<string, string> = { '01': 'Submission', '02': 'Clearance', '03': 'Appetite', '04': 'Extraction', '05': 'Risk assessment', '06': 'Pricing & modelling', '07': 'Authority & portfolio', '08': 'Terms & quote', '09': 'Negotiation', '10': 'Bind', '11': 'Issuance', '12': 'Mid-term', '13': 'Claims feedback', '14': 'Portfolio', '15': 'Renewal engine' };

export default function TimelineTab({ a }: { a: AccountDetail }) {
  const ev = useEvidence();
  const [kind, setKind] = useState<'all' | TimelineEvent['kind']>('all');
  const events = [...a.timeline].sort((x, y) => y.date.localeCompare(x.date)).filter((e) => kind === 'all' || e.kind === kind);
  return (
    <Card title={<span className="inline-flex items-center gap-1.5">Timeline & audit trail<Info id="account.timeline" /></span>} subtitle="Every document, engine run, mock-system event and user decision, with pipeline stage codes"
      actions={<Segmented value={kind} onChange={setKind} options={[{ key: 'all', label: 'All' }, ...(['document', 'engine', 'user', 'mock'] as const).map((k) => ({ key: k, label: KIND[k].label }))]} />}>
      <ol className="relative ml-3 border-l border-line">
        {events.map((e) => {
          const K = KIND[e.kind];
          return (
            <li key={e.event_id} className="relative mb-4 ml-6 last:mb-0">
              <span className={cx('absolute -left-[37px] flex size-6 items-center justify-center rounded-full ring-4 ring-surface', K.color)}><K.icon className="size-3 text-white" /></span>
              <div className="flex flex-wrap items-center gap-2">
                <span className="num text-[12px] text-ink-500">{fmtDate(e.date)}</span>
                <span className="mono rounded bg-ink-100 px-1.5 text-[10.5px] font-semibold text-ink-700" title={STAGE[e.stage]}>{e.stage} · {STAGE[e.stage] ?? ''}</span>
                {e.kind === 'mock' && <MockBadge />}
                <span className="text-[11.5px] text-ink-500">{e.actor}</span>
              </div>
              <div className="mt-0.5 text-[13px] font-medium text-ink-900">{e.title}</div>
              <div className="text-[12.5px] text-ink-600">{e.detail}</div>
              {(e.doc_id || e.finding_ids?.length) && (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {e.doc_id && <button onClick={() => ev.openDoc(e.doc_id!)} className="inline-flex items-center gap-1 rounded border border-line px-1.5 text-[11px] text-info hover:bg-info-bg"><FileText className="size-3" />document</button>}
                  {e.finding_ids?.map((id) => { const f = a.findings.find((x) => x.finding_id === id); return f ? <button key={id} onClick={() => ev.openFinding(f)} className="max-w-[320px] truncate rounded bg-accent-50 px-1.5 text-[11px] text-accent-700 hover:bg-accent-100">{f.title}</button> : null; })}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
