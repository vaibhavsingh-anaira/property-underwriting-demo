// /_viewers — every viewer rendered from static files in /public/samples (no backend needed).
import { useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { AccumulationZone, Anchor, EmlPayload, GeoFeatureCollection, XlsxPayload } from '@/api/types';
import { Card, ErrorBox, Loading, Page, Segmented, cx } from '@/components/ui';
import { PdfViewer, type PdfHighlight } from './PdfViewer';
import { XlsxViewer } from './XlsxViewer';
import { EmlViewer } from './EmlViewer';
import { ModelViewer } from './ModelViewer';
import { ImageViewer } from './ImageViewer';
import { ImageCompare } from './ImageCompare';
import { CsvViewer, parseCsv } from './CsvViewer';
import { JsonViewer } from './JsonViewer';
import { TextViewer } from './TextViewer';
import { GeoMap, type MapPoint } from './GeoMap';

const S = '/samples/';
function useSample<T = string>(file: string, as: 'json' | 'text' = 'text') {
  return useQuery({
    queryKey: ['sample', file, as], staleTime: Infinity,
    queryFn: async () => { const r = await fetch(S + file); if (!r.ok) throw new Error(`${file}: ${r.status}`); return (as === 'json' ? r.json() : r.text()) as Promise<T>; },
  });
}
function Q<T>({ q, children }: { q: { data: T | undefined; error: unknown }; children: (d: T) => ReactNode }) {
  if (q.error) return <div className="p-4"><ErrorBox error={q.error} /></div>;
  if (q.data === undefined) return <Loading />;
  return <>{children(q.data)}</>;
}

const SECTIONS = [
  ['pdf', 'PDF'], ['xlsx', 'Spreadsheet'], ['eml', 'Email'], ['glb', '3D model'], ['img', 'Imagery'], ['cat', 'CAT files'], ['map', 'Map'], ['yaml', 'Rule YAML'],
] as const;

export default function ViewerGallery() {
  // ?only=glb renders a single section (handy for screenshots)
  const only = new URLSearchParams(window.location.search).get('only');
  const show = (id: string) => !only || only === id;
  return (
    <Page title="Viewer gallery" subtitle="Every document viewer, rendered from fictional sample files in /public/samples — no backend required."
      crumbs={<span className="mono">/_viewers</span>}>
      <nav className="sticky top-0 z-20 -mx-6 mb-4 flex gap-1 border-b border-line bg-canvas/90 px-6 py-2 backdrop-blur">
        {SECTIONS.map(([id, l]) => (
          <a key={id} href={`#${id}`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
            className="rounded-md px-2.5 py-1 text-[12px] font-medium text-ink-600 hover:bg-surface hover:text-ink-950">{l}</a>
        ))}
      </nav>
      <div className="flex flex-col gap-5">
        {show('pdf') && <PdfSection />}
        {show('xlsx') && <XlsxSection />}
        {show('eml') && <EmlSection />}
        {show('glb') && <GlbSection />}
        {show('img') && <ImagerySection />}
        {show('cat') && <CatSection />}
        {show('map') && <MapSection />}
        {show('yaml') && <Card id="yaml" title="TextViewer · rule YAML" subtitle="rule_named_storm.yaml — line numbers, key/value tint" pad={false} className="scroll-mt-16">
          <YamlBody /></Card>}
      </div>
    </Page>
  );
}

function YamlBody() {
  const q = useSample<string>('rule_named_storm.yaml');
  return <Q<string> q={q}>{(t) => <TextViewer text={t} language="yaml" height={420} highlightLines={[14, 15, 16]} />}</Q>;
}

function Chips<T extends string>({ items, value, onChange }: { items: { k: T; label: string }[]; value: T | null; onChange: (k: T) => void }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((it) => (
        <button key={it.k} onClick={() => onChange(it.k)}
          className={cx('h-6 rounded-md border px-2 text-[11.5px] font-medium transition-colors', value === it.k ? 'border-accent-500 bg-accent-50 text-accent-700' : 'border-line-strong bg-surface text-ink-600 hover:bg-ink-50')}>
          {it.label}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ PDF
function PdfSection() {
  const m = useSample<{ pdf: { url: string; highlights: (PdfHighlight & { page_size: [number, number] })[] } }>('manifest.json', 'json');
  const [i, setI] = useState(2);
  return (
    <Card id="pdf" title="PdfViewer · declarations (3 pages)" subtitle="pdf.js, lazy canvas at devicePixelRatio, text layer, bbox highlight + smooth scroll to anchor" pad={false} className="scroll-mt-16"
      actions={m.data && <Chips items={m.data.pdf.highlights.map((h, k) => ({ k: String(k), label: `p.${h.page} · ${h.label}` }))} value={String(i)} onChange={(k) => setI(Number(k))} />}>
      <Q q={m}>{(d) => {
        const h = d.pdf.highlights[i];
        const anchor: Anchor = { doc_id: null, kind: 'pdf', page: h.page, bbox: h.bbox, page_size: h.page_size, text: h.label };
        return <PdfViewer url={d.pdf.url} anchor={anchor} highlights={d.pdf.highlights.filter((_, k) => k !== i).map(({ page, bbox }) => ({ page, bbox }))} height={620} />;
      }}</Q>
    </Card>
  );
}

// ------------------------------------------------------------------ XLSX
const XLSX_ANCHORS: { k: string; label: string; a: Anchor }[] = [
  { k: 'roof', label: 'Locations · M14 roof year', a: { doc_id: null, kind: 'xlsx', sheet: 'Locations', cell: 'M14', range: 'A14:S14' } },
  { k: 'total', label: 'Locations · R50 totals row', a: { doc_id: null, kind: 'xlsx', sheet: 'Locations', cell: 'R50', range: 'A50:S50' } },
  { k: 'hidden', label: 'Hidden row 21', a: { doc_id: null, kind: 'xlsx', sheet: 'Locations', cell: 'O21', range: 'A21:S21' } },
  { k: 'bld', label: 'Buildings · D7 ($000s)', a: { doc_id: null, kind: 'xlsx', sheet: 'Buildings', cell: 'D7' } },
];
function XlsxSection() {
  const q = useSample<XlsxPayload>('sov_payload.json', 'json');
  const [k, setK] = useState('roof');
  const a = XLSX_ANCHORS.find((x) => x.k === k)!.a;
  return (
    <Card id="xlsx" title="XlsxViewer · SOV (hand-built XlsxPayload)" subtitle="Merged title band, frozen panes at D4, hidden rows 20–22 + hidden column T, totals formulas, hidden sheet, 46 locations" pad={false} className="scroll-mt-16"
      actions={<Chips items={XLSX_ANCHORS} value={k} onChange={setK} />}>
      <Q q={q}>{(p) => <XlsxViewer payload={p} anchor={a} height={520} />}</Q>
    </Card>
  );
}

// ------------------------------------------------------------------ EML
function EmlSection() {
  const q = useSample<EmlPayload>('eml_payload.json', 'json');
  return (
    <Card id="eml" title="EmlViewer · broker email" subtitle="Attachment chips open documents; highlighted statements link to extracted observations (needs backend)" pad={false} className="scroll-mt-16">
      <Q q={q}>{(p) => <EmlViewer payload={p} height={520} />}</Q>
    </Card>
  );
}

// ------------------------------------------------------------------ GLB
const CAMPUS_COLORS: Record<string, Record<string, string>> = {
  none: {},
  flags: { 'B-2': '#e8a33d', 'B-5': '#d9534f', 'B-4': '#e8c95a' },
  roof: { 'ROOF-B-1': '#7fb89a', 'ROOF-B-2': '#d9534f', 'ROOF-B-3': '#7fb89a', 'ROOF-B-4': '#e8a33d', 'ROOF-B-5': '#7fb89a', 'ROOF-B-6': '#d9534f' },
};
function GlbSection() {
  const [model, setModel] = useState<'warehouse' | 'campus'>('warehouse');
  const [mode, setMode] = useState<'none' | 'flags' | 'roof'>('flags');
  const [picked, setPicked] = useState<{ node: string; extras: Record<string, unknown> } | null>(null);
  const legend = model === 'warehouse'
    ? [{ color: '#d65c40', label: 'Li-ion storage · 28 ft' }, { color: '#c7a87a', label: 'General storage · 20 ft' }, { color: 'rgba(19,163,163,.5)', label: 'Sprinkler design plane · 20 ft' }]
    : mode === 'flags' ? [{ color: '#d9534f', label: 'Not in CAT run' }, { color: '#e8a33d', label: 'Data conflict' }, { color: '#e8c95a', label: 'Aged roof' }]
      : mode === 'roof' ? [{ color: '#7fb89a', label: 'Roof < 10 yrs' }, { color: '#e8a33d', label: '10–20 yrs' }, { color: '#d9534f', label: '> 20 yrs / conflict' }] : [];
  return (
    <Card id="glb" title="ModelViewer · GLB with node extras" subtitle="Hover for extras, click to select; toolbar: reset / iso / top, wireframe, labels, 10 ft grid, translucent toggle" pad={false} className="scroll-mt-16"
      actions={<div className="flex items-center gap-2">
        {model === 'campus' && <Segmented options={[{ key: 'none', label: 'Plain' }, { key: 'flags', label: 'By flag' }, { key: 'roof', label: 'By roof age' }]} value={mode} onChange={setMode} />}
        <Segmented options={[{ key: 'warehouse', label: 'Warehouse (racks)' }, { key: 'campus', label: 'Campus (6 bldgs)' }]} value={model} onChange={(m) => { setModel(m); setPicked(null); }} />
      </div>}>
      <ModelViewer url={`${S}${model}.glb`} height={520} legend={legend} colorBy={model === 'campus' ? CAMPUS_COLORS[mode] : undefined}
        highlightNode={model === 'warehouse' ? 'RACK-06' : null} onSelectNode={(node, extras) => setPicked({ node, extras })} />
      <div className="mono border-t border-line bg-ink-50 px-4 py-2 text-[11.5px] text-ink-600">
        onSelectNode → {picked ? `${picked.node} ${JSON.stringify(picked.extras)}` : <span className="font-sans text-ink-400">click a building or rack</span>}
      </div>
    </Card>
  );
}

// ------------------------------------------------------------------ imagery
function ImagerySection() {
  return (
    <div id="img" className="grid scroll-mt-16 grid-cols-1 gap-5 xl:grid-cols-2">
      <Card title="ImageCompare · aerial then vs now" subtitle="Drag the divider (or ← →): roof replacement, solar array, expansion building" pad={false}>
        <ImageCompare before={{ url: `${S}aerial_2021.png`, label: 'Jun 2021' }} after={{ url: `${S}aerial_2025.png`, label: 'Jun 2025' }} height={420} />
      </Card>
      <Card title="ImageViewer · zoom / pan" subtitle="Wheel zooms at cursor, drag pans, double-click toggles" pad={false}>
        <ImageViewer url={`${S}aerial_2025.png`} alt="Aerial 2025" height={420} />
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ CAT
function CatSection() {
  const [tab, setTab] = useState<'elt' | 'oed' | 'ep' | 'geo'>('elt');
  const elt = useSample('cat_elt.csv'), oed = useSample('oed_locations.csv'), ep = useSample('ep_curve.json'), geo = useSample('hazards.geojson');
  return (
    <Card id="cat" title="CsvViewer / JsonViewer · CAT artefacts" subtitle="Format sniffing: ELT → AAL strip + loss histogram; OED → TIV totals; EP JSON → log-scale curve; GeoJSON → map" pad={false} className="scroll-mt-16"
      actions={<Segmented options={[{ key: 'elt', label: 'Event loss table' }, { key: 'oed', label: 'OED locations' }, { key: 'ep', label: 'EP curve JSON' }, { key: 'geo', label: 'GeoJSON' }]} value={tab} onChange={setTab} />}>
      {tab === 'elt' && <Q q={elt}>{(t) => <CsvViewer text={t} docType="CAT event loss table" height={560} />}</Q>}
      {tab === 'oed' && <Q q={oed}>{(t) => <CsvViewer text={t} docType="CAT exposure file" height={560} />}</Q>}
      {tab === 'ep' && <Q q={ep}>{(t) => <JsonViewer text={t} height={560} />}</Q>}
      {tab === 'geo' && <Q q={geo}>{(t) => <JsonViewer text={t} height={560} />}</Q>}
    </Card>
  );
}

// ------------------------------------------------------------------ map
const ZONES: AccumulationZone[] = [
  { zone_id: 'z1', name: 'Tampa Bay WS', peril: 'WS', lat: 27.9, lon: -82.5, radius_km: 60, threshold: 250e6, current: 190e6, post_renewal: 262e6, utilization: 1.05, accounts: [] },
  { zone_id: 'z2', name: 'Houston WS', peril: 'WS', lat: 29.76, lon: -95.3, radius_km: 70, threshold: 300e6, current: 230e6, post_renewal: 258e6, utilization: 0.86, accounts: [] },
  { zone_id: 'z3', name: 'Bay Area EQ', peril: 'EQ', lat: 37.7, lon: -122.2, radius_km: 55, threshold: 200e6, current: 110e6, post_renewal: 122e6, utilization: 0.61, accounts: [] },
];
function MapSection() {
  const oed = useSample('oed_locations.csv');
  const geo = useSample<GeoFeatureCollection>('hazards.geojson', 'json');
  const [sel, setSel] = useState<string | null>(null);
  const points = useMemo<MapPoint[]>(() => {
    if (!oed.data) return [];
    const [h, ...rows] = parseCsv(oed.data);
    const ix = (n: string) => h.indexOf(n);
    const sev = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'LOW', 'LOW'] as const;
    return rows.map((r, i) => ({
      id: r[ix('LocNumber')], lat: +r[ix('Latitude')], lon: +r[ix('Longitude')], label: r[ix('LocName')],
      sublabel: `${r[ix('City')]}, ${r[ix('AreaCode')]} · TIV $${((+r[ix('BuildingTIV')] + +r[ix('ContentsTIV')] + +r[ix('BITIV')]) / 1e6).toFixed(1)}M`,
      severity: sev[i % sev.length], value: +r[ix('BuildingTIV')],
    }));
  }, [oed.data]);
  return (
    <Card id="map" title="GeoMap · locations, accumulation zones, hazards" subtitle="Severity colour, size by TIV, zones by utilisation (teal < 80%, amber 80–100%, red > 100%), hazard toggles; falls back offline" pad={false} className="scroll-mt-16"
      actions={<span className="mono text-[11.5px] text-ink-500">selected: {sel ?? '—'}</span>}>
      <div className="p-3">
        <GeoMap points={points} zones={ZONES} hazards={geo.data ?? null} hazardLayers={['wind', 'eq']} selectedId={sel} onSelect={setSel} height={480} fitTo="us" />
      </div>
    </Card>
  );
}
