import { useMemo, useRef, useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, ChevronsUpDown, Search, X, Zap } from 'lucide-react';
import { api, getCurrentUserId, useRenewals, useUsers } from '@/api/client';
import type { RenewalQueueItem } from '@/api/types';
import { Page, Card, Tabs, Input, Select, Button, Badge, Loading, ErrorBox, Empty, ScoreRing, SeverityDot, cx } from '@/components/ui';
import { usd, pct, fmtDate } from '@/lib/format';
import { ActionChips, NoticeCountdown, PassDots, ScenarioChip, StatusBadge, useHotkeys } from './common';
import { FAMILY_LABEL, familyMatch } from './common/families';
import { Info } from '@/help/Info';

type Tab = 'all' | 'action' | 'fast' | 'referred' | 'not_started';
type SortKey = 'priority' | 'name' | 'expiry' | 'notice' | 'impact' | 'score' | 'rarc';

export default function RenewalsPage() {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const { data, isLoading, error } = useRenewals();
  const { data: users } = useUsers();
  const status = sp.get('status');
  const initialTab: Tab = status === 'FAST_TRACK' ? 'fast' : status === 'REFERRED' ? 'referred' : status === 'NOT_STARTED' ? 'not_started' : status === 'ACTION_REQUIRED' ? 'action' : 'all';
  const [tab, setTab] = useState<Tab>(initialTab);
  const [q, setQ] = useState('');
  const [mine, setMine] = useState(false);
  const [sort, setSort] = useState<{ k: SortKey; dir: 1 | -1 }>({ k: 'priority', dir: 1 });
  const [cursor, setCursor] = useState(0);
  const [lane, setLane] = useState(initialTab === 'fast');
  const uw = sp.get('uw') ?? '';
  const broker = sp.get('broker');
  const family = sp.get('family');
  const setParam = (k: string, v: string | null) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); setSp(n, { replace: true }); };

  const base = useMemo(() => (data ?? []).filter((i) =>
    (!uw || i.underwriter_id === uw) && (!mine || i.underwriter_id === getCurrentUserId()) && (!broker || i.broker === broker) &&
    (!family || familyMatch(family, i)) && (!q || `${i.name} ${i.broker} ${i.state} ${i.scenario ?? ''}`.toLowerCase().includes(q.toLowerCase()))), [data, uw, mine, broker, family, q]);
  const fast = base.filter((i) => i.status === 'FAST_TRACK');
  const rest = base.filter((i) => i.status !== 'FAST_TRACK');
  const counts = { all: rest.length, action: rest.filter((i) => i.status === 'ACTION_REQUIRED' || i.status === 'IN_REVIEW').length, fast: fast.length, referred: rest.filter((i) => i.status === 'REFERRED').length, not_started: rest.filter((i) => i.status === 'NOT_STARTED').length };
  const rows = useMemo(() => {
    const r = rest.filter((i) => tab === 'all' || tab === 'fast' ? true : tab === 'action' ? i.status === 'ACTION_REQUIRED' || i.status === 'IN_REVIEW' : tab === 'referred' ? i.status === 'REFERRED' : i.status === 'NOT_STARTED');
    if (sort.k === 'priority') return r;
    const val = (i: RenewalQueueItem): number | string => ({ name: i.name, expiry: i.days_to_expiry, notice: i.days_to_notice ?? 9999, impact: i.impact_usd, score: i.integrity_score, rarc: i.rarc ?? 9, priority: 0 })[sort.k];
    return [...r].sort((a, b) => (val(a) < val(b) ? -1 : val(a) > val(b) ? 1 : 0) * sort.dir);
  }, [rest, tab, sort]);

  useEffect(() => { setCursor(0); }, [tab, uw, mine, q, family, broker]);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);
  useHotkeys({
    j: () => setCursor((c) => Math.min(rows.length - 1, c + 1)),
    k: () => setCursor((c) => Math.max(0, c - 1)),
    Enter: () => rows[cursor] && nav(`/accounts/${rows[cursor].account_id}`),
    '/': () => document.getElementById('queue-search')?.focus(),
  }, [rows, cursor]);
  useEffect(() => { rowRefs.current[cursor]?.scrollIntoView({ block: 'nearest' }); }, [cursor]);

  const th = (k: SortKey, label: string, r = false) => (
    <th className={cx(r && 'r', 'cursor-pointer select-none hover:text-ink-800')} onClick={() => setSort((s) => (s.k === k ? { k, dir: s.dir === 1 ? -1 : 1 } : { k, dir: k === 'impact' ? -1 : 1 }))}>
      <span className="inline-flex items-center gap-0.5">{label}<ChevronsUpDown className={cx('size-3', sort.k === k ? 'text-ink-800' : 'text-ink-300')} /></span>
    </th>
  );
  const totalAtStake = rows.reduce((a, i) => a + i.impact_usd, 0);

  return (
    <Page title="Renewal queue" actions={<Info id="renewals.page" label="About this page" />} subtitle={<>Ranked by $ at stake × days to notice deadline · <span className="num">{usd(totalAtStake)}</span> at stake in view · <kbd className="mono rounded border border-line bg-surface px-1 text-[10px]">j</kbd>/<kbd className="mono rounded border border-line bg-surface px-1 text-[10px]">k</kbd> to move, <kbd className="mono rounded border border-line bg-surface px-1 text-[10px]">↵</kbd> to open</>}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-400" />
          <Input id="queue-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Account, broker, state…" className="w-[240px] pl-8" />
        </div>
        <Select value={uw} onChange={(e) => setParam('uw', e.target.value || null)}>
          <option value="">All underwriters</option>
          {users?.filter((u) => u.role === 'UNDERWRITER').map((u) => <option key={u.user_id} value={u.user_id}>{u.name} · L{u.authority_level}</option>)}
        </Select>
        <label className="flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-line-strong bg-surface px-2.5 text-[12px] text-ink-700">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} className="accent-[var(--color-accent-600)]" /> Only mine
        </label>
        {family && <Badge tone="accent" className="h-7 px-2">Family: {FAMILY_LABEL[family] ?? family}<button onClick={() => setParam('family', null)}><X className="size-3" /></button></Badge>}
        {broker && <Badge tone="accent" className="h-7 px-2">Broker: {broker}<button onClick={() => setParam('broker', null)}><X className="size-3" /></button></Badge>}
      </div>

      <Tabs className="mb-0" value={tab} onChange={(t) => { setTab(t); if (t === 'fast') setLane(true); }}
        tabs={[{ key: 'all', label: 'All', count: counts.all }, { key: 'action', label: 'Action required', count: counts.action }, { key: 'fast', label: 'Fast-track', count: counts.fast }, { key: 'referred', label: 'Referred', count: counts.referred }, { key: 'not_started', label: 'Not started', count: counts.not_started }]} />

      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
        <>
          {tab !== 'fast' && (
            <Card pad={false} className="mt-3 overflow-hidden">
              <div className="max-h-[calc(100vh-290px)] overflow-auto">
                <table className="dt min-w-[1380px]">
                  <thead>
                    <tr>
                      {th('name', 'Account')}{th('expiry', 'Expiry')}{th('notice', 'Notice')}<th>Pass</th><th>Status</th><th>Recommended</th>{th('impact', '$ at stake', true)}{th('score', 'Integrity')}<th>Top findings</th><th className="r">Gaps</th>{th('rarc', 'RARC / adequacy', true)}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((i, idx) => (
                      <tr key={i.account_id} ref={(el) => { rowRefs.current[idx] = el; }} onClick={() => nav(`/accounts/${i.account_id}`)} onMouseEnter={() => setCursor(idx)}
                        className={cx('cursor-pointer', idx === cursor && 'is-selected')}>
                        <td className="max-w-[240px]">
                          <div className="flex items-center gap-1.5"><ScenarioChip s={i.scenario} /><span className="truncate font-medium text-ink-950">{i.name}</span></div>
                          <div className="truncate text-[11px] text-ink-500">{i.segment} · {i.occupancy_family} · {i.state} · {i.broker} · {i.underwriter}</div>
                        </td>
                        <td className="whitespace-nowrap"><div className="num text-ink-900">{fmtDate(i.expiry)}</div><div className="num text-[11px] text-ink-500">T-{i.days_to_expiry}</div></td>
                        <td><NoticeCountdown days={i.days_to_notice} date={i.notice_deadline} /></td>
                        <td><PassDots pass={i.pass} /></td>
                        <td><StatusBadge s={i.status} /></td>
                        <td className="max-w-[200px]"><ActionChips actions={i.recommended_actions} max={2} /></td>
                        <td className="num r whitespace-nowrap font-semibold text-ink-950">{i.impact_usd ? usd(i.impact_usd) : <span className="font-normal text-ink-400">—</span>}</td>
                        <td><ScoreRing score={i.integrity_score} size={30} /></td>
                        <td className="max-w-[300px]">
                          {i.top_findings.length === 0 ? <span className="text-ink-400">{i.pass === 0 ? 'Pass 1 not yet run' : 'None material'}</span> :
                            i.top_findings.slice(0, 2).map((f) => <div key={f.finding_id} className="flex items-center gap-1.5 truncate text-[12px] text-ink-700"><SeverityDot s={f.severity} /><span className="truncate">{f.title}</span></div>)}
                          {i.finding_count > 2 && <div className="text-[11px] text-ink-400">+{i.finding_count - 2} more</div>}
                        </td>
                        <td className={cx('num r', i.data_gaps > 2 ? 'text-high' : 'text-ink-600')}>{i.data_gaps || '—'}</td>
                        <td className="num r whitespace-nowrap">
                          <div className={cx('font-medium', i.rarc === null ? 'text-ink-400' : i.rarc < -0.05 ? 'text-crit' : i.rarc < 0 ? 'text-high' : 'text-ok')}>{pct(i.rarc, 1, true)}</div>
                          <div className={cx('text-[11px]', i.adequacy !== null && i.adequacy < 0.95 ? 'text-crit' : 'text-ink-500')}>{pct(i.adequacy)}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {rows.length === 0 && <Empty>No renewals match these filters.</Empty>}
              </div>
            </Card>
          )}
          <FastTrackLane items={fast} open={lane || tab === 'fast'} onToggle={() => setLane((o) => !o)} />
        </>
      )}
    </Page>
  );
}

function FastTrackLane({ items, open, onToggle }: { items: RenewalQueueItem[]; open: boolean; onToggle: () => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [done, setDone] = useState<string | null>(null);
  const confirm = useMutation({
    mutationFn: async (ids: string[]) => { for (const id of ids) await api(`/accounts/${id}/confirm`, { method: 'POST', json: { action: 'MAINTAIN' } }); return ids.length; },
    onSuccess: (n) => { setSel(new Set()); setDone(`${n} renewal${n > 1 ? 's' : ''} confirmed — quotes on expiring terms sent to brokers`); setTimeout(() => setDone(null), 4000); qc.invalidateQueries(); },
  });
  const all = items.length > 0 && sel.size === items.length;
  const premium = items.reduce((a, i) => a + i.premium_expiring, 0);
  return (
    <Card className="mt-4" pad={false}>
      <div className="flex items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-1.5">
        <button onClick={onToggle} className="flex items-center gap-2 text-left">
          {open ? <ChevronDown className="size-4 text-ink-500" /> : <ChevronRight className="size-4 text-ink-500" />}
          <Zap className="size-4 text-ok" />
          <span className="text-[13px] font-semibold text-ink-900">Fast-track lane</span>
          <span className="text-[12px] text-ink-500"><span className="num">{items.length}</span> renewals · <span className="num">{usd(premium)}</span> premium · no material findings, adequacy ≥ floor, recommendations verified</span>
        </button>
        <Info id="renewals.fasttrack" />
        </div>
        <div className="flex items-center gap-2">
          {done && <span className="anim-fade text-[12px] text-ok">{done}</span>}
          {confirm.error && <span className="text-[12px] text-crit">{(confirm.error as Error).message}</span>}
          <Button size="sm" variant="primary" disabled={!sel.size} loading={confirm.isPending} onClick={() => confirm.mutate([...sel])}>Confirm maintain{sel.size ? ` (${sel.size})` : ''}</Button>
        </div>
      </div>
      {open && (
        <div className="max-h-[420px] overflow-auto border-t border-line">
          <table className="dt">
            <thead><tr>
              <th className="w-8"><input type="checkbox" checked={all} onChange={() => setSel(all ? new Set() : new Set(items.map((i) => i.account_id)))} className="accent-[var(--color-accent-600)]" /></th>
              <th>Account</th><th>Expiry</th><th>Underwriter</th><th className="r">TIV change</th><th className="r">Premium</th><th className="r">RARC</th><th className="r">Adequacy</th><th>Integrity</th><th />
            </tr></thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.account_id} className={cx(sel.has(i.account_id) && 'is-selected')}>
                  <td><input type="checkbox" checked={sel.has(i.account_id)} onChange={() => setSel((s) => { const n = new Set(s); if (n.has(i.account_id)) n.delete(i.account_id); else n.add(i.account_id); return n; })} className="accent-[var(--color-accent-600)]" /></td>
                  <td className="cursor-pointer" onClick={() => nav(`/accounts/${i.account_id}`)}><div className="flex items-center gap-1.5"><ScenarioChip s={i.scenario} /><span className="font-medium text-ink-900 hover:text-accent-700">{i.name}</span></div><div className="text-[11px] text-ink-500">{i.occupancy_family} · {i.state} · {i.broker}</div></td>
                  <td className="num whitespace-nowrap">{fmtDate(i.expiry)} <span className="text-[11px] text-ink-500">T-{i.days_to_expiry}</span></td>
                  <td className="text-ink-700">{i.underwriter}</td>
                  <td className="num r">{pct(i.tiv_current / i.tiv_expiring - 1, 1, true)}</td>
                  <td className="num r">{usd(i.premium_expiring)}</td>
                  <td className="num r text-ok">{pct(i.rarc, 1, true)}</td>
                  <td className="num r">{pct(i.adequacy)}</td>
                  <td><ScoreRing score={i.integrity_score} size={26} /></td>
                  <td className="r"><Button size="sm" onClick={() => confirm.mutate([i.account_id])} disabled={confirm.isPending}>Confirm</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && <Empty>No fast-track renewals in this view.</Empty>}
        </div>
      )}
    </Card>
  );
}
