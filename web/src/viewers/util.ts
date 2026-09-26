// Small shared helpers for viewers.
import { useEffect, useState, type RefObject } from 'react';
import type { Anchor } from '@/api/types';

export const colToNum = (c: string) => c.toUpperCase().split('').reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0);
export const numToCol = (n: number) => { let s = ''; while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); } return s; };
export function parseCell(a: string): { col: number; row: number } | null {
  const m = /^\$?([A-Za-z]+)\$?(\d+)$/.exec(a.trim());
  return m ? { col: colToNum(m[1]), row: parseInt(m[2], 10) } : null;
}
export function parseRange(r: string) {
  const [a, b] = r.split(':');
  const p = parseCell(a), q = parseCell(b ?? a);
  if (!p || !q) return null;
  return { c0: Math.min(p.col, q.col), c1: Math.max(p.col, q.col), r0: Math.min(p.row, q.row), r1: Math.max(p.row, q.row) };
}

/** "Sheet Locations · K14", "p.7", "PAS (mock) · POL-123". */
export function anchorSummary(a: Anchor | null | undefined): string {
  if (!a) return '—';
  switch (a.kind) {
    case 'pdf': return a.page ? `p.${a.page}` : 'PDF';
    case 'xlsx': return [a.sheet && `Sheet ${a.sheet}`, a.cell ?? a.range].filter(Boolean).join(' · ') || 'Spreadsheet';
    case 'eml': return a.text ? `Email · “${a.text.length > 28 ? a.text.slice(0, 28) + '…' : a.text}”` : 'Email body';
    case 'glb': return a.node ? `3D node ${a.node}` : '3D model';
    case 'system': case 'vendor': return [a.system, a.record_id].filter(Boolean).join(' · ') || a.kind;
    case 'json': return a.path ? `JSON ${a.path}` : 'JSON';
    case 'csv': return a.record_id ? `Row ${a.record_id}` : 'CSV';
    case 'image': return 'Image';
    case 'derived': return 'Derived';
    default: return a.kind;
  }
}

export function useElementWidth(ref: RefObject<HTMLElement | null>) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.floor(e.contentRect.width)));
    ro.observe(el);
    setW(el.clientWidth);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

export const cssSize = (v: number | string | undefined, d: number | string) => (v === undefined ? d : v);

export function fileExt(name: string) { const i = name.lastIndexOf('.'); return i >= 0 ? name.slice(i + 1).toLowerCase() : ''; }
