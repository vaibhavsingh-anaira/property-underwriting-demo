// "Start here": what the product is, what is real vs mocked, how to run it, a first-time tour,
// how to give a demo, what the audience should take away, and a glossary.
import { Link } from 'react-router-dom';
import { Play, Upload } from 'lucide-react';
import { S, H3, P, UL, Ol, Code, L, Box, PlaybookTable, ProductsStrip } from './guide/parts';
import { Page, Badge, MockBadge } from '@/components/ui';

const TOC = [
  ['products', 'Three products'], ['what', 'What this is'], ['world', 'What you are looking at'], ['real', 'Real vs mock'], ['run', 'How to run it'],
  ['tour', 'First-time tour (10 min)'], ['demo', 'Giving a demo'], ['pick', 'Which workflow for which audience'],
  ['infer', 'What the audience should take away'], ['glossary', 'Glossary'],
] as const;

export default function GuidePage() {
  return (
    <Page title="Start here · Renewal Integrity" subtitle="How to use this product the first time, how to give a demo, and what it all means">
      <div className="grid grid-cols-12 gap-6">
        <nav className="col-span-12 lg:col-span-3">
          <div className="sticky top-4 rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-[var(--shadow-card)]">
            <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[.1em] text-ink-500">On this page</div>
            {TOC.map(([id, l], i) => <a key={id} href={`#${id}`} className="block rounded px-2 py-1 text-[13px] text-ink-700 hover:bg-ink-50 hover:text-ink-950"><span className="num mr-1.5 text-ink-400">{i + 1}</span>{l}</a>)}
            <div className="mt-3 space-y-1.5 border-t border-line pt-3">
              <Link to="/pipeline/journey?pb=reprice-refer" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Play className="size-3.5" />Play the flagship workflow</Link>
              <Link to="/sandbox" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Upload className="size-3.5" />Try it on your own SOV</Link>
            </div>
          </div>
        </nav>
        <article className="col-span-12 max-w-[900px] space-y-8 lg:col-span-9">
          <S id="products" h="One platform, three products">
            <P>The same core — evidence ledger, document extraction, rule engine, authority engine — runs three products. Switch between them with the <b>Product</b> selector at the top of the sidebar; each has its own Start here, dashboard, pipeline, workflows and briefs. This page is for <b>Renewal Integrity</b>.</P>
            <ProductsStrip current="renewal" />
          </S>

          <S id="what" h="What this is">
            <P><b>Anaira Underwriting Control</b> is a control layer that sits across a carrier's commercial property renewal book. It does not replace the underwriter, the rater or the policy system. It reads everything that arrives, keeps every fact with its source, and checks each renewal against the carrier's own rules before the carrier commits to it.</P>
            <UL items={[
              'Reads every document (SOVs, emails, quotes, binders, policies, engineering reports, loss runs) and records each value with the exact cell or page it came from.',
              'Matches locations across years, so this year\'s schedule can be compared with last year\'s like-for-like.',
              'Runs the carrier\'s underwriting guidelines as versioned, testable rules and raises findings with a dollar impact.',
              'Re-runs the rater and CAT model three times to separate exposure growth, terms changes and true rate change (RARC).',
              'Enforces authority on the exact terms being bound, and checks quote ↔ binder ↔ policy for every renewal.',
              'Keeps watching mid-term: endorsements, claims and impairments re-evaluate the account immediately.',
            ]} />
            <P>This guide covers <b>Renewal Integrity</b>. Decision Assurance (new business, before commitment) and Delegated Authority Control (coverholder business) run on the same core — use the product selector.</P>
          </S>

          <S id="world" h="What you are looking at">
            <UL items={[
              'A fictional carrier, Northgate Specialty, with 120 commercial property renewals. Every name, document and number is fictional and watermarked SAMPLE.',
              '12 “hero” accounts (S1–S12) each carry one real-world problem (under-pricing, occupancy drift, lapsed safeguards, renumbered buildings, expired broker licence…). The other 108 are background: simulated underwriters work them as the clock moves.',
              'The demo clock starts at 1 Aug 2026. Moving it forward replays dated events (broker emails, endorsements, claims, imagery) and the engine reacts. Use the clock menu in the top bar; “Reset demo” returns to 1 Aug.',
              'The persona switcher (top right) changes who you are: underwriters (L1–L2), senior underwriter (L3), CUO (L4), risk engineer. Authority checks use the selected persona.',
            ]} />
          </S>

          <S id="real" h="Real vs mock — what is the product and what is a stand-in">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Box tone="ok" title={<><Badge tone="ok">REAL</Badge> The product (this is what a carrier buys)</>} items={[
                'Document extraction with anchors (Excel, PDF, email, CSV/JSON, 3D model metadata)',
                'Evidence ledger: every value, its source, type (C/S/N/V/D/M/R) and resolution policy',
                'Location matching across years with human review',
                'Rule engine: 43 rules, tests, backtest, publish',
                'RARC split, technical price, adequacy, model drift',
                'Authority matrix, referrals locked to a terms hash, bind gate',
                'Contract comparison quote ↔ binder ↔ policy; subjectivities',
                'Book, portfolio accumulation, data-quality and rule-precision views',
              ]} />
              <Box tone="mock" title={<><MockBadge /> Stand-ins for carrier & vendor systems</>} items={[
                'Broker: accepts at or near target/technical, otherwise counters; returns requested documents 3 days after a data request',
                'Rater and CAT model: deterministic stand-ins with the same inputs/outputs (called 3× per renewal)',
                'Policy admin: issues the policy — can deliberately mis-key a term (fault injection) — endorsements, billing',
                'Claims, engineering (site visit 7 days after it is ordered), clearance data (licence table, screening list), geocoding/hazard/imagery vendors',
              ]} />
            </div>
            <P className="mt-3">Each stand-in sits behind the same connector (“port”) a real system would use — the Pipeline page lists them. Swapping one for the carrier's system is integration work against that contract, not a rebuild.</P>
            <H3>Can I run the real thing?</H3>
            <UL items={[
              <>Yes, on your own data today: <Link to="/sandbox" className="font-medium text-accent-700 hover:underline">Your data (real mode)</Link> runs any .xlsx/.csv SOV through the real parser, occupancy/construction mapping, data-quality controls and year-over-year matching. Nothing is scripted and nothing leaves the machine.</>,
              'Everything else in the demo already runs the real engine — only the systems it talks to are stand-ins, and their inputs are scripted so the story is repeatable.',
              'A fully live deployment needs four connections: the carrier\'s rater, its CAT model, its policy admin/claims systems, and a mailbox or broker portal feed. Pricing, CAT and contract checks then run on the carrier\'s own numbers.',
            ]} />
          </S>

          <S id="run" h="How to run it">
            <Ol items={[
              <>From the project folder run <Code>./start.sh</Code>. It starts the API on port 8765 and the web app on port 5173. The first start builds the demo world (about a minute).</>,
              <>Open <Code>http://localhost:5173</Code>. If a page says it cannot reach the API, the API is still starting.</>,
              <>To rebuild from scratch, delete <Code>data/runtime/reset_state.pkl</Code> and restart.</>,
              'Every workflow’s Play button resets the demo to 1 Aug first, so each run is clean and repeatable.',
            ]} />
          </S>

          <S id="tour" h="First-time tour (10 minutes)">
            <Ol items={[
              <><L to="/">Book</L> — the CUO view: renewals analysed, fast-tracked vs needing action, the dollar pipeline (identified → validated → approved → corrected), computed vs reported RARC.</>,
              <><L to="/renewals">Renewals</L> — the work queue. The fast-track lane is renewals with no material change; everything else is ranked by dollar impact.</>,
              <><L to="/accounts/acc_s2">An account (S2)</L> — findings with evidence (click any value to see its source cell or page), pricing and the three rater runs, contract comparison, CAT, locations map and 3D site model, documents.</>,
              <><L to="/pipeline">Pipeline & mocks</L> — the 15 stages of the lifecycle. Click any stage to open that system for an account; the badge says whether it is the product or a stand-in.</>,
              <><L to="/pipeline/journey?pb=reprice-refer">Workflow player</L> — press Play. It narrates, moves a cursor, runs each step against the engine and reads out the live result. Read the Client brief panel alongside.</>,
              <><L to="/rules">Rule studio</L> — open a rule, edit it, run its tests and backtest it on the book before publishing.</>,
              <><L to="/sandbox">Your data</L> — upload an SOV of your own.</>,
            ]} />
            <P>Every page and most panels have an <b>(i)</b> button that says what it is and how it fits the product.</P>
          </S>

          <S id="demo" h="Giving a demo">
            <H3>Before</H3>
            <UL items={['Open the Workflow player on the flow you will show; press Restart so it is clean.', 'Set Pace to about 0.7× and pick a voice (or turn the voice off and narrate yourself; captions stay on).', 'Print or send the Client brief for that workflow (link on each playbook card) — it lists what is shown, what is real vs mocked and questions to ask.']} />
            <H3>20-minute version</H3>
            <Ol items={[
              'Book page (2 min): the book-level problem — reported rate change vs like-for-like, and the dollar pipeline.',
              'Play “Full renewal — reprice, refer, bind…” (12 min). Pause at stage 06 (the RARC split) and stage 11 (issuance error and correction).',
              'Open the account afterwards (4 min): click a finding to show the source cell in the SOV; show the contract tab.',
              'Close (2 min): the four connections needed for a pilot.',
            ]} />
            <H3>45-minute version</H3>
            <Ol items={[
              'Everything in the 20-minute version.',
              'Play two flows chosen for the audience (table below), e.g. Clearance hold for compliance, Mid-term event for property/engineering.',
              'Rule studio: edit a guideline threshold, backtest it on the book, show findings added/removed.',
              'Your data: upload the client\'s own (anonymised) SOV live.',
            ]} />
            <H3>Controls & recovery</H3>
            <UL items={['Space = play/pause · → = one step · Esc = stop. Stop keeps the state; Resume continues; Restart resets.', 'Click any step in the list to look at it; the stage workspace on the right shows that system with live data.', 'If something looks wrong, Restart — every run starts from the same clean state.']} />
          </S>

          <S id="pick" h="Which workflow for which audience"><PlaybookTable /></S>

          <S id="infer" h="What the audience should take away">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {[
                ['Headline rate change hides true rate change.', 'Stage 06 splits the premium change into exposure, terms and rate with three rater runs. Book page: computed vs reported RARC.'],
                ['Evidence, not assertions.', 'Every value links to the cell, page or email line it came from. Conflicts between sources are resolved by explicit policy.'],
                ['Guidelines become executable.', 'Rules are versioned, tested and backtested; precision is measured from underwriter decisions.'],
                ['Authority attaches to terms.', 'Change the terms and the approval is void; bind is blocked without a valid one.'],
                ['The contract is checked.', 'Quote ↔ binder ↔ policy compared on every renewal; errors corrected by endorsement the same day.'],
                ['Clean renewals get out of the way.', 'Fast-track lane: all controls ran, nothing material found, one-click confirm.'],
              ].map(([t, d]) => (
                <div key={t} className="rounded-md border border-line bg-surface p-3"><div className="text-[13.5px] font-semibold text-ink-950">{t}</div><div className="mt-0.5 text-[12.5px] text-ink-600">{d}</div></div>
              ))}
            </div>
          </S>

          <S id="glossary" h="Glossary">
            <dl className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
              {GLOSSARY.map(([t, d]) => <div key={t} className="border-b border-line py-1.5"><dt className="text-[13px] font-semibold text-ink-900">{t}</dt><dd className="text-[12.5px] text-ink-600">{d}</dd></div>)}
            </dl>
          </S>
        </article>
      </div>
    </Page>
  );
}

const GLOSSARY: [string, string][] = [
  ['RARC', 'Renewal adjusted rate change: proposed premium ÷ (expiring premium × exposure factor × terms factor) − 1. The true rate change once exposure and terms are removed.'],
  ['E0 / E1 · T0 / T1', 'Expiring / renewal exposure snapshots and expiring / proposed terms. The rater runs on E0/T0, E1/T0 and E1/T1 to split the change.'],
  ['Technical premium (TP)', 'What the rater and CAT model say the risk costs, before commercial adjustment.'],
  ['Adequacy', 'Premium ÷ technical premium. Guidelines set a floor; below it needs a referral.'],
  ['Finding', 'A rule that fired on an account, with observed vs expected, evidence and a dollar impact. Material findings exceed the materiality threshold.'],
  ['Pass 1 / 2 / 3', 'Internal drift check at T-150 days; re-check when the renewal submission arrives; contract integrity after bind and issuance.'],
  ['Evidence types', 'C claimed (broker/insured) · S system of record · N normalised · V verified (engineer) · D derived · M model output · R reference data.'],
  ['Fast-track', 'Renewal with no material findings: confirm with one click, quote at expected premium.'],
  ['Referral / authority level', 'L1–L4 limits by premium, TIV, rate change and rule. Approvals are locked to a hash of the exact terms.'],
  ['Subjectivity', 'A condition of the binder (e.g. a report within 30 days). Printed on the binder and cleared by a matching document.'],
  ['Corrective endorsement', 'Amends the issued policy to match what was bound.'],
  ['Clearance', 'Duplicate check, broker licence in each location state, sanctions screening. A hold blocks quoting.'],
  ['SOV / COPE', 'Statement of values; construction, occupancy, protection, exposure — the core property attributes.'],
  ['AAL / OEP / AEP', 'Average annual loss; occurrence and aggregate exceedance probability curves from the CAT model.'],
  ['Accumulation / zone', 'Total insured value in a CAT zone against its capacity; renewals that push a zone over threshold are flagged.'],
  ['Stand-in (mock)', 'A deterministic replacement for a carrier or vendor system, behind the production connector contract.'],
];

