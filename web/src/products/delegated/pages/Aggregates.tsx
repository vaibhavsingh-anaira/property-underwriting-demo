// Zone aggregates vs the limits in each binding authority, restrictions, and exposure prevented.
import { useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { Page, Card, Loading, ErrorBox, Badge, Button, cx } from '@/components/ui';
import { fmtDate, pct, usd } from '@/lib/format';
import { Info } from '@/help/Info';
import { MONTH, useAggregates, useDaAction } from '../api';
import { ChLink, Src, UtilBar } from '../parts';

export default function Aggregates() {
  const { data, isLoading, error } = useAggregates();
  const act = useDaAction();
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <Page title="Aggregates & capacity" actions={<Info id="delegated.aggregates" label="About this page" />}
      subtitle="In-force TIV by CAT zone = exposure return (30 Apr) + every bordereau movement since · limits and warning levels read from each BAA as endorsed">
      {msg && <div className="mb-3 rounded-md bg-ok-bg px-3 py-2 text-[12.5px] text-ok">{msg}</div>}
      {isLoading ? <Loading /> : error || !data ? <ErrorBox error={error} /> : (
        <div className="space-y-4">
          {data.map((c) => (
            <Card key={c.ch} pad={false} title={<span className="flex items-center gap-2"><Badge tone="dark">{c.scenario}</Badge><ChLink id={c.ch}>{c.name}</ChLink></span>}
              subtitle={`GPI ${usd(c.capacity.ytd)} YTD · projected ${usd(c.capacity.projected)} of ${usd(c.capacity.limit)} (${pct(c.capacity.util, 0)})` + (c.prevented.length ? ` · ${c.prevented.length} risks declined at referral, ${usd(c.prevented.reduce((a, p) => a + p.tiv, 0))} TIV kept out` : '')}>
              <table className="dt">
                <thead><tr><th>Zone</th><th>Peril</th><th className="r">In-force TIV</th><th className="r">Limit</th><th className="r">1-in-100 PML</th><th className="w-[26%]">Utilisation</th>{c.history.map((h) => <th key={h.month} className="r">{MONTH(h.month).slice(0, 3)}</th>)}<th>Status</th><th /></tr></thead>
                <tbody>{c.zones.map((z) => (
                  <tr key={z.zone}>
                    <td><span className="font-medium text-ink-900">{z.name}</span> <span className="mono text-[11px] text-ink-400">{z.zone}</span></td>
                    <td className="text-[12px]">{z.peril}</td><td className="num r">{usd(z.tiv)}</td><td className="num r">{usd(z.limit)} <Src anchor={z.anchor} kind="clause" label="p" /></td><td className="num r text-ink-600">{usd(z.pml_100)}</td>
                    <td><div className="flex items-center gap-2"><UtilBar util={z.util} warn={z.warn} /><span className={cx('num w-12 text-right text-[12px] font-semibold', z.util >= z.warn ? 'text-crit' : '')}>{pct(z.util, 1)}</span></div></td>
                    {c.history.map((h) => <td key={h.month} className={cx('num r text-[12px]', (h.zones[z.zone] ?? 0) >= z.warn ? 'font-semibold text-crit' : 'text-ink-600')}>{pct(h.zones[z.zone], 0)}</td>)}
                    <td><Badge tone={z.status !== 'Open' ? 'high' : z.util >= z.warn ? 'crit' : 'neutral'}>{z.status !== 'Open' ? `${z.status} only` : z.util >= z.warn ? 'Above warning' : 'Open'}</Badge></td>
                    <td className="r">{z.status === 'Open' && z.util >= z.warn && (
                      <Button size="sm" icon={<ShieldAlert className="size-3.5" />} loading={act.isPending}
                        onClick={() => act.mutate({ path: `coverholders/${c.ch}/restrict`, body: { zone: z.zone, mode: 'Refer' } }, { onSuccess: (r) => setMsg(r.message) })}>Refer new business</Button>)}</td>
                  </tr>))}</tbody>
              </table>
              {c.restrictions.map((r) => <div key={r.doc_id} className="border-t border-line px-4 py-2 text-[12px] text-high">{r.name}: incremental business {r.mode.toLowerCase()} from {fmtDate(r.effective)} (issued at {pct(r.util_at_issue, 1)}) <Src docId={r.doc_id} kind="clause" label="endorsement" /></div>)}
            </Card>
          ))}
        </div>
      )}
    </Page>
  );
}
