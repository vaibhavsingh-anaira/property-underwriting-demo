// Exceedance-probability curves: log return-period axis, OEP solid, AEP dashed, prior runs muted.
import { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { usd } from '@/lib/format';

type Pt = { rp: number; loss: number };
export interface EpCurveChartProps { oep: Pt[]; aep?: Pt[]; compare?: { label: string; oep: Pt[] }[]; height?: number }

const TICKS = [10, 25, 50, 100, 250, 500, 1000];
const CMP_COLORS = ['var(--color-ink-400)', 'var(--color-ink-300)', 'var(--color-obs-n)'];

export function EpCurveChart({ oep, aep, compare, height = 260 }: EpCurveChartProps) {
  const data = useMemo(() => {
    const rps = new Set<number>();
    [oep, aep ?? [], ...(compare ?? []).map((c) => c.oep)].forEach((s) => s.forEach((p) => p.rp > 0 && rps.add(p.rp)));
    const at = (s: Pt[] | undefined, rp: number) => s?.find((p) => p.rp === rp)?.loss;
    return [...rps].sort((a, b) => a - b).map((rp) => {
      const row: Record<string, number | undefined> = { rp, oep: at(oep, rp), aep: at(aep, rp) };
      compare?.forEach((c, i) => { row[`c${i}`] = at(c.oep, rp); });
      return row;
    });
  }, [oep, aep, compare]);
  const minRp = Math.max(1, Math.min(10, ...data.map((d) => d.rp as number)));
  const maxRp = Math.max(1000, ...data.map((d) => d.rp as number));

  return (
    <div style={{ height }} className="w-full">
      <div className="mb-1 flex items-center gap-4 text-[11px] text-ink-500">
        <LegendItem color="var(--color-accent-600)" label="OEP" />
        {aep && <LegendItem color="var(--color-ink-700)" label="AEP" dashed />}
        {compare?.map((c, i) => <LegendItem key={c.label} color={CMP_COLORS[i % CMP_COLORS.length]} label={c.label} thin />)}
      </div>
      <ResponsiveContainer width="100%" height={height - 20}>
        <LineChart data={data} margin={{ top: 14, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--color-line)" strokeDasharray="0" vertical={false} />
          <XAxis dataKey="rp" type="number" scale="log" domain={[minRp, maxRp]} ticks={TICKS.filter((t) => t >= minRp && t <= maxRp)} allowDataOverflow
            tickFormatter={(v: number) => `${v}`} tick={{ fontSize: 11, fill: 'var(--color-ink-500)' }} tickLine={false} axisLine={{ stroke: 'var(--color-line-strong)' }}
            label={{ value: 'Return period (years)', position: 'insideBottomRight', offset: -2, fontSize: 10.5, fill: 'var(--color-ink-400)' }} height={34} />
          <YAxis tickFormatter={(v: number) => usd(v)} tick={{ fontSize: 11, fill: 'var(--color-ink-500)' }} tickLine={false} axisLine={false} width={58} />
          <ReferenceLine x={100} stroke="var(--color-ink-300)" strokeDasharray="3 3" label={{ value: '1-in-100', position: 'top', fontSize: 10.5, fill: 'var(--color-ink-500)' }} />
          <ReferenceLine x={250} stroke="var(--color-ink-300)" strokeDasharray="3 3" label={{ value: '1-in-250', position: 'top', fontSize: 10.5, fill: 'var(--color-ink-500)' }} />
          <Tooltip content={<EpTooltip labels={compare?.map((c) => c.label) ?? []} />} cursor={{ stroke: 'var(--color-ink-300)' }} />
          {compare?.map((c, i) => (
            <Line key={c.label} dataKey={`c${i}`} name={c.label} stroke={CMP_COLORS[i % CMP_COLORS.length]} strokeWidth={1.25} dot={false} isAnimationActive={false} connectNulls />
          ))}
          {aep && <Line dataKey="aep" name="AEP" stroke="var(--color-ink-700)" strokeWidth={1.5} strokeDasharray="5 4" dot={false} isAnimationActive={false} connectNulls />}
          <Line dataKey="oep" name="OEP" stroke="var(--color-accent-600)" strokeWidth={2.25} dot={{ r: 2.5, fill: 'var(--color-accent-600)', strokeWidth: 0 }}
            activeDot={{ r: 4.5, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LegendItem({ color, label, dashed, thin }: { color: string; label: string; dashed?: boolean; thin?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <svg width="18" height="6"><line x1="0" y1="3" x2="18" y2="3" stroke={color} strokeWidth={thin ? 1.25 : 2} strokeDasharray={dashed ? '4 3' : undefined} /></svg>
      {label}
    </span>
  );
}

function EpTooltip({ active, payload, label, labels }: { active?: boolean; payload?: { dataKey: string; value: number; color: string }[]; label?: number; labels: string[] }) {
  if (!active || !payload?.length) return null;
  const name = (k: string) => (k === 'oep' ? 'OEP' : k === 'aep' ? 'AEP' : labels[+k.slice(1)] ?? k);
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-[12px] shadow-[var(--shadow-pop)]">
      <div className="mb-1 font-semibold text-ink-900">1-in-{label} yr <span className="font-normal text-ink-500">· {(100 / (label ?? 1)).toFixed(label && label >= 1000 ? 2 : 1)}% annual</span></div>
      {[...payload].reverse().map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-ink-600"><span className="size-2 rounded-full" style={{ background: p.color }} />{name(p.dataKey)}</span>
          <span className="num font-medium text-ink-900">{usd(p.value)}</span>
        </div>
      ))}
    </div>
  );
}
