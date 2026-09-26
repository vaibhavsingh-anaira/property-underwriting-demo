// Small shared pieces for the Decision Assurance pages.
import { BookOpen } from 'lucide-react';
import { Badge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { RESULT_TONE, STAGES, VERDICT_LABEL, VERDICT_TONE, type Citation, type Verdict } from './api';

export function VerdictBadge({ v, large }: { v: Verdict | null | undefined; large?: boolean }) {
  if (!v) return <span className="text-ink-400">—</span>;
  return <Badge tone={VERDICT_TONE[v]} className={large ? 'px-2.5 py-1 text-[13px]' : undefined}>{VERDICT_LABEL[v]}</Badge>;
}

export function ResultBadge({ r }: { r: string }) {
  return <Badge tone={RESULT_TONE[r] ?? 'neutral'}>{r === 'CONDITION' ? 'Condition' : r === 'PASS' ? 'Pass' : r === 'FLAG' ? 'Flag' : r === 'FAIL' ? 'Fail' : r}</Badge>;
}

export function Cite({ c }: { c: Citation }) {
  const ev = useEvidence();
  if (!c.doc_id) return <span className="text-[11.5px] text-ink-500">{c.label}</span>;
  return (
    <button onClick={() => ev.openDoc(c.doc_id!, { doc_id: c.doc_id, kind: 'pdf', page: c.page ?? 1 })} className="inline-flex items-center gap-1 text-[11.5px] font-medium text-accent-700 hover:underline">
      <BookOpen className="size-3" />{c.label}
    </button>
  );
}

/** Ten dots, one per pipeline stage; filled up to the stage reached. */
export function StageDots({ n }: { n: number }) {
  return (
    <span className="inline-flex items-center gap-[3px]" title={n ? `Stage ${n} of 10 · ${STAGES[n - 1]}` : 'Not received'}>
      {STAGES.map((s, i) => <span key={s} className={cx('h-[7px] w-[7px] rounded-full', i < n ? (i >= 6 ? 'bg-accent-700' : 'bg-accent-500') : 'bg-ink-200')} />)}
    </span>
  );
}

export function Dim({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: 'ok' | 'crit' | 'high' }) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <div className="text-[10.5px] font-medium uppercase tracking-wide text-ink-500">{label}</div>
      <div className={cx('num mt-0.5 text-[15px] font-semibold', tone === 'crit' ? 'text-crit' : tone === 'high' ? 'text-high' : tone === 'ok' ? 'text-ok' : 'text-ink-950')}>{value}</div>
      {sub && <div className="text-[11.5px] text-ink-500">{sub}</div>}
    </div>
  );
}
