// <Info id="book.pipeline" /> — a small (i) that explains what a page or section is and how it fits the product.
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { Info as InfoIcon, X, BookOpen } from 'lucide-react';
import { HELP, type HelpMode } from './content';
import { cx } from '@/components/ui';

const MODE: Record<HelpMode, { label: string; cls: string; hint: string }> = {
  REAL: { label: 'REAL · the product', cls: 'bg-ok-bg text-ok', hint: 'This is the Anaira product itself, running for real on the demo data.' },
  BASIC: { label: 'BASIC · thin implementation', cls: 'bg-info-bg text-info', hint: 'A working but deliberately simple implementation of something a carrier workbench normally provides.' },
  MOCK: { label: 'MOCK · stand-in', cls: 'bg-med-bg text-med', hint: 'A stand-in for a carrier or vendor system, behind the same connector a real system would use.' },
  MIXED: { label: 'REAL + MOCK', cls: 'bg-accent-50 text-accent-700', hint: 'The product (real) working on inputs from stand-in systems (mock).' },
};

export function Info({ id, className, label }: { id: string; className?: string; label?: string }) {
  const e = HELP[id];
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (ev: KeyboardEvent) => { if (ev.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [open]);
  if (!e) return null;
  const toggle = (ev: React.MouseEvent) => {
    ev.stopPropagation();
    const r = btn.current!.getBoundingClientRect();
    const w = 380;
    setPos({ x: Math.min(window.innerWidth - w - 12, Math.max(12, r.left - 8)), y: Math.min(window.innerHeight - 40, r.bottom + 6) });
    setOpen((o) => !o);
  };
  const m = e.mode ? MODE[e.mode] : null;
  return (
    <>
      <button ref={btn} onClick={toggle} title={`About: ${e.title}`} aria-label={`About ${e.title}`}
        className={cx('inline-flex shrink-0 items-center gap-1 rounded-full text-ink-400 transition-colors hover:text-accent-700', label && 'rounded-md border border-line-strong bg-surface px-2 py-0.5 text-[12px] font-medium text-ink-700 hover:border-accent-500', className)}>
        <InfoIcon className={label ? 'size-3.5' : 'size-[15px]'} />{label}
      </button>
      {open && createPortal(
        <>
          <div className="fixed inset-0 z-[90]" onClick={() => setOpen(false)} />
          <div className="anim-fade fixed z-[91] w-[380px] rounded-xl border border-line bg-surface p-4 text-left shadow-[var(--shadow-pop)]" style={{ left: pos.x, top: pos.y, maxHeight: 'calc(100vh - 24px)', overflowY: 'auto' }} onClick={(ev) => ev.stopPropagation()}>
            <div className="mb-2 flex items-start justify-between gap-2">
              <div className="text-[14px] font-semibold text-ink-950">{e.title}</div>
              <button onClick={() => setOpen(false)} className="text-ink-400 hover:text-ink-800"><X className="size-4" /></button>
            </div>
            {m && <div className={cx('mb-3 inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold', m.cls)} title={m.hint}>{m.label}</div>}
            <Section h="What it is">{e.what}</Section>
            <Section h="How it fits the product">{e.fits}</Section>
            {e.how && <Section h="How to use it">{e.how}</Section>}
            {e.demo && <Section h="In a demo">{e.demo}</Section>}
            {m && <div className="mt-2 border-t border-line pt-2 text-[11.5px] text-ink-500">{m.hint}</div>}
            <Link to="/guide" onClick={() => setOpen(false)} className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-accent-700 hover:underline"><BookOpen className="size-3.5" />Open the full guide</Link>
          </div>
        </>, document.body)}
    </>
  );
}

function Section({ h, children }: { h: string; children: React.ReactNode }) {
  return (
    <div className="mb-2.5">
      <div className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-[.08em] text-ink-500">{h}</div>
      <div className="text-[13px] leading-relaxed text-ink-800">{children}</div>
    </div>
  );
}
