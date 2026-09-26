// Your data (real): your bordereau through the real CRS mapper, validator and authority rules.
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Upload, FileSpreadsheet, Download } from 'lucide-react';
import { api, getCurrentUserId } from '@/api/client';
import type { Severity } from '@/api/types';
import { Page, Card, Stat, Badge, Button, ErrorBox, Select, Empty, sevTone, cx } from '@/components/ui';
import { pct, usd } from '@/lib/format';
import { Info } from '@/help/Info';

type Result = {
  filename: string; kind: string; sheet: string; header_row: number | null; method: string; authority_source: string; notes: string[]; missing: string[]; issue_count: number;
  mapping: { col: string; header: string; field: string | null; label: string | null; confidence: number; method: string }[];
  issues: { code: string; severity: Severity; label: string; cell: string | null }[];
  stats: { rows: number; completeness: number; validity: number; mapping_confidence: number; consistency: number; dq_score: number };
  rows: { row: number; certificate_ref: string; insured: string | null; txn: string | null; tiv: number | null; limit: number | null; premium: number | null; not_checked: number;
    exceptions: { check: string; result: string; written: string; authority: string; delta: string | null; cell: string | null; referral: string | null }[] }[];
  summary: { rows: number; with_exceptions: number; rate: number; by_family: { family: string; label: string; count: number }[]; premium_tied: number; commission_discrepancy: number; not_checked: number } | null;
};

export default function Sandbox() {
  const { data: auths } = useQuery({ queryKey: ['delegated', 'sb-auth'], queryFn: () => api<{ id: string; name: string; agreement: string }[]>('/delegated/sandbox/authorities') });
  const [file, setFile] = useState<File | null>(null);
  const [baa, setBaa] = useState<File | null>(null);
  const [auth, setAuth] = useState('ch_meridian');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [res, setRes] = useState<Result | null>(null);
  const [onlyEx, setOnlyEx] = useState(true);
  const run = async () => {
    if (!file) return;
    setBusy(true); setErr(null);
    try {
      const fd = new FormData();
      fd.append('bordereau', file);
      if (baa) fd.append('baa', baa);
      const r = await fetch(`/api/delegated/sandbox?authority=${auth}`, { method: 'POST', body: fd, headers: { 'X-User-Id': getCurrentUserId() } });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail ?? r.statusText);
      setRes(j);
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };
  const rows = (res?.rows ?? []).filter((r) => !onlyEx || r.exceptions.length);
  return (
    <Page title="Your data (real)" actions={<Info id="delegated.sandbox" label="About this page" />}
      subtitle="Upload a risk (or combined risk & premium) bordereau — .xlsx or .csv. It runs through the real mapper, validator and authority rules. Nothing is stored.">
      <Card className="mb-4" title="Inputs">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-md border border-dashed border-line-strong px-4 py-5 text-center hover:border-accent-500">
            <FileSpreadsheet className="size-5 text-ink-400" /><span className="text-[13px] font-medium text-ink-900">{file ? file.name : 'Bordereau (.xlsx / .csv)'}</span><span className="text-[11.5px] text-ink-500">Any column layout; headers are mapped to CRS v5.2</span>
            <input type="file" accept=".xlsx,.csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <div className="space-y-2">
            <div className="text-[12px] font-medium text-ink-700">Authority to check against</div>
            <Select value={auth} onChange={(e) => setAuth(e.target.value)} className="w-full" disabled={!!baa}>{auths?.map((a) => <option key={a.id} value={a.id}>{a.name} — {a.agreement}</option>)}</Select>
            <label className="flex cursor-pointer items-center gap-2 text-[12px] text-accent-700 hover:underline"><Upload className="size-3.5" />{baa ? `BAA: ${baa.name}` : 'or upload a BAA PDF in the same layout'}
              <input type="file" accept=".pdf" className="hidden" onChange={(e) => setBaa(e.target.files?.[0] ?? null)} /></label>
          </div>
          <div className="space-y-2">
            <Button variant="primary" icon={<Upload className="size-3.5" />} disabled={!file} loading={busy} onClick={run} className="w-full">Run the real checks</Button>
            <div className="text-[11.5px] text-ink-500">Samples: {[['meridian', 'coverholder template'], ['ridgeway', 'messy production report'], ['northfield', 'CRS template'], ['baa', 'BAA PDF']].map(([k, l]) => (
              <a key={k} href={`/api/delegated/sandbox/samples/${k}`} className="mr-2 inline-flex items-center gap-0.5 font-medium text-accent-700 hover:underline"><Download className="size-3" />{l}</a>))}</div>
          </div>
        </div>
      </Card>
      {err ? <ErrorBox error={err} /> : null}
      {res && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <Stat label="Lines" value={res.stats.rows} sub={`${res.kind} bordereau · sheet ${res.sheet}`} />
            <Stat label="DQ score" value={res.stats.dq_score.toFixed(0)} tone={res.stats.dq_score >= 90 ? 'ok' : 'high'} sub={`${res.issue_count} issues`} />
            <Stat label="Mapping" value={pct(res.stats.mapping_confidence, 0)} sub={`${res.missing.length} mandatory missing`} />
            <Stat label="With exceptions" value={res.summary?.with_exceptions ?? '—'} tone="crit" sub={res.summary ? pct(res.summary.rate, 1) : ''} />
            <Stat label="Premium tied" value={usd(res.summary?.premium_tied ?? 0)} />
            <Stat label="Not fully checked" value={res.summary?.not_checked ?? '—'} sub="lines with missing data" />
          </div>
          <div className="text-[12px] text-ink-600">Authority: {res.authority_source}</div>
          <div className="grid grid-cols-12 gap-4">
            <Card className="col-span-12 xl:col-span-5" pad={false} title="Column mapping (CRS v5.2)">
              <div className="max-h-[360px] overflow-y-auto"><table className="dt"><tbody>{res.mapping.map((m) => (
                <tr key={m.col}><td className="mono text-[12px]">{m.col}</td><td className="text-[12.5px]">{m.header}</td><td className={cx('text-[12.5px]', !m.field && 'text-ink-400')}>{m.label ?? 'not mapped'}</td><td><Badge tone={m.method === 'CRS label' ? 'ok' : m.method === 'synonym' ? 'info' : m.method === 'fuzzy' ? 'high' : 'neutral'}>{m.method}</Badge></td><td className="num r">{m.field ? pct(m.confidence, 0) : ''}</td></tr>))}</tbody></table></div>
              {res.missing.length > 0 && <div className="border-t border-line px-4 py-2 text-[12px] text-crit">Missing mandatory: {res.missing.join(', ')}</div>}
            </Card>
            <Card className="col-span-12 xl:col-span-7" pad={false} title="Validation issues (cell references)">
              <div className="max-h-[400px] overflow-y-auto"><table className="dt"><tbody>{res.issues.map((i, k) => <tr key={k}><td><Badge tone={sevTone(i.severity)}>{i.severity}</Badge></td><td className="mono text-[11px]">{i.code}</td><td className="mono text-[12px]">{i.cell ?? '—'}</td><td className="text-[12.5px]">{i.label}</td></tr>)}</tbody></table>
                {res.issues.length === 0 && <Empty>No issues.</Empty>}</div>
            </Card>
          </div>
          {res.summary && (
            <Card pad={false} title="Authority checks per line" actions={<label className="flex items-center gap-1.5 text-[12px]"><input type="checkbox" checked={onlyEx} onChange={(e) => setOnlyEx(e.target.checked)} />Only lines with exceptions</label>}
              subtitle={res.summary.by_family.map((f) => `${f.label} ${f.count}`).join(' · ') || 'No exceptions'}>
              <div className="max-h-[480px] overflow-y-auto"><table className="dt">
                <thead><tr><th>Row</th><th>Certificate</th><th>Insured</th><th className="r">TIV</th><th className="r">Limit</th><th className="r">Premium</th><th>Exceptions (written vs authority)</th></tr></thead>
                <tbody>{rows.slice(0, 300).map((r) => (
                  <tr key={r.row}><td className="num">{r.row}</td><td className="mono text-[11.5px]">{r.certificate_ref}</td><td className="text-[12.5px]">{r.insured}</td><td className="num r">{usd(r.tiv)}</td><td className="num r">{usd(r.limit)}</td><td className="num r">{usd(r.premium)}</td>
                    <td className="text-[12px]">{r.exceptions.map((e, k) => <div key={k}><span className="font-medium">{e.check}</span>: {e.written} vs {e.authority}{e.delta ? <span className="ml-1 text-crit">{e.delta}</span> : null}{e.cell ? <span className="mono ml-1 text-ink-400">[{e.cell}]</span> : null}{e.referral ? <span className="ml-1 text-ink-500">· referral {e.referral}</span> : null}</div>)}
                      {!r.exceptions.length && <span className="text-ok">Within authority{r.not_checked ? ` (${r.not_checked} checks not run — data missing)` : ''}</span>}</td></tr>))}</tbody></table></div>
            </Card>
          )}
          <Card title="What needs the carrier's systems"><ul className="list-disc pl-5 text-[12.5px] text-ink-700">{res.notes.map((n) => <li key={n}>{n}</li>)}</ul></Card>
        </div>
      )}
    </Page>
  );
}
