// Shared building blocks for screens.
import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react';
import { FileText, FileSpreadsheet, Mail, Box, Image as ImageIcon, Braces, Table2, FileCode, Check } from 'lucide-react';
import type { ActionType, DocFormat, Finding, PassNo, RenewalStatus, Disposition } from '@/api/types';
import { Badge, Button, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { ACTION_LABEL, STATUS_LABEL } from '@/lib/format';
import { useDisposition } from '@/api/client';

export function ScenarioChip({ s }: { s: string | null }) {
  if (!s) return null;
  return <span className="mono inline-flex h-[18px] items-center rounded-[4px] bg-ink-900 px-1.5 text-[10px] font-semibold text-white">{s}</span>;
}

const STATUS_TONE: Record<RenewalStatus, Parameters<typeof Badge>[0]['tone']> = {
  NOT_STARTED: 'neutral', FAST_TRACK: 'ok', ACTION_REQUIRED: 'crit', IN_REVIEW: 'med', REFERRED: 'info',
  QUOTED: 'accent', BOUND: 'dark', ISSUED: 'dark', NON_RENEWED: 'neutral', LOST: 'neutral',
};
export function StatusBadge({ s }: { s: RenewalStatus }) { return <Badge tone={STATUS_TONE[s]}>{STATUS_LABEL[s]}</Badge>; }

const ACTION_TONE: Partial<Record<ActionType, Parameters<typeof Badge>[0]['tone']>> = {
  MAINTAIN: 'ok', REPRICE: 'high', RESTRUCTURE: 'high', REFER: 'info', NON_RENEW: 'crit', CONDITIONAL_RENEWAL_NOTICE: 'crit', ENDORSEMENT_CORRECTION: 'crit', CONDITION: 'med', DATA_REQUEST: 'neutral',
};
export function ActionChips({ actions, max = 9 }: { actions: ActionType[]; max?: number }) {
  if (!actions.length) return <span className="text-ink-400">—</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {actions.slice(0, max).map((a) => <Badge key={a} tone={ACTION_TONE[a] ?? 'neutral'}>{ACTION_LABEL[a]}</Badge>)}
      {actions.length > max && <Badge>+{actions.length - max}</Badge>}
    </span>
  );
}

export function PassDots({ pass }: { pass: PassNo }) {
  return (
    <span className="inline-flex items-center gap-[3px]" title={pass ? `Pass ${pass} of 3` : 'Not run'}>
      {[1, 2, 3].map((p) => <span key={p} className={cx('size-[7px] rounded-full', p <= pass ? 'bg-accent-600' : 'bg-ink-200')} />)}
    </span>
  );
}

const PASSES = [
  { n: 1, t: 'Internal drift', s: 'T-150 · data already held' },
  { n: 2, t: 'Submission delta', s: 'Renewal SOV received' },
  { n: 3, t: 'Contract integrity', s: 'Quote ↔ binder ↔ policy' },
];
export function PassStepper({ pass }: { pass: PassNo }) {
  return (
    <div className="flex items-center">
      {PASSES.map((p, i) => (
        <Fragment key={p.n}>
          {i > 0 && <div className={cx('mx-2 h-px w-6', p.n <= pass ? 'bg-accent-600' : 'bg-ink-200')} />}
          <div className="flex items-center gap-1.5" title={p.s}>
            <span className={cx('flex size-[18px] items-center justify-center rounded-full text-[10px] font-semibold',
              p.n < pass ? 'bg-accent-600 text-white' : p.n === pass ? 'bg-accent-600 text-white ring-2 ring-accent-100' : 'bg-ink-100 text-ink-400')}>
              {p.n < pass ? <Check className="size-3" /> : p.n}
            </span>
            <span className={cx('text-[12px]', p.n <= pass ? 'font-medium text-ink-900' : 'text-ink-400')}>{p.t}</span>
          </div>
        </Fragment>
      ))}
    </div>
  );
}

export function NoticeCountdown({ days, date }: { days: number | null; date?: string | null }) {
  if (days === null || days === undefined) return <span className="text-ink-400" title="Not required (E&S or no notice action)">n/a</span>;
  const tone = days < 0 ? 'bg-crit text-white' : days < 21 ? 'bg-crit-bg text-crit border border-[#f6c5cc]' : days < 45 ? 'bg-med-bg text-med' : 'bg-ink-100 text-ink-700';
  return <span title={date ?? undefined} className={cx('num inline-flex rounded-[5px] px-1.5 py-[1px] text-[11px] font-semibold', tone)}>{days < 0 ? `${-days}d late` : `${days}d`}</span>;
}

const FMT_ICON: Record<DocFormat, typeof FileText> = { pdf: FileText, xlsx: FileSpreadsheet, eml: Mail, glb: Box, png: ImageIcon, json: Braces, geojson: Braces, csv: Table2, yaml: FileCode, txt: FileCode };
const FMT_COLOR: Record<DocFormat, string> = { pdf: 'text-crit', xlsx: 'text-ok', eml: 'text-info', glb: 'text-accent-700', png: 'text-high', json: 'text-ink-600', geojson: 'text-ink-600', csv: 'text-ok', yaml: 'text-[#7c4dcc]', txt: 'text-ink-500' };
export function FormatIcon({ f, className }: { f: DocFormat; className?: string }) {
  const I = FMT_ICON[f] ?? FileText;
  return <I className={cx('size-4 shrink-0', FMT_COLOR[f], className)} />;
}

/** Minimal markdown: paragraphs, **bold**, "- " bullets, plus [F:id] / [O:id] citation chips. */
export function CitedText({ text, findings, className }: { text: string; findings?: Finding[]; className?: string }) {
  const ev = useEvidence();
  const inline = (s: string, key: string) => {
    const parts = s.split(/(\[[FO]:[^\]]+\]|\*\*[^*]+\*\*)/g);
    let n = 0;
    return parts.map((p, i) => {
      const m = /^\[([FO]):([^\]]+)\]$/.exec(p);
      if (m) {
        n++;
        const f = m[1] === 'F' ? findings?.find((x) => x.finding_id === m[2]) : null;
        return (
          <button key={key + i} title={f ? f.title : m[2]} onClick={() => (m[1] === 'F' ? f && ev.openFinding(f) : ev.openObs(m[2]))}
            className={cx('mx-[1px] inline-flex -translate-y-[3px] items-center rounded-[3px] px-1 text-[9.5px] font-semibold leading-[14px]',
              m[1] === 'F' ? 'bg-accent-50 text-accent-700 hover:bg-accent-100' : 'bg-info-bg text-info hover:bg-[#dbe5fc]', m[1] === 'F' && !f && 'cursor-default opacity-60')}>
            {m[1] === 'F' ? 'F' : 'O'}{n}
          </button>
        );
      }
      if (p.startsWith('**')) return <strong key={key + i} className="font-semibold text-ink-950">{p.slice(2, -2)}</strong>;
      return <Fragment key={key + i}>{p}</Fragment>;
    });
  };
  const blocks = text.split(/\n\n+/);
  return (
    <div className={cx('space-y-2.5 text-[13px] leading-[1.6] text-ink-800', className)}>
      {blocks.map((b, i) => {
        const lines = b.split('\n');
        if (lines.every((l) => l.startsWith('- '))) return <ul key={i} className="list-disc space-y-1 pl-5">{lines.map((l, j) => <li key={j}>{inline(l.slice(2), `${i}-${j}-`)}</li>)}</ul>;
        return <p key={i}>{inline(b, `${i}-`)}</p>;
      })}
    </div>
  );
}

export const REASONS: { code: Disposition['reason_code']; label: string }[] = [
  { code: 'agree', label: 'Agree — act on it' },
  { code: 'data_wrong', label: 'Data wrong' },
  { code: 'already_known', label: 'Already known' },
  { code: 'commercial_override', label: 'Commercial override' },
  { code: 'immaterial', label: 'Immaterial' },
  { code: 'rule_outdated', label: 'Rule outdated' },
];

/** Accept / Reject / Defer with mandatory reason code. */
export function DispositionControl({ f }: { f: Finding }) {
  const [open, setOpen] = useState<Disposition['decision'] | null>(null);
  const [reason, setReason] = useState<Disposition['reason_code'] | ''>('');
  const [note, setNote] = useState('');
  const mut = useDisposition();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, [open]);
  if (f.disposition && !open) {
    return (
      <button onClick={(e) => { e.stopPropagation(); setOpen(f.disposition!.decision); setReason(f.disposition!.reason_code); setNote(f.disposition!.note); }}
        className="text-left text-[11px] leading-tight text-ink-500 hover:text-ink-800" title={f.disposition.note}>
        <span className={cx('font-semibold', f.disposition.decision === 'ACCEPT' ? 'text-ok' : f.disposition.decision === 'REJECT' ? 'text-crit' : 'text-med')}>{f.disposition.decision.toLowerCase()}ed</span>
        <span className="mono"> · {f.disposition.reason_code}</span><br />{f.disposition.actor}
      </button>
    );
  }
  const reasons = open === 'ACCEPT' ? REASONS.filter((r) => ['agree', 'already_known', 'commercial_override'].includes(r.code)) : REASONS.filter((r) => r.code !== 'agree');
  return (
    <div className="relative inline-flex gap-1" ref={ref} onClick={(e) => e.stopPropagation()}>
      {(['ACCEPT', 'REJECT', 'DEFER'] as const).map((d) => (
        <button key={d} onClick={() => { setOpen(d); setReason(d === 'ACCEPT' ? 'agree' : ''); }}
          className={cx('rounded-[5px] border px-1.5 py-[1px] text-[11px] font-medium', open === d ? 'border-ink-900 bg-ink-900 text-white' : 'border-line-strong text-ink-700 hover:bg-ink-50')}>
          {d === 'ACCEPT' ? 'Accept' : d === 'REJECT' ? 'Reject' : 'Defer'}
        </button>
      ))}
      {open && (
        <div className="anim-fade absolute right-0 top-7 z-30 w-[260px] rounded-lg border border-line bg-surface p-3 shadow-[var(--shadow-pop)]">
          <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-500">Reason code (required)</div>
          <div className="mb-2 grid gap-1">
            {reasons.map((r) => (
              <label key={r.code} className={cx('flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-[12px]', reason === r.code ? 'bg-accent-50 text-ink-950' : 'hover:bg-ink-50')}>
                <input type="radio" checked={reason === r.code} onChange={() => setReason(r.code)} className="accent-[var(--color-accent-600)]" />
                {r.label}<span className="mono ml-auto text-[10px] text-ink-400">{r.code}</span>
              </label>
            ))}
          </div>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" rows={2} className="mb-2 w-full resize-none rounded-md border border-line-strong px-2 py-1 text-[12px] outline-none focus:border-accent-500" />
          <div className="flex justify-end gap-1.5">
            <Button size="sm" variant="ghost" onClick={() => setOpen(null)}>Cancel</Button>
            <Button size="sm" variant="primary" disabled={!reason} loading={mut.isPending}
              onClick={() => reason && mut.mutate({ finding_id: f.finding_id, decision: open, reason_code: reason, note }, { onSuccess: () => setOpen(null) })}>
              Record {open.toLowerCase()}
            </Button>
          </div>
          {mut.error && <div className="mt-2 text-[11px] text-crit">{(mut.error as Error).message}</div>}
        </div>
      )}
    </div>
  );
}

export function Bar({ value, max = 1, tone = 'accent', className, marker }: { value: number; max?: number; tone?: 'accent' | 'crit' | 'high' | 'med' | 'ok' | 'ink'; className?: string; marker?: number }) {
  const c = { accent: 'bg-accent-600', crit: 'bg-crit', high: 'bg-high', med: 'bg-med', ok: 'bg-ok', ink: 'bg-ink-700' }[tone];
  return (
    <div className={cx('relative h-1.5 w-full overflow-hidden rounded-full bg-ink-100', className)}>
      <div className={cx('h-full rounded-full', c)} style={{ width: `${Math.max(0, Math.min(100, (value / max) * 100))}%` }} />
      {marker !== undefined && <div className="absolute inset-y-[-2px] w-px bg-ink-900" style={{ left: `${(marker / max) * 100}%` }} />}
    </div>
  );
}

export function SectionLabel({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return <div className="mb-2 flex items-center justify-between"><div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">{children}</div>{right}</div>;
}

export const flagTone = (f?: string) => (f === 'breach' ? 'text-crit' : f === 'warn' ? 'text-high' : f === 'ok' ? 'text-ok' : 'text-ink-700');
export const flagDot = (f?: string) => (f === 'breach' ? 'bg-crit' : f === 'warn' ? 'bg-high' : f === 'ok' ? 'bg-ok' : 'bg-ink-300');

export function useHotkeys(map: Record<string, () => void>, deps: unknown[] = []) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const fn = map[e.key]; if (fn) { e.preventDefault(); fn(); }
    };
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h);
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
}
