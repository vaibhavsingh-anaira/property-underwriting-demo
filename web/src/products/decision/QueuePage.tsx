// New-business case queue: every submission with its stage, draft, verdict and SLA.
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Page, Card, Tabs, Input, Select, Badge, Loading, ErrorBox, Empty, cx } from '@/components/ui';
import { usd, pct, fmtDate } from '@/lib/format';
import { Info } from '@/help/Info';
import { DRAFT_LABEL, STATUS_LABEL, useCases, type QueueItem } from './api';
import { StageDots, VerdictBadge } from './parts';

type Tab = 'open' | 'review' | 'referred' | 'decided' | 'all';
const OPEN = ['PREPARED', 'IN_REVIEW', 'READY', 'HOLD', 'REFERRED', 'APPROVED', 'QUOTED', 'ACCEPTED'];

export default function QueuePage() {
  const { data, isLoading, error } = useCases();
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>('open');
  const [q, setQ] = useState('');
  const [uw, setUw] = useState('');
  const [verdict, setVerdict] = useState('');
  const base = useMemo(() => (data ?? []).filter((c) => (!q || `${c.insured} ${c.broker} ${c.scenario ?? ''} ${c.state}`.toLowerCase().includes(q.toLowerCase()))
    && (!uw || c.underwriter_id === uw) && (!verdict || c.verdict === verdict)), [data, q, uw, verdict]);
  const pick = (t: Tab) => base.filter((c) => t === 'all' ? true : t === 'open' ? OPEN.includes(c.status) || c.status === 'EXPECTED'
    : t === 'review' ? ['PREPARED', 'IN_REVIEW', 'HOLD'].includes(c.status) : t === 'referred' ? c.referral_pending || c.status === 'REFERRED' : ['BOUND', 'DECLINED', 'LOST'].includes(c.status));
  const rows = [...pick(tab)].sort((a, b) => Number(b.hero) - Number(a.hero) || (a.sla_days ?? 999) - (b.sla_days ?? 999) || (b.received ?? '').localeCompare(a.received ?? ''));
  const uws = [...new Map((data ?? []).map((c) => [c.underwriter_id, c.underwriter])).entries()];
  return (
    <Page title="Case queue" subtitle="New-business submissions · hero cases first, then by quote deadline" actions={<Info id="decision.queue" label="About this page" />}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-400" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Insured, broker, scenario…" className="w-[240px] pl-8" /></div>
        <Select value={uw} onChange={(e) => setUw(e.target.value)}><option value="">All underwriters</option>{uws.map(([id, n]) => <option key={id} value={id}>{n}</option>)}</Select>
        <Select value={verdict} onChange={(e) => setVerdict(e.target.value)}><option value="">Any verdict</option><option value="PASS">Pass</option><option value="PASS_WITH_FLAGS">Pass with flags</option><option value="REFER_HOLD">Refer / hold</option></Select>
      </div>
      <Tabs value={tab} onChange={setTab} tabs={(['open', 'review', 'referred', 'decided', 'all'] as Tab[]).map((k) => ({ key: k, label: { open: 'Open', review: 'Needs underwriter', referred: 'Referred', decided: 'Decided', all: 'All' }[k], count: pick(k).length }))} />
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <Card pad={false} className="mt-3 overflow-hidden">
          <div className="max-h-[calc(100vh-270px)] overflow-auto">
            <table className="dt min-w-[1300px]">
              <thead><tr><th>Submission</th><th>Received</th><th>SLA</th><th>Stages</th><th>Status</th><th>Draft</th><th>Verdict</th><th className="r">TIV</th><th className="r">Technical</th><th className="r">Intended</th><th className="r">Issues</th><th className="r">Exposure</th></tr></thead>
              <tbody>{rows.map((c) => <Row key={c.case_id} c={c} onClick={() => nav(`/decision/cases/${c.case_id}`)} />)}</tbody>
            </table>
            {rows.length === 0 && <Empty>No cases match.</Empty>}
          </div>
        </Card>
      )}
    </Page>
  );
}

function Row({ c, onClick }: { c: QueueItem; onClick: () => void }) {
  return (
    <tr className="cursor-pointer" onClick={onClick}>
      <td className="max-w-[300px]">
        <div className="flex items-center gap-1.5">{c.scenario && <Badge tone="dark">{c.scenario}</Badge>}<span className="truncate font-medium text-ink-950">{c.short}</span></div>
        <div className="truncate text-[11px] text-ink-500">{c.title ?? `${c.class_label ?? '—'} · ${c.state}`} · {c.broker} · {c.underwriter}</div>
      </td>
      <td className="num whitespace-nowrap">{c.received ? fmtDate(c.received) : <span className="text-ink-400">expected {fmtDate(c.expected)}</span>}</td>
      <td className="whitespace-nowrap">{c.sla_days === null ? <span className="text-ink-400">—</span> : <span className={cx('num rounded px-1.5 text-[11px] font-semibold', c.sla_days < 0 ? 'bg-crit text-white' : c.sla_days < 4 ? 'bg-crit-bg text-crit' : 'bg-ink-100 text-ink-700')}>{c.sla_days < 0 ? `${-c.sla_days}d late` : `${c.sla_days}d`}</span>}</td>
      <td><StageDots n={c.stage} /></td>
      <td><Badge tone={c.status === 'BOUND' ? 'dark' : c.status === 'DECLINED' || c.status === 'HOLD' ? 'crit' : c.status === 'REFERRED' ? 'info' : 'neutral'}>{STATUS_LABEL[c.status] ?? c.status}</Badge></td>
      <td className="whitespace-nowrap text-[12px] text-ink-700">{c.draft ? DRAFT_LABEL[c.draft] : '—'}</td>
      <td><VerdictBadge v={c.verdict} /></td>
      <td className="num r">{usd(c.tiv)}</td>
      <td className="num r">{usd(c.technical)}</td>
      <td className="num r whitespace-nowrap">{c.premium ? <>{usd(c.premium)} <span className={cx('text-[11px]', (c.deviation ?? 0) < -0.05 ? 'text-crit' : 'text-ink-500')}>{pct(c.deviation, 1, true)}</span></> : '—'}</td>
      <td className="num r whitespace-nowrap text-[12px]">{c.contradictions ? <span className="text-high">{c.contradictions} contra.</span> : null}{c.contradictions && c.missing ? ' · ' : ''}{c.missing ? <span>{c.missing} missing</span> : null}{!c.contradictions && !c.missing && '—'}</td>
      <td className="num r font-medium">{c.exposure ? usd(c.exposure) : '—'}</td>
    </tr>
  );
}
