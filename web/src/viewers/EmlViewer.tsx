// Email viewer: header block, attachment chips, body with extracted-statement highlights.
import { useMemo, type ReactNode } from 'react';
import { FileSpreadsheet, FileText, FileArchive, FileImage, File as FileIcon, Paperclip, Box } from 'lucide-react';
import type { EmlPayload } from '@/api/types';
import { useEvidence } from '@/components/evidence';
import { cx } from '@/components/ui';
import { bytes } from '@/lib/format';
import { cssSize, fileExt } from './util';

export interface EmlViewerProps { payload: EmlPayload; height?: number | string; activeText?: string | null }

const extIcon = (name: string) => {
  const e = fileExt(name);
  if (['xlsx', 'xls', 'csv'].includes(e)) return <FileSpreadsheet className="size-4 text-ok" />;
  if (e === 'pdf') return <FileText className="size-4 text-crit" />;
  if (['zip', '7z'].includes(e)) return <FileArchive className="size-4 text-med" />;
  if (['png', 'jpg', 'jpeg', 'tif'].includes(e)) return <FileImage className="size-4 text-info" />;
  if (e === 'glb') return <Box className="size-4 text-accent-600" />;
  return <FileIcon className="size-4 text-ink-400" />;
};

function parseAddr(s: string) {
  const m = /^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/.exec(s);
  return m ? { name: m[1] || m[2], email: m[2] } : { name: s, email: '' };
}
const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');

export function EmlViewer({ payload, height, activeText }: EmlViewerProps) {
  const ev = useEvidence();
  const from = parseAddr(payload.from);
  const date = new Date(payload.date);

  const body = useMemo(() => {
    const text = payload.text || (payload.html ? payload.html.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '') : '');
    // collect non-overlapping matches
    const marks: { s: number; e: number; h: EmlPayload['highlights'][number] }[] = [];
    for (const h of payload.highlights) {
      if (!h.text) continue;
      let i = text.indexOf(h.text);
      while (i >= 0) {
        const e = i + h.text.length;
        if (!marks.some((m) => i < m.e && e > m.s)) { marks.push({ s: i, e, h }); break; }
        i = text.indexOf(h.text, i + 1);
      }
    }
    marks.sort((a, b) => a.s - b.s);
    const out: ReactNode[] = []; let p = 0;
    marks.forEach((m, k) => {
      if (m.s > p) out.push(text.slice(p, m.s));
      const active = activeText && m.h.text.includes(activeText);
      out.push(
        <button key={k} onClick={() => ev.openObs(m.h.obs_id)}
          className={cx('group relative rounded-[3px] bg-accent-100/70 px-0.5 text-left text-ink-950 underline decoration-accent-500 decoration-2 underline-offset-[3px] transition-colors hover:bg-accent-100',
            active && 'bg-accent-100 ring-2 ring-accent-500')}>
          {text.slice(m.s, m.e)}
          <span className="pointer-events-none absolute bottom-full left-0 z-10 mb-1.5 hidden whitespace-nowrap rounded-md bg-ink-900 px-2 py-1 text-[11px] font-medium text-white no-underline shadow-[var(--shadow-pop)] group-hover:block">
            Extracted → <span className="mono text-accent-100">{m.h.field_code}</span>
          </span>
        </button>,
      );
      p = m.e;
    });
    if (p < text.length) out.push(text.slice(p));
    return out;
  }, [payload, ev, activeText]);

  return (
    <div className="flex min-h-0 flex-col overflow-auto bg-surface" style={{ height: cssSize(height, 'auto') }}>
      <div className="border-b border-line px-5 pb-4 pt-4">
        <h2 className="text-[17px] font-semibold leading-snug tracking-[-0.01em] text-ink-950">{payload.subject || '(no subject)'}</h2>
        <div className="mt-3 flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-ink-800 text-[12px] font-semibold text-white">{initials(from.name)}</div>
          <div className="min-w-0 flex-1 text-[12.5px]">
            <div className="flex items-baseline justify-between gap-3">
              <div className="truncate"><span className="font-semibold text-ink-900">{from.name}</span> {from.email && <span className="text-ink-500">&lt;{from.email}&gt;</span>}</div>
              <div className="num shrink-0 text-[12px] text-ink-500">{Number.isNaN(+date) ? payload.date : date.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}</div>
            </div>
            <AddrLine k="To" v={payload.to} />
            {payload.cc.length > 0 && <AddrLine k="Cc" v={payload.cc} />}
          </div>
        </div>
        {payload.attachments.length > 0 && (
          <div className="mt-3.5">
            <div className="mb-1.5 flex items-center gap-1 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500"><Paperclip className="size-3" />{payload.attachments.length} attachments</div>
            <div className="flex flex-wrap gap-2">
              {payload.attachments.map((a) => {
                const can = !!a.doc_id;
                return (
                  <button key={a.filename} disabled={!can} onClick={() => a.doc_id && ev.openDoc(a.doc_id)}
                    title={can ? 'Open document' : 'Not ingested'}
                    className={cx('flex max-w-[260px] items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left transition-colors',
                      can ? 'border-line-strong bg-surface hover:border-accent-500 hover:bg-accent-50' : 'cursor-default border-line bg-ink-50 opacity-70')}>
                    {extIcon(a.filename)}
                    <span className="min-w-0">
                      <span className="block truncate text-[12px] font-medium text-ink-900">{a.filename}</span>
                      <span className="num block text-[10.5px] text-ink-500">{bytes(a.size_bytes)}{!can && ' · not ingested'}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <div className="whitespace-pre-wrap px-5 py-4 text-[13.5px] leading-[1.65] text-ink-800">{body}</div>
      {payload.highlights.length > 0 && (
        <div className="mx-5 mb-4 mt-auto flex items-center gap-2 rounded-md border border-line bg-ink-50 px-3 py-2 text-[11.5px] text-ink-500">
          <span className="inline-block h-2.5 w-5 rounded-[3px] bg-accent-100 ring-1 ring-accent-500" />
          {payload.highlights.length} statements extracted — click one to open its evidence
        </div>
      )}
    </div>
  );
}

function AddrLine({ k, v }: { k: string; v: string[] }) {
  return (
    <div className="mt-0.5 truncate text-[12px] text-ink-500">
      <span className="mr-1 text-ink-400">{k}</span>{v.map((a) => parseAddr(a).name).join(', ')}
    </div>
  );
}
