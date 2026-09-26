// MapLibre map: severity-coloured points, accumulation zones, hazard layers with toggles.
// Raster basemap (CARTO light) falls back to a plain background when tiles are unreachable.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Map as MlMap, Marker, NavigationControl, Popup, LngLatBounds, setWorkerUrl, type GeoJSONSource, type MapLayerMouseEvent } from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type { Severity, AccumulationZone, GeoFeatureCollection } from '@/api/types';
import { cx } from '@/components/ui';
import { usd } from '@/lib/format';
import { cssSize } from './util';

export interface MapPoint { id: string; lat: number; lon: number; label: string; sublabel?: string; severity?: Severity | null; value?: number; status?: string }
type HazardLayer = 'wind' | 'flood' | 'eq' | 'wildfire';
export interface GeoMapProps {
  points: MapPoint[];
  zones?: AccumulationZone[];
  hazards?: GeoFeatureCollection | null;
  hazardLayers?: HazardLayer[];   // initially visible
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  height?: number | string;
  fitTo?: 'points' | 'us';
}

// Pre-bundled maplibre can't locate its worker relative to import.meta.url; hand it a bundled one.
setWorkerUrl(maplibreWorkerUrl);

const SEV_COLOR: Record<string, string> = { CRITICAL: '#c2263a', HIGH: '#d15a12', MEDIUM: '#b88404', LOW: '#1f8a4c', NONE: '#45526e' };
const HAZ: Record<HazardLayer, { label: string; color: string }> = {
  wind: { label: 'Wind', color: '#7c4dcc' }, flood: { label: 'Flood', color: '#2f5bd3' },
  eq: { label: 'Earthquake', color: '#b8620a' }, wildfire: { label: 'Wildfire', color: '#c2263a' },
};
const US: [[number, number], [number, number]] = [[-125, 24], [-66.5, 49.5]];
const utilColor = (u: number) => (u > 1 ? '#c2263a' : u >= 0.8 ? '#b88404' : '#0e8585');

function circlePoly(lon: number, lat: number, km: number, n = 64): [number, number][] {
  const out: [number, number][] = [];
  const dLat = km / 110.574, dLon = km / (111.32 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i <= n; i++) { const a = (i / n) * 2 * Math.PI; out.push([lon + dLon * Math.cos(a), lat + dLat * Math.sin(a)]); }
  return out;
}

export function GeoMap({ points, zones, hazards, hazardLayers, selectedId, onSelect, height = 420, fitTo = 'points' }: GeoMapProps) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [tilesDown, setTilesDown] = useState(false);
  const [on, setOn] = useState<Set<HazardLayer>>(() => new Set(hazardLayers ?? []));
  const onSelectRef = useRef(onSelect); onSelectRef.current = onSelect;
  const pointsRef = useRef(points); pointsRef.current = points;
  const zoneMarkers = useRef<Marker[]>([]);
  const fitted = useRef<string | null>(null);

  const available = useMemo(() => {
    const s = new Set<HazardLayer>();
    hazards?.features.forEach((f) => { const l = f.properties?.layer as HazardLayer; if (l && HAZ[l]) s.add(l); });
    return (Object.keys(HAZ) as HazardLayer[]).filter((k) => s.has(k));
  }, [hazards]);

  // ---- init
  useEffect(() => {
    const container = el.current; if (!container) return;
    const map = new MlMap({
      container,
      style: 'https://tiles.openfreemap.org/styles/positron',
      bounds: US, fitBoundsOptions: { padding: 20 },
      attributionControl: { compact: true },
      dragRotate: false, pitchWithRotate: false, touchPitch: false,
    });
    map.touchZoomRotate.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    mapRef.current = map;
    let fails = 0;
    map.on('error', (e) => {
      const src = (e as unknown as { sourceId?: string }).sourceId;
      if (src === 'carto' || /tile|cartocdn|Failed to fetch/i.test(String(e.error?.message ?? ''))) {
        fails++;
        if (fails >= 4 && map.getLayer('carto')) { map.setLayoutProperty('carto', 'visibility', 'none'); setTilesDown(true); }
      }
    });
    map.on('load', () => {
      const empty = { type: 'FeatureCollection' as const, features: [] };
      map.addSource('hazards', { type: 'geojson', data: empty });
      map.addSource('zones', { type: 'geojson', data: empty });
      map.addSource('points', { type: 'geojson', data: empty });
      const hazColor = ['match', ['get', 'layer'], 'wind', HAZ.wind.color, 'flood', HAZ.flood.color, 'eq', HAZ.eq.color, 'wildfire', HAZ.wildfire.color, '#888'] as unknown as string;
      map.addLayer({ id: 'haz-fill', type: 'fill', source: 'hazards', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': hazColor, 'fill-opacity': 0.13 } });
      map.addLayer({ id: 'haz-line', type: 'line', source: 'hazards', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'line-color': hazColor, 'line-opacity': 0.55, 'line-width': 1, 'line-dasharray': [3, 2] } });
      map.addLayer({ id: 'zone-fill', type: 'fill', source: 'zones', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.12 } });
      map.addLayer({ id: 'zone-line', type: 'line', source: 'zones', paint: { 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': 0.8 } });
      map.addLayer({ id: 'pt-sel', type: 'circle', source: 'points', filter: ['==', ['get', 'id'], ''],
        paint: { 'circle-radius': ['+', ['get', 'r'], 5], 'circle-color': 'rgba(19,163,163,0.18)', 'circle-stroke-color': '#13a3a3', 'circle-stroke-width': 2 } });
      map.addLayer({ id: 'pt', type: 'circle', source: 'points',
        paint: { 'circle-radius': ['get', 'r'], 'circle-color': ['get', 'color'], 'circle-opacity': 0.9, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.5 } });
      setReady(true);
    });

    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 10, className: 'uwc-pop' });
    const show = (e: MapLayerMouseEvent) => {
      const f = e.features?.[0]; if (!f) return;
      map.getCanvas().style.cursor = 'pointer';
      const p = pointsRef.current.find((x) => x.id === f.properties?.id); if (!p) return;
      const node = document.createElement('div');
      node.className = 'text-[12px] leading-tight';
      const t = document.createElement('div'); t.className = 'font-semibold text-ink-900'; t.textContent = p.label; node.appendChild(t);
      if (p.sublabel) { const s = document.createElement('div'); s.className = 'mt-0.5 text-ink-500'; s.textContent = p.sublabel; node.appendChild(s); }
      if (p.severity || p.status) { const s = document.createElement('div'); s.className = 'mt-1 text-[11px] font-medium'; s.style.color = SEV_COLOR[p.severity ?? 'NONE']; s.textContent = [p.severity, p.status].filter(Boolean).join(' · '); node.appendChild(s); }
      popup.setLngLat([p.lon, p.lat]).setDOMContent(node).addTo(map);
    };
    map.on('mousemove', 'pt', show);
    map.on('mouseleave', 'pt', () => { map.getCanvas().style.cursor = ''; popup.remove(); });
    map.on('click', 'pt', (e) => { const id = e.features?.[0]?.properties?.id; if (id) onSelectRef.current?.(String(id)); });

    const ro = new ResizeObserver(() => map.resize());
    ro.observe(container);
    return () => { ro.disconnect(); popup.remove(); zoneMarkers.current.forEach((m) => m.remove()); map.remove(); mapRef.current = null; fitted.current = null; setReady(false); };
  }, []);

  // ---- points
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    const vals = points.map((p) => p.value ?? 0);
    const max = Math.max(1, ...vals);
    const hasVal = vals.some((v) => v > 0);
    (map.getSource('points') as GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: points.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
        properties: { id: p.id, color: SEV_COLOR[p.severity ?? 'NONE'], r: hasVal ? 4 + 11 * Math.sqrt((p.value ?? 0) / max) : 6 } })),
    });
  }, [ready, points]);

  // ---- fit (on first data, or when the set of ids changes)
  const idsKey = points.map((p) => p.id).join('|');
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map || fitted.current === idsKey + fitTo) return;
    const first = fitted.current === null;
    fitted.current = idsKey + fitTo;
    if (fitTo === 'points' && points.length) {
      if (points.length === 1) { map.jumpTo({ center: [points[0].lon, points[0].lat], zoom: 9 }); return; }
      const b = new LngLatBounds();
      points.forEach((p) => b.extend([p.lon, p.lat]));
      map.fitBounds(b, { padding: 48, maxZoom: 10, duration: first ? 0 : 600 });
    } else map.fitBounds(US, { padding: 20, duration: first ? 0 : 600 });
  }, [ready, idsKey, fitTo]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- selection
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    map.setFilter('pt-sel', ['==', ['get', 'id'], selectedId ?? '']);
  }, [ready, selectedId]);

  // ---- zones
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    (map.getSource('zones') as GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: (zones ?? []).map((z) => ({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [circlePoly(z.lon, z.lat, z.radius_km)] }, properties: { id: z.zone_id, color: utilColor(z.utilization) } })),
    });
    zoneMarkers.current.forEach((m) => m.remove());
    zoneMarkers.current = (zones ?? []).map((z) => {
      const d = document.createElement('div');
      d.className = 'pointer-events-none whitespace-nowrap rounded-md border bg-white/95 px-1.5 py-0.5 text-[10.5px] font-medium shadow-sm';
      d.style.borderColor = utilColor(z.utilization); d.style.color = utilColor(z.utilization);
      d.textContent = `${z.name} · ${Math.round(z.utilization * 100)}% of ${usd(z.threshold)}`;
      const dLat = z.radius_km / 110.574;
      return new Marker({ element: d, anchor: 'bottom' }).setLngLat([z.lon, z.lat + dLat]).addTo(map);
    });
  }, [ready, zones]);

  // ---- hazards
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    (map.getSource('hazards') as GeoJSONSource).setData((hazards ?? { type: 'FeatureCollection', features: [] }) as never);
  }, [ready, hazards]);
  useEffect(() => {
    const map = mapRef.current; if (!ready || !map) return;
    const f = ['all', ['==', ['geometry-type'], 'Polygon'], ['in', ['get', 'layer'], ['literal', [...on]]]] as never;
    map.setFilter('haz-fill', f); map.setFilter('haz-line', f);
  }, [ready, on]);

  const sevPresent = useMemo(() => [...new Set(points.map((p) => p.severity).filter(Boolean))] as Severity[], [points]);

  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-[#edf0f4]" style={{ height: cssSize(height, 420) }}>
      <div ref={el} className="absolute inset-0" style={{ position: "absolute", inset: 0 }} />
      {available.length > 0 && (
        <div className="absolute left-2.5 top-2.5 z-[1] flex items-center gap-1 rounded-lg border border-line bg-surface/95 p-1 shadow-[var(--shadow-card)] backdrop-blur">
          <span className="px-1.5 text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-400">Hazards</span>
          {available.map((k) => {
            const active = on.has(k);
            return (
              <button key={k} onClick={() => setOn((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; })}
                className={cx('inline-flex h-6 items-center gap-1.5 rounded-md px-2 text-[11.5px] font-medium transition-colors', active ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-100')}>
                <span className="size-2 rounded-full" style={{ background: HAZ[k].color, opacity: active ? 1 : 0.6 }} />{HAZ[k].label}
              </button>
            );
          })}
        </div>
      )}
      {(sevPresent.length > 0 || (zones && zones.length > 0)) && (
        <div className="pointer-events-none absolute bottom-2.5 left-2.5 z-[1] flex items-center gap-3 rounded-md border border-line bg-surface/95 px-2.5 py-1.5 text-[11px] text-ink-600 shadow-[var(--shadow-card)]">
          {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as Severity[]).filter((s) => sevPresent.includes(s)).map((s) => (
            <span key={s} className="inline-flex items-center gap-1"><span className="size-2 rounded-full" style={{ background: SEV_COLOR[s] }} />{s[0] + s.slice(1).toLowerCase()}</span>
          ))}
          {zones && zones.length > 0 && <>
            <span className="h-3 w-px bg-line" />
            {[['#0e8585', '< 80%'], ['#b88404', '80–100%'], ['#c2263a', '> 100%']].map(([c, l]) => (
              <span key={l} className="inline-flex items-center gap-1"><span className="size-2.5 rounded-full border-[1.5px]" style={{ borderColor: c, background: `${c}22` }} />{l}</span>
            ))}
          </>}
        </div>
      )}
      {tilesDown && <div className="pointer-events-none absolute bottom-2.5 right-2.5 z-[1] rounded bg-surface/90 px-1.5 py-0.5 text-[10.5px] text-ink-400">Basemap offline</div>}
    </div>
  );
}
