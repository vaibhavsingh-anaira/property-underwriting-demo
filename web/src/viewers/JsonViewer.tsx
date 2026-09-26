// JSON viewer: collapsible, type-tinted tree. EP-curve JSON gets a chart; GeoJSON gets a map.
import { useMemo, useState } from 'react';
import { ChevronRight, ChevronsDownUp, ChevronsUpDown } from 'lucide-react';
import type { GeoFeatureCollection } from '@/api/types';
import { cx } from '@/components/ui';
import { EpCurveChart } from './EpCurveChart';
import { GeoMap, type MapPoint } from './GeoMap';
import { TextViewer } from './TextViewer';
import { cssSize } from './util';

export interface JsonViewerProps { text: string; height?: number | string; highlightPath?: string | null }

type Pt = { rp: number; loss: number };
const isCurve = (v: unknown): v is Pt[] => Array.isArray(v) && v.length > 1 && v.every((p) => p && typeof p === 'object' && 'rp' in p && 'loss' in p);

export function JsonViewer({ text, height, highlightPath }: JsonViewerProps) {
  const parsed = useMemo(() => { try { return { ok: true as const, v: JSON.parse(text) as unknown }; } catch (e) { return { ok: false as const, e }; } }, [text]);
  const [depth, setDepth] = useState(2);
  const [gen, setGen] = useState(0);
  if (!parsed.ok) return <TextViewer text={text} height={height} />;
  const v = parsed.v as Record<string, unknown>;
  const ep = v && typeof v === 'object' && isCurve(v.oep) ? v : null;
  const geo = v && typeof v === 'object' && v.type === 'FeatureCollection' && Array.isArray(v.features) ? (v as unknown as GeoFeatureCollection) : null;

  return (
    <div className="flex min-h-0 flex-col overflow-auto bg-surface" style={{ height: cssSize(height, 'auto') }}>
      {ep && (
        <div className="border-b border-line px-4 pb-2 pt-3">
          <EpCurveChart oep={ep.oep as Pt[]} aep={isCurve(ep.aep) ? ep.aep : undefined}
            compare={Array.isArray(ep.compare) ? (ep.compare as { label: string; oep: Pt[] }[]).filter((c) => isCurve(c.oep)) : undefined} height={250} />
        </div>
      )}
      {geo && <GeoPreview fc={geo} />}
      <div className="flex items-center gap-2 border-b border-line bg-ink-50 px-3 py-1.5 text-[11.5px] text-ink-500">
        <span className="mono">{Array.isArray(v) ? `array[${(v as unknown[]).length}]` : `object{${Object.keys(v ?? {}).length}}`}</span>
        <span>· {text.length.toLocaleString()} chars</span>
        <div className="flex-1" />
        <button className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-ink-100 hover:text-ink-800" onClick={() => { setDepth(99); setGen((g) => g + 1); }}><ChevronsUpDown className="size-3" />Expand all</button>
        <button className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-ink-100 hover:text-ink-800" onClick={() => { setDepth(1); setGen((g) => g + 1); }}><ChevronsDownUp className="size-3" />Collapse</button>
      </div>
      <div className="mono px-3 py-2 text-[12px] leading-[20px]">
        <JsonNode key={gen} k={null} v={parsed.v} depth={0} open={depth} path="$" highlightPath={highlightPath ?? null} />
      </div>
    </div>
  );
}

function GeoPreview({ fc }: { fc: GeoFeatureCollection }) {
  const points: MapPoint[] = fc.features.filter((f) => f.geometry?.type === 'Point').map((f, i) => {
    const [lon, lat] = f.geometry.coordinates as [number, number];
    return { id: String(f.properties?.id ?? i), lat, lon, label: String(f.properties?.label ?? f.properties?.name ?? `Feature ${i + 1}`), severity: null };
  });
  const layers = [...new Set(fc.features.map((f) => f.properties?.layer).filter(Boolean))] as ('wind' | 'flood' | 'eq' | 'wildfire')[];
  return (
    <div className="border-b border-line p-3">
      <GeoMap points={points} hazards={fc} hazardLayers={layers.length ? layers : undefined} height={300} fitTo={points.length ? 'points' : 'us'} />
    </div>
  );
}

function JsonNode({ k, v, depth, open, path, highlightPath }: { k: string | number | null; v: unknown; depth: number; open: number; path: string; highlightPath: string | null }) {
  const isObj = v !== null && typeof v === 'object';
  const [expanded, setExpanded] = useState(depth < open);
  const [limit, setLimit] = useState(100);
  const hl = highlightPath && (highlightPath === path || highlightPath.replace(/^\$?\.?/, '$.') === path);
  const keyEl = k !== null && (
    <span className={typeof k === 'number' ? 'text-ink-400' : 'text-accent-700'}>{typeof k === 'number' ? k : `"${k}"`}<span className="text-ink-400">: </span></span>
  );
  if (!isObj) return <div className={cx('pl-4', hl && 'rounded bg-accent-100')}>{keyEl}<Scalar v={v} /></div>;
  const entries: [string | number, unknown][] = Array.isArray(v) ? v.map((x, i) => [i, x]) : Object.entries(v as Record<string, unknown>);
  const [o, c] = Array.isArray(v) ? ['[', ']'] : ['{', '}'];
  return (
    <div>
      <div className={cx('group flex cursor-pointer items-center rounded hover:bg-ink-50', hl && 'bg-accent-100')} onClick={() => setExpanded((e) => !e)}>
        <ChevronRight className={cx('size-3.5 shrink-0 text-ink-400 transition-transform', expanded && 'rotate-90')} />
        <span className="ml-0.5">{keyEl}<span className="text-ink-500">{o}</span>
          {!expanded && <><span className="mx-1 rounded bg-ink-100 px-1 text-[10.5px] text-ink-500">{entries.length} {Array.isArray(v) ? 'items' : 'keys'}</span><span className="text-ink-500">{c}</span></>}
        </span>
      </div>
      {expanded && (
        <div className="ml-[7px] border-l border-line pl-2">
          {entries.slice(0, limit).map(([ck, cv]) => (
            <JsonNode key={ck} k={ck} v={cv} depth={depth + 1} open={open} path={typeof ck === 'number' ? `${path}[${ck}]` : `${path}.${ck}`} highlightPath={highlightPath} />
          ))}
          {entries.length > limit && (
            <button className="ml-4 text-[11.5px] text-accent-700 hover:underline" onClick={() => setLimit((l) => l + 500)}>show {Math.min(500, entries.length - limit)} more of {entries.length - limit}…</button>
          )}
          <div className="text-ink-500">{c}</div>
        </div>
      )}
    </div>
  );
}

function Scalar({ v }: { v: unknown }) {
  if (v === null) return <span className="text-ink-400">null</span>;
  if (typeof v === 'string') return <span className="break-all text-[#1f7a4c]">"{v}"</span>;
  if (typeof v === 'number') return <span className="text-info">{v}</span>;
  if (typeof v === 'boolean') return <span className="text-obs-n">{String(v)}</span>;
  return <span>{String(v)}</span>;
}
