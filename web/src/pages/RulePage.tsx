import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronRight, Play, FlaskConical, Upload, CheckCircle2, XCircle, RotateCcw, BookOpen } from 'lucide-react';
import { useRule, useRuleBacktest, useRulePublish, useRuleTest } from '@/api/client';
import type { Rule } from '@/api/types';
import { Page, Card, Badge, Button, Loading, ErrorBox, SeverityPill, KV, cx } from '@/components/ui';
import { fmtDate, pct } from '@/lib/format';
import { SectionLabel } from './common';
import { Info } from '@/help/Info';
import { useProduct } from '@/products';

export default function RulePage() {
  const { id } = useParams();
  const { data: r, isLoading, error } = useRule(id);
  if (isLoading) return <Page title="Rule"><Loading /></Page>;
  if (error || !r) return <Page title="Rule"><ErrorBox error={error} /></Page>;
  return <Editor key={`${r.rule_id}@${r.version}`} r={r} />;
}

function Editor({ r }: { r: Rule }) {
  const prod = useProduct();
  const [yaml, setYaml] = useState(r.yaml);
  const test = useRuleTest(r.rule_id), back = useRuleBacktest(r.rule_id), pub = useRulePublish(r.rule_id);
  const [published, setPublished] = useState<string | null>(null);
  const dirty = yaml !== r.yaml;
  useEffect(() => { test.mutate(r.yaml); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const passing = test.data?.every((t) => t.pass);
  return (
    <Page crumbs={<span className="flex items-center gap-1"><Link to={prod.to('/rules')} className="hover:text-ink-800">Rule studio</Link><ChevronRight className="size-3" /><span className="mono">{r.rule_id}</span></span>}
      title={<span className="flex items-center gap-2"><span className="mono">{r.rule_id}</span><Badge tone="dark">v{r.version}</Badge><Badge tone={r.origin === 'carrier_guideline' ? 'accent' : 'neutral'}>{r.origin === 'carrier_guideline' ? 'Carrier guideline' : 'Standard library'}</Badge></span>}
      subtitle={r.title}
      actions={<>
        {dirty && <Button variant="ghost" icon={<RotateCcw className="size-3.5" />} onClick={() => setYaml(r.yaml)}>Revert</Button>}
        <Button icon={<Play className="size-3.5" />} loading={test.isPending} onClick={() => test.mutate(yaml)}>Run tests</Button>
        <Button icon={<FlaskConical className="size-3.5" />} loading={back.isPending} onClick={() => back.mutate(yaml)}>Backtest</Button>
        <Button variant="primary" icon={<Upload className="size-3.5" />} disabled={!dirty} loading={pub.isPending}
          onClick={() => pub.mutate(yaml, { onSuccess: (n) => setPublished(`Published v${n.version}, effective ${fmtDate(n.effective_from)}. Historical findings keep rule_id + version.`) })}>Publish v{r.version + 1}</Button>
      </>}>
      {published && <div className="anim-fade mb-3 rounded-md bg-ok-bg px-3 py-2 text-[12.5px] text-ok">{published}</div>}
      {pub.error && <div className="mb-3"><ErrorBox error={pub.error} /></div>}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 space-y-4 xl:col-span-7">
          <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Definition<Info id="rule.editor" /></span>} subtitle="YAML with a CEL `when` expression" actions={dirty ? <Badge tone="med">unsaved changes</Badge> : <Badge>published</Badge>}>
            <YamlEditor value={yaml} onChange={setYaml} />
          </Card>
          <Card title="Source" subtitle="Every rule cites the guideline it enforces">
            <div className="flex items-start gap-2 text-[13px] text-ink-800"><BookOpen className="mt-0.5 size-4 text-accent-600" />{r.source}</div>
            <div className="mt-3 grid grid-cols-2 gap-x-8">
              <KV k="Effective" v={`${fmtDate(r.effective_from)}${r.effective_to ? ` – ${fmtDate(r.effective_to)}` : ' → open'}`} />
              <KV k="Applies to" v={r.applies_to} mono />
              <KV k="Outcome" v={<span className="flex items-center gap-1">{r.outcome}<SeverityPill s={r.severity} /></span>} />
              <KV k="Referral level" v={r.referral_level ? `L${r.referral_level}` : '—'} />
              <KV k="Impact method" v={r.impact_method} mono />
              <KV k="Expected" v={r.expected} />
            </div>
          </Card>
        </div>
        <div className="col-span-12 space-y-4 xl:col-span-5">
          <Card title="Precision from dispositions" subtitle="Rules with > 40% rejection are auto-flagged for review">
            <div className="grid grid-cols-4 gap-2 text-center">
              {[['Fired', r.stats.fired, 'text-ink-950'], ['Accepted', r.stats.accepted, 'text-ok'], ['Rejected', r.stats.rejected, 'text-crit'], ['Precision', pct(r.stats.precision, 0), r.stats.precision !== null && r.stats.precision < 0.6 ? 'text-crit' : 'text-ink-950']].map(([l, v, c]) => (
                <div key={String(l)}><div className="text-[10.5px] uppercase tracking-wide text-ink-500">{l}</div><div className={cx('num text-[20px] font-semibold', String(c))}>{v}</div></div>
              ))}
            </div>
            {r.stats.precision !== null && r.stats.precision < 0.6 && <div className="mt-2 rounded-md bg-crit-bg px-2.5 py-1.5 text-[12px] text-crit">Flagged: underwriters reject {pct(1 - r.stats.precision, 0)} of this rule's findings. Check the most common reason codes and tighten the expression.</div>}
          </Card>
          <Card pad={false} title="Test cases" subtitle="No rule goes live without passing fixtures"
            actions={test.data && <Badge tone={passing ? 'ok' : 'crit'}>{test.data.filter((t) => t.pass).length}/{test.data.length} passing</Badge>}>
            {test.error && <div className="p-3"><ErrorBox error={test.error} /></div>}
            <table className="dt">
              <thead><tr><th /><th>Case</th><th>Expected</th><th>Actual</th></tr></thead>
              <tbody>
                {(test.data ?? []).map((t) => (
                  <tr key={t.name}>
                    <td className="w-6">{t.pass ? <CheckCircle2 className="size-4 text-ok" /> : <XCircle className="size-4 text-crit" />}</td>
                    <td className="mono text-[12px]">{t.name}{t.error && <div className="font-sans text-[11px] text-crit">{t.error}</div>}</td>
                    <td className="mono text-[11.5px]">{t.expected}</td>
                    <td className={cx('mono text-[11.5px]', !t.pass && 'font-semibold text-crit')}>{t.actual}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!test.data && !test.isPending && <div className="p-4 text-[12px] text-ink-500">Run tests to evaluate fixtures.</div>}
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5">Backtest on control set<Info id="rule.backtest" /></span>} subtitle="Findings diff before publishing">
            {back.error && <ErrorBox error={back.error} />}
            {!back.data ? <div className="text-[12px] text-ink-500">{back.isPending ? 'Replaying control set…' : 'Edit the rule and run a backtest to see which findings would appear or disappear.'}</div> : (
              <>
                <div className="text-[12px] text-ink-500">{back.data.control_set} · <span className="num">{back.data.duration_ms} ms</span></div>
                <div className="my-3 flex items-center gap-4">
                  <div><div className="text-[10.5px] uppercase tracking-wide text-ink-500">Before</div><div className="num text-[22px] font-semibold">{back.data.before}</div></div>
                  <span className="text-ink-300">→</span>
                  <div><div className="text-[10.5px] uppercase tracking-wide text-ink-500">After</div><div className="num text-[22px] font-semibold">{back.data.after}</div></div>
                  <Badge tone={back.data.after > back.data.before ? 'high' : back.data.after < back.data.before ? 'ok' : 'neutral'}>{back.data.after - back.data.before >= 0 ? '+' : ''}{back.data.after - back.data.before} findings</Badge>
                  <span className="text-[12px] text-ink-500"><span className="text-ok">+{back.data.added.length}</span> added · <span className="text-crit">−{back.data.removed.length}</span> removed</span>
                </div>
                <Diff title="Added" tone="ok" rows={back.data.added} />
                <Diff title="Removed" tone="crit" rows={back.data.removed} />
              </>
            )}
          </Card>
        </div>
      </div>
    </Page>
  );
}

function Diff({ title, tone, rows }: { title: string; tone: 'ok' | 'crit'; rows: { account_name: string; subject_label: string; observed: string }[] }) {
  if (!rows.length) return null;
  return (
    <div className="mb-2">
      <SectionLabel>{title} ({rows.length})</SectionLabel>
      <div className="max-h-[180px] overflow-y-auto rounded-md border border-line">
        {rows.map((x, i) => (
          <div key={i} className={cx('flex gap-2 border-b border-line px-2 py-1 text-[11.5px] last:border-0', tone === 'ok' ? 'bg-ok-bg/40' : 'bg-crit-bg/40')}>
            <span className={cx('mono font-semibold', tone === 'ok' ? 'text-ok' : 'text-crit')}>{tone === 'ok' ? '+' : '−'}</span>
            <span className="w-[38%] truncate text-ink-800">{x.account_name}</span><span className="w-[24%] truncate text-ink-500">{x.subject_label}</span><span className="mono flex-1 truncate text-[10.5px] text-ink-500">{x.observed}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function YamlEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const lines = value.split('\n').length;
  return (
    <div className="flex max-h-[600px] overflow-auto bg-ink-50/40">
      <div className="mono sticky left-0 select-none border-r border-line bg-ink-50 px-2 py-3 text-right text-[12px] leading-[20px] text-ink-400">
        {Array.from({ length: lines }, (_, i) => <div key={i}>{i + 1}</div>)}
      </div>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} spellCheck={false} wrap="off"
        className="mono flex-1 resize-none overflow-hidden bg-transparent px-3 py-3 text-[12px] leading-[20px] text-ink-900 outline-none" style={{ height: lines * 20 + 24, minWidth: 640 }} />
    </div>
  );
}
