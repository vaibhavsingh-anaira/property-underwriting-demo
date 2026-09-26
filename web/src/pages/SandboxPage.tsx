import { useState } from 'react';
import { Upload, FileSpreadsheet } from 'lucide-react';
import { getCurrentUserId } from '@/api/client';
import type { Severity } from '@/api/types';
import { Page, Card, Stat, Badge, Button, ErrorBox, Loading, Empty, sevTone, cx } from '@/components/ui';
import { usd, num, pct } from '@/lib/format';
import { Info } from '@/help/Info';

// ------------------------------------------------------------------ response types (local)
type Anchor = { sheet: string; cell: string; range?: string } | null;
type ParserIssue = { code: string; label: string; anchor: Anchor; severity: Severity };
type SovRow = {
  idx: number; row: number; loc_no: string | null; name: string | null; address: string | null; city: string | null; state: string | null;
  occupancy_raw: string | null; occupancy: string | null; occupancy_conf: number | null;
  construction_raw: string | null; construction: string | null; construction_conf: number | null; construction_class: number | null;
  year_built: number | null; stories: number | null; sqft: number | null; roof_year: number | null; sprinkler: number | null;
  building_value: number | null; tiv: number | null; cell_address: string | null; cell_tiv: string | null;
};
type Check = { row: number | null; location: string | null; code: string; severity: Severity; message: string };
type MatchStatus = 'MATCHED' | 'AMBIGUOUS' | 'NEW' | 'DELETED' | 'MERGED';
type Match = { status: MatchStatus; method: string | null; score: number | null; renewal: string | null; expiring: string | null; tiv_expiring: number | null; tiv_renewal: number | null };
type SovResult = {
  file: string; sheet: string; header_row: number; scale: number; columns: Record<string, string>; parser: string;
  parser_issues: ParserIssue[]; rows: SovRow[]; checks: Check[]; tiv: number; not_run: string[];
  expiring?: { file: string; rows: number; tiv: number; parser_issues: ParserIssue[] };
  matches?: Match[];
};

const SEVS: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const STATUSES: MatchStatus[] = ['MATCHED', 'AMBIGUOUS', 'NEW', 'DELETED', 'MERGED'];
const STATUS_TONE = { MATCHED: 'ok', AMBIGUOUS: 'high', NEW: 'info', DELETED: 'neutral', MERGED: 'accent' } as const;
const SAMPLES = [
  { k: 'expiring', l: 'expiring' },
  { k: 'renewal', l: 'renewal' },
  { k: 'messy', l: 'messy (renumbered campus in $000s)' },
];
const REAL = [
  'SOV parser: header-band detection, column synonyms, $000s scaling, totals-row and hidden sheet/column detection',
  'Occupancy and construction normalisation, with confidence',
  'Data-quality controls (arithmetic, missing and stale fields)',
  'Year-over-year location matching when an expiring SOV is also given',
];
const NOT_RUN_FALLBACK = [
  "Technical price and RARC split (needs the carrier's rater)",
  "CAT modelling (needs the carrier's CAT model)",
  'Contract checks (need quote/binder/policy documents)',
  'Geocoding and hazard enrichment',
];

const sev = (s: string) => <Badge tone={sevTone(s as Severity) ?? 'neutral'}>{s.charAt(0) + s.slice(1).toLowerCase()}</Badge>;
const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));
const anchorText = (a: Anchor) => (a ? `${a.sheet}!${a.range ?? a.cell}` : '—');

export default function SandboxPage() {
  const [renewal, setRenewal] = useState<File | null>(null);
  const [expiring, setExpiring] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [res, setRes] = useState<SovResult | null>(null);

  const analyse = async () => {
    if (!renewal) return;
    setBusy(true); setError(null); setRes(null);
    try {
      const fd = new FormData();
      fd.append('renewal', renewal);
      if (expiring) fd.append('expiring', expiring);
      const r = await fetch('/api/sandbox/sov', { method: 'POST', body: fd, headers: { 'X-User-Id': getCurrentUserId() } });
      const body = await r.json().catch(() => null);
      if (!r.ok) {
        const d = body?.detail;
        throw new Error(typeof d === 'string' ? d : d ? JSON.stringify(d) : `Request failed (${r.status})`);
      }
      setRes(body as SovResult);
    } catch (e) { setError(e); } finally { setBusy(false); }
  };

  return (
    <Page title="Your data (real mode)" subtitle="Upload your own SOV — the real product code parses and checks it, no mocks." actions={<Info id="sandbox.page" label="About this page" />}>
      <div className="grid grid-cols-12 gap-4">
        <Card className="col-span-12 xl:col-span-5" title="What runs for real here" subtitle="Files are processed by the local API only">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div>
              <div className="mb-1.5 flex items-center gap-2 text-[12px] font-semibold text-ink-900"><Badge tone="ok">REAL</Badge>Runs on your file</div>
              <ul className="list-disc space-y-1 pl-4 text-[12.5px] text-ink-700">{REAL.map((t) => <li key={t}>{t}</li>)}</ul>
            </div>
            <div>
              <div className="mb-1.5 flex items-center gap-2 text-[12px] font-semibold text-ink-900"><Badge>Not run</Badge>Needs your systems</div>
              <ul className="list-disc space-y-1 pl-4 text-[12.5px] text-ink-500">{(res?.not_run ?? NOT_RUN_FALLBACK).map((t) => <li key={t}>{t}</li>)}</ul>
            </div>
          </div>
        </Card>

        <Card className="col-span-12 xl:col-span-7" title="Upload statement of values" subtitle=".xlsx or .csv">
          <div className="grid gap-3 sm:grid-cols-2">
            <DropZone label="Renewal SOV" required file={renewal} onFile={setRenewal} />
            <DropZone label="Expiring SOV" file={expiring} onFile={setExpiring} />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="text-[12px] text-ink-500">
              Try a sample:{' '}
              {SAMPLES.map((s, i) => (
                <span key={s.k}>{i > 0 && ' · '}<a href={`/api/sandbox/samples/${s.k}`} download className="text-accent-700 hover:underline">{s.l}</a></span>
              ))}
            </div>
            <Button variant="primary" icon={<Upload className="size-3.5" />} disabled={!renewal} loading={busy} onClick={analyse}>Analyse</Button>
          </div>
          {error != null && <div className="mt-3"><ErrorBox error={error} /></div>}
        </Card>

        {busy && <div className="col-span-12"><Loading label="Parsing and checking…" /></div>}
        {res && <Results r={res} />}
      </div>
    </Page>
  );
}

function DropZone({ label, required, file, onFile }: { label: string; required?: boolean; file: File | null; onFile: (f: File | null) => void }) {
  const [over, setOver] = useState(false);
  return (
    <label
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onFile(e.dataTransfer.files[0] ?? null); }}
      className={cx('flex cursor-pointer flex-col items-center justify-center gap-1 rounded-md border border-dashed px-3 py-5 text-center transition-colors',
        over ? 'border-accent-500 bg-accent-50' : 'border-line-strong hover:bg-ink-50')}>
      <FileSpreadsheet className="size-5 text-ink-400" />
      <div className="text-[12.5px] font-medium text-ink-900">{label} {required ? <span className="text-crit">*</span> : <span className="font-normal text-ink-500">(optional)</span>}</div>
      <div className="max-w-full truncate text-[12px] text-ink-500">{file ? file.name : 'Drop a file or click to choose'}</div>
      <input type="file" accept=".xlsx,.csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
    </label>
  );
}

function Results({ r }: { r: SovResult }) {
  const checksBy = SEVS.map((s) => [s, r.checks.filter((c) => c.severity === s).length] as const).filter(([, n]) => n > 0);
  const m = r.matches;
  const matchBy = m ? STATUSES.map((s) => [s, m.filter((x) => x.status === s).length] as const).filter(([, n]) => n > 0) : [];
  const tivChange = r.expiring && r.expiring.tiv ? r.tiv / r.expiring.tiv - 1 : null;
  return (
    <>
      <div className="col-span-12 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Locations" value={num(r.rows.length)} sub={r.file} />
        <Stat label="TIV" value={usd(r.tiv)} sub={r.expiring ? `Expiring ${usd(r.expiring.tiv)} · ${pct(tivChange, 1, true)}` : undefined} />
        <Stat label="Scale" value={r.scale === 1 ? '×1' : `×${num(r.scale)}`} sub={r.scale === 1000 ? 'stated in $000s' : 'as stated'} />
        <Stat label="Header" value={`Row ${r.header_row}`} sub={`Sheet ${r.sheet}`} />
        <Stat label="Parser issues" value={r.parser_issues.length} tone={r.parser_issues.length ? 'high' : 'ok'} />
        <Stat label="DQ checks" value={r.checks.length} tone={r.checks.length ? 'high' : 'ok'} sub={checksBy.map(([s, n]) => `${n} ${s.toLowerCase()}`).join(' · ') || 'none'} />
      </div>
      {m && (
        <div className="col-span-12 flex flex-wrap items-center gap-2 text-[12px] text-ink-600">
          <span className="font-medium text-ink-900">Matching vs {r.expiring?.file}:</span>
          {matchBy.map(([s, n]) => <Badge key={s} tone={STATUS_TONE[s]}>{s.toLowerCase()} {n}</Badge>)}
          {tivChange !== null && <span>· TIV change <span className="num font-medium text-ink-900">{pct(tivChange, 1, true)}</span></span>}
        </div>
      )}

      <Card className="col-span-12 xl:col-span-5" pad={false} title="Parser issues" subtitle={r.parser}>
        {r.parser_issues.length === 0 && !r.expiring?.parser_issues.length ? <Empty>No parser issues.</Empty> : (
          <div className="divide-y divide-line">
            {[...r.parser_issues.map((p) => ({ p, f: 'Renewal' })), ...(r.expiring?.parser_issues ?? []).map((p) => ({ p, f: 'Expiring' }))].map(({ p, f }, i) => (
              <div key={i} className="flex items-center gap-2 px-4 py-2 text-[12.5px]">
                {sev(p.severity)}
                <span className="min-w-0 flex-1 text-ink-800">{p.label}</span>
                {r.expiring && <span className="text-[11px] text-ink-400">{f}</span>}
                <span className="mono shrink-0 text-[11px] text-ink-500">{anchorText(p.anchor)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="col-span-12 xl:col-span-7" pad={false} title="Data-quality checks" subtitle={`${r.checks.length} flagged`}>
        {r.checks.length === 0 ? <Empty>No data-quality issues.</Empty> : (
          <div className="max-h-[360px] overflow-auto">
            <table className="dt">
              <thead><tr><th>Severity</th><th className="r">Row</th><th>Location</th><th>Code</th><th>Message</th></tr></thead>
              <tbody>
                {r.checks.map((c, i) => (
                  <tr key={i}><td>{sev(c.severity)}</td><td className="num r">{dash(c.row)}</td><td>{dash(c.location)}</td><td className="mono text-[11px] text-ink-500">{c.code}</td><td className="text-ink-700">{c.message}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="col-span-12" pad={false} title="Extracted rows" subtitle={`${r.rows.length} locations · raw → normalised · source cells in ${r.sheet}`}>
        <div className="overflow-x-auto">
          <table className="dt">
            <thead><tr><th>Name / address</th><th>City / state</th><th>Occupancy</th><th>Construction</th><th className="r">Year</th><th className="r">Sq ft</th><th className="r">Roof</th><th className="r">Sprinkler</th><th className="r">TIV</th><th>Source</th></tr></thead>
            <tbody>
              {r.rows.map((x) => (
                <tr key={x.idx}>
                  <td><div className="font-medium text-ink-900">{x.loc_no && <span className="mono mr-1.5 text-[11px] text-ink-400">{x.loc_no}</span>}{dash(x.name)}</div><div className="text-[11.5px] text-ink-500">{dash(x.address)}</div></td>
                  <td className="whitespace-nowrap">{[x.city, x.state].filter(Boolean).join(', ') || '—'}</td>
                  <td><Norm raw={x.occupancy_raw} norm={x.occupancy} conf={x.occupancy_conf} /></td>
                  <td><Norm raw={x.construction_raw} norm={x.construction} conf={x.construction_conf} /></td>
                  <td className="num r">{dash(x.year_built)}</td>
                  <td className="num r">{num(x.sqft)}</td>
                  <td className="num r">{dash(x.roof_year)}</td>
                  <td className="num r">{pct(x.sprinkler, 0)}</td>
                  <td className="num r font-medium">{usd(x.tiv)}</td>
                  <td className="mono whitespace-nowrap text-[11px] text-ink-500">row {x.row}{x.cell_tiv && ` · ${x.cell_tiv}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {m && (
        <Card className="col-span-12" pad={false} title="Location matching" subtitle={`${r.expiring?.file} → ${r.file}`}>
          <div className="overflow-x-auto">
            <table className="dt">
              <thead><tr><th>Status</th><th>Method</th><th className="r">Score</th><th>Expiring</th><th>Renewal</th><th className="r">TIV exp.</th><th className="r">TIV ren.</th></tr></thead>
              <tbody>
                {m.map((x, i) => (
                  <tr key={i}>
                    <td><Badge tone={STATUS_TONE[x.status]}>{x.status.toLowerCase()}</Badge></td>
                    <td className="text-ink-600">{dash(x.method)}</td>
                    <td className="num r">{x.score == null ? '—' : x.score.toFixed(2)}</td>
                    <td>{dash(x.expiring)}</td><td>{dash(x.renewal)}</td>
                    <td className="num r">{usd(x.tiv_expiring)}</td><td className="num r">{usd(x.tiv_renewal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

function Norm({ raw, norm, conf }: { raw: string | null; norm: string | null; conf: number | null }) {
  return (
    <div className="min-w-[180px] text-[12px]">
      <span className="text-ink-500">{dash(raw)}</span> <span className="text-ink-400">→</span>{' '}
      <span className="text-ink-900">{dash(norm)}</span>
      {conf != null && <span className={cx('num ml-1 text-[11px]', conf < 0.8 ? 'text-high' : 'text-ink-400')}>{pct(conf, 0)}</span>}
    </div>
  );
}
