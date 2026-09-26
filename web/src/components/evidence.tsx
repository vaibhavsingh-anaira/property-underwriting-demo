// Global evidence context. Any number on any screen can call
//   const ev = useEvidence(); ev.openObs(obsId)       -> evidence drawer for an observation
//                             ev.openDoc(docId, anchor) -> full document viewer at an anchor
//                             ev.openFinding(finding)   -> drawer focused on a finding's evidence
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { Anchor, Finding } from '@/api/types';

type EvidenceTarget =
  | { kind: 'obs'; obsId: string }
  | { kind: 'finding'; finding: Finding }
  | null;

type DocTarget = { docId: string; anchor?: Anchor | null } | null;

interface EvidenceCtx {
  target: EvidenceTarget;
  doc: DocTarget;
  openObs: (obsId: string) => void;
  openFinding: (f: Finding) => void;
  openDoc: (docId: string, anchor?: Anchor | null) => void;
  closeDrawer: () => void;
  closeDoc: () => void;
}

const Ctx = createContext<EvidenceCtx | null>(null);

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<EvidenceTarget>(null);
  const [doc, setDoc] = useState<DocTarget>(null);
  const openObs = useCallback((obsId: string) => setTarget({ kind: 'obs', obsId }), []);
  const openFinding = useCallback((finding: Finding) => setTarget({ kind: 'finding', finding }), []);
  const openDoc = useCallback((docId: string, anchor?: Anchor | null) => setDoc({ docId, anchor }), []);
  const closeDrawer = useCallback(() => setTarget(null), []);
  const closeDoc = useCallback(() => setDoc(null), []);
  const v = useMemo(() => ({ target, doc, openObs, openFinding, openDoc, closeDrawer, closeDoc }), [target, doc, openObs, openFinding, openDoc, closeDrawer, closeDoc]);
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>;
}

export function useEvidence() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useEvidence outside EvidenceProvider');
  return c;
}

/** Inline clickable value that opens the evidence drawer. */
export function EvidenceLink({ obsId, children, className }: { obsId?: string | null; children: ReactNode; className?: string }) {
  const ev = useEvidence();
  if (!obsId) return <span className={className}>{children}</span>;
  return (
    <button onClick={(e) => { e.stopPropagation(); ev.openObs(obsId); }}
      className={`cursor-pointer rounded-sm underline decoration-accent-500/50 decoration-dotted underline-offset-[3px] hover:bg-accent-50 hover:decoration-accent-600 ${className ?? ''}`}>
      {children}
    </button>
  );
}
