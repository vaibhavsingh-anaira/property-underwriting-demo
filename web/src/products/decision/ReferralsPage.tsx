// Referral queue (tier-3 human decisions) and the log of every assurance run.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Page, Card, Tabs, Loading, ErrorBox, Empty, Badge } from '@/components/ui';
import { usd, pct, fmtDate } from '@/lib/format';
import { Info } from '@/help/Info';
import { useAssuranceLog, useDaReferrals } from './api';
import { ReferralCard } from './DecisionTab';
import { VerdictBadge } from './parts';

export default function ReferralsPage() {
  const { data, isLoading, error } = useDaReferrals();
  const log = useAssuranceLog();
  const [tab, setTab] = useState<'pending' | 'decided' | 'log'>('pending');
  const rows = (data ?? []).filter((r) => (tab === 'pending' ? r.status === 'PENDING' : r.status !== 'PENDING'));
  return (
    <Page title="Referrals & assurance runs" subtitle="Referrals wait for an approver with the required level · approvals are envelopes on the action" actions={<Info id="decision.referrals" label="About this page" />}>
      <Tabs value={tab} onChange={setTab} tabs={[{ key: 'pending', label: 'Pending', count: (data ?? []).filter((r) => r.status === 'PENDING').length }, { key: 'decided', label: 'Decided', count: (data ?? []).filter((r) => r.status !== 'PENDING').length }, { key: 'log', label: 'Assurance log', count: log.data?.length }]} />
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : tab !== 'log' ? (
        <Card pad={false} className="mt-3">{rows.length === 0 ? <Empty>No referrals here.</Empty> : <div className="divide-y divide-line">{rows.map((r) => <ReferralCard key={r.referral_id} r={r} showCase />)}</div>}</Card>
      ) : (
        <Card pad={false} className="mt-3">
          <div className="max-h-[calc(100vh-240px)] overflow-auto">
            <table className="dt">
              <thead><tr><th>Date</th><th>Case</th><th>Underwriter</th><th>Action</th><th className="r">Premium</th><th className="r">vs technical</th><th className="r">Fail</th><th className="r">Flags</th><th>Verdict</th></tr></thead>
              <tbody>{(log.data ?? []).map((x) => (
                <tr key={x.assurance_id}><td className="num">{fmtDate(x.at)}</td><td><Link to={`/decision/cases/${x.case_id}`} className="text-ink-900 hover:text-accent-700">{x.scenario && <Badge tone="dark" className="mr-1">{x.scenario}</Badge>}{x.insured}</Link></td><td>{x.underwriter}</td><td><Badge>{x.action_type}</Badge></td>
                  <td className="num r">{usd(x.premium)}</td><td className="num r">{pct(x.deviation, 1, true)}</td><td className="num r">{x.fails || ''}</td><td className="num r">{x.flags || ''}</td><td><VerdictBadge v={x.verdict} /></td></tr>
              ))}</tbody>
            </table>
          </div>
        </Card>
      )}
    </Page>
  );
}
