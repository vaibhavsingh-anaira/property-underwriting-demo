// "Start here" for Decision Assurance.
import { Link } from 'react-router-dom';
import { Play, Upload } from 'lucide-react';
import { Page, Badge, MockBadge } from '@/components/ui';
import { S, H3, P, UL, Ol, Code, L, Box, PlaybookTable, ProductsStrip, GuideToc, Glossary } from '@/pages/guide/parts';

const TOC = [
  ['products', 'Three products'], ['what', 'What this is'], ['why', 'Where it sits'], ['world', 'What you are looking at'], ['real', 'Real vs mock'],
  ['run', 'How to run it'], ['tour', 'First-time tour (10 min)'], ['demo', 'Giving a demo'], ['pick', 'Which workflow for which audience'],
  ['measure', 'How the numbers are computed'], ['infer', 'What the audience should take away'], ['glossary', 'Glossary'],
] as const;

export default function GuidePage() {
  return (
    <Page title="Start here · Decision Assurance" subtitle="Prepare the decision. Support the judgement. Control the commitment. The human underwriter remains the final decision owner.">
      <div className="grid grid-cols-12 gap-6">
        <GuideToc toc={TOC} links={<>
          <Link to="/decision/pipeline/journey?pb=da-deck-d1" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Play className="size-3.5" />Play the deck example (D1)</Link>
          <Link to="/decision/sandbox" className="flex items-center gap-1.5 text-[12.5px] font-medium text-accent-700 hover:underline"><Upload className="size-3.5" />Try it on your own files</Link>
        </>} />
        <article className="col-span-12 max-w-[900px] space-y-8 lg:col-span-9">
          <S id="products" h="One platform, three products">
            <P>The same core — evidence ledger, document extraction, rule engine, authority engine — runs three products. This page is for <b>Decision Assurance</b>, the new-business product.</P>
            <ProductsStrip current="decision" />
          </S>

          <S id="what" h="What this is">
            <P>Decision Assurance works on both sides of the underwriter's decision on a new-business submission.</P>
            <H3>Stage 1 — decision intelligence (before human review)</H3>
            <UL items={[
              'Reads the ACORD application, SOV, loss runs, inspection, broker email and manuscript wording; every value keeps its cell, page or email anchor.',
              'Normalises risk facts to carrier classes and finds contradictions between sources (application vs inspection vs SOV vs vendor data), each priced by re-rating on the other value.',
              'Lists missing information (five years of loss runs, inspection above $50M TIV, COPE gaps) with a one-click request to the broker.',
              'Applies appetite and guidelines with citations, gives the technical price and a suggested range, the authority and referral requirements, suggested terms and a draft action.',
            ]} />
            <H3>Stage 2 — decision assurance (after judgement, before commitment)</H3>
            <UL items={[
              'The underwriter records the intended action: quote, bind, refer or decline, with premium, deductible, limit, line, wording and rationale; overrides carry a reason.',
              'The action is checked independently on five dimensions — Evidence, Pricing, Guidelines, Appetite, Authority — and gets Pass, Pass with flags, or Refer / hold, with the remaining conditions and the decision owner.',
              'Approvals are envelopes (minimum premium and deductible, maximum line, approved wording). An action outside the envelope is not covered.',
              'Bind is assured again; it is blocked while a pre-bind condition or a required document is open. The quote and binder documents are read back and compared with the action.',
              'Outcomes (losses or clean experience six months after bind) are scored against the flags that fired, which updates rule precision in the Rule studio.',
            ]} />
          </S>

          <S id="why" h="Where it sits">
            <P>Most tools work on one side of the human decision. <b>Sixfold</b> helps underwriters understand risk faster; <b>Athenium</b> audits quality after the fact; <b>Federato</b> runs workflow and appetite; <b>hyperexponential</b> provides pricing infrastructure. Decision Assurance covers both sides: draft decision → human judgement → independent assurance → human final decision.</P>
            <H3>Control model — by materiality</H3>
            <UL items={[
              <><b>Tier 1 · deterministic</b> — authority, referral, deductible and limit thresholds, pricing deviation, prohibited classes, required documents. Versioned YAML rules with tests.</>,
              <><b>Tier 2 · assurance model</b> — conflicting evidence, unusual risk, large limit and high severity, manuscript wording, override and rationale critique. <i>Here a transparent, deterministic stand-in for the production model</i>: every signal is computed from the ledger and shown. The production version is a model-based critique with the same inputs and outputs.</>,
              <><b>Tier 3 · human judgement</b> — material overrides, unresolved ambiguity, complex coverage, high severity and every final bind or decline.</>,
            ]} />
          </S>

          <S id="world" h="What you are looking at">
            <UL items={[
              'Northgate Specialty (fictional) receiving new-business commercial property submissions. All names, documents and numbers are fictional and watermarked SAMPLE.',
              <>Six hero cases, D1–D6, each a different decision situation — they arrive in the mailbox between 3 and 7 Aug. <L to="/decision/cases">Case queue</L>.</>,
              'About 36 background submissions (Nov 2025 – Jul 2026) worked by simulated underwriters through the same code, so the dashboard has a real distribution; six are still in flight on 1 Aug.',
              'The demo clock starts on 1 Aug 2026 and is shared with Renewal Integrity. Broker replies, inspections and outcomes happen when the clock moves.',
              'The persona switcher (top right) sets whose authority applies when you submit an action or decide a referral.',
            ]} />
          </S>

          <S id="real" h="Real vs mock">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Box tone="ok" title={<><Badge tone="ok">REAL</Badge> The product</>} items={[
                'Extraction of application, SOV, loss runs, inspection, email and manuscript into the evidence ledger',
                'Classification guide (operations description, class codes, company data) — most hazardous class governs',
                'Contradiction and missing-information detection; resolution policies',
                '28 rules (tier 1 and tier 2) with tests, backtest and publish in the Rule studio',
                'Authority matrix, approval envelopes, verdict, conditions, decision owner, bind gate',
                'Read-back of quote and binder; outcome scoring; dashboard metrics',
              ]} />
              <Box tone="mock" title={<><MockBadge /> Stand-ins</>} items={[
                'Mailbox and broker (documents 3 days after a request; quote replies after 4)',
                'Rater and CAT model (NS-PROP-RATER v8.0 mock, MockCat 3.1)',
                'Hazard, property and company-data vendors; loss-control inspection vendor (7 days)',
                'Policy admin (quote and binder PDFs) and claims feed (outcomes)',
                'Tier 2 assurance model (deterministic stand-in, labelled in every view)',
              ]} />
            </div>
            <H3>Can I run it for real?</H3>
            <UL items={[
              <>Yes, on your own files: <L to="/decision/sandbox">Your data (real)</L> runs your SOV (and optionally an application PDF in the ACORD layout) through the real Stage 1 pack and the real Stage 2 assurance.</>,
              'Pricing and CAT then come from the mock rater, and hazard zones from a city reference table; both are labelled. A live deployment needs the carrier rater, CAT model, a geocoder/hazard feed and the submission mailbox.',
            ]} />
          </S>

          <S id="run" h="How to run it">
            <Ol items={[
              <>Run <Code>./start.sh</Code> and open <Code>http://localhost:5173</Code>. Pick <b>Decision Assurance</b> in the product selector.</>,
              'Every workflow’s Play button resets the demo to 1 Aug, so each run is clean.',
              <>If the pages say the decision world is building, the first request after an old snapshot builds it (a few seconds). Deleting <Code>data/runtime/reset_state.pkl</Code> rebuilds everything.</>,
            ]} />
          </S>

          <S id="tour" h="First-time tour (10 minutes)">
            <Ol items={[
              <><L to="/decision">Dashboard</L> — exposure corrected or prevented, verdict mix, the ten-stage funnel, results by tier, underwriter and broker, outcome feedback.</>,
              <><L to="/decision/cases">Case queue</L> — open D1 after advancing the clock to 3 Aug (the header of the case page has the button).</>,
              <><b>Stage 1 tab</b> — draft recommendation, the sprinkler contradiction side by side (open either source at its anchor), missing information, risk factors with citations, pricing, authority.</>,
              <><b>Stage 2 tab</b> — change the premium and watch the live verdict; submit; read the per-dimension result and the checks.</>,
              <><L to="/decision/referrals">Referrals</L> — switch persona to an approver and decide one.</>,
              <><L to="/rules?product=decision">Rule studio</L> — open <Code>DA.ROOF.AGE</Code>, change the threshold, backtest on the book.</>,
              <><L to="/decision/pipeline/journey?pb=da-deck-d1">Workflow player</L> — press Play.</>,
            ]} />
          </S>

          <S id="demo" h="Giving a demo">
            <H3>20-minute version</H3>
            <Ol items={[
              'Dashboard (2 min): the primary measure — exposure corrected or prevented before commitment — and the verdict mix.',
              'Play the deck example D1 (10 min). Pause on stage 02 (the contradiction) and stage 08 (pass with flags).',
              'Open D1 afterwards (5 min): click the inspection value to show the anchor; change the premium in Stage 2 to see the verdict flip beyond ±5%.',
              'Close (3 min): both sides of the decision, and the human stays the owner.',
            ]} />
            <H3>45-minute version</H3>
            <Ol items={['Everything above.', 'Play D3 (bind below technical on incomplete loss runs) and D6 (override + manuscript, outcome months later).', 'Rule studio: backtest a threshold change on the book.', 'Your data: run the client’s own schedule.']} />
          </S>

          <S id="pick" h="Which workflow for which audience"><PlaybookTable product="decision" /></S>

          <S id="measure" h="How the numbers are computed">
            <UL items={[
              <><b>Exposure corrected or prevented</b> (premium-equivalent $): at preparation, the rating impact of material contradictions resolved on the more adverse, verified source; at assurance, premium raised after a refer/hold, plus technical premium removed by tighter terms, line or wording, or the full technical premium of a commitment declined. Losses later excluded by corrected wording are shown separately as loss avoided.</>,
              <><b>Errors intercepted</b>: failing checks on intended actions that were changed or declined before commitment, plus adverse contradictions resolved.</>,
              <><b>Preparation hours saved</b>: an explicit estimate — manual assembly 2.0 h + 0.35 h per location + 0.3 h per document + 0.25 h per contradiction + 0.2 h per missing item, less 0.5 h + 0.1 h per contradiction to review the pack.</>,
              <><b>Flag precision</b>: flags acted on count as upheld; overridden flags count as upheld if the outcome confirms them (a linked loss) and as rejected if the outcome is clean.</>,
            ]} />
          </S>

          <S id="infer" h="What the audience should take away">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {[
                ['The file is ready before the expert is.', 'Stage 1 assembles, reconciles and prices the evidence; the underwriter starts from a draft, not a pile of attachments.'],
                ['Contradictions are found and priced.', 'Application vs inspection vs schedule, with the dollar effect of believing the wrong one.'],
                ['Assurance is independent of the person deciding.', 'The intended action is checked on five dimensions before commitment, not audited afterwards.'],
                ['Authority attaches to the action.', 'Approval envelopes cover only the premium, deductible, line and wording approved.'],
                ['Senior review only where it matters.', 'Tier 1 handles the thresholds; tier 2 raises what needs judgement; tier 3 sends it to the right human.'],
                ['It learns.', 'Outcomes score the flags; rules with weak precision show up in the Rule studio.'],
              ].map(([t, d]) => <div key={t} className="rounded-md border border-line bg-surface p-3"><div className="text-[13.5px] font-semibold text-ink-950">{t}</div><div className="mt-0.5 text-[12.5px] text-ink-600">{d}</div></div>)}
            </div>
          </S>

          <S id="glossary" h="Glossary"><Glossary items={[
            ['Decision pack', 'Stage 1 output: normalised facts, contradictions, missing information, risk factors, guidelines, pricing context, authority requirements, suggested terms and a draft action, all source-linked.'],
            ['Intended action', 'What the underwriter proposes to do: quote, bind, refer or decline, with premium, deductible, limit, line, wording and rationale.'],
            ['Verdict', 'Pass · Pass with flags (flags or conditions before bind) · Refer / hold (a failing check needs a higher level, or a blocking item must be resolved).'],
            ['Pricing deviation', 'Intended premium ÷ technical premium at the action’s terms − 1. Permitted: L1 ±5%, L2 ±10%, L3 ±15%, L4 ±30%.'],
            ['Technical premium', 'What the (mock) rater and CAT model say the risk costs at the action’s terms and line, including schedule and experience modifiers.'],
            ['Approval envelope', 'The limits an approval covers (minimum premium and deductible, maximum line, approved wording). Actions outside it are not covered.'],
            ['Tier 1 / 2 / 3', 'Deterministic rules · assurance-model critique (stand-in here) · human judgement.'],
            ['Decision owner', 'The person who must take the final decision: the underwriter when within authority, otherwise the approver at the required level.'],
            ['Contradiction', 'The same field with materially different values in two sources; resolved by policy (verified evidence first) or by the underwriter, with a reason.'],
            ['Pre-bind condition', 'Evidence required before bind (roof schedule, in-rack sprinkler verification); cleared automatically when the document is parsed.'],
            ['Evidence types', 'C claimed · S system of record · N normalised · V verified · M model / vendor · D derived · R reference.'],
            ['Outcome feedback', 'Losses or clean experience six months after bind, scored against the flags that fired.'],
          ]} /></S>
        </article>
      </div>
    </Page>
  );
}
