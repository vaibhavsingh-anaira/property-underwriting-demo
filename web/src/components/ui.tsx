// Shared UI primitives. Every screen composes these — do not restyle ad hoc.
import clsx from 'clsx';
import type { ReactNode, ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';
import type { ObsType, Severity } from '@/api/types';
import { OBS_TYPE_LABEL } from '@/api/types';

export const cx = clsx;

// ------------------------------------------------------------------ layout
export function Page({ title, subtitle, actions, children, crumbs }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; crumbs?: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1600px] px-6 py-5">
      {crumbs && <div className="mb-1 text-[12px] text-ink-500">{crumbs}</div>}
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[20px] font-semibold tracking-[-0.01em] text-ink-950">{title}</h1>
          {subtitle && <div className="mt-0.5 text-[13px] text-ink-500">{subtitle}</div>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function Card({ title, subtitle, actions, children, className, pad = true, id }: { title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; pad?: boolean; id?: string }) {
  return (
    <section id={id} className={cx('rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)]', className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
          <div className="min-w-0">
            <div className="text-[13px] font-semibold text-ink-900">{title}</div>
            {subtitle && <div className="text-[12px] text-ink-500">{subtitle}</div>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cx(pad && 'p-4')}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, sub, tone, onClick }: { label: ReactNode; value: ReactNode; sub?: ReactNode; tone?: 'crit' | 'high' | 'ok' | 'accent' | 'info'; onClick?: () => void }) {
  const toneCls = { crit: 'text-crit', high: 'text-high', ok: 'text-ok', accent: 'text-accent-700', info: 'text-info' } as const;
  return (
    <div onClick={onClick} className={cx('rounded-[var(--radius-card)] border border-line bg-surface px-4 py-3 shadow-[var(--shadow-card)]', onClick && 'cursor-pointer hover:border-line-strong')}>
      <div className="text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">{label}</div>
      <div className={cx('num mt-1 text-[22px] font-semibold tracking-[-0.02em]', tone ? toneCls[tone] : 'text-ink-950')}>{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-ink-500">{sub}</div>}
    </div>
  );
}

// ------------------------------------------------------------------ controls
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; loading?: boolean; icon?: ReactNode };
export function Button({ variant = 'secondary', size = 'md', loading, icon, className, children, disabled, ...rest }: BtnProps) {
  const v = {
    primary: 'bg-ink-900 text-white hover:bg-ink-800 border-ink-900',
    secondary: 'bg-surface text-ink-800 border-line-strong hover:bg-ink-50',
    ghost: 'bg-transparent text-ink-700 border-transparent hover:bg-ink-100',
    danger: 'bg-crit text-white border-crit hover:opacity-90',
  }[variant];
  const s = size === 'sm' ? 'h-7 px-2.5 text-[12px] gap-1.5' : 'h-8 px-3 text-[13px] gap-2';
  return (
    <button {...rest} disabled={disabled || loading} className={cx('inline-flex items-center justify-center rounded-md border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50', v, s, className)}>
      {loading ? <Loader2 className="size-3.5 animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function Tabs<K extends string>({ tabs, value, onChange, className }: { tabs: { key: K; label: ReactNode; count?: number }[]; value: K; onChange: (k: K) => void; className?: string }) {
  return (
    <div className={cx('flex items-center gap-1 border-b border-line', className)}>
      {tabs.map((t) => (
        <button key={t.key} onClick={() => onChange(t.key)}
          className={cx('-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-[13px] font-medium transition-colors',
            value === t.key ? 'border-ink-900 text-ink-950' : 'border-transparent text-ink-500 hover:text-ink-800')}>
          {t.label}
          {t.count !== undefined && <span className={cx('num rounded-full px-1.5 text-[11px]', value === t.key ? 'bg-ink-900 text-white' : 'bg-ink-100 text-ink-600')}>{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Segmented<K extends string>({ options, value, onChange }: { options: { key: K; label: ReactNode }[]; value: K; onChange: (k: K) => void }) {
  return (
    <div className="inline-flex rounded-md border border-line-strong bg-ink-50 p-0.5">
      {options.map((o) => (
        <button key={o.key} onClick={() => onChange(o.key)}
          className={cx('rounded-[5px] px-2.5 py-1 text-[12px] font-medium', value === o.key ? 'bg-surface text-ink-950 shadow-sm' : 'text-ink-500 hover:text-ink-800')}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx('h-8 rounded-md border border-line-strong bg-surface px-2.5 text-[13px] outline-none placeholder:text-ink-400 focus:border-accent-500', props.className)} />;
}
export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx('h-8 rounded-md border border-line-strong bg-surface px-2 text-[13px] outline-none focus:border-accent-500', props.className)} />;
}

// ------------------------------------------------------------------ badges
export function Badge({ children, tone = 'neutral', className, title }: { children: ReactNode; tone?: 'neutral' | 'crit' | 'high' | 'med' | 'low' | 'ok' | 'info' | 'accent' | 'dark' | 'mock'; className?: string; title?: string }) {
  const t = {
    neutral: 'bg-ink-100 text-ink-700 border-ink-200',
    crit: 'bg-crit-bg text-crit border-[#f6c5cc]',
    high: 'bg-high-bg text-high border-[#f5d2b8]',
    med: 'bg-med-bg text-med border-[#efdf9f]',
    low: 'bg-low-bg text-low border-ink-200',
    ok: 'bg-ok-bg text-ok border-[#bfe3cd]',
    info: 'bg-info-bg text-info border-[#c9d6f8]',
    accent: 'bg-accent-50 text-accent-700 border-accent-100',
    dark: 'bg-ink-900 text-white border-ink-900',
    mock: 'bg-[repeating-linear-gradient(45deg,#fff7e0,#fff7e0_4px,#fdefc4_4px,#fdefc4_8px)] text-[#8a6100] border-[#efd98f]',
  }[tone];
  return <span title={title} className={cx('inline-flex items-center gap-1 whitespace-nowrap rounded-[5px] border px-1.5 py-[1px] text-[11px] font-medium leading-[18px]', t, className)}>{children}</span>;
}

export const sevTone = (s: Severity) => ({ CRITICAL: 'crit', HIGH: 'high', MEDIUM: 'med', LOW: 'low' } as const)[s];
export function SeverityPill({ s }: { s: Severity }) {
  return <Badge tone={sevTone(s)}>{s === 'CRITICAL' ? 'Critical' : s === 'HIGH' ? 'High' : s === 'MEDIUM' ? 'Medium' : 'Low'}</Badge>;
}
export function SeverityDot({ s }: { s: Severity }) {
  const c = { CRITICAL: 'bg-crit', HIGH: 'bg-high', MEDIUM: 'bg-med', LOW: 'bg-ink-300' }[s];
  return <span className={cx('inline-block size-2 shrink-0 rounded-full', c)} />;
}

const OBS_COLOR: Record<ObsType, string> = {
  C: 'var(--color-obs-c)', S: 'var(--color-obs-s)', N: 'var(--color-obs-n)', V: 'var(--color-obs-v)',
  D: 'var(--color-obs-d)', M: 'var(--color-obs-m)', R: 'var(--color-obs-r)',
};
export function ObsTypeChip({ t, withLabel = false }: { t: ObsType; withLabel?: boolean }) {
  return (
    <span title={OBS_TYPE_LABEL[t]} className="inline-flex items-center gap-1 text-[11px] font-medium" style={{ color: OBS_COLOR[t] }}>
      <span className="mono inline-flex size-[18px] items-center justify-center rounded-[4px] text-[10px] font-semibold text-white" style={{ background: OBS_COLOR[t] }}>{t}</span>
      {withLabel && OBS_TYPE_LABEL[t]}
    </span>
  );
}

export function MockBadge({ label = 'MOCK' }: { label?: string }) {
  return <Badge tone="mock" title="Stand-in for a carrier system — same connector contract as production">{label}</Badge>;
}

// ------------------------------------------------------------------ misc
export function Empty({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-[13px] text-ink-500">{icon}{children}</div>;
}
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="flex items-center justify-center gap-2 py-10 text-[13px] text-ink-500"><Loader2 className="size-4 animate-spin" />{label}</div>;
}
export function ErrorBox({ error }: { error: unknown }) {
  return <div className="rounded-md border border-[#f6c5cc] bg-crit-bg px-3 py-2 text-[13px] text-crit">{error instanceof Error ? error.message : String(error)}</div>;
}
export function KV({ k, v, mono }: { k: ReactNode; v: ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="text-[12px] text-ink-500">{k}</span>
      <span className={cx('num text-right text-[13px] text-ink-900', mono && 'mono text-[12px]')}>{v}</span>
    </div>
  );
}
export function Delta({ value, invert = false, digits = 1 }: { value: number | null | undefined; invert?: boolean; digits?: number }) {
  if (value === null || value === undefined) return <span className="text-ink-400">—</span>;
  const good = invert ? value < 0 : value > 0;
  const cls = Math.abs(value) < 0.0005 ? 'text-ink-500' : good ? 'text-ok' : 'text-crit';
  return <span className={cx('num font-medium', cls)}>{value > 0 ? '+' : value < 0 ? '−' : ''}{Math.abs(value * 100).toFixed(digits)}%</span>;
}
export function ScoreRing({ score, size = 44 }: { score: number; size?: number }) {
  const r = size / 2 - 4, c = 2 * Math.PI * r, p = Math.max(0, Math.min(100, score)) / 100;
  const color = score >= 85 ? 'var(--color-ok)' : score >= 70 ? 'var(--color-med)' : score >= 55 ? 'var(--color-high)' : 'var(--color-crit)';
  return (
    <svg width={size} height={size} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--color-ink-100)" strokeWidth="4" fill="none" />
      <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="4" fill="none" strokeDasharray={`${c * p} ${c}`} strokeLinecap="round" transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="num" style={{ fontSize: size * 0.3, fontWeight: 600, fill: 'var(--color-ink-900)' }}>{Math.round(score)}</text>
    </svg>
  );
}
