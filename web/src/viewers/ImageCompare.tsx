// Before/after image comparison with a draggable vertical divider (aerial then-vs-now).
import { useRef, useState } from 'react';
import { ChevronsLeftRight } from 'lucide-react';
import { cssSize } from './util';

export interface ImageCompareProps { before: { url: string; label: string }; after: { url: string; label: string }; height?: number | string }

export function ImageCompare({ before, after, height = 460 }: ImageCompareProps) {
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(0.5);
  const [dragging, setDragging] = useState(false);
  const move = (clientX: number) => {
    const r = box.current?.getBoundingClientRect(); if (!r) return;
    setPos(Math.min(1, Math.max(0, (clientX - r.left) / r.width)));
  };
  return (
    <div ref={box} className="relative select-none overflow-hidden bg-ink-900" style={{ height: cssSize(height, 460), cursor: dragging ? 'ew-resize' : 'default' }}
      onPointerDown={(e) => { box.current?.setPointerCapture(e.pointerId); setDragging(true); move(e.clientX); }}
      onPointerMove={(e) => { if (dragging) move(e.clientX); }}
      onPointerUp={() => setDragging(false)}
      onKeyDown={(e) => { if (e.key === 'ArrowLeft') setPos((p) => Math.max(0, p - 0.05)); if (e.key === 'ArrowRight') setPos((p) => Math.min(1, p + 0.05)); }}
      tabIndex={0} role="slider" aria-valuenow={Math.round(pos * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Compare images">
      <img src={after.url} alt={after.label} draggable={false} className="absolute inset-0 size-full object-cover" />
      <img src={before.url} alt={before.label} draggable={false} className="absolute inset-0 size-full object-cover" style={{ clipPath: `inset(0 ${100 - pos * 100}% 0 0)` }} />
      <Label side="left" text={before.label} dim={pos < 0.12} />
      <Label side="right" text={after.label} dim={pos > 0.88} />
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow-[0_0_0_1px_rgba(0,0,0,.15),0_0_12px_rgba(0,0,0,.35)]" style={{ left: `calc(${pos * 100}% - 1px)` }}>
        <div className="absolute left-1/2 top-1/2 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-ink-200 bg-white text-ink-700 shadow-[var(--shadow-pop)]">
          <ChevronsLeftRight className="size-4" />
        </div>
      </div>
    </div>
  );
}

function Label({ side, text, dim }: { side: 'left' | 'right'; text: string; dim: boolean }) {
  return (
    <span className={`pointer-events-none absolute top-3 ${side === 'left' ? 'left-3' : 'right-3'} rounded-md bg-ink-950/75 px-2 py-1 text-[11.5px] font-medium text-white backdrop-blur transition-opacity ${dim ? 'opacity-0' : 'opacity-100'}`}>
      {text}
    </span>
  );
}
