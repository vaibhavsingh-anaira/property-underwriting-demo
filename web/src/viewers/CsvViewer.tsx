// CSV viewer: RFC-4180 parse, sortable virtualised table.
// CAT event loss tables get a summary strip + loss histogram; OED location files get a totals strip.
import { useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { cx } from '@/components/ui';
import { num, usd } from '@/lib/format';
import { cssSize } from './util';

export interface CsvViewerProps { text: string; docType?: string; height?: number | string; highlightRow?: number | null }

export function parseCsv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = []; let f = ''; let q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
      else f += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(f); f = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(f); f = ''; rows.push(row); row = [];
    } else f += ch;
  }
  if (f !== '' || row.length) { row.push(f); rows.push(row); }
  return rows.filter((r) => r.length > 1 || r[0] !== '');
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const ROW_H = 28;

export function CsvViewer({ text, docType, height = 520, highlightRow }: CsvViewerProps) {
  const { header, rows, numeric } = useMemo(() => {
    const all = parseCsv(text);
    const header = all[0] ?? [];
    const rows = all.slice(1);
    const numeric = header.map((_, c) => rows.length > 0 && rows.slice(0, 200).every((r) => r[c] === undefined || r[c] === '' || !Number.isNaN(Number(r[c]))));
    return { header, rows, numeric };
  }, [text]);
  const idx = (names: string[]) => header.findIndex((h) => names.includes(norm(h)));
  const elt = { id: idx(['eventid', 'event']), rate: idx(['rate', 'annualrate', 'freq']), loss: idx(['meanloss', 'loss', 'perspvalue']) };
  const isElt = (elt.id >= 0 && elt.rate >= 0 && elt.loss >= 0) || /event loss/i.test(docType ?? '');
  const oed = { loc: idx(['locnumber']), b: idx(['buildingtiv']), o: idx(['othertiv']), c: idx(['contentstiv']), bi: idx(['bitiv']), st: idx(['areacode', 'state']) };
  const isOed = oed.loc >= 0 && oed.b >= 0;

  const [sort, setSort] = useState<{ c: number; dir: 1 | -1 } | null>(null);
  const sorted = useMemo(() => {
    const withIdx = rows.map((r, i) => ({ r, i }));
    if (!sort) return withIdx;
    const { c, dir } = sort;
    return withIdx.sort((a, b) => (numeric[c] ? (Number(a.r[c]) - Number(b.r[c])) : (a.r[c] ?? '').localeCompare(b.r[c] ?? '')) * dir);
  }, [rows, sort, numeric]);

  const scroll = useRef<HTMLDivElement>(null);
  const virt = useVirtualizer({ count: sorted.length, getScrollElement: () => scroll.current, estimateSize: () => ROW_H, overscan: 20 });
  const colW = header.map((h, c) => Math.min(260, Math.max(64, h.length * 7.5 + 28, ...rows.slice(0, 50).map((r) => (r[c]?.length ?? 0) * 7 + 20))));
  const totalW = colW.reduce((a, b) => a + b, 0) + 48;

  return (
    <div className="flex min-h-0 flex-col bg-surface" style={{ height: cssSize(height, 520) }}>
      {isElt && elt.rate >= 0 && elt.loss >= 0 && <EltSummary rows={rows} rate={elt.rate} loss={elt.loss} />}
      {isOed && <OedSummary rows={rows} ix={oed} />}
      <div ref={scroll} className="min-h-0 flex-1 overflow-auto text-[12px]">
        <div style={{ width: totalW, minWidth: '100%' }}>
          <div className="sticky top-0 z-[2] flex border-b border-line bg-ink-50">
            <div className="shrink-0 border-r border-line" style={{ width: 48 }} />
            {header.map((h, c) => (
              <button key={c} onClick={() => setSort((s) => (s?.c === c ? (s.dir === 1 ? { c, dir: -1 } : null) : { c, dir: 1 }))}
                className={cx('flex h-8 shrink-0 items-center gap-1 border-r border-line px-2.5 text-[11px] font-medium uppercase tracking-[.03em] text-ink-500 hover:bg-ink-100 hover:text-ink-800', numeric[c] && 'justify-end')}
                style={{ width: colW[c] }} title={h}>
                <span className="truncate">{h}</span>
                {sort?.c === c && (sort.dir === 1 ? <ArrowUp className="size-3 shrink-0 text-accent-600" /> : <ArrowDown className="size-3 shrink-0 text-accent-600" />)}
              </button>
            ))}
          </div>
          <div className="relative" style={{ height: virt.getTotalSize() }}>
            {virt.getVirtualItems().map((vi) => {
              const { r, i } = sorted[vi.index];
              return (
                <div key={vi.key} className={cx('absolute left-0 flex border-b border-line hover:bg-[#fafbfd]', highlightRow === i + 1 && 'bg-accent-50')} style={{ top: vi.start, height: ROW_H, width: '100%' }}>
                  <div className="num flex shrink-0 items-center justify-end border-r border-line bg-ink-50/60 pr-2 text-[11px] text-ink-400" style={{ width: 48 }}>{i + 1}</div>
                  {header.map((_, c) => (
                    <div key={c} className={cx('flex shrink-0 items-center overflow-hidden whitespace-nowrap border-r border-line/60 px-2.5 text-ink-800', numeric[c] && 'num justify-end')} style={{ width: colW[c] }}>
                      <span className="truncate">{fmtCsv(r[c], numeric[c])}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="flex h-7 shrink-0 items-center gap-3 border-t border-line bg-ink-50 px-3 text-[11px] text-ink-500">
        <span className="num">{num(rows.length)} rows · {header.length} columns</span>
        {isElt && <span className="rounded bg-accent-50 px-1.5 text-accent-700">Detected: CAT event loss table</span>}
        {isOed && <span className="rounded bg-accent-50 px-1.5 text-accent-700">Detected: OED location file</span>}
      </div>
    </div>
  );
}

function fmtCsv(v: string | undefined, numeric: boolean) {
  if (v === undefined || v === '') return '';
  if (!numeric) return v;
  const n = Number(v);
  if (Math.abs(n) >= 10000 && Number.isInteger(n)) return n.toLocaleString('en-US');
  return v;
}

function Strip({ items }: { items: { k: string; v: string; sub?: string }[] }) {
  return (
    <div className="flex shrink-0 divide-x divide-line border-b border-line bg-surface">
      {items.map((it) => (
        <div key={it.k} className="min-w-0 flex-1 px-4 py-2.5">
          <div className="text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-500">{it.k}</div>
          <div className="num mt-0.5 text-[17px] font-semibold tracking-[-0.01em] text-ink-950">{it.v}</div>
          {it.sub && <div className="text-[11px] text-ink-400">{it.sub}</div>}
        </div>
      ))}
    </div>
  );
}

function EltSummary({ rows, rate, loss }: { rows: string[][]; rate: number; loss: number }) {
  const s = useMemo(() => {
    const ls = rows.map((r) => ({ rate: Number(r[rate]) || 0, loss: Number(r[loss]) || 0 }));
    const aal = ls.reduce((a, x) => a + x.rate * x.loss, 0);
    const freq = ls.reduce((a, x) => a + x.rate, 0);
    const max = Math.max(0, ...ls.map((x) => x.loss));
    // log-spaced histogram of mean loss
    const pos = ls.filter((x) => x.loss > 0);
    const lo = Math.log10(Math.max(1, Math.min(...pos.map((x) => x.loss)))), hi = Math.log10(max || 10);
    const nb = 18, w = (hi - lo) / nb || 1;
    const bins = Array.from({ length: nb }, (_, i) => ({ x0: 10 ** (lo + i * w), x1: 10 ** (lo + (i + 1) * w), count: 0, aal: 0 }));
    for (const x of pos) { const b = Math.min(nb - 1, Math.floor((Math.log10(x.loss) - lo) / w)); bins[b].count++; bins[b].aal += x.rate * x.loss; }
    return { aal, freq, max, bins, n: rows.length };
  }, [rows, rate, loss]);
  return (
    <div className="shrink-0">
      <Strip items={[{ k: 'Events', v: num(s.n) }, { k: 'AAL (Σ rate × mean loss)', v: usd(s.aal) }, { k: 'Annual event frequency', v: s.freq.toFixed(3) }, { k: 'Largest mean loss', v: usd(s.max) }]} />
      <div className="h-[128px] border-b border-line px-3 pb-1 pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={s.bins} margin={{ top: 4, right: 8, bottom: 0, left: 0 }} barCategoryGap={1}>
            <XAxis dataKey="x0" tickFormatter={(v: number) => usd(v)} tick={{ fontSize: 10, fill: 'var(--color-ink-400)' }} tickLine={false} axisLine={{ stroke: 'var(--color-line)' }} interval={2} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--color-ink-400)' }} tickLine={false} axisLine={false} width={28} allowDecimals={false} />
            <Tooltip cursor={{ fill: 'var(--color-ink-50)' }} content={({ active, payload }) => {
              const b = active && payload?.[0]?.payload as { x0: number; x1: number; count: number; aal: number } | undefined;
              return b ? (
                <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[11.5px] shadow-[var(--shadow-pop)]">
                  <div className="font-medium text-ink-900">{usd(b.x0)} – {usd(b.x1)}</div>
                  <div className="text-ink-500">{b.count} events · AAL {usd(b.aal)}</div>
                </div>
              ) : null;
            }} />
            <Bar dataKey="count" fill="var(--color-accent-500)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function OedSummary({ rows, ix }: { rows: string[][]; ix: { loc: number; b: number; o: number; c: number; bi: number; st: number } }) {
  const sum = (c: number) => (c < 0 ? 0 : rows.reduce((a, r) => a + (Number(r[c]) || 0), 0));
  const b = sum(ix.b), o = sum(ix.o), c = sum(ix.c), bi = sum(ix.bi);
  const states = ix.st >= 0 ? new Set(rows.map((r) => r[ix.st])).size : null;
  return <Strip items={[
    { k: 'Locations', v: num(new Set(rows.map((r) => r[ix.loc])).size), sub: states ? `${states} states` : undefined },
    { k: 'Building TIV', v: usd(b) }, { k: 'Contents TIV', v: usd(c) }, { k: 'BI TIV', v: usd(bi) },
    { k: 'Total TIV', v: usd(b + o + c + bi) },
  ]} />;
}
