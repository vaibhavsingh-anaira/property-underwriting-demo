import { Link, useNavigate, useParams } from 'react-router-dom';
import { ChevronRight, AlertTriangle, Clock } from 'lucide-react';
import { useAccount } from '@/api/client';
import type { AccountDetail } from '@/api/types';
import { Tabs, Loading, ErrorBox, ScoreRing, Badge, cx } from '@/components/ui';
import { fmtDate, pct, usd } from '@/lib/format';
import { ActionChips, NoticeCountdown, PassStepper, ScenarioChip, StatusBadge } from '../common';
import OverviewTab from './OverviewTab';
import LocationsTab from './LocationsTab';
import PricingTab from './PricingTab';
import ContractTab from './ContractTab';
import CatTab from './CatTab';
import ClaimsTab from './ClaimsTab';
import DocumentsTab from './DocumentsTab';
import TimelineTab from './TimelineTab';
import { Info } from '@/help/Info';

const TABS = ['overview', 'locations', 'pricing', 'contract', 'cat', 'claims', 'documents', 'timeline'] as const;
type TabKey = (typeof TABS)[number];
const LABEL: Record<TabKey, string> = { overview: 'Overview', locations: 'Locations', pricing: 'Pricing · RARC', contract: 'Contract', cat: 'CAT', claims: 'Claims & engineering', documents: 'Documents', timeline: 'Timeline / audit' };

export default function AccountPage() {
  const { id, tab: tabParam } = useParams();
  const nav = useNavigate();
  const tab: TabKey = (TABS as readonly string[]).includes(tabParam ?? '') ? (tabParam as TabKey) : 'overview';
  const { data: a, isLoading, error } = useAccount(id);
  if (isLoading) return <Loading label="Loading integrity record…" />;
  if (error || !a) return <div className="p-6"><ErrorBox error={error ?? 'Account not found'} /></div>;
  const openCount = a.findings.filter((f) => f.status === 'OPEN').length;
  return (
    <div className="min-h-full">
      <Header a={a} />
      <div className="sticky top-0 z-10 border-b border-line bg-surface/95 px-6 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center gap-4">
          <div className="flex shrink-0 items-center gap-2 border-r border-line py-1.5 pr-4">
            <ScoreRing score={a.renewal.integrity_score} size={26} />
            <div className="leading-tight">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-ink-950"><ScenarioChip s={a.scenario} />{a.name}</div>
              <div className="num text-[10.5px] text-ink-500">T-{a.renewal.days_to_expiry} · {a.policy.policy_no}{a.renewal.notice.days_remaining !== null && <> · notice {a.renewal.notice.days_remaining}d</>}</div>
            </div>
          </div>
          <Tabs className="border-b-0" value={tab} onChange={(k) => nav(`/accounts/${a.account_id}/${k === 'overview' ? '' : k}`)}
            tabs={TABS.map((k) => ({ key: k, label: LABEL[k], count: k === 'overview' ? openCount : k === 'locations' ? a.locations.length : k === 'documents' ? a.documents.length : undefined }))} />
        </div>
      </div>
      <div className="mx-auto w-full max-w-[1600px] px-6 py-5">
        {tab === 'overview' && <OverviewTab a={a} />}
        {tab === 'locations' && <LocationsTab a={a} />}
        {tab === 'pricing' && <PricingTab a={a} />}
        {tab === 'contract' && <ContractTab a={a} />}
        {tab === 'cat' && <CatTab a={a} />}
        {tab === 'claims' && <ClaimsTab a={a} />}
        {tab === 'documents' && <DocumentsTab a={a} />}
        {tab === 'timeline' && <TimelineTab a={a} />}
      </div>
    </div>
  );
}

function Header({ a }: { a: AccountDetail }) {
  const r = a.renewal, p = a.policy;
  return (
    <div className="border-b border-line bg-surface px-6 pb-4 pt-4">
      <div className="mx-auto max-w-[1600px]">
        <div className="mb-1 flex items-center gap-1 text-[12px] text-ink-500">
          <Link to="/renewals" className="hover:text-ink-800">Renewals</Link><ChevronRight className="size-3" /><span className="text-ink-700">{a.name}</span>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <h1 className="text-[22px] font-semibold tracking-[-0.015em] text-ink-950">{a.name}</h1>
              <StatusBadge s={r.status} />
              {a.scenario && <span className="flex items-center gap-1.5"><ScenarioChip s={a.scenario} /><span className="text-[12px] text-ink-600">{a.scenario_title}</span></span>}
              <Info id="account.page" label="About this page" />
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[12px] text-ink-600">
              <span className="mono text-ink-800">{p.policy_no}</span>
              <span className="num">{fmtDate(p.term_start)} – {fmtDate(p.term_end)}</span>
              <span>{p.layer}{p.carrier_share < 1 && <> · <span className="font-medium text-ink-900">{pct(p.carrier_share, 0)} share</span></>}</span>
              <span>{p.admitted ? 'Admitted' : 'E&S'} · {a.state}</span>
              <span>{a.segment} · {a.occupancy_family}</span>
              <span>Broker <span className="text-ink-900">{a.broker}</span> <span className="text-ink-400">({a.broker_contact})</span></span>
              <span>UW <span className="text-ink-900">{a.underwriter}</span></span>
              <span>Expiring <span className="num text-ink-900">{usd(p.premium)}</span></span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-5">
              <span className="inline-flex items-center gap-1.5"><PassStepper pass={r.pass} /><Info id="account.passes" /></span>
              <div className="h-5 w-px bg-line" />
              <span className="text-[12px] text-ink-500">Recommended</span><ActionChips actions={r.recommended_actions} />
            </div>
          </div>
          <div className="flex shrink-0 items-stretch gap-3">
            <HeaderBox label="Expiry">
              <div className="num text-[15px] font-semibold text-ink-950">T-{r.days_to_expiry}</div>
              <div className="num text-[11px] text-ink-500">{fmtDate(r.expiry)}</div>
            </HeaderBox>
            <HeaderBox label={<span className="inline-flex items-center gap-1.5">Notice deadline<Info id="account.notice" className="normal-case" /></span>}>
              {r.notice.required ? <><div className="flex items-center gap-1.5"><NoticeCountdown days={r.notice.days_remaining} /><span className="num text-[12px] text-ink-700">{fmtDate(r.notice.latest_notice_date)}</span></div><div className="mt-0.5 max-w-[170px] truncate text-[10.5px] text-ink-400" title={r.notice.rule_ref}>{r.notice.state} · {r.notice.days_required}d · {r.notice.rule_ref}</div></>
                : <div className="max-w-[170px] text-[11px] leading-tight text-ink-500">{r.notice.rule_ref}</div>}
            </HeaderBox>
            <HeaderBox label="Owner · due">
              <div className="text-[13px] font-medium text-ink-900">{r.owner}</div>
              <div className="flex items-center gap-1 text-[11px] text-ink-500"><Clock className="size-3" /><span className="num">{fmtDate(r.due)}</span> · {r.confidence.toLowerCase()} confidence</div>
            </HeaderBox>
            <div className="flex items-center gap-2 rounded-lg border border-line px-3">
              <ScoreRing score={r.integrity_score} size={48} />
              <div className="text-[11px] leading-tight text-ink-500">Integrity<br />score</div>
              <Info id="account.integrity" />
            </div>
          </div>
        </div>
        {r.missing.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[12px]">
            <span className={cx('flex items-center gap-1 font-medium text-high')}><AlertTriangle className="size-3.5" />Missing:</span>
            {r.missing.map((m) => <Badge key={m} tone="high">{m}</Badge>)}
          </div>
        )}
      </div>
    </div>
  );
}

function HeaderBox({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2">
      <div className="mb-0.5 text-[10.5px] font-medium uppercase tracking-[.05em] text-ink-500">{label}</div>
      {children}
    </div>
  );
}
