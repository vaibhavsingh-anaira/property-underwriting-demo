// Shared building blocks for the Delegated Authority pages.
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { FileSpreadsheet, FileText } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Anchor } from '@/api/types';
import { Badge, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { pct, usd } from '@/lib/format';
import { CH_COLOR, MONTH, STATUS_LABEL, STATUS_TONE, type SideCheck, type TrendPoint } from './api';

export function StatusPill({ s }: { s: string }) {
  return <Badge tone={STATUS_TONE[s] ?? 'neutral'}>{STATUS_LABEL[s] ?? s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, ' ')}</Badge>;
}

export function Grade({ g, score, size = 'md' }: { g: string; score?: number; size?: 'sm' | 'md' }) {
  const tone = g === 'A' ? 'bg-ok text-white' : g === 'B' ? 'bg-accent-600 text-white' : g === 'C' ? 'bg-med text-white' : 'bg-crit text-white';
  return (
    <span className="inline-flex items-center gap-1.5" title="Scorecard grade: authority, data quality, timeliness, loss and trend">
      <span className={cx('mono inline-flex items-center justify-center rounded-md font-bold', tone, size === 'sm' ? 'size-6 text-[12px]' : 'size-8 text-[15px]')}>{g}</span>
      {score !== undefined && <span className="num text-[12px] text-ink-500">{Math.round(score)}</span>}
    </span>
  );
}

/** Opens a document at an anchor (bordereau cell or BAA clause). */
export function Src({ anchor, docId, label, kind }: { anchor?: Anchor | null; docId?: string | null; label?: ReactNode; kind?: 'cell' | 'clause' }) {
  const ev = useEvidence();
  const id = anchor?.doc_id ?? docId;
  if (!id) return null;
  const k = kind ?? (anchor?.kind === 'pdf' ? 'clause' : 'cell');
  const Icon = k === 'clause' ? FileText : FileSpreadsheet;
  const txt = label ?? (k === 'clause' ? `BAA p.${anchor?.page ?? 1}` : anchor?.cell ? `${anchor.cell}` : 'Open');
  return (
    <button onClick={(e) => { e.stopPropagation(); ev.openDoc(id, anchor ?? null); }} title={k === 'clause' ? 'Open the agreement at this clause' : 'Open the bordereau at this cell'}
      className="mono inline-flex items-center gap-1 rounded border border-line bg-surface px-1.5 py-[1px] text-[10.5px] text-accent-700 hover:border-accent-500 hover:bg-accent-50">
      <Icon className="size-3" />{txt}
    </button>
  );
}

export function UtilBar({ util, warn = 0.9, className }: { util: number | null; warn?: number; className?: string }) {
  const u = util ?? 0;
  const tone = u >= 1 ? 'bg-crit' : u >= warn ? 'bg-high' : u >= warn - 0.1 ? 'bg-med' : 'bg-accent-600';
  return (
    <div className={cx('relative h-2 w-full rounded-full bg-ink-100', className)}>
      <div className={cx('h-2 rounded-full', tone)} style={{ width: `${Math.min(100, u * 100)}%` }} />
      <div className="absolute -top-1 h-4 w-px bg-ink-700" style={{ left: `${warn * 100}%` }} title={`Warning ${pct(warn, 0)}`} />
    </div>
  );
}

/** The deck's risk-level authority result: written vs authority, with the evidence on both sides. */
export function SideBySide({ checks, onlyFired = false }: { checks: SideCheck[]; onlyFired?: boolean }) {
  const rows = onlyFired ? checks.filter((c) => c.result !== 'PASS' && c.result !== 'NA') : checks;
  const res = (c: SideCheck) => {
    if (c.rule_id === 'REFERRAL') return c.result === 'PASS' ? <Badge tone="ok">OK</Badge> : <Badge tone="crit">None located</Badge>;
    if (c.result === 'PASS') return <Badge tone="ok">Approved</Badge>;
    if (c.result === 'NA') return <Badge tone="neutral">Not checked</Badge>;
    if (c.result === 'REFER') return c.referral?.result === 'AUTHORISED' ? <Badge tone="ok">Referred · approved</Badge> : <Badge tone="high">Refer · {c.referral?.result === 'DIFFERENT_TERMS' ? 'approval covers less' : 'no approval'}</Badge>;
    return <Badge tone={c.result === 'BREACH' ? 'crit' : 'high'}>{c.result === 'BREACH' ? 'Breach' : c.result}</Badge>;
  };
  return (
    <table className="dt">
      <thead><tr><th>Check</th><th>Written</th><th>Authority</th><th className="r">Delta</th><th>Result</th><th>Evidence</th></tr></thead>
      <tbody>
        {rows.map((c) => (
          <tr key={c.rule_id} className={cx(c.result !== 'PASS' && c.result !== 'NA' && !(c.referral?.result === 'AUTHORISED') && 'bg-crit-bg/30')}>
            <td><div className="text-[12.5px] font-medium text-ink-900">{c.check}</div>{c.referral && c.referral.result !== 'AUTHORISED' && <div className="text-[11px] text-ink-500">{c.referral.detail}</div>}</td>
            <td className="num text-[12.5px] text-ink-900">{c.written}</td>
            <td className="num text-[12.5px] text-ink-700">{c.authority}</td>
            <td className="num r text-[12px] font-semibold text-crit">{c.delta ?? ''}</td>
            <td>{res(c)}</td>
            <td className="whitespace-nowrap"><span className="inline-flex gap-1"><Src anchor={c.anchor_written} kind="cell" /><Src anchor={c.anchor_authority} kind="clause" /></span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function TrendChart({ series, height = 220 }: { series: { key: string; label: string; points: TrendPoint[] }[]; height?: number }) {
  const months = [...new Set(series.flatMap((s) => s.points.map((p) => p.month)))].sort();
  const data = months.map((m) => ({ month: MONTH(m).slice(0, 3), ...Object.fromEntries(series.map((s) => [s.key, (s.points.find((p) => p.month === m)?.rate ?? null) as number | null]).map(([k, v]) => [k, v === null ? null : +((v as number) * 100).toFixed(2)])) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--color-line)" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--color-ink-500)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--color-ink-500)' }} axisLine={false} tickLine={false} unit="%" />
        <Tooltip formatter={(v) => `${v}%`} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {series.map((s) => <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={CH_COLOR[s.key] ?? 'var(--color-accent-600)'} strokeWidth={2} dot={{ r: 3 }} connectNulls isAnimationActive={false} />)}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ChLink({ id, children }: { id: string; children: ReactNode }) {
  return <Link to={`/delegated/coverholders/${id}`} onClick={(e) => e.stopPropagation()} className="font-medium text-ink-900 hover:text-accent-700">{children}</Link>;
}

export const money = (v: number | null | undefined) => usd(v ?? 0);
export function Mini({ label, value, tone }: { label: string; value: ReactNode; tone?: 'crit' | 'ok' | 'high' }) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <div className="text-[10.5px] font-medium uppercase tracking-wide text-ink-500">{label}</div>
      <div className={cx('num mt-0.5 text-[15px] font-semibold', tone === 'crit' ? 'text-crit' : tone === 'ok' ? 'text-ok' : tone === 'high' ? 'text-high' : 'text-ink-950')}>{value}</div>
    </div>
  );
}
