// Your data (real): upload a schedule (and optionally an ACORD-style application PDF); the real Stage 1 pack is built,
// then an intended action gets the real Stage 2 verdict. Pricing and hazard are stand-ins and say so.
import { useMemo, useState } from 'react';
import { Upload, Download, FlaskConical } from 'lucide-react';
import { Page, Card, Button, Badge, ErrorBox, MockBadge } from '@/components/ui';
import { Box } from '@/pages/guide/parts';
import { Info } from '@/help/Info';
import { useSandbox, useSandboxAssure, type SandboxResult } from './api';
import { PackView } from './PackTab';
import { ActionFields, AssuranceView, defaults } from './ActionTab';

export default function SandboxPage() {
  const [sov, setSov] = useState<File | null>(null);
  const [app, setApp] = useState<File | null>(null);
  const run = useSandbox();
  return (
    <Page title="Your data (real mode)" subtitle="Your own schedule and application through the real Stage 1 pack and Stage 2 assurance · nothing leaves this machine" actions={<Info id="decision.sandbox" label="About this page" />}>
      <Card title="Upload" subtitle="SOV as .xlsx or .csv (required) · application as PDF in the ACORD 125/140 layout the samples use (optional — it enables the contradictions check between the two files)">
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-[12px] text-ink-600">Statement of values<input type="file" accept=".xlsx,.csv" onChange={(e) => setSov(e.target.files?.[0] ?? null)} className="mt-1 block text-[12px]" /></label>
          <label className="text-[12px] text-ink-600">Application (PDF, optional)<input type="file" accept=".pdf" onChange={(e) => setApp(e.target.files?.[0] ?? null)} className="mt-1 block text-[12px]" /></label>
          <Button variant="primary" icon={<Upload className="size-3.5" />} disabled={!sov} loading={run.isPending} onClick={() => sov && run.mutate({ sov, application: app })}>Build the decision pack</Button>
          <span className="flex gap-3 text-[12px]">
            <a href="/api/decision/sandbox/samples/sov" className="inline-flex items-center gap-1 font-medium text-accent-700 hover:underline"><Download className="size-3.5" />Sample SOV</a>
            <a href="/api/decision/sandbox/samples/application" className="inline-flex items-center gap-1 font-medium text-accent-700 hover:underline"><Download className="size-3.5" />Sample application</a>
          </span>
        </div>
        {run.error && <div className="mt-3"><ErrorBox error={run.error} /></div>}
      </Card>
      {run.data && <Result r={run.data} />}
    </Page>
  );
}

function Result({ r }: { r: SandboxResult }) {
  const prev = useSandboxAssure(r.token);
  const [recorded, setRecorded] = useState(false);
  const init = useMemo(() => defaults(r.pack), [r.pack]);
  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Box tone="ok" title={<><Badge tone="ok">REAL</Badge> Ran on your files</>} items={r.real} />
        <Box tone="mock" title={<><MockBadge /> Needs carrier systems</>} items={r.not_real} />
      </div>
      <div className="text-[12.5px] text-ink-600">{r.sov}{r.application ? ` + ${r.application}` : ''} → {r.observations} observations · parser notes: {r.issues.map((i) => i.label).join('; ') || 'none'}</div>
      <PackView pack={r.pack} facts={r.facts} />
      <Card title={<span className="inline-flex items-center gap-1.5"><FlaskConical className="size-4" />Your intended action</span>} subtitle="Assured against the live rules and the authority of the persona selected in the header">
        <ActionFields pack={r.pack} init={init} preview={prev.data?.assurance} onPreview={(a) => prev.mutate(a)} footer={() => <Button onClick={() => setRecorded(true)} disabled={!prev.data}>Show full assurance result</Button>} />
      </Card>
      {recorded && prev.data && <AssuranceView a={prev.data.assurance} />}
    </div>
  );
}
