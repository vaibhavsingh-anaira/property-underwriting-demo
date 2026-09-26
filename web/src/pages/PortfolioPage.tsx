import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { useAccumulation, useHazards } from '@/api/client';
import { Page, Card, Loading, ErrorBox, Badge, Stat, cx } from '@/components/ui';
import { usd, pct } from '@/lib/format';
import { GeoMap, type MapPoint } from '@/viewers/GeoMap';
import { Bar } from './common';
import { Info } from '@/help/Info';

export default function PortfolioPage() {
  const { data: zones, isLoading, error } = useAccumulation();
  const { data: hazards } = useHazards();
  const sorted = useMemo(() => [...(zones ?? [])].sort((a, b) => b.utilization - a.utilization), [zones]);
  const [sel, setSel] = useState<string | null>(null);
  const zone = sorted.find((z) => z.zone_id === sel) ?? sorted[0];
  const points = useMemo<MapPoint[]>(() => sorted.flatMap((z) => z.accounts.slice(0, 8).map((a, i) => ({
    id: `${z.zone_id}|${a.account_id}`, lat: z.lat + Math.sin(i * 2.4) * z.radius_km / 260, lon: z.lon + Math.cos(i * 2.4) * z.radius_km / 200,
    label: a.name, sublabel: `${z.name} · ${usd(a.contribution)} PML contribution`, value: a.contribution, severity: z.utilization > 0.9 ? 'HIGH' as const : z.utilization > 0.8 ? 'MEDIUM' as const : null,
  }))), [sorted]);
  if (isLoading) return <Page title="Portfolio accumulation"><Loading /></Page>;
  if (error || !zones) return <Page title="Portfolio accumulation"><ErrorBox error={error} /></Page>;
  const hot = sorted.filter((z) => z.utilization > 0.9);
  const inc = zones.reduce((a, z) => a + (z.post_renewal - z.current), 0);
  return (
    <Page title="Portfolio accumulation" actions={<Info id="portfolio.page" label="About this page" />} subtitle="Net PML by zone before renewals and if every renewal binds as proposed · hazard layers from vendor stubs">
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Zones monitored" value={zones.length} />
        <Stat label="Zones over 90% post-renewal" value={hot.length} tone={hot.length ? 'crit' : 'ok'} sub={hot.map((z) => z.name).join(', ') || 'none'} />
        <Stat label="PML added by renewals" value={usd(inc)} sub="Σ post-renewal − current" />
        <Stat label="Peak utilisation" value={pct(sorted[0]?.utilization, 0)} tone={sorted[0]?.utilization > 0.9 ? 'crit' : undefined} sub={sorted[0]?.name} />
      </div>
      <Card pad={false} className="mb-4">
        <GeoMap points={points} zones={zones} hazards={hazards} hazardLayers={['wind']} height={520} fitTo="us" selectedId={null}
          onSelect={(id) => setSel(id.split('|')[0])} />
      </Card>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-7" pad={false} title="Zones" subtitle="Threshold = net PML capacity · tick marks 90% referral line">
          <table className="dt">
            <thead><tr><th>Zone</th><th>Peril</th><th className="r">Threshold</th><th className="r">Current</th><th className="r">Post-renewal</th><th className="w-[22%]">Utilisation</th><th className="r" /></tr></thead>
            <tbody>
              {sorted.map((z) => (
                <tr key={z.zone_id} onClick={() => setSel(z.zone_id)} className={cx('cursor-pointer', zone?.zone_id === z.zone_id && 'is-selected')}>
                  <td className="font-medium text-ink-900">{z.name}{z.utilization > 0.9 && <AlertTriangle className="ml-1 inline size-3.5 text-crit" />}</td>
                  <td className="text-ink-600">{z.peril}</td>
                  <td className="num r">{usd(z.threshold)}</td>
                  <td className="num r">{usd(z.current)} <span className="text-[11px] text-ink-400">{pct(z.current / z.threshold, 0)}</span></td>
                  <td className="num r font-semibold">{usd(z.post_renewal)}</td>
                  <td><Bar value={z.post_renewal} max={z.threshold} marker={z.threshold * 0.9} tone={z.utilization > 0.9 ? 'crit' : z.utilization > 0.8 ? 'med' : 'accent'} /></td>
                  <td className={cx('num r font-semibold', z.utilization > 0.9 ? 'text-crit' : 'text-ink-800')}>{pct(z.utilization, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        {zone && (
          <Card className="col-span-12 xl:col-span-5" pad={false} title={`${zone.name} — contributing renewals`} subtitle={`${zone.peril} · radius ${zone.radius_km} km · +${usd(zone.post_renewal - zone.current)} from renewals`}
            actions={zone.utilization > 0.9 ? <Badge tone="crit">Senior referral required</Badge> : undefined}>
            <table className="dt">
              <thead><tr><th>Account</th><th className="r">PML contribution</th><th className="r">Share of zone</th></tr></thead>
              <tbody>
                {zone.accounts.map((a) => (
                  <tr key={a.account_id}>
                    <td><Link to={`/accounts/${a.account_id}`} className="text-ink-900 hover:text-accent-700">{a.name}</Link></td>
                    <td className="num r">{usd(a.contribution)}</td>
                    <td className="num r text-ink-500">{pct(a.contribution / zone.post_renewal, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {zone.accounts.length === 0 && <div className="p-4 text-[12px] text-ink-500">No renewing accounts in this zone.</div>}
            <div className="border-t border-line px-4 py-2 text-[11px] text-ink-500">Remaining zone PML is from in-force policies not renewing in this window.</div>
          </Card>
        )}
      </div>
    </Page>
  );
}
