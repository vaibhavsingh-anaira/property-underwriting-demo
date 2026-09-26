// Fixtures mode: patches window.fetch for /api/* (VITE_FIXTURES=1). Dev only.
import * as S from './store';

type Handler = (m: RegExpMatchArray, q: URLSearchParams, body: any, uid: string) => unknown; // eslint-disable-line @typescript-eslint/no-explicit-any
const routes: [string, RegExp, Handler][] = [
  ['GET', /^\/users$/, () => S.users()],
  ['GET', /^\/demo\/state$/, () => S.demoState()],
  ['POST', /^\/demo\/reset$/, () => S.reset()],
  ['POST', /^\/demo\/advance$/, (_m, _q, b) => S.advance(b ?? {})],
  ['POST', /^\/demo\/injections$/, (_m, _q, b) => S.setInjections(b ?? {})],
  ['GET', /^\/book$/, () => S.book()],
  ['GET', /^\/renewals$/, (_m, q) => S.renewals(q)],
  ['GET', /^\/accounts\/([^/]+)$/, (m) => S.account(m[1])],
  ['GET', /^\/accounts\/([^/]+)\/fields$/, (m, q) => S.fields(m[1], q.get('subject_id'))],
  ['GET', /^\/observations\/([^/]+)$/, (m) => S.observation(decodeURIComponent(m[1]))],
  ['GET', /^\/accounts\/([^/]+)\/rarc$/, (m) => S.rarc(m[1])],
  ['POST', /^\/accounts\/([^/]+)\/rarc\/whatif$/, (m, _q, b) => S.rarc(m[1], b)],
  ['GET', /^\/accounts\/([^/]+)\/contract$/, (m) => S.contract(m[1])],
  ['GET', /^\/accounts\/([^/]+)\/cat$/, (m) => S.cat(m[1])],
  ['GET', /^\/accounts\/([^/]+)\/claims-engineering$/, (m) => S.claims(m[1])],
  ['POST', /^\/findings\/([^/]+)\/disposition$/, (m, _q, b, u) => S.disposition(m[1], b, u)],
  ['POST', /^\/accounts\/([^/]+)\/quotes$/, (m, _q, b, u) => S.createQuote(m[1], b, u)],
  ['POST', /^\/accounts\/([^/]+)\/quotes\/([^/]+)\/send$/, (m, _q, _b, u) => S.sendQuote(m[1], m[2], u)],
  ['POST', /^\/accounts\/([^/]+)\/referrals$/, (m, _q, b, u) => S.createReferral(m[1], b, u)],
  ['GET', /^\/referrals$/, (_m, q) => S.referrals(q.get('status'))],
  ['POST', /^\/referrals\/([^/]+)\/decision$/, (m, _q, b, u) => S.decideReferral(m[1], b, u)],
  ['POST', /^\/accounts\/([^/]+)\/data-request$/, (m, _q, b, u) => S.dataRequest(m[1], b.items, u)],
  ['POST', /^\/accounts\/([^/]+)\/bind$/, (m, _q, b, u) => S.bind(m[1], b.quote_id, u)],
  ['POST', /^\/accounts\/([^/]+)\/issue$/, (m, _q, _b, u) => S.issue(m[1], u)],
  ['POST', /^\/accounts\/([^/]+)\/confirm$/, (m, _q, _b, u) => S.confirmMaintain(m[1], u)],
  ['GET', /^\/documents$/, (_m, q) => S.documents(q)],
  ['GET', /^\/documents\/([^/]+)$/, (m) => S.documentMeta(m[1])],
  ['GET', /^\/documents\/([^/]+)\/xlsx$/, (m) => S.xlsx(m[1])],
  ['GET', /^\/documents\/([^/]+)\/eml$/, (m) => S.eml(m[1])],
  ['GET', /^\/documents\/([^/]+)\/extraction$/, (m) => S.extraction(m[1])],
  ['GET', /^\/rules$/, () => S.rules()],
  ['GET', /^\/rules\/([^/]+)$/, (m) => S.rule(m[1])],
  ['POST', /^\/rules\/([^/]+)\/test$/, (m, _q, b) => S.ruleTest(m[1], b.yaml)],
  ['POST', /^\/rules\/([^/]+)\/backtest$/, (m, _q, b) => S.ruleBacktest(m[1], b.yaml)],
  ['POST', /^\/rules\/([^/]+)\/publish$/, (m, _q, b) => S.rulePublish(m[1], b.yaml)],
  ['GET', /^\/data-quality$/, () => S.dataQuality()],
  ['POST', /^\/data-quality\/review\/([^/]+)$/, (m, _q, b, u) => S.matchDecision(m[1], b, u)],
  ['GET', /^\/portfolio\/accumulation$/, () => S.accumulation()],
  ['GET', /^\/geo\/hazards$/, () => S.hazards()],
  ['GET', /^\/pipeline$/, () => S.pipeline()],
  ['GET', /^\/mocks\/systems$/, () => S.mockSystems()],
  ['GET', /^\/mocks\/outbox$/, () => S.outbox()],
  ['GET', /^\/search$/, (_m, q) => S.search(q.get('q') ?? '')],
];

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });

export function installMockApi() {
  const real = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, location.origin);
    if (!url.pathname.startsWith('/api/')) return real(input, init);
    const path = url.pathname.slice(4);
    const method = (init?.method ?? 'GET').toUpperCase();
    const uid = (init?.headers as Record<string, string> | undefined)?.['X-User-Id'] ?? 'u_maya';
    await new Promise((r) => setTimeout(r, 80 + Math.random() * 120));
    const raw = /^\/documents\/([^/]+)\/raw$/.exec(path);
    if (raw) {
      const txt = S.rawText(raw[1]);
      if (txt !== null) return new Response(txt, { headers: { 'content-type': 'text/plain' } });
      const meta = S.documentMeta(raw[1], false);
      const f = meta?.format;
      const sample = f === 'pdf' ? 'declarations.pdf' : f === 'glb' ? (meta!.filename.includes('campus') ? 'campus.glb' : 'warehouse.glb') : f === 'png' ? (/20(2[0-4]|1)/.test(meta!.filename) ? 'aerial_2021.png' : 'aerial_2025.png') : f === 'csv' ? 'oed_locations.csv' : f === 'json' ? 'ep_curve.json' : null;
      return sample ? real(`/samples/${sample}`) : json({ detail: 'No raw content' }, 404);
    }
    for (const [m, re, h] of routes) {
      if (m !== method) continue;
      const mm = path.match(re);
      if (!mm) continue;
      try {
        const body = init?.body ? JSON.parse(String(init.body)) : undefined;
        return json(h(mm, url.searchParams, body, uid));
      } catch (e) {
        const status = e instanceof S.HttpError ? e.status : 500;
        console.warn('[mockApi]', method, path, e);
        return json({ detail: e instanceof Error ? e.message : String(e) }, status);
      }
    }
    return json({ detail: `No mock for ${method} ${path}` }, 404);
  };
  console.info('[mockApi] fixtures mode — /api/* served from src/dev');
}
