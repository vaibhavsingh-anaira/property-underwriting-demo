// Spreadsheet viewer for XlsxPayload: merged cells, hidden rows/cols (collapsed markers),
// frozen panes, number formats, virtualised rows, anchor cell/range highlight.
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Eye, EyeOff, FunctionSquare } from 'lucide-react';
import type { Anchor, XlsxCell, XlsxPayload, XlsxSheet } from '@/api/types';
import { cx } from '@/components/ui';
import { cssSize, numToCol, parseCell, parseRange } from './util';
import './viewers.css';

export interface XlsxViewerProps { payload: XlsxPayload; anchor?: Anchor | null; height?: number | string }

const ROW_H = 24, GAP = 7, HDR_W = 46, COL_HDR_H = 22;

// ------------------------------------------------------------------ formats
function decimalsOf(fmt: string) { const m = /\.(0+)/.exec(fmt); return m ? m[1].length : 0; }
function excelSerialToDate(n: number) { return new Date(Math.round((n - 25569) * 86400 * 1000)); }
export function formatCell(c: XlsxCell | undefined): string {
  if (!c || c.v === null || c.v === undefined || c.t === 'z') return '';
  if (c.t === 'b' || typeof c.v === 'boolean') return c.v ? 'TRUE' : 'FALSE';
  if (c.t === 'd' && typeof c.v === 'string') {
    const d = new Date(c.v.length === 10 ? c.v + 'T00:00:00' : c.v);
    return Number.isNaN(+d) ? c.v : d.toLocaleDateString('en-US');
  }
  if (typeof c.v === 'string') return c.v;
  let v = c.v;
  const fmt = (c.num_fmt ?? 'General').split(';')[0];
  if (fmt === 'General' || fmt === '@') return Number.isInteger(v) ? String(v) : String(+v.toPrecision(10));
  if (/[dmy]{2}/i.test(fmt) && !fmt.includes('0')) return excelSerialToDate(v).toLocaleDateString('en-US', { timeZone: 'UTC' });
  const d = decimalsOf(fmt);
  if (fmt.includes('%')) return `${(v * 100).toFixed(d)}%`;
  const scaleCommas = /(,+)(?:["\w\s)]*)$/.exec(fmt.replace(/\\./g, ''));
  if (scaleCommas && /0,+/.test(fmt)) v = v / 1000 ** scaleCommas[1].length;
  const neg = v < 0;
  const body = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: fmt.includes('#,') || fmt.includes('0,0') });
  const cur = fmt.includes('$') ? '$' : '';
  return neg ? (fmt.includes('(') ? `(${cur}${body})` : `−${cur}${body}`) : `${cur}${body}`;
}
const colPx = (s: XlsxSheet, c: string) => { const w = s.col_widths?.[c]; return w ? Math.round(w * 7 + 12) : 76; };
function normFill(f?: string) {
  if (!f) return undefined;
  const h = f.replace('#', '');
  const hex = h.length === 8 ? h.slice(2) : h.length === 6 ? h : null;
  if (!hex || /^0{6}$/.test(hex) && h.length === 8 && h.startsWith('00')) return undefined;
  return `#${hex}`;
}
function isDark(hex: string) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b < 110;
}

type ColItem = { kind: 'col'; c: number; w: number; hidden: boolean; left: number } | { kind: 'gap'; cols: number[]; w: number; left: number };
type RowItem = { kind: 'row'; r: number; h: number; hidden: boolean } | { kind: 'gap'; rows: number[]; h: number };

// ------------------------------------------------------------------ component
export function XlsxViewer({ payload, anchor, height = 560 }: XlsxViewerProps) {
  const sheets = payload.sheets;
  const [si, setSi] = useState(() => Math.max(0, sheets.findIndex((s) => s.name === anchor?.sheet)));
  const [showHidden, setShowHidden] = useState(false);
  const [sel, setSel] = useState<string | null>(anchor?.cell ?? null);
  const sheet = sheets[Math.min(si, sheets.length - 1)];
  const scrollRef = useRef<HTMLDivElement>(null);

  // anchor → switch sheet, select cell, reveal hidden if needed
  const anchorKey = `${anchor?.sheet}|${anchor?.cell}|${anchor?.range}`;
  useEffect(() => {
    if (!anchor) return;
    const idx = sheets.findIndex((s) => s.name === anchor.sheet);
    if (idx >= 0) setSi(idx);
    if (anchor.cell) setSel(anchor.cell);
    const s = sheets[idx >= 0 ? idx : si];
    const p = anchor.cell ? parseCell(anchor.cell) : null;
    if (s && p && (s.hidden_rows.includes(p.row) || s.hidden_cols.includes(numToCol(p.col)))) setShowHidden(true);
  }, [anchorKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const model = useMemo(() => buildModel(sheet, showHidden), [sheet, showHidden]);
  const anchorOnSheet = anchor && (!anchor.sheet || anchor.sheet === sheet.name) ? anchor : null;
  const anchorCell = anchorOnSheet?.cell ? parseCell(anchorOnSheet.cell) : null;
  const anchorRange = anchorOnSheet?.range ? parseRange(anchorOnSheet.range) : null;

  const headerH = COL_HDR_H + model.frozen.reduce((a, r) => a + r.h, 0);
  const virt = useVirtualizer({
    count: model.body.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => model.body[i].h,
    overscan: 16,
    scrollMargin: headerH,
  });
  useEffect(() => { virt.measure(); }, [model, virt]);

  // scroll anchor into view
  useEffect(() => {
    if (!anchorCell) return;
    const id = requestAnimationFrame(() => {
      const sc = scrollRef.current; if (!sc) return;
      const bi = model.body.findIndex((it) => it.kind === 'row' && it.r === anchorCell.row);
      if (bi >= 0) virt.scrollToIndex(bi, { align: 'center' });
      const ci = model.cols.find((c) => c.kind === 'col' && c.c === anchorCell.col);
      if (ci) {
        const target = ci.left - HDR_W - model.frozenW - 80;
        if (ci.left + ci.w > sc.scrollLeft + sc.clientWidth || ci.left - HDR_W - model.frozenW < sc.scrollLeft) sc.scrollTo({ left: Math.max(0, target), behavior: 'smooth' });
      }
    });
    return () => cancelAnimationFrame(id);
  }, [anchorKey, si, model]); // eslint-disable-line react-hooks/exhaustive-deps

  const selCell = sel ? sheet.cells[sel.toUpperCase()] : undefined;
  const hiddenCount = sheet.hidden_rows.length + sheet.hidden_cols.length;

  const rowProps = { sheet, model, sel, setSel, anchorCell, anchorRange };
  return (
    <div className="flex min-h-0 flex-col overflow-hidden bg-surface" style={{ height: cssSize(height, 560) }}>
      {/* formula bar */}
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-line bg-surface px-2 text-[12px]">
        <div className="mono flex h-6 w-[72px] items-center justify-center rounded border border-line bg-ink-50 text-[11.5px] font-medium text-ink-800">{sel?.toUpperCase() ?? '—'}</div>
        <FunctionSquare className="size-4 shrink-0 text-ink-400" />
        <div className={cx('mono min-w-0 flex-1 truncate text-[12px]', selCell?.f ? 'text-accent-700' : 'text-ink-800')}>
          {selCell ? (selCell.f ? (selCell.f.startsWith('=') ? selCell.f : `=${selCell.f}`) : String(selCell.v ?? '')) : <span className="font-sans text-ink-400">Select a cell</span>}
        </div>
        {selCell && (
          <div className="flex shrink-0 items-center gap-2 text-[11px] text-ink-500">
            {selCell.f && <span>value <span className="mono text-ink-800">{String(selCell.v)}</span></span>}
            {selCell.num_fmt && <span className="mono rounded bg-ink-100 px-1 text-ink-600">{selCell.num_fmt}</span>}
            <span className="rounded bg-ink-100 px-1 uppercase text-ink-600">{ { s: 'text', n: 'number', b: 'bool', d: 'date', f: 'formula', z: 'blank' }[selCell.t] }</span>
          </div>
        )}
      </div>

      {/* grid */}
      <div ref={scrollRef} className="relative min-h-0 flex-1 overflow-auto bg-surface text-[12px]">
        <div style={{ width: model.totalW, minWidth: '100%' }}>
          <div className="sticky top-0 z-[4] bg-surface" style={{ width: model.totalW }}>
            <div className="flex border-b border-line-strong bg-ink-50" style={{ height: COL_HDR_H }}>
              <div className="sticky left-0 z-[3] shrink-0 border-r border-line-strong bg-ink-50" style={{ width: HDR_W }} />
              {model.cols.map((c, i) => c.kind === 'gap' ? (
                <button key={'g' + i} onClick={() => setShowHidden(true)} title={`Hidden column${c.cols.length > 1 ? 's' : ''} ${c.cols.map(numToCol).join(', ')} — click to show`}
                  className="shrink-0 border-r border-line bg-[repeating-linear-gradient(90deg,var(--color-ink-300)_0_1px,transparent_1px_3px)] hover:bg-accent-100"
                  style={{ width: c.w, ...stickyCol(c, model) }} />
              ) : (
                <div key={c.c} className={cx('flex shrink-0 items-center justify-center border-r border-line text-[11px] font-medium',
                  anchorCell?.col === c.c || parseCell(sel ?? '')?.col === c.c ? 'bg-accent-100 text-accent-700' : 'text-ink-500',
                  c.hidden && 'bg-med-bg text-med')} style={{ width: c.w, ...stickyCol(c, model, 'var(--color-ink-50)') }}>
                  {c.hidden && <EyeOff className="mr-0.5 size-2.5" />}{numToCol(c.c)}
                </div>
              ))}
            </div>
            {model.frozen.map((it, i) => <GridRow key={'f' + i} it={it} {...rowProps} frozenRow />)}
            {model.frozen.length > 0 && <div className="h-0 border-b-2 border-ink-300" />}
          </div>
          <div className="relative" style={{ height: virt.getTotalSize() }}>
            {virt.getVirtualItems().map((vi) => (
              <div key={vi.key} className="absolute left-0" style={{ top: vi.start - headerH, height: vi.size, width: model.totalW }}>
                <GridRow it={model.body[vi.index]} {...rowProps} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* sheet tabs */}
      <div className="flex h-9 shrink-0 items-center gap-0.5 border-t border-line bg-ink-50 px-1.5">
        {sheets.map((s, i) => (
          <button key={s.name} onClick={() => setSi(i)} title={s.hidden ? 'Hidden sheet' : undefined}
            className={cx('-mt-px inline-flex h-7 items-center gap-1.5 rounded-b-md border border-t-0 px-3 text-[12px] font-medium transition-colors',
              i === si ? 'border-line-strong bg-surface text-ink-950 shadow-[0_1px_0_var(--color-accent-500)_inset]' : 'border-transparent text-ink-500 hover:bg-ink-100 hover:text-ink-800',
              s.hidden && 'italic')}>
            {s.hidden && <EyeOff className="size-3 text-ink-400" />}{s.name}
            {anchor?.sheet === s.name && <span className="size-1.5 rounded-full bg-accent-500" />}
          </button>
        ))}
        <div className="flex-1" />
        <span className="num mr-2 text-[11px] text-ink-400">{sheet.max_row} rows × {sheet.max_col} cols{sheet.freeze ? ` · frozen at ${sheet.freeze}` : ''}</span>
        {hiddenCount > 0 && (
          <button onClick={() => setShowHidden((v) => !v)}
            className={cx('inline-flex h-6 items-center gap-1 rounded-md border px-2 text-[11.5px] font-medium',
              showHidden ? 'border-[#efdf9f] bg-med-bg text-med' : 'border-line-strong bg-surface text-ink-700 hover:bg-ink-50')}>
            {showHidden ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
            {showHidden ? 'Hide' : 'Show'} hidden ({hiddenCount})
          </button>
        )}
      </div>
    </div>
  );
}

function stickyCol(c: ColItem, m: Model, bg?: string): CSSProperties {
  if (c.kind === 'col' && c.c <= m.frozenCols) return { position: 'sticky', left: c.left, zIndex: 2, background: bg ?? 'var(--color-surface)' };
  return {};
}

// ------------------------------------------------------------------ model
interface Model {
  cols: ColItem[]; frozen: RowItem[]; body: RowItem[]; totalW: number;
  frozenCols: number; frozenW: number; colLeft: Map<number, number>; colW: Map<number, number>;
  merges: Map<string, { r0: number; r1: number; c0: number; c1: number }>; covered: Set<string>;
  rowH: Map<number, number>;
}
function buildModel(s: XlsxSheet, showHidden: boolean): Model {
  const fz = s.freeze ? parseCell(s.freeze) : null;
  const frozenRows = fz ? fz.row - 1 : 0, frozenCols = fz ? fz.col - 1 : 0;
  const hc = new Set(s.hidden_cols.map((c) => c.toUpperCase())), hr = new Set(s.hidden_rows);
  const cols: ColItem[] = []; let left = HDR_W;
  const colLeft = new Map<number, number>(), colW = new Map<number, number>();
  for (let c = 1; c <= Math.max(1, s.max_col); c++) {
    const L = numToCol(c), hidden = hc.has(L);
    if (hidden && !showHidden) {
      const last = cols[cols.length - 1];
      if (last?.kind === 'gap') last.cols.push(c); else { cols.push({ kind: 'gap', cols: [c], w: GAP, left }); left += GAP; }
      colW.set(c, 0); colLeft.set(c, left);
      continue;
    }
    const w = colPx(s, L);
    cols.push({ kind: 'col', c, w, hidden, left }); colLeft.set(c, left); colW.set(c, w); left += w;
  }
  const frozenW = cols.filter((c) => c.kind === 'col' && c.c <= frozenCols).reduce((a, c) => a + c.w, 0);
  const rows: RowItem[] = [];
  const rowH = new Map<number, number>();
  for (let r = 1; r <= Math.max(1, s.max_row); r++) {
    const hidden = hr.has(r);
    if (hidden && !showHidden) {
      const last = rows[rows.length - 1];
      if (last?.kind === 'gap') last.rows.push(r); else rows.push({ kind: 'gap', rows: [r], h: GAP });
      rowH.set(r, 0);
      continue;
    }
    rows.push({ kind: 'row', r, h: ROW_H, hidden }); rowH.set(r, ROW_H);
  }
  const isFrozen = (it: RowItem) => (it.kind === 'row' ? it.r : it.rows[0]) <= frozenRows;
  const merges = new Map<string, { r0: number; r1: number; c0: number; c1: number }>(), covered = new Set<string>();
  for (const m of s.merges) {
    const p = parseRange(m); if (!p) continue;
    merges.set(`${numToCol(p.c0)}${p.r0}`, p);
    for (let r = p.r0; r <= p.r1; r++) for (let c = p.c0; c <= p.c1; c++) if (r !== p.r0 || c !== p.c0) covered.add(`${numToCol(c)}${r}`);
  }
  return { cols, frozen: rows.filter(isFrozen), body: rows.filter((r) => !isFrozen(r)), totalW: left, frozenCols, frozenW, colLeft, colW, merges, covered, rowH };
}

// ------------------------------------------------------------------ row
function GridRow({ it, sheet, model, sel, setSel, anchorCell, anchorRange, frozenRow }: {
  it: RowItem; sheet: XlsxSheet; model: Model; sel: string | null; setSel: (a: string) => void;
  anchorCell: { row: number; col: number } | null; anchorRange: { r0: number; r1: number; c0: number; c1: number } | null; frozenRow?: boolean;
}) {
  if (it.kind === 'gap') {
    return (
      <div className="flex border-b border-line" style={{ height: it.h, width: model.totalW }} title={`Hidden row${it.rows.length > 1 ? 's' : ''} ${it.rows.join(', ')}`}>
        <div className="sticky left-0 z-[3] flex shrink-0 items-center justify-center border-r border-line-strong bg-ink-50" style={{ width: HDR_W }}>
          <span className="h-[3px] w-5 rounded bg-med" />
        </div>
        <div className="flex-1 bg-[repeating-linear-gradient(0deg,var(--color-ink-300)_0_1px,transparent_1px_3px)] opacity-60" />
      </div>
    );
  }
  const r = it.r;
  const inRangeRow = anchorRange && r >= anchorRange.r0 && r <= anchorRange.r1;
  const selRow = parseCell(sel ?? '')?.row === r;
  return (
    <div className={cx('flex', it.hidden && 'bg-med-bg/60')} style={{ height: it.h, width: model.totalW }}>
      <div className={cx('sticky left-0 z-[3] flex shrink-0 items-center justify-end gap-0.5 border-b border-r border-line-strong pr-1.5 text-[11px] num',
        anchorCell?.row === r || selRow ? 'bg-accent-100 font-semibold text-accent-700' : inRangeRow ? 'bg-accent-50 text-accent-700' : it.hidden ? 'bg-med-bg text-med' : 'bg-ink-50 text-ink-500')}
        style={{ width: HDR_W }}>
        {it.hidden && <EyeOff className="size-2.5" />}{r}
      </div>
      {model.cols.map((c, i) => {
        if (c.kind === 'gap') return <div key={'g' + i} className="shrink-0 border-b border-r border-line bg-ink-50" style={{ width: c.w }} />;
        const addr = `${numToCol(c.c)}${r}`;
        if (model.covered.has(addr)) {
          // covered by a merge: render nothing, but keep flow width if the merge starts in a different row
          const owner = [...model.merges.values()].find((m) => r >= m.r0 && r <= m.r1 && c.c >= m.c0 && c.c <= m.c1);
          if (owner && owner.r0 === r) return null;
          return <div key={addr} className="shrink-0" style={{ width: c.w }} />;
        }
        const cell = sheet.cells[addr];
        const m = model.merges.get(addr);
        let w = c.w, h = it.h;
        if (m) {
          w = 0; for (let k = m.c0; k <= m.c1; k++) w += model.colW.get(k) ?? 0;
          w += model.cols.filter((x) => x.kind === 'gap' && x.cols[0] > m.c0 && x.cols[0] <= m.c1).length * GAP;
          h = 0; for (let k = m.r0; k <= m.r1; k++) h += model.rowH.get(k) ?? 0;
        }
        const fill = normFill(cell?.fill);
        const numeric = cell && (typeof cell.v === 'number') && cell.t !== 's';
        const isSel = sel?.toUpperCase() === addr;
        const isAnchor = anchorCell && anchorCell.row === r && anchorCell.col === c.c;
        const inRange = inRangeRow && c.c >= anchorRange!.c0 && c.c <= anchorRange!.c1;
        const style: CSSProperties = { width: w, height: h, ...(fill ? { background: fill, color: isDark(fill) ? '#fff' : undefined } : {}), ...(m ? {} : stickyCol(c, model, fill ?? (inRange ? 'var(--color-accent-50)' : it.hidden ? '#fdf6de' : 'var(--color-surface)'))) };
        // merged cells scroll with the grid; their text sticks to the frozen edge so titles stay readable
        if (m) { style.position = 'relative'; style.zIndex = 1; if (!fill) style.background = 'var(--color-surface)'; }
        return (
          <div key={addr} onClick={() => setSel(addr)} style={style}
            className={cx('flex shrink-0 cursor-cell items-center whitespace-nowrap border-b border-r border-line px-1.5 text-ink-900', m ? 'overflow-visible' : 'overflow-hidden',
              numeric ? 'justify-end num' : 'justify-start', cell?.bold && 'font-semibold', m && 'justify-start',
              !fill && inRange && 'bg-accent-50', !fill && c.hidden && !inRange && 'bg-med-bg/60', cell?.f && !fill && 'text-ink-800',
              isSel && !isAnchor && 'shadow-[inset_0_0_0_2px_var(--color-ink-800)]', isAnchor && 'cell-anchor relative z-[1]',
              frozenRow && !fill && !inRange && 'bg-surface')}>
            {m ? <span className="sticky" style={{ left: HDR_W + 8 }}>{formatCell(cell)}</span> : <span className="truncate">{formatCell(cell)}</span>}
          </div>
        );
      })}
    </div>
  );
}
