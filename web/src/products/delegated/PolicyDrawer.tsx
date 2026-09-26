// Breach register detail: the deck's side-by-side authority result for one policy, with evidence, history and actions.
import { useEffect, useState } from 'react';
import { X, Send, ShieldCheck, ArrowUpRight, MessageSquareQuote } from 'lucide-react';
import { Badge, Button, ErrorBox, Loading, cx } from '@/components/ui';
import { fmtDate, usd } from '@/lib/format';
import { Info } from '@/help/Info';
import { useDaAction, usePolicy, MONTH } from './api';
import { ChLink, SideBySide, Src, StatusPill } from './parts';

export function PolicyDrawer({ k, onClose }: { k: string | null; onClose: () => void }) {
  const { data: p, isLoading, error } = usePolicy(k);
  const act = useDaAction();
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  useEffect(() => { setMsg(null); }, [k]);
  useEffect(() => {
    if (!k) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [k, onClose]);
  if (!k) return null;
  const run = (path: string, body: unknown) => act.mutate({ path, body }, { onSuccess: (r) => setMsg({ ok: true, t: r.message }), onError: (e) => setMsg({ ok: false, t: (e as Error).message }) });
  const openIds = p?.exc_ids_open ?? [];
  const queryable = p?.checks.filter((c) => c.status === 'OPEN').map((c) => c.exc_id) ?? [];
  return (
    <div className="fixed inset-0 z-40">
      <div className="anim-fade absolute inset-0 bg-ink-950/20" onClick={onClose} />
      <aside className="anim-slide-in absolute right-0 top-0 flex h-full w-[860px] max-w-[100vw] flex-col border-l border-line bg-surface shadow-[var(--shadow-pop)]">
        <div className="flex h-11 shrink-0 items-center justify-between border-b border-line px-4">
          <div className="flex items-center gap-2 text-[12px] font-medium uppercase tracking-[.05em] text-ink-500">Breach register · risk-level authority result<Info id="delegated.breach.detail" className="normal-case" /></div>
          <button onClick={onClose} className="rounded-md p-1 text-ink-500 hover:bg-ink-100"><X className="size-4" /></button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {error ? <div className="p-4"><ErrorBox error={error} /></div> : isLoading || !p ? <Loading /> : (
            <div className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2"><Badge tone="dark">{p.scenario}</Badge><ChLink id={p.ch}>{p.ch_name}</ChLink><span className="text-[12px] text-ink-400">·</span><span className="mono text-[12px] text-ink-600">{p.certificate_ref}</span></div>
                  <div className="mt-1 text-[18px] font-semibold text-ink-950">{p.insured}</div>
                  <div className="text-[12px] text-ink-500">{p.txn ?? p.subject_type} · {MONTH(p.month)} bordereau · raised {fmtDate(p.raised_at)}{p.query_ids.length ? ` · ${p.query_ids.join(', ')}` : ''}</div>
                </div>
                <div className="text-right">
                  <StatusPill s={p.status} />
                  <div className="mt-1 text-[11px] text-ink-500">authority result</div>
                  <div className={cx('text-[20px] font-bold tracking-tight', p.open ? 'text-crit' : 'text-ok')}>{p.open ? 'BREACH' : p.status === 'AUTHORISED' ? 'WITHIN' : 'CLOSED'}</div>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {[['Premium tied', usd(p.premium_tied)], ['Exposure above authority', usd(p.exposure_above)], ['Commission discrepancy', `$${p.commission_discrepancy.toLocaleString('en-US', { maximumFractionDigits: 2 })}`], ['$ at stake (open)', usd(p.impact_usd)]].map(([l, v]) => (
                  <div key={l} className="rounded-md border border-line px-3 py-2"><div className="text-[10.5px] uppercase tracking-wide text-ink-500">{l}</div><div className="num text-[15px] font-semibold text-ink-950">{v}</div></div>
                ))}
              </div>
              <div className="overflow-hidden rounded-md border border-line"><SideBySide checks={p.side_by_side} /></div>
              <div className="rounded-md border border-accent-100 bg-accent-50 px-3 py-2">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-accent-700">Recommended</div>
                <ul className="mt-1 list-disc pl-4 text-[12.5px] text-ink-800">{p.recommended.map((r) => <li key={r}>{r}</li>)}</ul>
              </div>
              {openIds.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  {queryable.length > 0 && <Button size="sm" variant="primary" icon={<Send className="size-3.5" />} loading={act.isPending} onClick={() => run(`coverholders/${p.ch}/query`, { exc_ids: queryable, kind: p.subject_type === 'claim' ? 'claims' : 'breach' })}>Query coverholder</Button>}
                  <Button size="sm" icon={<ShieldCheck className="size-3.5" />} onClick={() => run('actions/decide', { exc_ids: openIds, decision: 'ACCEPT', note: 'Reviewed — held covered' })}>Accept (ratify)</Button>
                  <Button size="sm" icon={<ArrowUpRight className="size-3.5" />} onClick={() => run('actions/decide', { exc_ids: openIds, decision: 'ESCALATE', note: 'Escalated to DA committee' })}>Escalate</Button>
                  {msg && <span className={cx('text-[12px]', msg.ok ? 'text-ok' : 'text-crit')}>{msg.t}</span>}
                </div>
              )}
              {p.row_fields.length > 0 && (
                <div>
                  <div className="mb-1 flex items-center justify-between"><div className="text-[12px] font-semibold uppercase tracking-wide text-ink-500">Bordereau line (as reported)</div>
                    <div className="flex gap-1">{p.bordereau_doc_id && <Src docId={p.bordereau_doc_id} label="Open bordereau" />}{p.authority_doc_id && <Src docId={p.authority_doc_id} kind="clause" label="Authority in force" />}</div></div>
                  <div className="grid grid-cols-2 gap-x-6 rounded-md border border-line px-3 py-1">
                    {p.row_fields.map((f) => (
                      <div key={f.field} className="flex items-center justify-between gap-2 border-b border-line py-1 last:border-0">
                        <span className="text-[12px] text-ink-500">{f.label}</span>
                        <span className="flex items-center gap-1.5"><span className="num text-[12.5px] text-ink-900">{f.value}</span>{f.anchor && <Src anchor={f.anchor} />}</span>
                      </div>
                    ))}
                  </div>
                  {p.corrections.length > 0 && <div className="mt-1 text-[12px] text-ink-600">Corrected: {p.corrections.map((c) => <span key={c.doc_id} className="mr-2">{fmtDate(c.date)} ({c.fields.join(', ') || 'reference'}) <Src docId={c.doc_id} label="correction file" /></span>)}</div>}
                </div>
              )}
              {p.claims.length > 0 && (
                <div>
                  <div className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-ink-500">Claims on this policy</div>
                  {p.claims.map((c) => <div key={c.claim_ref} className="flex items-center justify-between rounded-md border border-line px-3 py-1.5 text-[12.5px]"><span><span className="mono">{c.claim_ref}</span> · {c.cause} · {fmtDate(c.date_of_loss)}</span><span className="num font-semibold">{usd(c.incurred)} incurred <Src anchor={c.anchor} /></span></div>)}
                </div>
              )}
              {p.responses.length > 0 && (
                <div>
                  <div className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-ink-500">Coverholder response</div>
                  {[...new Map(p.responses.map((r) => [r.text, r])).values()].map((r) => <div key={r.exc_id} className="flex gap-2 rounded-md bg-ink-50 px-3 py-2 text-[12.5px] text-ink-800"><MessageSquareQuote className="mt-0.5 size-3.5 shrink-0 text-ink-400" /><span><Badge>{r.kind}</Badge> {r.text} <span className="text-ink-400">({fmtDate(r.date)})</span></span></div>)}
                </div>
              )}
              <div>
                <div className="mb-1 text-[12px] font-semibold uppercase tracking-wide text-ink-500">History</div>
                <div className="divide-y divide-line rounded-md border border-line">
                  {p.history.map((h, i) => <div key={i} className="flex gap-3 px-3 py-1.5 text-[12px]"><span className="num w-[84px] shrink-0 text-ink-500">{fmtDate(h.date)}</span><span className="w-[150px] shrink-0 font-medium text-ink-800">{h.event}</span><span className="min-w-0 flex-1 text-ink-600">{h.check}{h.note ? ` — ${h.note}` : ''}</span><span className="text-ink-400">{h.by}</span></div>)}
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
