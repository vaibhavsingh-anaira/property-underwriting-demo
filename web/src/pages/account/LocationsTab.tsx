import { useMemo, useState } from 'react';
import type { AccountDetail, LocationRow, Severity } from '@/api/types';
import { rawUrl } from '@/api/client';
import { Card, Badge, Segmented, SeverityDot, Empty, cx } from '@/components/ui';
import { EvidenceLink, useEvidence } from '@/components/evidence';
import { usd, pct, num } from '@/lib/format';
import { GeoMap, type MapPoint } from '@/viewers/GeoMap';
import { ModelViewer } from '@/viewers/ModelViewer';
import { ImageCompare } from '@/viewers/ImageCompare';
import { Bar, SectionLabel } from '../common';
import { Info } from '@/help/Info';

type Filter = 'all' | 'new' | 'deleted' | 'changed' | 'flagged';
const SEV_RANK: Record<Severity, number> = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };
const topSev = (l: LocationRow): Severity | null => l.flags.reduce<Severity | null>((a, f) => (!a || SEV_RANK[f.severity] > SEV_RANK[a] ? f.severity : a), null);
const SEV_COLOR: Record<Severity, string> = { CRITICAL: '#c2263a', HIGH: '#d15a12', MEDIUM: '#b88404', LOW: '#8b95aa' };
const MATCH_TONE = { MATCHED: 'ok', NEW: 'info', DELETED: 'neutral', MERGED: 'accent', SPLIT: 'accent', AMBIGUOUS: 'high' } as const;

export default function LocationsTab({ a }: { a: AccountDetail }) {
  const [filter, setFilter] = useState<Filter>('all');
  const [sel, setSel] = useState<string | null>(() => a.locations.find((l) => l.model_doc_id)?.location_uid ?? a.locations.find((l) => l.flags.length)?.location_uid ?? null);
  const changed = (l: LocationRow) => (l.tiv_change_pct !== null && Math.abs(l.tiv_change_pct) >= 0.05) || (!!l.occupancy_prior && l.occupancy_prior !== l.occupancy);
  const rows = a.locations.filter((l) => filter === 'all' || (filter === 'new' ? l.match_status === 'NEW' : filter === 'deleted' ? l.match_status === 'DELETED' : filter === 'changed' ? changed(l) : l.flags.length > 0));
  const cnt = { new: a.locations.filter((l) => l.match_status === 'NEW').length, deleted: a.locations.filter((l) => l.match_status === 'DELETED').length, changed: a.locations.filter(changed).length, flagged: a.locations.filter((l) => l.flags.length).length };
  const tp = a.locations.reduce((s, l) => s + (l.tiv_prior ?? 0), 0), tc = a.locations.reduce((s, l) => s + (l.tiv_current ?? 0), 0);
  const selected = a.locations.find((l) => l.location_uid === sel) ?? null;
  const points: MapPoint[] = useMemo(() => a.locations.map((l) => ({ id: l.location_uid, lat: l.lat, lon: l.lon, label: `Loc ${l.loc_no_current ?? l.loc_no_prior} · ${l.name}`, sublabel: `${l.city}, ${l.state} · ${usd(l.tiv_current ?? l.tiv_prior)}`, severity: topSev(l), value: l.tiv_current ?? l.tiv_prior ?? 0, status: l.match_status })), [a.locations]);

  return (
    <div className="space-y-4">
      {a.site_model_doc_id && (
        <Card title="Site model" subtitle="Buildings coloured by worst open flag · hover for attributes" pad={false}>
          <ModelViewer url={rawUrl(a.site_model_doc_id)} height={380} colorBy={colorFor(a.locations)} legend={LEGEND} />
        </Card>
      )}
      <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Location redline<Info id="account.locations" /></span>} subtitle={<>TIV <span className="num">{usd(tp)} → {usd(tc)}</span> (<span className="num">{pct(tp ? tc / tp - 1 : null, 1, true)}</span>) · values compared per matched building, never only at account totals</>}
        actions={<Segmented value={filter} onChange={setFilter} options={[{ key: 'all', label: `All ${a.locations.length}` }, { key: 'new', label: `New ${cnt.new}` }, { key: 'deleted', label: `Deleted ${cnt.deleted}` }, { key: 'changed', label: `Changed ${cnt.changed}` }, { key: 'flagged', label: `Flagged ${cnt.flagged}` }]} />}>
        <div className="max-h-[520px] overflow-auto">
          <table className="dt min-w-[1300px]">
            <thead><tr><th>Loc</th><th>Location</th><th>Match</th><th className="r">TIV prior → current</th><th className="r">Δ</th><th>COPE change</th><th>Valuation vs model RC</th><th>Wind</th><th className="r">AAL</th><th>Flags</th></tr></thead>
            <tbody>
              {rows.map((l) => <Row key={l.location_uid} l={l} selected={l.location_uid === sel} onClick={() => setSel(l.location_uid)} />)}
            </tbody>
          </table>
          {rows.length === 0 && <Empty>No locations in this filter.</Empty>}
        </div>
      </Card>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-6" pad={false} title={<span className="inline-flex items-center gap-1.5">Map<Info id="account.map" /></span>} subtitle="Selection syncs with the table">
          <GeoMap points={points} selectedId={sel} onSelect={setSel} height={420} />
        </Card>
        <div className="col-span-12 space-y-4 xl:col-span-6">
          {selected ? <LocationDetail l={selected} /> : <Card><Empty>Select a location.</Empty></Card>}
        </div>
      </div>
    </div>
  );
}

const LEGEND = [{ color: SEV_COLOR.CRITICAL, label: 'Critical flag' }, { color: SEV_COLOR.HIGH, label: 'High flag' }, { color: SEV_COLOR.MEDIUM, label: 'Medium flag' }, { color: '#9aa6bb', label: 'No open flag' }];
function colorFor(locs: LocationRow[]) {
  const c: Record<string, string> = {};
  locs.forEach((l, i) => { const s = topSev(l); if (s) { c[`B-${l.loc_no_current ?? i + 1}`] = SEV_COLOR[s]; c[`B-${i + 1}`] ??= SEV_COLOR[s]; } });
  if (locs.some((l) => l.flags.some((f) => f.code === 'FIRE.SPRINKLER_ADEQUACY'))) { c['RACK-04'] = SEV_COLOR.CRITICAL; c['RACK-05'] = SEV_COLOR.CRITICAL; }
  return c;
}

function Row({ l, selected, onClick }: { l: LocationRow; selected: boolean; onClick: () => void }) {
  const ev = useEvidence();
  const occChanged = !!l.occupancy_prior && l.occupancy_prior !== l.occupancy;
  return (
    <tr onClick={onClick} className={cx('cursor-pointer', selected && 'is-selected', l.match_status === 'DELETED' && 'opacity-50')}>
      <td className="num whitespace-nowrap text-[12px]"><span className="text-ink-400">{l.loc_no_prior ?? '—'}</span> → <span className="font-semibold text-ink-900">{l.loc_no_current ?? '—'}</span></td>
      <td className="max-w-[230px]"><div className="truncate font-medium text-ink-900">{l.name}</div><div className="truncate text-[11px] text-ink-500">{l.address ? `${l.address}, ` : ''}{l.city}, {l.state}{l.buildings > 1 ? ` · ${l.buildings} bldgs` : ''}</div></td>
      <td><Badge tone={MATCH_TONE[l.match_status]} title={`${l.match_method ?? 'no prior match'}${l.match_score !== null ? ` · score ${l.match_score.toFixed(2)}` : ''}${l.match_confirmed_by ? ` · confirmed by ${l.match_confirmed_by}` : ''}`}>{l.match_status}{l.match_score !== null && l.match_status !== 'MATCHED' ? ` ${l.match_score.toFixed(2)}` : ''}</Badge></td>
      <td className="num r whitespace-nowrap">
        <span className="text-ink-500">{usd(l.tiv_prior)}</span> → <EvidenceLink obsId={l.tiv_current !== null ? `ob-${l.location_uid}-tiv` : null} className="font-semibold text-ink-950">{usd(l.tiv_current)}</EvidenceLink>
      </td>
      <td className={cx('num r font-medium', l.match_status === 'NEW' ? 'text-info' : l.tiv_change_pct === 0 ? 'text-med' : l.tiv_change_pct !== null && l.tiv_change_pct > 0.15 ? 'text-high' : 'text-ink-700')}>
        {l.match_status === 'NEW' ? 'new' : l.match_status === 'DELETED' ? 'deleted' : pct(l.tiv_change_pct, 1, true)}
      </td>
      <td className="max-w-[260px] text-[12px]">
        {occChanged ? <button onClick={(e) => { e.stopPropagation(); ev.openObs(`ob-${l.location_uid}-occ`); }} className="text-left"><span className="text-ink-400 line-through">{l.occupancy_prior}</span> → <span className="rounded bg-crit-bg px-1 font-medium text-crit">{l.occupancy}</span></button>
          : l.flags.some((f) => f.code === 'ROOF.YEAR_CONFLICT') ? <button onClick={(e) => { e.stopPropagation(); ev.openObs(`ob-${l.location_uid}-roof`); }} className="text-left text-high underline decoration-dotted underline-offset-2">Roof: {l.flags.find((f) => f.code === 'ROOF.YEAR_CONFLICT')!.label.replace('Roof year: ', '')}</button>
          : l.match_status === 'NEW' ? <span className="text-ink-500">{l.construction} · roof {l.roof_year ?? 'unknown'} · sprinkler {l.sprinkler}</span> : <span className="text-ink-400">—</span>}
      </td>
      <td className="w-[150px]">
        {l.valuation_ratio === null ? <span className="text-ink-400">n/a</span> : (
          <div className="flex items-center gap-2"><Bar value={l.valuation_ratio} max={1.1} marker={0.8} tone={l.valuation_ratio < 0.8 ? 'crit' : l.valuation_ratio < 0.9 ? 'med' : 'ok'} className="w-20" /><span className={cx('num text-[12px] font-medium', l.valuation_ratio < 0.8 ? 'text-crit' : 'text-ink-700')}>{pct(l.valuation_ratio, 0)}</span></div>
        )}
      </td>
      <td>{l.wind_tier ? <Badge tone={l.wind_tier === 'T1' ? 'crit' : l.wind_tier === 'T2' ? 'high' : 'neutral'}>{l.wind_tier}</Badge> : <span className="text-ink-400">—</span>}</td>
      <td className="num r">{l.aal !== null ? usd(l.aal) : <span className="text-crit">not modelled</span>}</td>
      <td className="max-w-[280px]">
        <div className="flex flex-wrap gap-1">{l.flags.map((f, i) => <Badge key={i} tone={f.severity === 'CRITICAL' ? 'crit' : f.severity === 'HIGH' ? 'high' : f.severity === 'MEDIUM' ? 'med' : 'low'}>{f.label}</Badge>)}</div>
      </td>
    </tr>
  );
}

function LocationDetail({ l }: { l: LocationRow }) {
  const [node, setNode] = useState<{ name: string; extras: Record<string, unknown> } | null>(null);
  const imgs = l.imagery_doc_ids.slice(-2);
  return (
    <>
      <Card title={<span className="flex items-center gap-2">{topSev(l) && <SeverityDot s={topSev(l)!} />}Loc {l.loc_no_current ?? l.loc_no_prior} · {l.name}</span>} subtitle={`${l.address}, ${l.city}, ${l.state}`}>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[12px] md:grid-cols-3">
          {[
            ['Occupancy', <EvidenceLink key="o" obsId={`ob-${l.location_uid}-occ`}>{l.occupancy}</EvidenceLink>],
            ['Construction', <EvidenceLink key="c" obsId={`ob-${l.location_uid}-const`}>{l.construction}</EvidenceLink>],
            ['Year built', l.year_built ?? '—'], ['Stories', l.stories ?? '—'], ['Sq ft', num(l.sqft)],
            ['Roof year', <EvidenceLink key="r" obsId={`ob-${l.location_uid}-roof`}>{l.roof_year ?? 'unknown'}</EvidenceLink>],
            ['Sprinkler', l.sprinkler], ['CAT zone', l.cat_zone ?? '—'], ['TIV $/sq ft', l.sqft && l.tiv_current ? `$${Math.round(l.tiv_current / l.sqft)}` : '—'],
          ].map(([k, v]) => <div key={String(k)} className="flex justify-between gap-2 border-b border-line py-1"><span className="text-ink-500">{k}</span><span className="num truncate text-right text-ink-900">{v}</span></div>)}
        </div>
      </Card>
      {l.model_doc_id && (
        <Card pad={false} title={<span className="inline-flex items-center gap-1.5">3D model<Info id="account.model3d" /></span>} subtitle={node ? `${node.name}${node.extras.flag ? ` — ${String(node.extras.flag)}` : ''}` : 'Click a building or rack for attributes'}>
          <ModelViewer url={rawUrl(l.model_doc_id)} height={340} colorBy={colorFor([l])} legend={LEGEND} onSelectNode={(name, extras) => setNode({ name, extras })} />
        </Card>
      )}
      {imgs.length === 2 && (
        <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Aerial imagery — before / after<Info id="account.imagery" /></span>}>
          <ImageCompare before={{ url: rawUrl(imgs[0]), label: 'Earlier capture' }} after={{ url: rawUrl(imgs[1]), label: 'Latest capture' }} height={300} />
        </Card>
      )}
      {!l.model_doc_id && imgs.length < 2 && <div className="px-1"><SectionLabel>No 3D model or imagery pair for this location</SectionLabel></div>}
    </>
  );
}
