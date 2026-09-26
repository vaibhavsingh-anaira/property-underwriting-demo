// Renders one pipeline stage's system (real or mock) with the account's data and its runnable step.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Circle, CircleDot, FileText, MinusCircle, Play, Loader2, ExternalLink } from 'lucide-react';
import type { StageStatus, StageTable, StageView } from '@/api/types';
import { usePresenterEvent, useRunStage } from '@/api/client';
import { Info } from '@/help/Info';
import { Badge, Card, MockBadge, SeverityPill, Empty, cx } from '@/components/ui';
import { useEvidence } from '@/components/evidence';
import { fmtDate, pct, usd } from '@/lib/format';

export const STATUS_META: Record<StageStatus, { label: string; tone: 'ok' | 'accent' | 'neutral' | 'low'; icon: typeof Circle }> = {
  DONE: { label: 'Done', tone: 'ok', icon: CheckCircle2 },
  READY: { label: 'Ready to run', tone: 'accent', icon: CircleDot },
  PENDING: { label: 'Waiting on earlier step', tone: 'neutral', icon: Circle },
  NOT_APPLICABLE: { label: 'Not applicable', tone: 'low', icon: MinusCircle },
};

export function ModeBadge({ mode }: { mode: StageView['mode'] }) {
  return mode === 'MOCK' ? <MockBadge /> : <Badge tone={mode === 'REAL' ? 'ok' : 'info'}>{mode}</Badge>;
}

export interface ActionOverride { label: string; description: string; onRun: () => void; running: boolean; done: boolean; kind: 'action' | 'view' }

export function StageWorkspace({ v, onRan, action }: { v: StageView; onRan?: (msg: string) => void; action?: ActionOverride | null }) {
  const run = useRunStage();
  const ev = useEvidence();
  const [msg, setMsg] = useState<{ tone: 'ok' | 'crit'; text: string } | null>(null);
  const st = STATUS_META[v.status];
  const doRun = () => run.mutate({ code: v.code, account_id: v.account.account_id, product: v.product }, {
    onSuccess: (r) => { setMsg({ tone: 'ok', text: r.message }); onRan?.(r.message); },
    onError: (e) => setMsg({ tone: 'crit', text: (e as Error).message }),
  });
  return (
    <div className="space-y-4" data-stage={v.code}>
      {/* system header */}
      <div data-demo="system" className="rounded-[var(--radius-card)] border border-line bg-surface p-4 shadow-[var(--shadow-card)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className={cx('mono flex size-10 items-center justify-center rounded-lg text-[14px] font-semibold', v.mode === 'REAL' ? 'bg-accent-600 text-white' : 'bg-ink-900 text-white')}>{v.code}</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[17px] font-semibold text-ink-950">{v.name}</span>
                <ModeBadge mode={v.mode} />
                <Info id="stage.page" />
                <Badge tone={st.tone}><st.icon className="size-3" />{st.label}</Badge>
              </div>
              <div className="mt-0.5 text-[12.5px] text-ink-600">
                <span className="font-medium text-ink-800">{v.component}</span>
                {v.port && <span className="mono ml-1.5 text-[11px] text-ink-400">{v.port}</span>}
                <span className="text-ink-400"> · stands in for </span>{v.stands_in_for}
              </div>
              <div className="mt-1 max-w-[760px] text-[12px] text-ink-500">{v.description}</div>
            </div>
          </div>
          <div className="text-right text-[12px] text-ink-500">
            <div>{v.account.href && !v.account.href.startsWith('/accounts') ? 'Subject' : 'Account'} <Link to={v.account.href ?? `/accounts/${v.account.account_id}`} className="font-medium text-accent-700 hover:underline">{v.account.name}</Link>{v.account.scenario && <Badge tone="dark" className="ml-1">{v.account.scenario}</Badge>}</div>
            <div className="mt-0.5">Demo clock <span className="num font-medium text-ink-800">{fmtDate(v.clock)}</span></div>
          </div>
        </div>
        <div data-demo="headline" className="mt-3 rounded-md bg-ink-50 px-3 py-2 text-[13px] font-medium text-ink-900">{v.headline}</div>
        {v.kpis.length > 0 && (
          <div data-demo="kpis" className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
            {v.kpis.map((k) => (
              <div key={k.label} className="rounded-md border border-line px-3 py-2">
                <div className="text-[10.5px] font-medium uppercase tracking-wide text-ink-500">{k.label}</div>
                <div className={cx('num mt-0.5 truncate text-[15px] font-semibold', k.tone === 'crit' ? 'text-crit' : k.tone === 'high' ? 'text-high' : k.tone === 'ok' ? 'text-ok' : 'text-ink-950')}>{k.value}</div>
              </div>
            ))}
          </div>
        )}
        {action && (
          <div className={cx('mt-3 flex items-center gap-3 rounded-md border px-3 py-2.5', action.done ? 'border-[#bfe3cd] bg-ok-bg' : 'border-accent-100 bg-accent-50')}>
            <div className="flex-1">
              <div className={cx('text-[13px] font-semibold', action.done ? 'text-ok' : 'text-accent-700')}>{action.done ? 'Done: ' : 'Playbook step: '}{action.label}</div>
              <div className="text-[12px] text-ink-600">{action.description}</div>
            </div>
            {action.kind === 'action' && !action.done && (
              <button data-demo="pb-action" onClick={action.onRun} disabled={action.running} className="flex h-8 items-center gap-1.5 rounded-md bg-accent-600 px-3 text-[13px] font-semibold text-white hover:bg-accent-700 disabled:opacity-60">
                {action.running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} Run step
              </button>
            )}
          </div>
        )}
        {!action && v.next_action && (
          <div className="mt-3 flex items-center gap-3 rounded-md border border-accent-100 bg-accent-50 px-3 py-2.5">
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-accent-700">Next step: {v.next_action.label}</div>
              <div className="text-[12px] text-ink-600">{v.next_action.description}</div>
            </div>
            <button onClick={doRun} disabled={run.isPending} className="flex h-8 items-center gap-1.5 rounded-md bg-accent-600 px-3 text-[13px] font-semibold text-white hover:bg-accent-700 disabled:opacity-60">
              {run.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} Run step
            </button>
          </div>
        )}
        {!action && v.code === '12' && (v.product ?? 'renewal') === 'renewal' && <LiveEvents acct={v.account.account_id} onMsg={setMsg} />}
        {msg && <div className={cx('anim-fade mt-2 rounded-md px-3 py-1.5 text-[12.5px]', msg.tone === 'ok' ? 'bg-ok-bg text-ok' : 'bg-crit-bg text-crit')}>{msg.text}</div>}
      </div>

      {v.tables.map((t, i) => <div key={t.title} data-demo={`table-${i}`}><DataTable t={t} /></div>)}

      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-6" pad={false} title="Findings raised at this stage" subtitle="Click to open the evidence" id="demo-findings">
          {v.findings.length === 0 ? <Empty>None open.</Empty> : (
            <div className="divide-y divide-line">
              {v.findings.map((f) => (
                <button key={f.finding_id} onClick={() => ev.openFinding(f)} className="flex w-full items-start gap-2 px-4 py-2 text-left hover:bg-ink-50">
                  <SeverityPill s={f.severity} />
                  <span className="min-w-0 flex-1"><span className="block text-[13px] font-medium text-ink-900">{f.title}</span><span className="block truncate text-[12px] text-ink-500">{f.subject_label} — {f.observed}</span></span>
                  <span className="num text-[12px] font-semibold text-ink-800">{f.impact_usd ? usd(f.impact_usd) : ''}</span>
                </button>
              ))}
            </div>
          )}
        </Card>
        <Card className="col-span-12 xl:col-span-6" pad={false} title="Documents in this system" subtitle="Open in the viewer">
          {v.documents.length === 0 ? <Empty>No documents at this stage.</Empty> : (
            <div className="max-h-[320px] divide-y divide-line overflow-y-auto">
              {v.documents.map((d) => (
                <button key={d.doc_id} onClick={() => ev.openDoc(d.doc_id)} className="flex w-full items-center gap-2 px-4 py-2 text-left hover:bg-ink-50">
                  <FileText className="size-3.5 shrink-0 text-ink-400" />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-ink-900">{d.title}</span>
                  <Badge>{d.format}</Badge>
                  <span className="num text-[11.5px] text-ink-500">{fmtDate(d.received_at)}</span>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card pad={false} title="Activity at this stage" subtitle="From the account's audit trail">
        {v.events.length === 0 ? <Empty>No activity recorded yet.</Empty> : (
          <div className="divide-y divide-line">
            {v.events.slice(0, 15).map((e) => (
              <div key={e.event_id} className="flex items-start gap-3 px-4 py-2">
                <span className="num w-[86px] shrink-0 text-[12px] text-ink-500">{fmtDate(e.date)}</span>
                <span className="min-w-0 flex-1"><span className="block text-[13px] text-ink-900">{e.title}</span><span className="block truncate text-[12px] text-ink-500">{e.detail}</span></span>
                <span className="text-[11.5px] text-ink-500">{e.actor}</span>
                {e.doc_id && <button onClick={() => ev.openDoc(e.doc_id!)} className="text-ink-400 hover:text-accent-700"><ExternalLink className="size-3.5" /></button>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function DataTable({ t }: { t: StageTable }) {
  const ev = useEvidence();
  const cell = (kind: string, val: unknown) => {
    if (val === null || val === undefined || val === '') return <span className="text-ink-400">—</span>;
    switch (kind) {
      case 'money': return <span className="num">{usd(val as number)}</span>;
      case 'pct': return <span className="num">{pct(val as number)}</span>;
      case 'date': return <span className="num whitespace-nowrap">{fmtDate(String(val))}</span>;
      case 'mono': return <span className="mono text-[11.5px]">{String(val)}</span>;
      case 'doc': return <button onClick={() => ev.openDoc(String(val))} className="inline-flex items-center gap-1 text-accent-700 hover:underline"><FileText className="size-3.5" />Open</button>;
      case 'badge': {
        const s = String(val);
        const tone = /PASS|DONE|APPROVED|ACCEPTED|BOUND|VERIFIED|MATCHED|CURRENT/.test(s) ? 'ok' : /FAIL|CRIT|DECLINE|INVALID|DELETED|REFER|OPEN/.test(s) ? 'crit' : /HIGH|FLAG|PENDING|AMBIG|SENT|TERM|DRAFT|NEW/.test(s) ? 'high' : 'neutral';
        return <Badge tone={tone as 'ok' | 'crit' | 'high' | 'neutral'}>{s}</Badge>;
      }
      default: return <span>{String(val)}</span>;
    }
  };
  return (
    <Card pad={false} title={t.title} subtitle={`${t.rows.length} record${t.rows.length === 1 ? '' : 's'}`}>
      {t.rows.length === 0 ? <Empty>No records yet.</Empty> : (
        <div className="max-h-[420px] overflow-auto">
          <table className="dt">
            <thead><tr>{t.columns.map((c) => <th key={c.key} className={cx((c.kind === 'money' || c.kind === 'pct') && 'r')}>{c.label}</th>)}</tr></thead>
            <tbody>
              {t.rows.map((r, i) => (
                <tr key={i}>{t.columns.map((c) => <td key={c.key} className={cx('text-[12.5px]', (c.kind === 'money' || c.kind === 'pct') && 'r')}>{cell(c.kind, r[c.key])}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// Presenter-triggered in-force events: raise a claim, impairment or vacancy live and watch the re-evaluation.
function LiveEvents({ acct, onMsg }: { acct: string; onMsg: (m: { tone: 'ok' | 'crit'; text: string }) => void }) {
  const ev = usePresenterEvent();
  const fire = (kind: 'claim' | 'impairment' | 'vacancy', params?: Record<string, unknown>) =>
    ev.mutate({ account_id: acct, kind, params }, { onSuccess: (r) => onMsg({ tone: 'ok', text: r.message }), onError: (e) => onMsg({ tone: 'crit', text: (e as Error).message }) });
  const B = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) => (
    <button onClick={onClick} disabled={ev.isPending} className="h-7 rounded-md border border-line-strong bg-surface px-2.5 text-[12px] font-medium text-ink-800 hover:border-accent-500 disabled:opacity-50">{children}</button>
  );
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-dashed border-line-strong px-3 py-2.5">
      <span className="text-[12px] font-medium text-ink-700">Raise a live event (mock PAS / claims):</span>
      <B onClick={() => fire('claim', { amount: 750000, cause: 'fire' })}>$750k fire claim</B>
      <B onClick={() => fire('claim', { amount: 120000, cause: 'water_damage' })}>$120k water claim</B>
      <B onClick={() => fire('impairment')}>Sprinkler impairment</B>
      <B onClick={() => fire('vacancy', { vacancy_pct: 0.6 })}>60% vacancy</B>
      <span className="text-[11.5px] text-ink-500">The engine re-evaluates the account immediately; see the findings below.</span>
    </div>
  );
}
