// Breach register across coverholders — one entry per policy (or claim / zone / bordereau), filterable.
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Page, Card, Loading, ErrorBox, Input, Select, Segmented, Badge, Empty, cx } from '@/components/ui';
import { fmtDate, usd } from '@/lib/format';
import { Info } from '@/help/Info';
import { FAMILY_LABEL, MONTH, useCoverholders, useRegister } from '../api';
import { StatusPill } from '../parts';
import { PolicyDrawer } from '../PolicyDrawer';

export default function Breaches() {
  const [sp, setSp] = useSearchParams();
  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); setSp(n, { replace: true }); };
  const f = { ch: sp.get('ch') ?? undefined, status: sp.get('status') ?? 'open', family: sp.get('family') ?? undefined, month: sp.get('month') ?? undefined, subject: sp.get('subject') ?? undefined, query: sp.get('query') ?? undefined };
  const { data, isLoading, error } = useRegister(f);
  const { data: chs } = useCoverholders();
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<string | null>(sp.get('key'));
  const rows = useMemo(() => (data ?? []).filter((r) => !q || `${r.insured} ${r.certificate_ref} ${r.ch_name}`.toLowerCase().includes(q.toLowerCase())), [data, q]);
  const stake = rows.reduce((a, r) => a + r.impact_usd, 0);
  return (
    <Page title="Breach register" actions={<Info id="delegated.breaches" label="About this page" />}
      subtitle={<>{rows.length} entries · <span className="num">{usd(stake)}</span> at stake in view · premium tied <span className="num">{usd(rows.reduce((a, r) => a + r.premium_tied, 0))}</span> · click a row for the side-by-side authority result</>}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-400" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Insured, certificate…" className="w-[220px] pl-8" /></div>
        <Segmented value={f.status} onChange={(v) => set('status', v)} options={[{ key: 'open', label: 'Open' }, { key: 'closed', label: 'Closed' }, { key: 'all', label: 'All' }]} />
        <Select value={f.ch ?? ''} onChange={(e) => set('ch', e.target.value || null)}><option value="">All coverholders</option>{chs?.map((c) => <option key={c.id} value={c.id}>{c.scenario} · {c.short}</option>)}</Select>
        <Select value={f.family ?? ''} onChange={(e) => set('family', e.target.value || null)}><option value="">All exception types</option>{Object.entries(FAMILY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
        <Select value={f.month ?? ''} onChange={(e) => set('month', e.target.value || null)}><option value="">All months</option>{['2026-05', '2026-06', '2026-07', '2026-08'].map((m) => <option key={m} value={m}>{MONTH(m)}</option>)}</Select>
        <Select value={f.subject ?? ''} onChange={(e) => set('subject', e.target.value || null)}><option value="">Policies, claims, zones, files</option><option value="policy">Policies</option><option value="claim">Claims</option><option value="zone">Zones</option><option value="bordereau">Bordereaux</option></Select>
        {f.query && <Badge tone="accent" className="h-7 px-2">Query {f.query}<button onClick={() => set('query', null)}>×</button></Badge>}
      </div>
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <Card pad={false}>
          <div className="max-h-[calc(100vh-240px)] overflow-auto">
            <table className="dt min-w-[1200px]">
              <thead><tr><th>Coverholder</th><th>Month</th><th>Policy / subject</th><th>Authority exceptions (written vs authority)</th><th>Referral</th><th>Status</th><th className="r">Premium tied</th><th className="r">$ at stake</th><th>Raised</th></tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.key} className="cursor-pointer" onClick={() => setOpen(r.key)}>
                  <td className="whitespace-nowrap"><Badge tone="dark">{r.scenario}</Badge> <span className="text-[12.5px]">{r.ch_name}</span></td>
                  <td className="whitespace-nowrap text-[12px]">{MONTH(r.month)}</td>
                  <td className="max-w-[240px]"><div className="truncate text-[12.5px] font-medium text-ink-900">{r.insured}</div><div className="mono text-[11px] text-ink-500">{r.certificate_ref}{r.txn ? ` · ${r.txn}` : ` · ${r.subject_type}`}</div></td>
                  <td className="max-w-[460px]">{r.checks.filter((c) => c.status !== 'AUTHORISED').map((c) => (
                    <div key={c.exc_id} className={cx('truncate text-[12px]', ['OPEN', 'QUERIED', 'RESPONDED', 'ESCALATED'].includes(c.status) ? 'text-ink-800' : 'text-ink-400 line-through')}>
                      <span className="font-medium">{c.check}</span>: {c.written} vs {c.authority}{c.delta ? <span className="ml-1 font-semibold text-crit">{c.delta}</span> : null}</div>))}</td>
                  <td className="text-[11.5px]">{r.checks.some((c) => c.referral && c.referral !== 'AUTHORISED') ? <span className="text-crit">none located</span> : r.checks.some((c) => c.referral) ? <span className="text-ok">approved</span> : '—'}</td>
                  <td><StatusPill s={r.status} /></td>
                  <td className="num r">{r.premium_tied ? usd(r.premium_tied) : '—'}</td>
                  <td className="num r font-semibold">{r.impact_usd ? usd(r.impact_usd) : '—'}</td>
                  <td className="num whitespace-nowrap text-[12px] text-ink-500">{fmtDate(r.raised_at)}</td>
                </tr>))}</tbody>
            </table>
            {rows.length === 0 && <Empty>No entries match these filters.</Empty>}
          </div>
        </Card>
      )}
      <PolicyDrawer k={open} onClose={() => setOpen(null)} />
    </Page>
  );
}
