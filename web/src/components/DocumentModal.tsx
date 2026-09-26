// Near-full-screen document viewer for ev.doc (opened via openDoc(docId, anchor)).
import { useEffect } from 'react';
import { X } from 'lucide-react';
import { useEvidence } from '@/components/evidence';
import { DocumentViewer } from '@/viewers/DocumentViewer';

export function DocumentModal() {
  const ev = useEvidence();
  const doc = ev.doc;
  useEffect(() => {
    if (!doc) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopImmediatePropagation(); ev.closeDoc(); } };
    window.addEventListener('keydown', h, true);
    const prev = document.body.style.overflow; document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', h, true); document.body.style.overflow = prev; };
  }, [doc, ev]);
  if (!doc) return null;
  return (
    <div className="anim-fade fixed inset-0 z-50 flex bg-ink-950/45 p-6 backdrop-blur-[2px]" onClick={ev.closeDoc}>
      <div className="flex min-h-0 w-full flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-[var(--shadow-pop)]" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <DocumentViewer key={doc.docId} docId={doc.docId} anchor={doc.anchor} height="100%" showExtraction={false}
          headerExtra={<button onClick={ev.closeDoc} title="Close (Esc)" className="ml-1 rounded-md p-1.5 text-ink-500 hover:bg-ink-100 hover:text-ink-900"><X className="size-4" /></button>} />
      </div>
    </div>
  );
}
