// Delegated authority rules (YAML + CEL). Editing, tests, backtest and publish use the shared rule studio.
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Rule } from '@/api/types';
import { Page, Card, Loading, ErrorBox, Badge, SeverityPill } from '@/components/ui';
import { Info } from '@/help/Info';
import { FAMILY_LABEL } from '../api';

export default function Rules() {
  const { data, isLoading, error } = useQuery({ queryKey: ['rules', 'delegated'], queryFn: () => api<Rule[]>('/rules?product=delegated') });
  const groups = [...new Set((data ?? []).map((r) => r.applies_to))];
  return (
    <Page title="Rule studio · delegated authority" actions={<Info id="delegated.rules" label="About this page" />}
      subtitle="Authority checks as versioned YAML rules with CEL conditions and tests · open a rule to edit, test, backtest on every bordereau line and publish">
      {isLoading ? <Loading /> : error || !data ? <ErrorBox error={error} /> : groups.map((g) => (
        <Card key={g} className="mb-4" pad={false} title={`Applies to: ${g}`} subtitle={`${data.filter((r) => r.applies_to === g).length} rules`}>
          <table className="dt">
            <thead><tr><th>Rule</th><th>Family</th><th>Outcome</th><th>Severity</th><th>When</th><th className="r">Tests</th><th className="r">Fired</th></tr></thead>
            <tbody>{data.filter((r) => r.applies_to === g).map((r) => (
              <tr key={r.rule_id}>
                <td><Link to={`/delegated/rules/${r.rule_id}`} className="font-medium text-ink-900 hover:text-accent-700">{r.title}</Link><div className="mono text-[11px] text-ink-500">{r.rule_id} · v{r.version}</div></td>
                <td className="text-[12px]">{FAMILY_LABEL[r.family] ?? r.family}</td>
                <td><Badge tone={String(r.outcome) === 'BREACH' ? 'crit' : String(r.outcome) === 'REFER' ? 'high' : 'med'}>{r.outcome}</Badge></td>
                <td><SeverityPill s={r.severity} /></td>
                <td className="mono max-w-[380px] truncate text-[11px] text-ink-600" title={r.when}>{r.when}</td>
                <td className="num r">{r.tests.length}</td><td className="num r font-semibold">{r.stats.fired}</td>
              </tr>))}</tbody>
          </table>
        </Card>
      ))}
    </Page>
  );
}
