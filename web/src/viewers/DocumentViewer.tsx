// Dispatches by DocumentMeta.format to the right viewer. Header with metadata + download,
// optional "Extracted fields" side panel that re-anchors the viewer on click.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Download, FileText, FileSpreadsheet, Mail, Box, Image as ImageIcon, Braces, Table2, FileCode, ListChecks, AlertTriangle, ArrowUpRight } from 'lucide-react';
import type { Anchor, DocumentMeta, DocFormat } from '@/api/types';
import { rawUrl, useDocText, useDocument, useEml, useExtraction, useXlsx } from '@/api/client';
import { Badge, cx, ErrorBox, Loading, MockBadge, SeverityDot, Empty } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { bytes, fmtDate } from '@/lib/format';
import { PdfViewer } from './PdfViewer';
import { XlsxViewer } from './XlsxViewer';
import { EmlViewer } from './EmlViewer';
import { ModelViewer } from './ModelViewer';
import { ImageViewer } from './ImageViewer';
import { CsvViewer } from './CsvViewer';
import { JsonViewer } from './JsonViewer';
import { TextViewer } from './TextViewer';
import { anchorSummary, cssSize } from './util';
import { Info } from '@/help/Info';

export interface DocumentViewerProps { docId: string; anchor?: Anchor | null; height?: number | string; compact?: boolean; showExtraction?: boolean; headerExtra?: ReactNode }

const FORMAT_ICON: Record<DocFormat, typeof FileText> = {
  pdf: FileText, xlsx: FileSpreadsheet, eml: Mail, glb: Box, png: ImageIcon, json: Braces, geojson: Braces, csv: Table2, yaml: FileCode, txt: FileCode,
};

export function DocumentViewer({ docId, anchor, height = 640, compact = false, showExtraction, headerExtra }: DocumentViewerProps) {
  const { data: meta, isLoading, error } = useDocument(docId);
  const anchorKey = JSON.stringify(anchor ?? null);
  const [active, setActive] = useState<Anchor | null>(anchor ?? null);
  useEffect(() => { setActive(anchor ?? null); }, [anchorKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const [panel, setPanel] = useState(!!showExtraction);
  const canExtract = meta?.extraction?.status === 'EXTRACTED';

  return (
    <div className="flex min-h-0 flex-col overflow-hidden bg-surface" style={{ height: cssSize(height, 640) }}>
      {!compact && (
        <div className="flex shrink-0 items-center gap-3 border-b border-line px-4 py-2.5">
          {meta ? <Header meta={meta} /> : <div className="h-9 flex-1" />}
          <div className="flex shrink-0 items-center gap-1.5">
            {canExtract && (
              <button onClick={() => setPanel((p) => !p)}
                className={cx('inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-[12px] font-medium transition-colors',
                  panel ? 'border-accent-500 bg-accent-50 text-accent-700' : 'border-line-strong bg-surface text-ink-700 hover:bg-ink-50')}>
                <ListChecks className="size-3.5" />Extracted fields
                <span className="num rounded-full bg-ink-100 px-1.5 text-[10.5px] text-ink-600">{meta!.extraction!.fields}</span>
              </button>
            )}
            {meta && (
              <a href={rawUrl(docId)} download={meta.filename} title={`Download ${meta.filename} (${bytes(meta.size_bytes)})`}
                className="inline-flex h-7 items-center gap-1.5 rounded-md border border-line-strong bg-surface px-2.5 text-[12px] font-medium text-ink-700 hover:bg-ink-50">
                <Download className="size-3.5" />Download
              </a>
            )}
            {headerExtra}
          </div>
        </div>
      )}
      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1">
          {error ? <div className="p-4"><ErrorBox error={error} /></div>
            : isLoading || !meta ? <Loading label="Loading document…" />
              : <FormatBody meta={meta} anchor={active} />}
        </div>
        {panel && canExtract && <ExtractionPanel docId={docId} active={active} onAnchor={setActive} />}
      </div>
    </div>
  );
}

function Header({ meta }: { meta: DocumentMeta }) {
  const Icon = FORMAT_ICON[meta.format] ?? FileText;
  const mock = meta.source_channel.includes('(mock)');
  return (
    <div className="flex min-w-0 flex-1 items-center gap-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-ink-50 text-ink-600"><Icon className="size-4" /></div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-[14px] font-semibold text-ink-950" title={meta.title}>{meta.title}</span>
          <Badge tone="accent">{meta.doc_type}</Badge>
          {meta.is_sample && <Badge tone="dark" title="Fictional sample document">SAMPLE</Badge>}
          <Info id="document.viewer" />
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-[11.5px] text-ink-500">
          <span className="mono uppercase">{meta.format}</span><span className="text-ink-300">·</span>
          <span className="truncate" title={meta.filename}>{meta.filename}</span><span className="text-ink-300">·</span>
          <span className="num whitespace-nowrap">Received {fmtDate(meta.received_at)}</span><span className="text-ink-300">·</span>
          {mock ? <MockBadge label={meta.source_channel} /> : <span className="whitespace-nowrap">{meta.source_channel}</span>}
          {meta.term && <><span className="text-ink-300">·</span><span className="whitespace-nowrap">Term {meta.term}</span></>}
        </div>
      </div>
    </div>
  );
}

function FormatBody({ meta, anchor }: { meta: DocumentMeta; anchor: Anchor | null }) {
  const id = meta.doc_id;
  switch (meta.format) {
    case 'pdf': return <PdfViewer url={rawUrl(id)} anchor={anchor} height="100%" />;
    case 'xlsx': return <XlsxBody id={id} anchor={anchor} />;
    case 'eml': return <EmlBody id={id} anchor={anchor} />;
    case 'glb': return <ModelViewer url={rawUrl(id)} highlightNode={anchor?.node ?? null} height="100%" />;
    case 'png': return <ImageViewer url={rawUrl(id)} alt={meta.title} height="100%" />;
    default: return <TextBody meta={meta} anchor={anchor} />;
  }
}

function XlsxBody({ id, anchor }: { id: string; anchor: Anchor | null }) {
  const q = useXlsx(id);
  if (q.error) return <div className="p-4"><ErrorBox error={q.error} /></div>;
  if (!q.data) return <Loading label="Parsing workbook…" />;
  return <XlsxViewer payload={q.data} anchor={anchor} height="100%" />;
}
function EmlBody({ id, anchor }: { id: string; anchor: Anchor | null }) {
  const q = useEml(id);
  if (q.error) return <div className="p-4"><ErrorBox error={q.error} /></div>;
  if (!q.data) return <Loading label="Loading message…" />;
  return <EmlViewer payload={q.data} height="100%" activeText={anchor?.text ?? null} />;
}
function TextBody({ meta, anchor }: { meta: DocumentMeta; anchor: Anchor | null }) {
  const q = useDocText(meta.doc_id);
  const text = useMemo(() => { const d = q.data as unknown; return d === undefined ? null : typeof d === 'string' ? d : JSON.stringify(d, null, 2); }, [q.data]);
  if (q.error) return <div className="p-4"><ErrorBox error={q.error} /></div>;
  if (text === null) return <Loading />;
  switch (meta.format) {
    case 'csv': return <CsvViewer text={text} docType={meta.doc_type} height="100%" highlightRow={anchor?.record_id ? Number(anchor.record_id) : null} />;
    case 'json': case 'geojson': return <JsonViewer text={text} height="100%" highlightPath={anchor?.path ?? null} />;
    case 'yaml': return <TextViewer text={text} language="yaml" height="100%" />;
    default: return <TextViewer text={text} language="txt" height="100%" />;
  }
}

// ------------------------------------------------------------------ extraction panel
export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const c = value >= 0.9 ? 'bg-ok' : value >= 0.75 ? 'bg-med' : 'bg-high';
  return (
    <span className={cx('inline-flex items-center gap-1.5', className)} title={`Confidence ${(value * 100).toFixed(0)}%`}>
      <span className="h-1 w-10 overflow-hidden rounded-full bg-ink-100"><span className={cx('block h-full rounded-full', c)} style={{ width: `${Math.max(4, value * 100)}%` }} /></span>
      <span className="num text-[10.5px] text-ink-500">{Math.round(value * 100)}%</span>
    </span>
  );
}

function ExtractionPanel({ docId, active, onAnchor }: { docId: string; active: Anchor | null; onAnchor: (a: Anchor) => void }) {
  const { data, error, isLoading } = useExtraction(docId);
  const ev = useEvidence();
  const same = (a: Anchor | null, b: Anchor | null) => !!a && !!b && JSON.stringify(a) === JSON.stringify(b);
  return (
    <aside className="anim-fade flex w-[300px] shrink-0 flex-col border-l border-line bg-surface">
      <div className="border-b border-line px-3 py-2.5">
        <div className="text-[12px] font-semibold text-ink-900">Extracted fields</div>
        {data && <div className="mt-0.5 text-[11px] leading-snug text-ink-500">{data.method}</div>}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {error ? <div className="p-3"><ErrorBox error={error} /></div> : isLoading || !data ? <Loading /> : (
          <>
            {data.issues.length > 0 && (
              <div className="border-b border-line p-2">
                <div className="mb-1 flex items-center gap-1 px-1 text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-500"><AlertTriangle className="size-3" />Issues ({data.issues.length})</div>
                {data.issues.map((is, i) => (
                  <button key={i} disabled={!is.anchor} onClick={() => is.anchor && onAnchor(is.anchor)}
                    className={cx('flex w-full items-start gap-2 rounded-md px-1.5 py-1 text-left text-[12px] text-ink-800', is.anchor && 'hover:bg-ink-50', same(is.anchor, active) && 'bg-accent-50')}>
                    <span className="mt-1.5"><SeverityDot s={is.severity} /></span>
                    <span className="min-w-0 flex-1">{is.label}{is.anchor && <span className="ml-1 text-[11px] text-ink-400">{anchorSummary(is.anchor)}</span>}</span>
                  </button>
                ))}
              </div>
            )}
            {data.fields.length === 0 ? <Empty>No fields extracted</Empty> : (
              <div className="p-1.5">
                {data.fields.map((f) => {
                  const sel = same(f.anchor, active);
                  return (
                    <div key={f.obs_id} role="button" tabIndex={0} onClick={() => onAnchor(f.anchor)} onKeyDown={(e) => e.key === 'Enter' && onAnchor(f.anchor)}
                      className={cx('group cursor-pointer rounded-md px-2 py-1.5 transition-colors', sel ? 'bg-accent-50 ring-1 ring-accent-500/40' : 'hover:bg-ink-50')}>
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-[12px] text-ink-600">{f.label}</span>
                        <span className="num shrink-0 text-[12.5px] font-semibold text-ink-950">{f.value_display}</span>
                      </div>
                      <div className="mt-0.5 flex items-center justify-between gap-2">
                        <span className="truncate text-[11px] text-ink-400">{f.subject_label} · {anchorSummary(f.anchor)}</span>
                        <span className="flex shrink-0 items-center gap-1">
                          <ConfidenceBar value={f.confidence} />
                          <button title="Open evidence" onClick={(e) => { e.stopPropagation(); ev.openObs(f.obs_id); }}
                            className="rounded p-0.5 text-ink-400 opacity-0 hover:bg-ink-100 hover:text-accent-700 group-hover:opacity-100"><ArrowUpRight className="size-3.5" /></button>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
