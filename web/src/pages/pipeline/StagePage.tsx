import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Route } from 'lucide-react';
import { usePipeline, usePlaybooks, useStage, useSubjects } from '@/api/client';
import { useProduct } from '@/products';
import { Badge } from '@/components/ui';
import { Page, Loading, ErrorBox, Select, Button } from '@/components/ui';
import { StageWorkspace } from './StageWorkspace';
import { Info } from '@/help/Info';


export default function StagePage() {
  const { code = '01' } = useParams();
  const [sp, setSp] = useSearchParams();
  const product = useProduct();
  const { data: subjects } = useSubjects(product.id);
  const { data: stages } = usePipeline(product.id);
  const acct = sp.get('account') ?? subjects?.[0]?.id;
  const nav = useNavigate();
  const { data, isLoading, error } = useStage(acct ? code : undefined, acct, product.id);
  const n = parseInt(code, 10);
  const last = stages?.length ?? 15;
  const go = (k: number) => nav(product.to(`/pipeline/${String(k).padStart(2, '0')}?account=${acct}`));
  return (
    <Page
      crumbs={<Link to={product.to('/pipeline')} className="hover:underline">{product.name} · Pipeline & mocks</Link>}
      title={data ? `${data.code} · ${data.name}` : `Stage ${code}`}
      subtitle={`The system behind this stage, loaded with the selected ${product.subjectLabel.toLowerCase()}'s data`}
      actions={<>
        <Info id="stage.page" label="About this page" />
        <Select value={acct ?? ''} onChange={(e) => setSp({ account: e.target.value })}>
          {(subjects ?? []).map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
        </Select>
        <Button size="md" icon={<ArrowLeft className="size-3.5" />} disabled={n <= 1} onClick={() => go(n - 1)}>Prev</Button>
        <Button size="md" disabled={n >= last} onClick={() => go(n + 1)}>Next <ArrowRight className="size-3.5" /></Button>
        <Link to={product.to(`/pipeline/journey?pb=lifecycle-${acct}`)}><Button variant="primary" icon={<Route className="size-3.5" />}>Play all {last} stages</Button></Link>
      </>}
    >
      <FlowsThrough code={code} />
      {isLoading || !acct ? <Loading /> : error || !data ? <ErrorBox error={error} /> : <StageWorkspace v={data} />}
    </Page>
  );
}

function FlowsThrough({ code }: { code: string }) {
  const product = useProduct();
  const { data } = usePlaybooks(product.id);
  const flows = (data ?? []).filter((p) => !p.id.startsWith('lifecycle-') && p.steps.some((s) => s.code === code));
  if (!flows.length) return null;
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface px-3 py-2">
      <span className="text-[12px] font-medium text-ink-600">Workflows through this stage:</span>
      {flows.map((p) => (
        <Link key={p.id} to={product.to(`/pipeline/journey?pb=${p.id}&autoplay=1`)} className="inline-flex items-center gap-1 rounded-md border border-line-strong px-2 py-0.5 text-[12px] text-ink-800 hover:border-accent-500 hover:text-accent-700">
          <Badge tone="dark">{p.scenario}</Badge>{p.title.split(' — ')[0]} ▸
        </Link>
      ))}
    </div>
  );
}
