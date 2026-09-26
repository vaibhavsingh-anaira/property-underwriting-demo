// Zoom / pan image viewer. Wheel zooms around the cursor, drag pans, double-click toggles fit/2x.
import { useCallback, useEffect, useRef, useState } from 'react';
import { Minus, Plus, Maximize } from 'lucide-react';
import { cssSize } from './util';

export interface ImageViewerProps { url: string; alt?: string; height?: number | string }

export function ImageViewer({ url, alt = '', height = 520 }: ImageViewerProps) {
  const box = useRef<HTMLDivElement>(null);
  const [nat, setNat] = useState<{ w: number; h: number } | null>(null);
  const [t, setT] = useState({ k: 1, x: 0, y: 0 });
  const [fitK, setFitK] = useState(1);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);

  const fit = useCallback(() => {
    const el = box.current; if (!el || !nat) return;
    const k = Math.min(el.clientWidth / nat.w, el.clientHeight / nat.h);
    setFitK(k);
    setT({ k, x: (el.clientWidth - nat.w * k) / 2, y: (el.clientHeight - nat.h * k) / 2 });
  }, [nat]);
  useEffect(() => {
    fit();
    const el = box.current; if (!el) return;
    const ro = new ResizeObserver(() => fit()); ro.observe(el);
    return () => ro.disconnect();
  }, [fit]);

  const zoomAt = useCallback((factor: number, cx: number, cy: number) => {
    setT((p) => {
      const k = Math.min(fitK * 12, Math.max(fitK * 0.5, p.k * factor));
      const f = k / p.k;
      return { k, x: cx - (cx - p.x) * f, y: cy - (cy - p.y) * f };
    });
  }, [fitK]);

  useEffect(() => {
    const el = box.current; if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomAt]);

  const center = () => { const el = box.current!; return [el.clientWidth / 2, el.clientHeight / 2] as const; };
  return (
    <div ref={box} className="relative select-none overflow-hidden bg-[#1b2230]" style={{ height: cssSize(height, 520), cursor: drag.current ? 'grabbing' : 'grab' }}
      onPointerDown={(e) => { (e.target as HTMLElement).setPointerCapture(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, tx: t.x, ty: t.y }; }}
      onPointerMove={(e) => { const d = drag.current; if (d) setT((p) => ({ ...p, x: d.tx + e.clientX - d.x, y: d.ty + e.clientY - d.y })); }}
      onPointerUp={() => { drag.current = null; }}
      onDoubleClick={(e) => { const r = box.current!.getBoundingClientRect(); if (t.k > fitK * 1.05) fit(); else zoomAt(2.5, e.clientX - r.left, e.clientY - r.top); }}>
      <img src={url} alt={alt} draggable={false} onLoad={(e) => setNat({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
        className="absolute left-0 top-0 max-w-none origin-top-left"
        style={{ transform: `translate(${t.x}px, ${t.y}px) scale(${t.k})`, imageRendering: t.k > 2 * fitK ? 'pixelated' : 'auto', opacity: nat ? 1 : 0, transition: 'opacity .2s' }} />
      <div className="absolute bottom-3 right-3 flex items-center gap-0.5 rounded-lg border border-white/10 bg-ink-950/80 p-0.5 text-white shadow-lg backdrop-blur" onPointerDown={(e) => e.stopPropagation()}>
        <CtrlBtn onClick={() => zoomAt(1 / 1.4, ...center())} title="Zoom out"><Minus className="size-3.5" /></CtrlBtn>
        <span className="num w-11 text-center text-[11px] text-ink-200">{Math.round((t.k / fitK) * 100)}%</span>
        <CtrlBtn onClick={() => zoomAt(1.4, ...center())} title="Zoom in"><Plus className="size-3.5" /></CtrlBtn>
        <CtrlBtn onClick={fit} title="Fit"><Maximize className="size-3.5" /></CtrlBtn>
      </div>
    </div>
  );
}

function CtrlBtn(p: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...p} className="inline-flex size-7 items-center justify-center rounded-md hover:bg-white/10" />;
}
