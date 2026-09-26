// A presenter cursor that glides to UI elements, spotlights them and shows click ripples.
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';

interface CursorApi {
  moveTo: (selector: string, label?: string) => Promise<boolean>;
  click: () => Promise<void>;
  hide: () => void;
  setPace: (p: number) => void;
}
const Ctx = createContext<CursorApi | null>(null);
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function GhostCursorProvider({ children }: { children: ReactNode }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [label, setLabel] = useState<string | null>(null);
  const [ring, setRing] = useState<DOMRect | null>(null);
  const [ripple, setRipple] = useState(0);
  const pace = useRef(1);
  const target = useRef<string | null>(null);

  const moveTo = useCallback(async (selector: string, lbl?: string) => {
    let el: Element | null = null;
    for (let i = 0; i < 40 && !el; i++) { el = document.querySelector(selector); if (!el) await wait(100); }
    if (!el) return false;
    target.current = selector;
    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    await wait(450);
    const r = el.getBoundingClientRect();
    setRing(r);
    setLabel(lbl ?? null);
    setPos({ x: r.left + Math.min(r.width * 0.5, r.width - 12), y: r.top + Math.min(r.height * 0.55, r.height - 6) });
    await wait(1100 / pace.current);
    return true;
  }, []);

  const click = useCallback(async () => {
    setRipple((n) => n + 1);
    await wait(520);
  }, []);

  const hide = useCallback(() => { setPos(null); setRing(null); setLabel(null); target.current = null; }, []);
  const setPace = useCallback((p: number) => { pace.current = p; }, []);
  const api = useMemo(() => ({ moveTo, click, hide, setPace }), [moveTo, click, hide, setPace]);
  const dur = `${Math.round(1000 / pace.current)}ms`;

  return (
    <Ctx.Provider value={api}>
      {children}
      {ring && (
        <div className="pointer-events-none fixed z-[70] rounded-lg ring-2 ring-accent-500/70 transition-all"
          style={{ left: ring.left - 6, top: ring.top - 6, width: ring.width + 12, height: ring.height + 12, transitionDuration: dur, boxShadow: '0 0 0 4000px rgba(11,18,32,0.10)' }} />
      )}
      {pos && (
        <div className="pointer-events-none fixed left-0 top-0 z-[80]" style={{ transform: `translate(${pos.x}px, ${pos.y}px)`, transition: `transform ${dur} cubic-bezier(.22,.8,.26,1)` }}>
          <span key={ripple} className="ghost-ripple absolute -left-5 -top-5 size-10 rounded-full border-2 border-accent-500" />
          <svg width="26" height="26" viewBox="0 0 24 24" className="drop-shadow-[0_2px_4px_rgba(0,0,0,.35)]">
            <path d="M4 2 L4 19 L8.6 14.9 L11.6 21.6 L14.4 20.4 L11.5 13.8 L17.8 13.8 Z" fill="#0b1220" stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
          </svg>
          {label && <span className="absolute left-6 top-6 whitespace-nowrap rounded-md bg-ink-950 px-2 py-1 text-[11.5px] font-medium text-white shadow-[var(--shadow-pop)]">{label}</span>}
        </div>
      )}
    </Ctx.Provider>
  );
}

export function useGhostCursor() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useGhostCursor outside provider');
  return c;
}
