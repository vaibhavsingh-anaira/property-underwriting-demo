// PDF viewer: pdf.js v5, lazy per-page canvas render at devicePixelRatio,
// fit-width zoom, text layer, and bbox highlight overlays (PDF points, top-left origin).
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import * as pdfjs from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { ChevronDown, ChevronUp, Minus, Plus, MoveHorizontal } from 'lucide-react';
import type { Anchor } from '@/api/types';
import { cx, ErrorBox, Loading } from '@/components/ui';
import { cssSize, useElementWidth } from './util';
import './viewers.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

export interface PdfHighlight { page: number; bbox: [number, number, number, number]; label?: string }
export interface PdfViewerProps {
  url: string;
  anchor?: Anchor | null;
  highlights?: PdfHighlight[];
  height?: number | string;
  toolbarExtra?: ReactNode;
}

const GAP = 14, PAD = 16;

export function PdfViewer({ url, anchor, highlights, height = '100%', toolbarExtra }: PdfViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const width = useElementWidth(scrollRef);
  const [doc, setDoc] = useState<{ pdf: PDFDocumentProxy; sizes: [number, number][] } | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [zoom, setZoom] = useState<number | 'fit'>('fit');
  const [current, setCurrent] = useState(1);
  const pageEls = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    setDoc(null); setErr(null);
    const task = pdfjs.getDocument({ url });
    let alive = true;
    task.promise.then(async (pdf) => {
      const sizes: [number, number][] = [];
      for (let i = 1; i <= pdf.numPages; i++) {
        const vp = (await pdf.getPage(i)).getViewport({ scale: 1 });
        sizes.push([vp.width, vp.height]);
      }
      if (alive) setDoc({ pdf, sizes });
    }).catch((e) => { if (alive) setErr(e); });
    return () => { alive = false; void task.destroy(); };
  }, [url]);

  const maxW = doc ? Math.max(...doc.sizes.map((s) => s[0])) : 612;
  const fitScale = width > 0 ? Math.max(0.3, (width - PAD * 2) / maxW) : 1;
  const scale = zoom === 'fit' ? fitScale : zoom;

  const active: PdfHighlight | null = useMemo(() => (anchor?.kind === 'pdf' && anchor.page && anchor.bbox) ? { page: anchor.page, bbox: anchor.bbox, label: anchor.text } : null, [anchor]);
  const all = useMemo(() => {
    const list = [...(highlights ?? [])];
    if (active && !list.some((h) => h.page === active.page && h.bbox.join() === active.bbox.join())) list.push(active);
    return list;
  }, [highlights, active]);

  // scroll anchor (or anchored page) into view
  const anchorKey = anchor ? `${anchor.page}|${anchor.bbox?.join()}` : '';
  const lastKey = useRef('');
  useEffect(() => {
    if (!doc || !anchor?.page || width === 0) return;
    const el = pageEls.current[anchor.page - 1], sc = scrollRef.current;
    if (!el || !sc) return;
    const y = el.offsetTop + (anchor.bbox ? anchor.bbox[1] * scale : 0) - (anchor.bbox ? sc.clientHeight * 0.3 : PAD);
    const smooth = lastKey.current !== anchorKey && lastKey.current !== '';
    lastKey.current = anchorKey;
    const x = anchor.bbox ? Math.max(0, anchor.bbox[0] * scale - 40) : 0;
    sc.scrollTo({ top: Math.max(0, y), left: sc.scrollWidth > sc.clientWidth ? x : 0, behavior: smooth ? 'smooth' : 'auto' });
  }, [doc, anchorKey, scale, width]); // eslint-disable-line react-hooks/exhaustive-deps

  const onScroll = useCallback(() => {
    const sc = scrollRef.current; if (!sc) return;
    const probe = sc.scrollTop + sc.clientHeight * 0.35;
    let p = 1;
    pageEls.current.forEach((el, i) => { if (el && el.offsetTop <= probe) p = i + 1; });
    setCurrent(p);
  }, []);

  const goto = (p: number) => {
    if (!doc) return;
    const n = Math.min(doc.sizes.length, Math.max(1, p));
    const el = pageEls.current[n - 1];
    if (el) scrollRef.current?.scrollTo({ top: el.offsetTop - PAD, behavior: 'smooth' });
  };
  const step = (dir: 1 | -1) => setZoom(Math.min(4, Math.max(0.3, +(scale * (dir > 0 ? 1.2 : 1 / 1.2)).toFixed(3))));

  return (
    <div className="flex min-h-0 flex-col overflow-hidden bg-ink-100" style={{ height: cssSize(height, '100%') }}>
      <div className="flex h-9 shrink-0 items-center gap-1 border-b border-line bg-surface px-2 text-[12px] text-ink-600">
        <IconBtn onClick={() => goto(current - 1)} disabled={current <= 1} title="Previous page"><ChevronUp className="size-3.5" /></IconBtn>
        <IconBtn onClick={() => goto(current + 1)} disabled={!doc || current >= doc.sizes.length} title="Next page"><ChevronDown className="size-3.5" /></IconBtn>
        <span className="num ml-1 min-w-[56px] text-ink-800">{doc ? `${current} / ${doc.sizes.length}` : '—'}</span>
        <div className="mx-2 h-4 w-px bg-line" />
        <IconBtn onClick={() => step(-1)} title="Zoom out"><Minus className="size-3.5" /></IconBtn>
        <span className="num w-11 text-center text-ink-800">{Math.round(scale * 100)}%</span>
        <IconBtn onClick={() => step(1)} title="Zoom in"><Plus className="size-3.5" /></IconBtn>
        <button onClick={() => setZoom('fit')} title="Fit width"
          className={cx('ml-1 inline-flex h-6 items-center gap-1 rounded px-1.5 font-medium', zoom === 'fit' ? 'bg-accent-50 text-accent-700' : 'hover:bg-ink-100')}>
          <MoveHorizontal className="size-3.5" />Fit
        </button>
        <div className="flex-1" />
        {all.length > 0 && <span className="text-ink-500">{all.length} highlight{all.length > 1 ? 's' : ''}</span>}
        {toolbarExtra}
      </div>
      <div ref={scrollRef} onScroll={onScroll} className="relative min-h-0 flex-1 overflow-auto" style={{ padding: PAD }}>
        {err ? <ErrorBox error={err} /> : !doc ? <Loading label="Loading PDF…" /> : (
          <div className="mx-auto flex w-max flex-col" style={{ gap: GAP }}>
            {doc.sizes.map((s, i) => (
              <PdfPage key={i} pdf={doc.pdf} n={i + 1} size={s} scale={scale} root={scrollRef}
                ref={(el) => { pageEls.current[i] = el; }}
                highlights={all.filter((h) => h.page === i + 1)} active={active} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IconBtn({ children, ...p }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...p} className="inline-flex size-6 items-center justify-center rounded text-ink-600 hover:bg-ink-100 disabled:opacity-30">{children}</button>;
}

function PdfPage({ pdf, n, size, scale, root, highlights, active, ref }: {
  pdf: PDFDocumentProxy; n: number; size: [number, number]; scale: number; root: React.RefObject<HTMLDivElement | null>;
  highlights: PdfHighlight[]; active: PdfHighlight | null; ref: (el: HTMLDivElement | null) => void;
}) {
  const box = useRef<HTMLDivElement | null>(null);
  const canvasHost = useRef<HTMLDivElement>(null);
  const textHost = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    const el = box.current; if (!el) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { root: root.current, rootMargin: '800px 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, [root]);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    let renderTask: ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']> | null = null;
    let textLayer: pdfjs.TextLayer | null = null;
    (async () => {
      const page = await pdf.getPage(n);
      if (cancelled) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      const vp = page.getViewport({ scale: scale * dpr });
      const canvas = document.createElement('canvas');
      canvas.width = Math.floor(vp.width); canvas.height = Math.floor(vp.height);
      canvas.style.width = '100%'; canvas.style.height = '100%'; canvas.style.display = 'block';
      renderTask = page.render({ canvas, viewport: vp });
      try { await renderTask.promise; } catch { return; }
      if (cancelled) return;
      canvasHost.current?.replaceChildren(canvas);
      setRendered(true);
      const th = textHost.current;
      if (th) {
        th.replaceChildren();
        textLayer = new pdfjs.TextLayer({ textContentSource: page.streamTextContent(), container: th, viewport: page.getViewport({ scale }) });
        try { await textLayer.render(); } catch { /* cancelled */ }
      }
    })();
    return () => { cancelled = true; renderTask?.cancel(); textLayer?.cancel(); };
  }, [visible, pdf, n, scale]);

  const w = size[0] * scale, h = size[1] * scale;
  return (
    <div ref={(el) => { box.current = el; ref(el); }} className="pdf-page relative bg-white shadow-[0_1px_3px_rgba(16,24,40,.12),0_0_0_1px_rgba(16,24,40,.04)]"
      style={{ width: w, height: h, ['--scale-factor' as string]: scale }}>
      <div ref={canvasHost} className="absolute inset-0" />
      {!rendered && <div className="absolute inset-0 flex items-center justify-center text-[12px] text-ink-300">Page {n}</div>}
      <div ref={textHost} className="textLayer" />
      {highlights.map((hl, i) => {
        const [x0, t, x1, b] = hl.bbox;
        const isActive = !!active && active.page === hl.page && active.bbox.join() === hl.bbox.join();
        return (
          <div key={i} className={cx('hl-in pointer-events-none absolute z-[2] rounded-[3px] border-2 border-accent-500 bg-accent-500/15', isActive && 'pulse-ring')}
            style={{ left: x0 * scale - 2, top: t * scale - 2, width: (x1 - x0) * scale + 4, height: (b - t) * scale + 4 }}>
            {hl.label && (
              <span className="absolute -top-[21px] left-[-2px] whitespace-nowrap rounded-[4px] bg-accent-600 px-1.5 py-[1px] text-[10.5px] font-medium leading-[16px] text-white shadow-sm">{hl.label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
