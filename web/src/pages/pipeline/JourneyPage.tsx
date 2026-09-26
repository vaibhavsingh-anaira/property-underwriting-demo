// Workflow player — presenter mode. Narrates each step (voice + captions), moves a visible
// cursor to what it acts on, clicks, runs the step against the real engine, shows the result.
// Play / Pause / Resume / Stop / Step / Restart, pace and voice controls.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Circle, CircleDot, Pause, Play, RotateCcw, SkipForward, Square, Loader2, Keyboard, Volume2, VolumeX, Captions, FileText, Printer } from 'lucide-react';
import { Info } from '@/help/Info';
import { usePlaybook, usePlaybooks, useStage, useStartPlaybook, useStepPlaybook } from '@/api/client';
import type { Playbook } from '@/api/types';
import { Page, Loading, ErrorBox, Badge, Select, cx } from '@/components/ui';
import { useGhostCursor } from '@/components/GhostCursor';
import { cancelSpeech, defaultVoice, listVoices, onVoicesChanged, readMs, sentences, speakOne } from '@/lib/narrator';
import { fmtDate } from '@/lib/format';
import { StageWorkspace } from './StageWorkspace';
import { productById, useProduct } from '@/products';

type PlayState = 'idle' | 'playing' | 'paused' | 'stopped' | 'completed';
class Abort extends Error {}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const lsGet = (k: string, d: string) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* ignore */ } };

export default function JourneyPage() {
  const [sp, setSp] = useSearchParams();
  const product = useProduct();
  const { data: all } = usePlaybooks(product.id);
  const pbId = sp.get('pb') ?? all?.find((p) => !p.id.startsWith('lifecycle-'))?.id ?? '';
  const { data: pb, error } = usePlaybook(pbId);
  const start = useStartPlaybook();
  const step = useStepPlaybook();
  const cursor = useGhostCursor();

  const [state, setStateUI] = useState<PlayState>('idle');
  const [focus, setFocus] = useState<number | null>(null);
  const [caption, setCaption] = useState<{ title: string; text: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pace, setPace] = useState(() => parseFloat(lsGet('uwc.pace', '0.7')));
  const [voiceOn, setVoiceOn] = useState(() => lsGet('uwc.voice', '1') === '1');
  const [captionsOn, setCaptionsOn] = useState(true);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voiceName, setVoiceName] = useState(() => lsGet('uwc.voiceName', ''));
  const [rate, setRate] = useState(() => parseFloat(lsGet('uwc.rate', '0.95')));

  const ctl = useRef({ state: 'idle' as PlayState, token: 0, alive: false, introDone: false });
  const pbRef = useRef<Playbook | undefined>(undefined);
  const opts = useRef({ pace, voiceOn, rate, voice: undefined as SpeechSynthesisVoice | undefined });
  useEffect(() => { pbRef.current = pb; }, [pb]);
  useEffect(() => {
    const load = () => setVoices(listVoices());
    load();
    return onVoicesChanged(load);
  }, []);
  const voice = useMemo(() => voices.find((v) => v.name === voiceName) ?? defaultVoice(voices), [voices, voiceName]);
  useEffect(() => { opts.current = { pace, voiceOn, rate, voice }; cursor.setPace(pace); lsSet('uwc.pace', String(pace)); lsSet('uwc.rate', String(rate)); lsSet('uwc.voice', voiceOn ? '1' : '0'); if (voice) lsSet('uwc.voiceName', voice.name); }, [pace, voiceOn, rate, voice, cursor]);

  const setState = (s: PlayState) => { ctl.current.state = s; setStateUI(s); };
  useEffect(() => () => { cancelSpeech(); cursor.hide(); ctl.current.token++; }, [cursor]);
  useEffect(() => { stopAll('idle'); setFocus(null); setErr(null); ctl.current.introDone = false; }, [pbId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ------------------------------------------------------------------ sequencer primitives
  const gate = async (token: number) => {
    while (ctl.current.state === 'paused' && ctl.current.token === token) await sleep(120);
    if (ctl.current.token !== token || ctl.current.state === 'stopped' || ctl.current.state === 'idle') throw new Abort();
  };
  const hold = async (ms: number, token: number) => { for (let t = 0; t < ms; t += 100) { await gate(token); await sleep(100); } };
  const narrate = async (title: string, text: string, token: number) => {
    for (const s of sentences(text)) {
      for (;;) {
        await gate(token);
        setCaption({ title, text: s });
        const o = opts.current;
        if (!o.voiceOn || !window.speechSynthesis) { await hold(readMs(s, o.pace), token); break; }
        const ok = await speakOne(s, { voice: o.voice, rate: o.rate });
        if (ok) { await hold(220 / o.pace, token); break; }
        // interrupted by pause → the same sentence is repeated after resume; by stop → gate throws
      }
    }
  };
  const exists = (sel: string) => !!document.querySelector(sel);
  const waitFor = async (sel: string, token: number, ms = 6000) => { for (let t = 0; t < ms && !exists(sel); t += 100) { await gate(token); await sleep(100); } };

  const playStep = async (token: number) => {
    const cur = pbRef.current;
    if (!cur) return false;
    const i = cur.progress;
    if (i >= cur.steps.length) return false;
    const st = cur.steps[i];
    setFocus(i);
    await waitFor(`[data-stage="${st.code}"]`, token);
    await gate(token);
    await cursor.moveTo(`[data-demo-step="${i}"]`, `Step ${i + 1} of ${cur.steps.length}`);
    await hold(450 / opts.current.pace, token);
    const isAction = st.action !== 'view';
    const target = isAction ? '[data-demo="pb-action"]' : exists('[data-demo="table-0"]') ? '[data-demo="table-0"]' : '[data-demo="headline"]';
    await cursor.moveTo(target, isAction ? 'Run step' : 'Reviewing');
    await narrate(`Step ${i + 1} · ${st.code} ${st.label}`, st.say, token);
    await gate(token);
    if (isAction) await cursor.click();
    const r = await step.mutateAsync(cur.id);
    pbRef.current = r;
    await sleep(650);
    await cursor.moveTo('[data-demo="headline"]', 'Result');
    const live = r.steps[i]?.then_say;
    if (live) await narrate(`Result · live from the engine`, live, token);
    await hold((live ? 1200 : 2400) / opts.current.pace, token);
    return !r.done;
  };

  const drain = async () => { for (let i = 0; i < 100 && ctl.current.alive; i++) await sleep(100); };
  const runLoop = async (token: number, once = false) => {
    await drain();
    if (ctl.current.alive || ctl.current.token !== token) return;
    ctl.current.alive = true;
    try {
      const cur = pbRef.current;
      if (cur && cur.progress === 0 && !ctl.current.introDone && !once) {
        setFocus(0);
        await waitFor('[data-demo="system"]', token);
        await cursor.moveTo('[data-demo="system"]', cur.account_name);
        await narrate(cur.title, cur.intro, token);
        ctl.current.introDone = true;
      }
      let more = true;
      while (more) {
        more = await playStep(token);
        if (once) break;
      }
      const after = pbRef.current;
      if (after?.done && !once) {
        await narrate('Summary', after.outro, token);
        setState('completed');
        cursor.hide();
        setCaption(null);
      } else if (once) {
        if (after?.done) setState('completed'); else setState('paused');
      }
    } catch (e) {
      if (!(e instanceof Abort)) { setErr((e as Error).message); setState('paused'); }
    } finally { ctl.current.alive = false; }
  };

  // ------------------------------------------------------------------ controls
  const stopAll = (to: PlayState) => { ctl.current.token++; cancelSpeech(); setState(to); cursor.hide(); if (to !== 'stopped') setCaption(null); };
  const play = async () => {
    stopAll('idle'); setErr(null); ctl.current.introDone = false;
    const r = await start.mutateAsync(pbId);
    pbRef.current = r;
    const token = ++ctl.current.token;
    setState('playing');
    void runLoop(token);
  };
  const pause = () => { if (ctl.current.state !== 'playing') return; setState('paused'); cancelSpeech(); };
  const resume = () => {
    setErr(null); setFocus(null);
    if (ctl.current.alive && ctl.current.state === 'paused') { setState('playing'); return; }
    cancelSpeech();
    const token = ++ctl.current.token;
    setState('playing');
    void runLoop(token);
  };
  const stop = () => stopAll('stopped');
  const restart = async () => { stopAll('idle'); setErr(null); setFocus(null); ctl.current.introDone = false; const r = await start.mutateAsync(pbId); pbRef.current = r; };
  const stepOnce = async () => {
    if (ctl.current.alive && ctl.current.state === 'playing') return;
    ctl.current.token++; await drain();
    if (pbRef.current && pbRef.current.progress === 0 && state === 'idle') { const r = await start.mutateAsync(pbId); pbRef.current = r; }
    const token = ++ctl.current.token;
    setState('playing');
    void runLoop(token, true);
  };

  useEffect(() => {
    if (sp.get('autoplay') === '1' && pb && state === 'idle') { sp.delete('autoplay'); setSp(sp, { replace: true }); void play(); }
  }, [pb]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName?.match(/INPUT|TEXTAREA|SELECT/)) return;
      if (e.code === 'Space') { e.preventDefault(); if (state === 'playing') pause(); else if (state === 'paused' || state === 'stopped') resume(); else void play(); }
      if (e.code === 'ArrowRight' && state !== 'playing') void stepOnce();
      if (e.code === 'Escape' && (state === 'playing' || state === 'paused')) stop();
    };
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h);
  });

  // ------------------------------------------------------------------ view
  const viewIdx = focus ?? (pb ? Math.max(0, Math.min(pb.steps.length - 1, pb.progress - (pb.done ? 1 : 0))) : 0);
  const viewStep = pb?.steps[viewIdx];
  const { data: stage, isLoading } = useStage(viewStep?.code, pb?.account_id, pb?.product ?? product.id);
  const grouped = useMemo(() => ({ flows: (all ?? []).filter((p) => !p.id.startsWith('lifecycle-')), life: (all ?? []).filter((p) => p.id.startsWith('lifecycle-')) }), [all]);
  const manualRun = () => { if (!ctl.current.alive) void stepOnce(); };

  return (
    <Page crumbs={<Link to={product.to('/pipeline')} className="hover:underline">{product.name} · Pipeline & mocks</Link>} title="Workflow player"
      subtitle="Presenter mode — narrated walkthroughs of the pipeline against the real engine and the mocks"
      actions={<Info id="player.page" label="About the player" />}>
      {error ? <ErrorBox error={error} /> : !pb ? <Loading /> : (
        <>
          <div className="sticky top-0 z-20 -mx-6 mb-4 border-y border-line bg-surface/95 px-6 py-3 backdrop-blur">
            <div className="flex flex-wrap items-center gap-3">
              <Select value={pbId} disabled={state === 'playing'} onChange={(e) => setSp({ pb: e.target.value })} className="max-w-[400px]">
                <optgroup label="Workflow playbooks">{grouped.flows.map((p) => <option key={p.id} value={p.id}>{p.scenario} · {p.title}</option>)}</optgroup>
                <optgroup label={`All stages, one ${product.subjectLabel.toLowerCase()}`}>{grouped.life.map((p) => <option key={p.id} value={p.id}>{p.scenario} · {p.account_name} — all {p.steps.length} stages</option>)}</optgroup>
              </Select>
              <Controls state={state} busy={start.isPending} done={pb.done} onPlay={play} onPause={pause} onResume={resume} onStop={stop} onStep={stepOnce} onRestart={restart} />
              <StateChip state={state} pb={pb} />
            </div>
            <div className="mt-2.5 flex flex-wrap items-center gap-x-5 gap-y-2">
              <label className="flex items-center gap-2 text-[12px] text-ink-600">
                <span className="font-medium text-ink-800">Pace</span>
                <input type="range" min={0.4} max={1.5} step={0.05} value={pace} onChange={(e) => setPace(parseFloat(e.target.value))} className="w-36 accent-[var(--color-accent-600)]" />
                <span className="num w-[86px] text-ink-500">{pace.toFixed(2)}× {pace <= 0.55 ? '· slow' : pace <= 0.85 ? '· presenter' : pace <= 1.1 ? '· normal' : '· fast'}</span>
              </label>
              <button onClick={() => { setVoiceOn((v) => !v); if (voiceOn) cancelSpeech(); }} className={cx('inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[12px] font-medium', voiceOn ? 'border-accent-100 bg-accent-50 text-accent-700' : 'border-line-strong text-ink-600')}>
                {voiceOn ? <Volume2 className="size-3.5" /> : <VolumeX className="size-3.5" />}{voiceOn ? 'Voiceover on' : 'Voiceover off'}
              </button>
              <Select value={voice?.name ?? ''} onChange={(e) => setVoiceName(e.target.value)} disabled={!voiceOn || !voices.length} className="h-7 max-w-[210px] text-[12px]">
                {voices.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
              </Select>
              <label className="flex items-center gap-2 text-[12px] text-ink-600">
                <span className="font-medium text-ink-800">Voice speed</span>
                <input type="range" min={0.75} max={1.25} step={0.05} value={rate} onChange={(e) => setRate(parseFloat(e.target.value))} disabled={!voiceOn} className="w-24 accent-[var(--color-accent-600)]" />
                <span className="num text-ink-500">{rate.toFixed(2)}×</span>
              </label>
              <button onClick={() => setCaptionsOn((c) => !c)} className={cx('inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[12px] font-medium', captionsOn ? 'border-accent-100 bg-accent-50 text-accent-700' : 'border-line-strong text-ink-600')}><Captions className="size-3.5" />Captions</button>
              <span className="ml-auto hidden items-center gap-1 text-[11px] text-ink-400 xl:flex"><Keyboard className="size-3" />space play/pause · → step · esc stop</span>
            </div>
            <div className="mt-2.5 flex items-center gap-3">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-100"><div className={cx('h-full rounded-full transition-all duration-700', state === 'stopped' ? 'bg-high' : 'bg-accent-500')} style={{ width: `${(pb.progress / pb.steps.length) * 100}%` }} /></div>
              <span className="num text-[12px] text-ink-600">{pb.progress}/{pb.steps.length} steps · demo clock {fmtDate(pb.clock)}</span>
            </div>
            {err && <div className="mt-2 rounded-md bg-crit-bg px-3 py-1.5 text-[12.5px] text-crit">{err} — paused.</div>}
          </div>

          <div className="grid grid-cols-12 gap-4">
            <aside className="col-span-12 lg:col-span-4 xl:col-span-3">
              <div className="rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)]">
                <div className="text-[13px] font-semibold text-ink-950">{pb.title}</div>
                <div className="mt-0.5 text-[12px] text-ink-500">{pb.subject_href ? <Link to={pb.subject_href} className="text-accent-700 hover:underline">{pb.account_name}</Link> : <span>{pb.account_name}</span>} {pb.scenario && <Badge tone="dark">{pb.scenario}</Badge>}</div>
                <div className="mt-2 flex flex-wrap gap-1">{pb.aspects.map((a) => <Badge key={a} tone="accent">{a}</Badge>)}</div>
                <div className="mt-3 space-y-0.5">
                  {pb.steps.map((s) => {
                    const running = step.isPending && s.index === pb.progress;
                    const Icon = running ? Loader2 : s.status === 'DONE' ? CheckCircle2 : s.status === 'CURRENT' ? CircleDot : Circle;
                    return (
                      <button key={s.index} data-demo-step={s.index} onClick={() => { setFocus(s.index); pause(); }}
                        className={cx('flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left', viewIdx === s.index ? 'bg-accent-50 ring-1 ring-accent-100' : 'hover:bg-ink-50')}>
                        <Icon className={cx('mt-0.5 size-4 shrink-0', running && 'animate-spin', s.status === 'DONE' ? 'text-ok' : s.status === 'CURRENT' ? 'text-accent-600' : 'text-ink-300')} />
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-1.5"><span className="mono text-[10.5px] text-ink-400">{s.code}</span><span className="text-[12.5px] font-medium text-ink-900">{s.label}</span></span>
                          {s.result && <span className="block text-[11.5px] leading-snug text-ink-500">{s.result}</span>}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <BriefPanel pb={pb} />
            </aside>
            <section className="col-span-12 lg:col-span-8 xl:col-span-9">
              {isLoading || !stage || !viewStep ? <Loading /> : (
                <StageWorkspace v={stage} action={{
                  label: viewStep.label,
                  description: viewStep.result ? `Result: ${viewStep.result}` : viewStep.action === 'view' ? 'Review step — nothing is changed' : 'Runs this step against the engine and the mocks',
                  onRun: manualRun, running: step.isPending, done: viewStep.status === 'DONE', kind: viewStep.action === 'view' ? 'view' : 'action',
                }} />
              )}
            </section>
          </div>

          {captionsOn && caption && (state === 'playing' || state === 'paused') && (
            <div className="pointer-events-none fixed bottom-6 z-[60] w-[min(880px,calc(100vw-280px))]" style={{ left: 'calc(50% + 108px)', transform: 'translateX(-50%)' }}>
              <div key={caption.text} className="caption-in rounded-xl bg-ink-950/92 px-5 py-3 text-center shadow-[var(--shadow-pop)] ring-1 ring-white/10">
                <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.1em] text-accent-500">{caption.title}{state === 'paused' && ' · paused'}</div>
                <div className="text-[16px] leading-snug text-white">{caption.text}</div>
              </div>
            </div>
          )}
        </>
      )}
    </Page>
  );
}

function Controls({ state, busy, done, onPlay, onPause, onResume, onStop, onStep, onRestart }: {
  state: PlayState; busy: boolean; done: boolean; onPlay: () => void; onPause: () => void; onResume: () => void; onStop: () => void; onStep: () => void; onRestart: () => void;
}) {
  const B = ({ onClick, icon, children, primary, disabled }: { onClick: () => void; icon: React.ReactNode; children: React.ReactNode; primary?: boolean; disabled?: boolean }) => (
    <button onClick={onClick} disabled={disabled} className={cx('inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[13px] font-medium disabled:opacity-40',
      primary ? 'border-accent-600 bg-accent-600 text-white hover:bg-accent-700' : 'border-line-strong bg-surface text-ink-800 hover:bg-ink-50')}>{icon}{children}</button>
  );
  return (
    <div className="flex items-center gap-1.5">
      {(state === 'idle' || state === 'completed') && <B primary onClick={onPlay} icon={<Play className="size-3.5" />} disabled={busy}>{state === 'completed' ? 'Replay' : 'Play'}</B>}
      {state === 'playing' && <B primary onClick={onPause} icon={<Pause className="size-3.5" />}>Pause</B>}
      {(state === 'paused' || state === 'stopped') && <B primary onClick={onResume} icon={<Play className="size-3.5" />} disabled={busy || done}>Resume</B>}
      {(state === 'playing' || state === 'paused') && <B onClick={onStop} icon={<Square className="size-3.5" />}>Stop</B>}
      {state !== 'playing' && <B onClick={onStep} icon={<SkipForward className="size-3.5" />} disabled={busy || done}>Step</B>}
      {state !== 'playing' && <B onClick={onRestart} icon={<RotateCcw className="size-3.5" />} disabled={busy}>Restart</B>}
    </div>
  );
}

function StateChip({ state, pb }: { state: PlayState; pb: Playbook }) {
  const m = {
    idle: { t: 'Ready — Play runs a clean, narrated pass from 1 Aug 2026', c: 'bg-ink-100 text-ink-700' },
    playing: { t: 'Playing', c: 'bg-accent-50 text-accent-700' },
    paused: { t: `Paused at step ${Math.min(pb.progress + 1, pb.steps.length)}`, c: 'bg-med-bg text-med' },
    stopped: { t: `Stopped after step ${pb.progress} — state kept; Resume or Restart`, c: 'bg-high-bg text-high' },
    completed: { t: 'Completed', c: 'bg-ok-bg text-ok' },
  }[state];
  return <span className={cx('inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium', m.c)}>{state === 'playing' && <span className="pulse-ring inline-block size-2 rounded-full bg-accent-500" />}{m.t}</span>;
}

function BriefPanel({ pb }: { pb: Playbook }) {
  const [tab, setTab] = useState<'brief' | 'facts'>('brief');
  const b = pb.brief;
  const L = ({ h, items }: { h: string; items?: string[] }) => items && items.length ? (
    <div className="mb-2.5"><div className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-[.08em] text-ink-500">{h}</div>
      <ul className="list-disc space-y-0.5 pl-4 text-[12px] leading-snug text-ink-800">{items.map((x) => <li key={x}>{x}</li>)}</ul></div>) : null;
  const P = ({ h, t }: { h: string; t?: string }) => t ? (
    <div className="mb-2.5"><div className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-[.08em] text-ink-500">{h}</div><div className="text-[12px] leading-snug text-ink-800">{t}</div></div>) : null;
  return (
    <div className="mt-3 rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)]">
      <div className="mb-2 flex items-center gap-1.5">
        <FileText className="size-3.5 text-accent-600" />
        {(['brief', 'facts'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={cx('rounded-md px-2 py-0.5 text-[12px] font-medium', tab === t ? 'bg-accent-50 text-accent-700' : 'text-ink-500 hover:text-ink-800')}>{t === 'brief' ? 'Client brief' : 'Live facts'}</button>
        ))}
        <Info id="player.brief" className="ml-1" />
        <Link to={productById(pb.product).base + `/pipeline/brief/${pb.id}`} target="_blank" className="ml-auto inline-flex items-center gap-1 text-[11.5px] font-medium text-accent-700 hover:underline"><Printer className="size-3" />Printable</Link>
      </div>
      {tab === 'brief' ? (
        <div>
          <P h="Who it's for" t={b.audience} />
          <P h="Business problem" t={b.problem} />
          <L h="What happens" items={b.story} />
          <L h="Point at" items={b.watch} />
          <P h="Value shown" t={b.value} />
          <L h="Real (the product)" items={b.real} />
          <L h="Stand-ins (mocked systems)" items={b.mocked} />
          <L h="Questions to ask the client" items={b.questions} />
        </div>
      ) : (
        <div>
          <div className="mb-2 text-[11.5px] text-ink-500">Computed by the engine for this account right now — changes as the playbook runs.</div>
          <dl className="space-y-1">{pb.facts.map((f) => (
            <div key={f.label} className="grid grid-cols-[130px_1fr] gap-2 text-[12px]"><dt className="text-ink-500">{f.label}</dt><dd className="num text-ink-900">{f.value}</dd></div>
          ))}</dl>
        </div>
      )}
    </div>
  );
}
