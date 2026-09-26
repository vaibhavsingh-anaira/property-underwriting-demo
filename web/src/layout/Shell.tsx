import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { Search, RotateCcw, FastForward, ChevronDown, CalendarClock, Check } from 'lucide-react';
import { PRODUCTS, useProduct } from '@/products';
import { cx, Badge } from '@/components/ui';
import { useAdvance, useDemoState, useReferrals, useReset, useSearch, useUsers, setCurrentUserId, getCurrentUserId } from '@/api/client';
import { fmtDate } from '@/lib/format';
import { useQueryClient } from '@tanstack/react-query';
import { EvidenceDrawer } from '@/components/EvidenceDrawer';
import { DocumentModal } from '@/components/DocumentModal';
import { Info } from '@/help/Info';


export function Shell() {
  const { data: pending } = useReferrals('PENDING');
  const product = useProduct();
  return (
    <div className="flex h-full">
      <aside className="flex w-[216px] shrink-0 flex-col border-r border-ink-800 bg-ink-950 text-ink-200">
        <div className="flex items-center gap-2.5 px-4 pb-4 pt-4">
          <div className="flex size-7 items-center justify-center rounded-md bg-accent-500 text-[13px] font-bold text-ink-950">A</div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold text-white">Anaira</div>
            <div className="text-[11px] text-ink-400">Underwriting Control</div>
          </div>
          <Info id="app.overview" className="ml-auto text-ink-500 hover:text-white" />
        </div>
        <ProductSwitcher />
        <nav className="flex flex-1 flex-col gap-0.5 px-2">
          {product.nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => cx('flex items-center gap-2.5 rounded-md px-2.5 py-[7px] text-[13px] transition-colors',
                isActive ? 'bg-ink-800 text-white' : 'text-ink-300 hover:bg-ink-900 hover:text-white')}>
              <n.icon className="size-4 opacity-80" />
              <span className="flex-1">{n.label}</span>
              {n.badge === 'referrals' && pending && pending.length > 0 && (
                <span className="num rounded-full bg-accent-500 px-1.5 text-[10.5px] font-semibold text-ink-950">{pending.length}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-ink-800 px-4 py-3 text-[10.5px] leading-snug text-ink-500">
          Northgate Specialty · Commercial Property US<br />Demo tenant · fictional data · every document watermarked SAMPLE
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <EvidenceDrawer />
      <DocumentModal />
    </div>
  );
}

function TopBar() {
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-surface px-4">
      <GlobalSearch />
      <div className="flex-1" />
      <DemoClock />
      <UserSwitcher />
    </header>
  );
}

function GlobalSearch() {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const nav = useNavigate();
  const { data } = useSearch(q);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); ref.current?.focus(); } };
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h);
  }, []);
  return (
    <div className="relative w-[380px]">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-400" />
      <input ref={ref} value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search accounts, documents, rules…" className="h-8 w-full rounded-md border border-line bg-ink-50 pl-8 pr-12 text-[13px] outline-none focus:border-accent-500 focus:bg-surface" />
      <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-line bg-surface px-1 text-[10px] text-ink-400">⌘K</kbd>
      {open && data && data.length > 0 && (
        <div className="absolute left-0 right-0 top-9 z-50 max-h-[420px] overflow-y-auto rounded-lg border border-line bg-surface p-1 shadow-[var(--shadow-pop)]">
          {data.map((h) => (
            <button key={h.kind + h.id} onMouseDown={() => { nav(h.href); setQ(''); setOpen(false); }} className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-ink-50">
              <Badge>{h.kind}</Badge>
              <span className="truncate text-[13px] text-ink-900">{h.title}</span>
              <span className="ml-auto truncate text-[12px] text-ink-500">{h.subtitle}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function DemoClock() {
  const { data } = useDemoState();
  const adv = useAdvance();
  const reset = useReset();
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const go = (b: { days?: number; to?: string }) => adv.mutate(b, {
    onSuccess: (r) => { setToast(`${r.applied.length} events · ${r.new_findings} new findings`); setTimeout(() => setToast(null), 3500); setOpen(false); },
  });
  return (
    <div className="relative flex items-center gap-1.5">
      {toast && <div className="anim-fade absolute right-0 top-10 z-50 whitespace-nowrap rounded-md bg-ink-900 px-3 py-1.5 text-[12px] text-white shadow-[var(--shadow-pop)]">{toast}</div>}
      <button onClick={() => setOpen((o) => !o)} className="flex h-8 items-center gap-2 rounded-md border border-line-strong bg-surface px-2.5 hover:bg-ink-50">
        <CalendarClock className="size-3.5 text-accent-600" />
        <span className="text-[11px] uppercase tracking-wide text-ink-500">Demo clock</span>
        <span className="num text-[13px] font-semibold text-ink-900">{data ? fmtDate(data.clock) : '…'}</span>
        <ChevronDown className="size-3.5 text-ink-400" />
      </button>
      <Info id="app.demo_clock" />
      <button title="Advance 7 days" onClick={() => go({ days: 7 })} disabled={adv.isPending}
        className="flex h-8 items-center gap-1 rounded-md border border-line-strong bg-surface px-2 text-[12px] font-medium text-ink-700 hover:bg-ink-50 disabled:opacity-50">
        <FastForward className={cx('size-3.5', adv.isPending && 'animate-pulse')} /> +7d
      </button>
      {open && data && (
        <div className="absolute right-0 top-10 z-50 w-[380px] rounded-lg border border-line bg-surface p-3 shadow-[var(--shadow-pop)]">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-[12px] text-ink-500">Timeline · <span className="num">{data.events_applied}/{data.events_total}</span> events applied</div>
            <button onClick={() => reset.mutate(undefined, { onSuccess: () => setOpen(false) })} className="flex items-center gap-1 text-[12px] text-ink-600 hover:text-crit">
              <RotateCcw className="size-3" /> Reset demo
            </button>
          </div>
          <div className="mb-3 grid grid-cols-4 gap-1.5">
            {[1, 7, 30, 90].map((d) => (
              <button key={d} onClick={() => go({ days: d })} className="rounded-md border border-line-strong py-1.5 text-[12px] font-medium hover:bg-ink-50">+{d} day{d > 1 ? 's' : ''}</button>
            ))}
          </div>
          <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-ink-500">Next events</div>
          <div className="max-h-[260px] overflow-y-auto">
            {data.next_events.map((e, i) => (
              <button key={i} onClick={() => go({ to: e.date })} className="flex w-full items-start gap-2 rounded-md px-1.5 py-1.5 text-left hover:bg-ink-50">
                <span className="num w-[74px] shrink-0 text-[12px] text-ink-500">{fmtDate(e.date)}</span>
                <span className="text-[12px] text-ink-800">{e.title}{e.account_name && <span className="text-ink-500"> · {e.account_name}</span>}</span>
              </button>
            ))}
            {data.next_events.length === 0 && <div className="py-3 text-center text-[12px] text-ink-500">End of scripted timeline</div>}
          </div>
        </div>
      )}
    </div>
  );
}

function UserSwitcher() {
  const { data: users } = useUsers();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [uid, setUid] = useState(getCurrentUserId());
  const me = users?.find((u) => u.user_id === uid);
  return (
    <div className="relative flex items-center gap-1">
      <Info id="app.persona" />
      <button onClick={() => setOpen((o) => !o)} className="flex h-8 items-center gap-2 rounded-md px-1.5 hover:bg-ink-50">
        <span className="flex size-6 items-center justify-center rounded-full bg-ink-800 text-[10.5px] font-semibold text-white">{me?.initials ?? '··'}</span>
        <span className="text-left leading-tight">
          <span className="block text-[12px] font-medium text-ink-900">{me?.name ?? '…'}</span>
          <span className="block text-[10.5px] text-ink-500">{me?.title} · L{me?.authority_level}</span>
        </span>
        <ChevronDown className="size-3.5 text-ink-400" />
      </button>
      {open && users && (
        <div className="absolute right-0 top-10 z-50 w-[280px] rounded-lg border border-line bg-surface p-1 shadow-[var(--shadow-pop)]">
          <div className="px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-ink-500">Switch persona</div>
          {users.map((u) => (
            <button key={u.user_id} onClick={() => { setCurrentUserId(u.user_id); setUid(u.user_id); setOpen(false); qc.invalidateQueries(); }}
              className={cx('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-ink-50', u.user_id === uid && 'bg-accent-50')}>
              <span className="flex size-6 items-center justify-center rounded-full bg-ink-800 text-[10.5px] font-semibold text-white">{u.initials}</span>
              <span className="leading-tight"><span className="block text-[12px] font-medium">{u.name}</span><span className="block text-[11px] text-ink-500">{u.title} · authority L{u.authority_level}</span></span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// One platform, three products. Switching keeps the demo clock and persona; each product has its own
// start-here guide, dashboard, pipeline, playbooks and briefs.
function ProductSwitcher() {
  const cur = useProduct();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  return (
    <div className="relative mx-3 mb-3">
      <button onClick={() => setOpen((o) => !o)} data-demo="product-switcher"
        className="flex w-full items-center gap-2 rounded-md border border-ink-700 bg-ink-900 px-2.5 py-2 text-left hover:border-accent-500">
        <span className="mono flex size-6 shrink-0 items-center justify-center rounded bg-accent-500 text-[10.5px] font-bold text-ink-950">{cur.number}</span>
        <span className="min-w-0 flex-1 leading-tight">
          <span className="block text-[10px] uppercase tracking-[.08em] text-ink-500">Product</span>
          <span className="block truncate text-[12.5px] font-semibold text-white">{cur.name}</span>
        </span>
        <ChevronDown className="size-3.5 text-ink-400" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-50 mt-1 w-[300px] rounded-lg border border-ink-700 bg-ink-900 p-1 shadow-[var(--shadow-pop)]">
            {PRODUCTS.map((p) => (
              <button key={p.id} onClick={() => { setOpen(false); nav(p.id === 'renewal' ? '/' : p.nav.find((n) => n.label !== 'Start here')?.to ?? p.base); }}
                className={cx('flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left hover:bg-ink-800', p.id === cur.id && 'bg-ink-800')}>
                <span className={cx('mono mt-0.5 flex size-6 shrink-0 items-center justify-center rounded text-[10.5px] font-bold', p.id === cur.id ? 'bg-accent-500 text-ink-950' : 'bg-ink-700 text-ink-200')}>{p.number}</span>
                <span className="min-w-0 flex-1 leading-tight">
                  <span className="block text-[13px] font-semibold text-white">{p.name}</span>
                  <span className="block text-[11.5px] text-ink-400">{p.tagline}</span>
                </span>
                {p.id === cur.id && <Check className="mt-1 size-3.5 text-accent-500" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
