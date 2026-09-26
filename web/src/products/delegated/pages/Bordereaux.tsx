// Bordereaux: every file received, its CRS v5.2 mapping and validation issues, opened at the cell.
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Page, Card, Loading, ErrorBox, Badge, Select, Empty, sevTone, cx } from '@/components/ui';
import { fmtDate, pct } from '@/lib/format';
import { Info } from '@/help/Info';
import { useEvidence } from '@/components/evidence';
import { MONTH, useBordereau, useBordereaux, useCoverholders } from '../api';
import { StatusPill } from '../parts';

export default function Bordereaux() {
  const [sp, setSp] = useSearchParams();
  const ch = sp.get('ch') ?? undefined;
  const { data, isLoading, error } = useBordereaux(ch);
  const { data: chs } = useCoverholders();
  const [sel, setSel] = useState<string | null>(null);
  const cur = sel ?? data?.find((b) => b.kind === 'risk')?.doc_id ?? null;
  return (
    <Page title="Bordereaux" actions={<Info id="delegated.bordereaux" label="About this page" />}
      subtitle="Risk, premium, claims bordereaux and exposure returns as received · mapped to Lloyd's CRS v5.2 · every issue opens the file at its cell">
      <div className="mb-3 flex items-center gap-2">
        <Select value={ch ?? ''} onChange={(e) => { const n = new URLSearchParams(sp); if (e.target.value) n.set('ch', e.target.value); else n.delete('ch'); setSp(n, { replace: true }); setSel(null); }}>
          <option value="">All coverholders</option>{chs?.map((c) => <option key={c.id} value={c.id}>{c.scenario} · {c.short}</option>)}
        </Select>
      </div>
      {isLoading ? <Loading /> : error || !data ? <ErrorBox error={error} /> : (
        <div className="grid grid-cols-12 gap-4">
          <Card className="col-span-12 xl:col-span-5" pad={false} title={<span className="inline-flex items-center gap-1.5">Files received<Info id="delegated.bdx.list" /></span>} subtitle={`${data.length} files`}>
            <div className="max-h-[calc(100vh-230px)] overflow-y-auto">
              <table className="dt"><thead><tr><th>File</th><th>Received</th><th className="r">Late</th><th className="r">DQ</th><th className="r">Exc.</th></tr></thead>
                <tbody>{data.map((b) => (
                  <tr key={b.doc_id} onClick={() => setSel(b.doc_id)} className={cx('cursor-pointer', cur === b.doc_id && 'is-selected', b.superseded_by && 'opacity-50')}>
                    <td className="max-w-[260px]"><div className="truncate text-[12.5px] font-medium text-ink-900">{b.title}</div>
                      <div className="text-[11px] text-ink-500">{b.ch_name} · {b.kind}{b.correction ? (b.replaces ? ' · resubmission' : ' · correction') : ''}{b.superseded_by ? ' · superseded' : ''} · {b.rows} rows</div></td>
                    <td className="num whitespace-nowrap text-[12px]">{fmtDate(b.received)}</td>
                    <td className={cx('num r', b.days_late ? 'font-semibold text-crit' : 'text-ink-400')}>{b.days_late || '—'}</td>
                    <td className={cx('num r', b.dq_score < 85 ? 'font-semibold text-high' : '')}>{b.dq_score.toFixed(0)}</td>
                    <td className="num r">{b.exceptions || '—'}</td>
                  </tr>))}</tbody></table>
            </div>
          </Card>
          <div className="col-span-12 xl:col-span-7">{cur ? <Detail id={cur} /> : <Empty>Select a file.</Empty>}</div>
        </div>
      )}
    </Page>
  );
}

function Detail({ id }: { id: string }) {
  const { data: b, isLoading, error } = useBordereau(id);
  const ev = useEvidence();
  if (isLoading) return <Loading />;
  if (error || !b) return <ErrorBox error={error} />;
  const at = (cell: string | null) => ev.openDoc(b.doc_id, cell ? { doc_id: b.doc_id, kind: 'xlsx', sheet: b.sheet, cell } : null);
  return (
    <div className="space-y-4">
      <Card title={b.title} subtitle={`${b.ch_name} · ${MONTH(b.month)} · received ${fmtDate(b.received)} · due ${fmtDate(b.due)}${b.days_late ? ` · ${b.days_late} days late` : ''} · sheet “${b.sheet}”, header row ${b.header_row}`}
        actions={<button onClick={() => at(null)} className="text-[12px] font-medium text-accent-700 hover:underline">Open file</button>}>
        <div className="grid grid-cols-5 gap-2">
          {[['DQ score', b.dq_score.toFixed(0)], ['Completeness', pct(b.stats.completeness, 0)], ['Validity', pct(b.stats.validity, 1)], ['Mapping', pct(b.stats.mapping_confidence, 0)], ['Consistency', pct(b.stats.consistency, 0)]].map(([l, v]) => (
            <div key={l} className="rounded-md border border-line px-3 py-2"><div className="text-[10.5px] uppercase tracking-wide text-ink-500">{l}</div><div className="num text-[15px] font-semibold">{v}</div></div>))}
        </div>
        {b.missing_labels.length > 0 && <div className="mt-2 rounded-md bg-crit-bg px-3 py-1.5 text-[12px] text-crit">Mandatory CRS v5.2 fields missing: {b.missing_labels.join(', ')}</div>}
        <div className="mt-2 text-[11px] text-ink-500">{b.method} · DQ = 45% completeness + 25% validity + 20% mapping confidence + 10% consistency</div>
      </Card>
      <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Column mapping to CRS v5.2<Info id="delegated.bdx.mapping" /></span>} subtitle={`${b.mapping.filter((m) => m.field).length} of ${b.mapping.length} columns mapped`}>
        <div className="max-h-[300px] overflow-y-auto">
          <table className="dt"><thead><tr><th>Col</th><th>Header in the file</th><th>CRS v5.2 field</th><th>Method</th><th className="r">Confidence</th></tr></thead>
            <tbody>{b.mapping.map((m) => (
              <tr key={m.col} className="cursor-pointer" onClick={() => at(`${m.col}${b.header_row}`)}>
                <td className="mono text-[12px]">{m.col}</td><td className="text-[12.5px]">{m.header}</td><td className={cx('text-[12.5px]', !m.field && 'text-ink-400')}>{m.label ?? 'not mapped'}</td>
                <td><Badge tone={m.method === 'CRS label' ? 'ok' : m.method === 'synonym' ? 'info' : m.method === 'fuzzy' ? 'high' : 'neutral'}>{m.method}</Badge></td>
                <td className="num r">{m.field ? pct(m.confidence, 0) : '—'}</td>
              </tr>))}</tbody></table>
        </div>
      </Card>
      <Card pad={false} title={<span className="inline-flex items-center gap-1.5">Validation issues<Info id="delegated.bdx.issues" /></span>} subtitle={`${b.issues.length} issues · click to open the cell`}>
        <div className="max-h-[320px] overflow-y-auto">
          <table className="dt"><thead><tr><th>Severity</th><th>Check</th><th>Cell</th><th>Issue</th></tr></thead>
            <tbody>{b.issues.map((i, k) => (
              <tr key={k} className="cursor-pointer" onClick={() => at(i.cell)}>
                <td><Badge tone={sevTone(i.severity)}>{i.severity}</Badge></td><td className="mono text-[11px]">{i.code}</td><td className="mono text-[12px]">{i.cell ?? '—'}</td><td className="text-[12.5px]">{i.label}</td>
              </tr>))}</tbody></table>
          {b.issues.length === 0 && <Empty>No validation issues.</Empty>}
        </div>
      </Card>
      {b.exceptions.length > 0 && (
        <Card pad={false} title="Authority exceptions on this file">
          <table className="dt"><tbody>{b.exceptions.map((e) => (
            <tr key={e.exc_id} className="cursor-pointer" onClick={() => e.anchor && ev.openDoc(e.anchor.doc_id ?? b.doc_id, e.anchor)}>
              <td className="mono text-[11.5px]">{e.certificate_ref}</td><td className="text-[12.5px]">{e.insured}</td><td className="text-[12px]">{e.check}: {e.written} vs {e.authority}</td><td><StatusPill s={e.status} /></td>
            </tr>))}</tbody></table>
        </Card>
      )}
    </div>
  );
}
