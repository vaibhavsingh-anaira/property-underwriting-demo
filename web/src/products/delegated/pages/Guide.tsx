// "Start here" for Delegated Authority Control.
import { Link } from 'react-router-dom';
import { Play, Upload } from 'lucide-react';
import { S, H3, P, UL, Ol, Code, L, Box, PlaybookTable, ProductsStrip, GuideToc, Glossary } from '@/pages/guide/parts';
import { Page, Badge, MockBadge } from '@/components/ui';

const TOC = [
  ['products', 'Three products'], ['what', 'What this is'], ['world', 'What you are looking at'], ['real', 'Real vs mock'], ['run', 'How to run it'],
  ['tour', 'First-time tour (10 min)'], ['demo', 'Giving a demo'], ['pick', 'Which workflow for which audience'], ['position', 'Where it sits in the market'],
  ['infer', 'What the audience should take away'], ['glossary', 'Glossary'],
] as const;

export default function Guide() {
  return (
    <Page title="Start here · Delegated Authority Control" subtitle="Is the coverholder actually writing the business we authorised?">
      <div className="grid grid-cols-12 gap-6">
        <GuideToc toc={TOC} links={<>
          <Link to="/delegated/pipeline/journey?pb=dac-monthly-close" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Play className="size-3.5" />Play the monthly close</Link>
          <Link to="/delegated/sandbox" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Upload className="size-3.5" />Try it on your own bordereau</Link>
        </>} />
        <article className="col-span-12 max-w-[900px] space-y-8 lg:col-span-9">
          <S id="products" h="One platform, three products">
            <P>The same core — evidence anchors, document extraction, rule engine, authority engine — runs three products. This page is for <b>Delegated Authority Control</b>.</P>
            <ProductsStrip current="delegated" />
          </S>
          <S id="what" h="What this is">
            <P>Delegated business is written by someone else — an MGA or coverholder — on the carrier's paper, under a binding authority agreement the carrier rarely re-reads after signing. This product compares <b>authority granted</b> with <b>business written</b>, every month, for every policy, and turns every difference into an evidenced, dollar-quantified exception with an action.</P>
            <UL items={[
              <><b>Authority granted:</b> the BAA and its endorsements are read back from PDF into a versioned authority — classes and rating, territories, maximum limit, deductible minimums, referral triggers, exclusions, commission, aggregate limits, authority period. Each term keeps its page and box.</>,
              <><b>Business written:</b> risk, premium and claims bordereaux in the coverholder's own layout are mapped to Lloyd's CRS v5.2 with a confidence per column and validated; every value keeps its cell.</>,
              <><b>Control result:</b> each line is checked against the authority in force on the day it was bound; referrals are reconciled to the carrier's referral system; commission and premium are reconciled; zone aggregates rebuilt; claims checked against the policy register.</>,
              <><b>Output:</b> a breach register per policy (written vs authority, side by side, with the cell and the clause), a monthly authority report and scorecard per coverholder, and quarterly RARC computed from the bordereaux.</>,
              <><b>Remediation:</b> queries go to the coverholder with the evidence; corrections come back as bordereaux and are re-checked; commission becomes a debit note; zones are restricted and authorities amended by endorsement.</>,
            ]} />
          </S>
          <S id="world" h="What you are looking at">
            <UL items={[
              'Fictional carrier Northgate Specialty with five coverholders on commercial property programs, May–August 2026. Every name, document and number is fictional and watermarked SAMPLE.',
              <><b>A1 Meridian Gulf</b> — deteriorating: limit and deductible breaches, missing referrals, commission deducted at 25% against 22.5%. <b>A2 Northfield</b> — the clean benchmark. <b>A3 Palm Coast</b> — Florida program through its South Florida aggregate warning. <b>A4 Ridgeway</b> — late, non-standard bordereaux with mandatory fields missing. <b>A5 Sierra Crest</b> — a wildfire loss on a risk bound in an excluded county, a large loss notified late.</>,
              'About 3,500 bordereau lines, 5 agreements with endorsements, exposure returns and claims bordereaux. The demo clock starts on 1 Aug 2026: May–July are history (with past queries already worked); July arrives late for Ridgeway on 24 Aug; August bordereaux arrive 3–12 Sep.',
              'Persona: Claire Donovan, Head of Delegated Authority (switch in the top bar).',
            ]} />
          </S>
          <S id="real" h="Real vs mock">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Box tone="ok" title={<><Badge tone="ok">REAL</Badge> The product</>} items={[
                'BAA and endorsement extraction from PDF into a versioned authority with page anchors',
                'Bordereau header detection, CRS v5.2 mapping with confidence, validation with cell references',
                '27 authority, capacity, claims and reporting rules (YAML + CEL, with tests, backtest, publish)',
                'Referral reconciliation (exists, pre-dates binding, covers the written terms)',
                'Commission and premium reconciliation, zone aggregates, GPI, claims controls',
                'Breach register, monthly report, scorecard, quarterly RARC, endorsements parsed back',
              ]} />
              <Box tone="mock" title={<><MockBadge /> Stand-ins</>} items={[
                'Coverholder portal and the coverholder itself: sends files on dated events; replies to queries by rule after a few days (corrects, supplies a reference, cancels, disputes, agrees)',
                'Carrier referral system: holds approvals; decides zone referrals by a headroom rule',
                'Finance ledger (debit notes, settlement), CAT aggregate feed (county → zone, PML ratio)',
                'DA registry / binder store and the audit team',
              ]} />
            </div>
            <H3>Can I run it for real?</H3>
            <UL items={[
              <>Yes, on your own file: <L to="/delegated/sandbox">Your data (real)</L> maps any .xlsx/.csv bordereau to CRS v5.2, validates it and checks every line against a demo BAA or your own BAA PDF in the same layout.</>,
              'A live deployment connects four things: the bordereau feed (coverholder portal or DDM), the carrier referral system, the finance ledger, and the CAT accumulation feed. Everything between them is already the product.',
            ]} />
          </S>
          <S id="run" h="How to run it">
            <Ol items={[<>Run <Code>./start.sh</Code> and open <Code>http://localhost:5173</Code>; pick <b>Delegated Authority</b> in the product selector.</>,
              'The first boot builds all three products and saves a reset snapshot. Every workflow’s Play resets to 1 Aug 2026.',
              'Use the demo clock to move time: bordereaux, coverholder replies, settlements and audit reports arrive as dated events.']} />
          </S>
          <S id="tour" h="First-time tour (10 minutes)">
            <Ol items={[
              <><L to="/delegated">Dashboard</L> — the monthly authority report across coverholders: policies checked, within authority, exceptions by type, premium tied, commission discrepancy, trend, aggregates.</>,
              <><L to="/delegated/coverholders/ch_meridian">Meridian Gulf</L> — scorecard and trend; the Authority tab shows every term with a link to the clause; Breach register → open Bayou City Cold Storage for the side-by-side result.</>,
              <><L to="/delegated/bordereaux?ch=ch_ridgeway">Bordereaux</L> — Ridgeway's mapping table and validation issues; click an issue to open the file at the cell.</>,
              <><L to="/delegated/aggregates">Aggregates</L> — South Florida above its warning level; “Refer new business” issues an endorsement.</>,
              <><L to="/delegated/pipeline">Pipeline & mocks</L> — the 11 stages; each opens its system for a coverholder.</>,
              <><L to="/delegated/pipeline/journey?pb=dac-monthly-close">Workflow player</L> — press Play.</>,
            ]} />
          </S>
          <S id="demo" h="Giving a demo">
            <H3>20-minute version</H3>
            <Ol items={['Dashboard (3 min): trend by coverholder, exceptions by type, premium tied, commission.', 'Play “Monthly bordereau close” (10 min); pause on the breach register and the coverholder reply.',
              'Open the cold-storage policy (3 min): click the cell and the clause.', 'Close (4 min): Florida aggregate on the dashboard; the four connections for a pilot.']} />
            <H3>45-minute version</H3>
            <Ol items={['The 20-minute version.', 'Play the flow for the audience (table below) — Florida aggregate for CAT/CUO, resubmission for DA operations, claims for claims leaders.',
              'Quarterly review: trend, RARC from bordereaux, scorecard, audit, tightened authority.', 'Upload the client’s own (anonymised) bordereau in Your data.']} />
          </S>
          <S id="pick" h="Which workflow for which audience"><PlaybookTable product="delegated" /></S>
          <S id="position" h="Where it sits in the market">
            <UL items={[
              <><b>Send / Duck Creek DA module</b> ingests bordereaux, maps them and checks them against binder authority as they arrive — tied to a core system; reconciliation against the contract as endorsed is not published. Here the authority itself is a versioned contract object read from the PDF.</>,
              <><b>VIPR, Pro Global, Charles Taylor Tide, Lloyd's DDM</b> collect and standardise bordereaux and support audits. This product consumes those feeds and adds the control result: per-policy authority checks with evidence, referral reconciliation, commission recovery, aggregates, and quarterly RARC from bordereaux (required by MS3, not documented by bordereau platforms).</>,
            ]} />
          </S>
          <S id="infer" h="What the audience should take away">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {[['Every policy, every month.', 'Not a sample: each line against the authority in force when it was bound.'], ['Evidence on both sides.', 'The bordereau cell and the BAA clause behind every exception.'],
                ['Referral means approval that covers what was bound.', 'Missing, late or narrower approvals are breaches.'], ['Corrections are verified.', 'The coverholder’s reply is a file that is parsed and re-checked.'],
                ['Capacity is controlled before it is bound.', 'Zone restrictions are endorsements; the next bordereau proves they worked.'], ['Rate is measured like for like.', 'Quarterly RARC from renewal lines using the agreement’s own rating factors.']].map(([t, d]) => (
                <div key={t} className="rounded-md border border-line bg-surface p-3"><div className="text-[13.5px] font-semibold text-ink-950">{t}</div><div className="mt-0.5 text-[12.5px] text-ink-600">{d}</div></div>))}
            </div>
          </S>
          <S id="glossary" h="Glossary">
            <Glossary items={[
              ['Coverholder / MGA', 'A firm authorised to bind insurance on the carrier’s behalf under a binding authority.'],
              ['BAA', 'Binding authority agreement: classes, territories, limits, deductibles, rating, referrals, exclusions, commission, aggregates and the authority period.'],
              ['Endorsement', 'A change to the BAA from an effective date. Each one creates a new authority version here.'],
              ['UMR', 'Unique market reference identifying the contract in the London market.'],
              ['Bordereau', 'The coverholder’s periodic report: risk (policies), premium (premium and commission), claims (paid, reserve, incurred).'],
              ['CRS v5.2', 'Lloyd’s Coverholder Reporting Standards: the standard field set bordereaux are mapped to.'],
              ['Referral', 'A risk outside the coverholder’s own authority that needs the carrier’s prior written approval, evidenced by a reference.'],
              ['Aggregate / zone', 'In-force TIV in a CAT zone against the limit and warning level in the BAA.'],
              ['GPI', 'Gross premium income limit for the authority period.'],
              ['Rated premium / tolerance', 'Premium from the BAA rating rules; the written premium must be within the tolerance of it.'],
              ['Rate on line', 'Premium ÷ limit.'],
              ['RARC from bordereaux', 'Renewal premium ÷ (expiring premium × TIV change × deductible-factor change) − 1, weighted by expiring premium.'],
              ['Debit note', 'Finance entry recovering commission deducted above the contract rate.'],
              ['Large loss advice', 'Immediate notification of a claim above the BAA threshold, separate from the bordereau.'],
            ]} />
          </S>
        </article>
      </div>
    </Page>
  );
}
