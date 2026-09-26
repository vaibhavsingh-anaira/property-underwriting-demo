import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { useRules } from '@/api/client';
import { Page, Card, Badge, Segmented, Loading, ErrorBox, SeverityPill, Stat, cx } from '@/components/ui';
import { fmtDate, pct } from '@/lib/format';
import { FAMILY_LABEL } from './common/families';
import { Info } from '@/help/Info';
import { useProduct } from '@/products';

export default function RulesPage() {
  const { data: all, isLoading, error } = useRules();
  const nav = useNavigate();
  const prod = useProduct();
  const product = useSearchParams()[0].get('product') ?? prod.id;
  const data = useMemo(() => all?.filter((r) => ((r as { product?: string }).product ?? 'renewal') === product), [all, product]);
  const [origin, setOrigin] = useState<'all' | 'standard_library' | 'carrier_guideline'>('all');
  const rules = useMemo(() => (data ?? []).filter((r) => origin === 'all' || r.origin === origin), [data, origin]);
  const fams = [...new Set(rules.map((r) => r.family))];
  const flagged = (data ?? []).filter((r) => r.stats.precision !== null && r.stats.precision < 0.6);
  return (
    <Page title="Rule studio" subtitle="YAML + CEL rules with effective dates · every change is tested and backtested on a frozen control set before publishing"
      actions={<><Info id="rules.page" label="About this page" /><Segmented value={origin} onChange={setOrigin} options={[{ key: 'all', label: 'All' }, { key: 'standard_library', label: 'Standard library' }, { key: 'carrier_guideline', label: 'Carrier guideline' }]} /></>}>
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Rules live" value={data!.length} sub={`${data!.filter((r) => r.origin === 'standard_library').length} standard library · ${data!.filter((r) => r.origin === 'carrier_guideline').length} carrier`} />
            <Stat label="Fired (book)" value={data!.reduce((a, r) => a + r.stats.fired, 0)} />
            <Stat label="Book precision" value={pct(data!.reduce((a, r) => a + r.stats.accepted, 0) / Math.max(1, data!.reduce((a, r) => a + r.stats.accepted + r.stats.rejected, 0)), 0)} sub="accepted ÷ dispositioned" />
            <Stat label="Flagged for review" value={flagged.length} tone={flagged.length ? 'high' : 'ok'} sub="precision < 60% (rejection > 40%)" />
          </div>
          <Card pad={false}>
            <table className="dt">
              <thead><tr><th>Rule</th><th>Origin</th><th className="r">Ver</th><th>Effective</th><th>Applies to</th><th>Outcome</th><th className="r">Fired</th><th className="r">Accepted</th><th className="r">Rejected</th><th className="r">Precision</th></tr></thead>
              {fams.map((f) => (
                <tbody key={f}>
                  <tr><td colSpan={10} className="!bg-ink-50/60 !py-1 text-[11px] font-medium uppercase tracking-[.05em] text-ink-500">{FAMILY_LABEL[f] ?? f}</td></tr>
                  {rules.filter((r) => r.family === f).map((r) => {
                    const low = r.stats.precision !== null && r.stats.precision < 0.6;
                    return (
                      <tr key={r.rule_id} className="cursor-pointer" onClick={() => nav(prod.to(`/rules/${r.rule_id}`))}>
                        <td><div className="mono text-[12px] font-semibold text-ink-900">{r.rule_id}</div><div className="text-[11.5px] text-ink-500">{r.title}</div></td>
                        <td><Badge tone={r.origin === 'carrier_guideline' ? 'accent' : 'neutral'}>{r.origin === 'carrier_guideline' ? 'Carrier guideline' : 'Standard library'}</Badge></td>
                        <td className="num r">v{r.version}</td>
                        <td className="num text-[12px]">{fmtDate(r.effective_from)}{r.effective_to ? ` – ${fmtDate(r.effective_to)}` : ' →'}</td>
                        <td className="mono text-[11.5px] text-ink-600">{r.applies_to}</td>
                        <td><span className="flex items-center gap-1"><Badge>{r.outcome}</Badge><SeverityPill s={r.severity} /></span></td>
                        <td className="num r">{r.stats.fired}</td><td className="num r text-ok">{r.stats.accepted}</td><td className="num r text-crit">{r.stats.rejected}</td>
                        <td className={cx('num r font-semibold', low ? 'text-crit' : 'text-ink-900')}>{low && <AlertTriangle className="mr-1 inline size-3.5" />}{pct(r.stats.precision, 0)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              ))}
            </table>
          </Card>
        </>
      )}
    </Page>
  );
}
