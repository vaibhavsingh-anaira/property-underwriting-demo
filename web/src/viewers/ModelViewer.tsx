// GLB viewer (react-three-fiber). Scene units are metres. Nodes carry glTF extras (→ userData).
// Hover → tooltip with extras; click → select + onSelectNode; colorBy recolours by node name;
// nodes named *PLANE* or with extras.transparent render translucent (toggleable).
import { Component, Fragment, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { Grid, Html, OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { Box, Eye, EyeOff, Grid3x3, Layers, RotateCcw, Square, Tag } from 'lucide-react';
import { cx, Loading } from '@/components/ui';
import { usd } from '@/lib/format';
import { cssSize } from './util';

export interface ModelViewerProps { url: string; colorBy?: Record<string, string>; highlightNode?: string | null; onSelectNode?: (node: string, extras: Record<string, unknown>) => void; height?: number | string; legend?: { color: string; label: string }[] }

type View = 'iso' | 'top' | 'front';
type Extras = Record<string, unknown>;
const FT = 0.3048;
const ACCENT = new THREE.Color('#13a3a3');

const meaningful = (u: Extras | undefined) => !!u && Object.keys(u).some((k) => !k.startsWith('__') && k !== 'transparent' && k !== 'name');
const isTranslucentNode = (o: THREE.Object3D) => /PLANE/i.test(o.name) || o.userData?.transparent === true;

/** Nearest ancestor (inclusive) that carries meaningful extras — the "selectable" node. */
function pickTarget(o: THREE.Object3D | null, root: THREE.Object3D): THREE.Object3D | null {
  let cur: THREE.Object3D | null = o;
  while (cur && cur !== root) { if (meaningful(cur.userData)) return cur; cur = cur.parent; }
  return o && o !== root ? o : null;
}
function chainNames(o: THREE.Object3D, root: THREE.Object3D) { const n: string[] = []; let c: THREE.Object3D | null = o; while (c && c !== root) { n.push(c.name); c = c.parent; } return n; }
function isVisibleChain(o: THREE.Object3D) { let c: THREE.Object3D | null = o; while (c) { if (!c.visible) return false; c = c.parent; } return true; }

export function ModelViewer({ url, colorBy, highlightNode, onSelectNode, height = 480, legend }: ModelViewerProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [hover, setHover] = useState<{ name: string; extras: Extras } | null>(null);
  const [wire, setWire] = useState(false);
  const [showTranslucent, setShowTranslucent] = useState(true);
  const [labels, setLabels] = useState(false);
  const [grid, setGrid] = useState(true);
  const [info, setInfo] = useState<{ size: THREE.Vector3; nodes: number; translucent: number } | null>(null);
  const [view, setView] = useState<{ v: View; n: number }>({ v: 'iso', n: 0 });
  const tip = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => { setInfo(null); setSelected(null); }, [url]);

  return (
    <div ref={box} className="relative overflow-hidden bg-[linear-gradient(180deg,#f7f9fb_0%,#e9edf2_100%)]" style={{ height: cssSize(height, 480) }}
      onPointerMove={(e) => {
        const r = box.current?.getBoundingClientRect(); const t = tip.current; if (!r || !t) return;
        const x = e.clientX - r.left, y = e.clientY - r.top;
        const flip = x > r.width - 280;
        t.style.transform = `translate(${flip ? x - 14 - t.offsetWidth : x + 14}px, ${Math.min(y + 14, r.height - t.offsetHeight - 8)}px)`;
      }}>
      <ModelErrorBoundary key={url}>
        <Canvas shadows dpr={[1, 2]} camera={{ fov: 35, position: [120, 90, 140], near: 0.5, far: 20000 }} gl={{ antialias: true }}
          onPointerMissed={() => setSelected(null)}>
          <Suspense fallback={null}>
            <Scene url={url} colorBy={colorBy} selected={selected} highlightNode={highlightNode ?? null} hovered={hover?.name ?? null}
              onHover={setHover} onPick={(n, x) => { setSelected(n); onSelectNode?.(n, x); }}
              wire={wire} showTranslucent={showTranslucent} labels={labels} grid={grid} view={view} onInfo={setInfo} />
          </Suspense>
        </Canvas>
      </ModelErrorBoundary>
      {!info && <div className="pointer-events-none absolute inset-0 flex items-center justify-center"><Loading label="Loading 3D model…" /></div>}

      {/* toolbar */}
      <div className="absolute right-2.5 top-2.5 flex items-center gap-0.5 rounded-lg border border-line bg-surface/95 p-0.5 shadow-[var(--shadow-card)] backdrop-blur">
        <TB title="Reset view" onClick={() => setView((p) => ({ v: 'iso', n: p.n + 1 }))}><RotateCcw className="size-3.5" /></TB>
        <TB title="Isometric" active={view.v === 'iso'} onClick={() => setView((p) => ({ v: 'iso', n: p.n + 1 }))}><Box className="size-3.5" /></TB>
        <TB title="Top view" active={view.v === 'top'} onClick={() => setView((p) => ({ v: 'top', n: p.n + 1 }))}><Square className="size-3.5" /></TB>
        <span className="mx-0.5 h-4 w-px bg-line" />
        <TB title="Wireframe" active={wire} onClick={() => setWire((w) => !w)}><Layers className="size-3.5" /></TB>
        <TB title="Labels" active={labels} onClick={() => setLabels((w) => !w)}><Tag className="size-3.5" /></TB>
        <TB title="Grid (10 ft)" active={grid} onClick={() => setGrid((w) => !w)}><Grid3x3 className="size-3.5" /></TB>
        {info && info.translucent > 0 && (
          <TB title={showTranslucent ? 'Hide translucent (design planes, shells)' : 'Show translucent'} active={showTranslucent} onClick={() => setShowTranslucent((w) => !w)}>
            {showTranslucent ? <Eye className="size-3.5" /> : <EyeOff className="size-3.5" />}
          </TB>
        )}
      </div>

      {/* legend + scale */}
      <div className="pointer-events-none absolute bottom-2.5 left-2.5 flex flex-col gap-1.5">
        {legend && legend.length > 0 && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line bg-surface/95 px-2.5 py-1.5 text-[11px] text-ink-600 shadow-[var(--shadow-card)]">
            {legend.map((l) => <span key={l.label} className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-[3px]" style={{ background: l.color }} />{l.label}</span>)}
          </div>
        )}
        {info && (
          <div className="num w-fit rounded-md bg-ink-950/70 px-2 py-1 text-[10.5px] text-ink-100 backdrop-blur">
            {info.nodes} nodes · {Math.round(info.size.x / FT)} × {Math.round(info.size.z / FT)} ft footprint · {Math.round(info.size.y / FT)} ft tall{grid ? ' · grid 10 ft' : ''}
          </div>
        )}
      </div>

      {/* hover tooltip */}
      <div ref={tip} className={cx('pointer-events-none absolute left-0 top-0 z-10 w-[260px] rounded-lg border border-line bg-surface/97 p-2.5 shadow-[var(--shadow-pop)] transition-opacity duration-100', hover ? 'opacity-100' : 'opacity-0')}>
        {hover && <ExtrasCard name={hover.name} extras={hover.extras} />}
      </div>
    </div>
  );
}

function TB({ children, active, ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return <button {...p} className={cx('inline-flex size-7 items-center justify-center rounded-md transition-colors', active ? 'bg-accent-50 text-accent-700' : 'text-ink-600 hover:bg-ink-100')}>{children}</button>;
}

const EXTRA_LABEL: Record<string, string> = { stories: 'Stories', construction: 'Construction', occupancy: 'Occupancy', tiv: 'TIV', roof_year: 'Roof year', height_ft: 'Height', commodity: 'Commodity', levels: 'Levels', design: 'Design', sprinkler: 'Sprinkler' };
function fmtExtra(k: string, v: unknown) {
  if (k === 'tiv' && typeof v === 'number') return usd(v);
  if (k.endsWith('_ft') && typeof v === 'number') return `${v} ft`;
  return String(v);
}
function ExtrasCard({ name, extras }: { name: string; extras: Extras }) {
  const rows = Object.entries(extras).filter(([k]) => !['label', 'flag', 'transparent', 'name'].includes(k) && !k.startsWith('__'));
  return (
    <div className="text-[12px]">
      <div className="flex items-start justify-between gap-2">
        <div className="font-semibold leading-snug text-ink-950">{String(extras.label ?? name)}</div>
        <span className="mono shrink-0 rounded bg-ink-100 px-1 text-[10.5px] text-ink-600">{name}</span>
      </div>
      {extras.flag ? <div className="mt-1.5 rounded-md border border-[#f6c5cc] bg-crit-bg px-2 py-1 text-[11px] font-medium leading-snug text-crit">{String(extras.flag)}</div> : null}
      {rows.length > 0 && (
        <div className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
          {rows.map(([k, v]) => <Fragment key={k}><span className="text-ink-500">{EXTRA_LABEL[k] ?? k.replace(/_/g, ' ')}</span><span className="num text-right text-ink-900">{fmtExtra(k, v)}</span></Fragment>)}
        </div>
      )}
    </div>
  );
}

class ModelErrorBoundary extends Component<{ children: ReactNode }, { err: Error | null }> {
  state = { err: null as Error | null };
  static getDerivedStateFromError(err: Error) { return { err }; }
  render() {
    if (this.state.err) return <div className="flex h-full items-center justify-center px-6 text-center text-[13px] text-ink-500">Could not load 3D model — {this.state.err.message}</div>;
    return this.props.children;
  }
}

// ------------------------------------------------------------------ scene
/** Distance along `dir` at which the box's farthest projected corner reaches ~97% of the viewport (iterative projection). */
function fitDistance(camera: THREE.PerspectiveCamera, box: THREE.Box3, center: THREE.Vector3, dir: THREE.Vector3, radius: number) {
  const cam = camera.clone();
  const corners = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
  let d = radius / Math.tan(THREE.MathUtils.degToRad(cam.fov / 2));
  for (let k = 0; k < 4; k++) {
    cam.position.copy(center).addScaledVector(dir, d); cam.up.set(0, 1, 0); cam.lookAt(center); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
    let m = 0; for (const c of corners) { const p = c.clone().project(cam); m = Math.max(m, Math.abs(p.x), Math.abs(p.y)); }
    d *= Math.min(3, Math.max(0.3, m / 0.97));
  }
  return d;
}

function Scene({ url, colorBy, selected, highlightNode, hovered, onHover, onPick, wire, showTranslucent, labels, grid, view, onInfo }: {
  url: string; colorBy?: Record<string, string>; selected: string | null; highlightNode: string | null; hovered: string | null;
  onHover: (h: { name: string; extras: Extras } | null) => void; onPick: (n: string, x: Extras) => void;
  wire: boolean; showTranslucent: boolean; labels: boolean; grid: boolean; view: { v: View; n: number }; onInfo: (i: { size: THREE.Vector3; nodes: number; translucent: number }) => void;
}) {
  const gltf = useGLTF(url, false);
  const { camera, controls } = useThree() as unknown as { camera: THREE.PerspectiveCamera; controls: OrbitControlsImpl | null };

  const model = useMemo(() => {
    const root = gltf.scene.clone(true);
    const meshes: THREE.Mesh[] = [];
    let translucent = 0;
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const tgt = pickTarget(m, root);
      let trans = false; let c: THREE.Object3D | null = m;
      while (c && c !== root) { if (isTranslucentNode(c)) { trans = true; break; } c = c.parent; }
      const mats = (Array.isArray(m.material) ? m.material : [m.material]).map((mt) => {
        const cl = (mt as THREE.MeshStandardMaterial).clone();
        cl.userData.__base = cl.color.clone();
        if (trans) { cl.transparent = true; cl.opacity = Math.min(cl.opacity < 1 ? cl.opacity * 1.3 : 0.3, 0.4); cl.depthWrite = false; cl.side = THREE.DoubleSide; }
        return cl;
      });
      m.material = Array.isArray(m.material) ? mats : mats[0];
      m.castShadow = !trans; m.receiveShadow = true;
      m.userData.__target = tgt?.name ?? m.name;
      m.userData.__chain = chainNames(m, root);
      m.userData.__trans = trans;
      if (trans) { translucent++; m.renderOrder = 2; }
      meshes.push(m);
    });
    root.updateMatrixWorld(true);
    const bbox = new THREE.Box3().setFromObject(root);
    const size = bbox.getSize(new THREE.Vector3()), center = bbox.getCenter(new THREE.Vector3());
    // top-level labelled nodes: meaningful extras, no labelled ancestor
    const tops: { name: string; label: string; pos: THREE.Vector3; flag: boolean }[] = [];
    root.traverse((o) => {
      if (!meaningful(o.userData) || /PLANE/i.test(o.name)) return;
      let p = o.parent; while (p && p !== root) { if (meaningful(p.userData)) return; p = p.parent; }
      const b = new THREE.Box3().setFromObject(o);
      const c = b.getCenter(new THREE.Vector3());
      tops.push({ name: o.name, label: String(o.userData.label ?? o.name), pos: new THREE.Vector3(c.x, b.max.y + size.y * 0.04 + 1, c.z), flag: !!o.userData.flag });
    });
    let labelled = 0; root.traverse((o) => { if (meaningful(o.userData)) labelled++; });
    return { root, meshes, bbox, size, center, radius: Math.max(1, size.length() / 2), tops, translucent, labelled };
  }, [gltf.scene]);

  useEffect(() => { onInfo({ size: model.size, nodes: model.labelled, translucent: model.translucent }); }, [model]); // eslint-disable-line react-hooks/exhaustive-deps

  // appearance
  useEffect(() => {
    const focus = selected ?? highlightNode;
    for (const m of model.meshes) {
      const chain = m.userData.__chain as string[];
      const colorKey = colorBy ? chain.find((n) => colorBy[n]) : undefined;
      const isFocus = !!focus && chain.includes(focus);
      const isHover = !!hovered && chain.includes(hovered);
      const trans = m.userData.__trans as boolean;
      m.visible = !trans || showTranslucent;
      for (const mt of (Array.isArray(m.material) ? m.material : [m.material]) as THREE.MeshStandardMaterial[]) {
        const base = mt.userData.__base as THREE.Color;
        mt.color.copy(colorKey && !trans ? new THREE.Color(colorBy![colorKey]) : base);
        if (!trans && (isFocus || isHover)) mt.color.lerp(ACCENT, isFocus ? 0.55 : 0.25);
        mt.emissive.copy(ACCENT);
        mt.emissiveIntensity = isFocus ? 0.22 : isHover ? 0.08 : 0;
        mt.wireframe = wire && !trans;
      }
    }
  }, [model, colorBy, selected, highlightNode, hovered, wire, showTranslucent]);

  // camera views (animated)
  const anim = useRef<{ from: THREE.Vector3; to: THREE.Vector3; tFrom: THREE.Vector3; tTo: THREE.Vector3; t: number } | null>(null);
  const first = useRef(true);
  useEffect(() => {
    const { center, radius, bbox } = model;
    const dir = (view.v === 'top' ? new THREE.Vector3(0, 1, 0.001) : view.v === 'front' ? new THREE.Vector3(0, 0.25, 1) : new THREE.Vector3(0.9, 0.75, 1.15)).normalize();
    const dist = fitDistance(camera, bbox, center, dir, radius);
    const to = center.clone().add(dir.clone().multiplyScalar(dist));
    camera.near = Math.max(0.05, radius / 200); camera.far = radius * 40; camera.updateProjectionMatrix();
    if (first.current || !controls) {
      camera.position.copy(to); camera.lookAt(center);
      if (controls) { controls.target.copy(center); controls.update(); first.current = false; }
    } else {
      anim.current = { from: camera.position.clone(), to, tFrom: controls.target.clone(), tTo: center.clone(), t: 0 };
    }
    if (controls) { controls.maxDistance = dist * 4; controls.minDistance = radius * 0.08; }
  }, [model, view, controls, camera]);
  useFrame((_, dt) => {
    const a = anim.current; if (!a || !controls) return;
    a.t = Math.min(1, a.t + dt / 0.55);
    const k = 1 - Math.pow(1 - a.t, 3);
    camera.position.lerpVectors(a.from, a.to, k);
    controls.target.lerpVectors(a.tFrom, a.tTo, k);
    controls.update();
    if (a.t >= 1) anim.current = null;
  });

  // picking: prefer opaque hits; translucent only if nothing opaque is under the cursor
  const resolve = (e: ThreeEvent<PointerEvent | MouseEvent>) => {
    const hits = e.intersections.filter((h) => isVisibleChain(h.object) && (h.object as THREE.Mesh).isMesh);
    const hit = hits.find((h) => !h.object.userData.__trans) ?? hits[0];
    if (!hit) return null;
    const tgt = pickTarget(hit.object, model.root);
    return tgt ? { name: tgt.name, extras: Object.fromEntries(Object.entries(tgt.userData).filter(([k]) => k !== 'name' && !k.startsWith('__'))) as Extras } : null;
  };
  const lastHover = useRef<string | null>(null);

  const selObj = selected ? model.root.getObjectByName(selected) : null;
  const selBox = useMemo(() => (selObj ? new THREE.Box3().setFromObject(selObj) : null), [selObj]);
  const { center, size, radius, bbox } = model;

  return (
    <>
      <hemisphereLight args={['#ffffff', '#aeb6c4', 1.15]} />
      <ambientLight intensity={0.25} />
      <directionalLight position={[center.x + radius * 0.8, center.y + radius * 1.6, center.z + radius * 0.5]} intensity={1.9} castShadow
        shadow-mapSize={[2048, 2048]} shadow-bias={-0.0004} shadow-normalBias={0.02}
        shadow-camera-left={-radius * 1.2} shadow-camera-right={radius * 1.2} shadow-camera-top={radius * 1.2} shadow-camera-bottom={-radius * 1.2}
        shadow-camera-near={0.5} shadow-camera-far={radius * 5}>
        <object3D attach="target" position={[center.x, bbox.min.y, center.z]} />
      </directionalLight>
      <directionalLight position={[center.x - radius, center.y + radius * 0.6, center.z - radius * 0.8]} intensity={0.45} />
      <primitive object={model.root}
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          const r = resolve(e);
          if ((r?.name ?? null) !== lastHover.current) { lastHover.current = r?.name ?? null; onHover(r); document.body.style.cursor = r ? 'pointer' : ''; }
        }}
        onPointerOut={() => { lastHover.current = null; onHover(null); document.body.style.cursor = ''; }}
        onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); const r = resolve(e); if (r) onPick(r.name, r.extras); }} />
      <mesh rotation-x={-Math.PI / 2} position={[center.x, bbox.min.y - 0.01, center.z]} receiveShadow>
        <planeGeometry args={[Math.max(size.x, size.z) * 6, Math.max(size.x, size.z) * 6]} />
        <shadowMaterial transparent opacity={0.16} />
      </mesh>
      {grid && (
        <Grid position={[center.x, bbox.min.y + 0.005, center.z]} args={[10, 10]} infiniteGrid cellSize={10 * FT} sectionSize={100 * FT}
          cellThickness={0.6} sectionThickness={1} cellColor="#c9d0db" sectionColor="#9aa4b5" fadeDistance={radius * 5} fadeStrength={2} followCamera={false} />
      )}
      {selBox && <SelectionBox box={selBox} />}
      {labels && model.tops.map((t) => (
        <Html key={t.name} position={t.pos} center zIndexRange={[5, 0]} style={{ pointerEvents: 'none' }}>
          <div className={cx('whitespace-nowrap rounded-md border px-1.5 py-0.5 text-[10.5px] font-medium shadow-sm', t.flag ? 'border-[#f6c5cc] bg-crit-bg text-crit' : 'border-line bg-surface/95 text-ink-800')}>
            <span className="mono mr-1 text-ink-400">{t.name}</span>{t.label}
          </div>
        </Html>
      ))}
      <OrbitControls makeDefault enableDamping dampingFactor={0.12} maxPolarAngle={Math.PI / 2 - 0.02} screenSpacePanning />
    </>
  );
}

function SelectionBox({ box }: { box: THREE.Box3 }) {
  const { geo, pos } = useMemo(() => {
    const b = box.clone().expandByScalar(0.4);
    const size = b.getSize(new THREE.Vector3());
    return { geo: new THREE.EdgesGeometry(new THREE.BoxGeometry(size.x, size.y, size.z)), pos: b.getCenter(new THREE.Vector3()) };
  }, [box]);
  useEffect(() => () => geo.dispose(), [geo]);
  return (
    <lineSegments geometry={geo} position={pos} renderOrder={10}>
      <lineBasicMaterial color="#0e8585" depthTest={false} transparent opacity={0.9} />
    </lineSegments>
  );
}
