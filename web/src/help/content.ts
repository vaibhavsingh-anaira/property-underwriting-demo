// Help content for every page and section. `mode` tells the viewer whether what they are looking
// at is the product itself (REAL), a thin working implementation (BASIC), a stand-in for a carrier
// system (MOCK), or both (MIXED).
import { HELP_DECISION } from '@/products/decision/help';
import { HELP_DELEGATED } from '@/products/delegated/help';

export type HelpMode = 'REAL' | 'BASIC' | 'MOCK' | 'MIXED';
export interface HelpEntry {
  title: string;
  what: string;          // what this is
  fits: string;          // how it fits the product / why a carrier cares
  how?: string;          // how to use it
  mode?: HelpMode;
  demo?: string;         // what to say or point at in a demo
}

const HELP_RENEWAL: Record<string, HelpEntry> = {
  // ------------------------------------------------------------------ global
  'app.overview': {
    title: 'Anaira Underwriting Control',
    what: 'A control layer that sits beside a carrier\'s policy, rating and claims systems. For every renewing commercial-property account it compares what the carrier wrote, what it actually issued and what it holds today, and turns every difference into a dollar-quantified, evidence-linked finding and a recommended action.',
    fits: 'It does not replace the policy system, rater, cat model or workbench — it reads from them. The value is catching leakage (under-priced renewals, weak terms, contract errors, missing referrals) before the carrier commits capital again.',
    mode: 'MIXED',
  },
  'app.demo_clock': {
    title: 'Demo clock',
    what: 'The whole demo world runs on a simulated calendar that starts on 1 Aug 2026. Advancing the clock replays dated events — broker emails, claims, endorsements, engineering notices, broker replies — through the mock systems, and the engine reacts exactly as it would in production.',
    fits: 'Renewal control is time-based: passes run at 150 days before expiry, when the submission arrives and at bind/issue. The clock lets you show a quarter of real life in a few minutes.',
    how: 'Use +7d, pick a “next event”, or Reset demo to return to 1 Aug. The workflow player resets the clock automatically when you press Play.',
    mode: 'MOCK',
  },
  'app.persona': {
    title: 'Persona switcher',
    what: 'Switches who you are acting as: underwriters (authority L1–L2), the head of property (L3), the CUO (L4) or the risk engineer.',
    fits: 'Authority is enforced per persona: an L1 underwriter cannot send a quote that needs L3 approval, and an L3 cannot approve an L4 referral. In production this comes from the carrier\'s single sign-on.',
    how: 'Switch to Robert Hale (CUO) for the book view and approvals; Maya Chen (L1) for the underwriter view.',
    mode: 'MOCK',
  },
  'app.evidence': {
    title: 'Evidence drawer',
    what: 'Clicking almost any number opens the evidence behind it: every observation for that field from every source (broker SOV, engineering, carrier systems, vendors, models), which one won and why, and the source document scrolled to the exact cell or page area.',
    fits: 'This is the trust feature. Underwriters and auditors can see that every finding rests on a specific piece of evidence, not an opaque score.',
    how: 'Click a value, then “Open full document” for the full viewer.',
    mode: 'REAL',
    demo: 'Open a finding on ABC Manufacturing and click the building value — the issued declarations PDF opens with the cell highlighted.',
  },

  // ------------------------------------------------------------------ book
  'book.page': {
    title: 'Renewal book (CUO view)',
    what: 'The whole renewing book of 120 fictional accounts at a glance: how much leakage has been found, how much has been fixed, true versus reported rate change, and where the portfolio is concentrated.',
    fits: 'This is the buyer\'s screen. A chief underwriting officer sees whether the book is being renewed at the price and terms intended, and which underwriters, brokers and zones need attention.',
    mode: 'REAL',
    demo: 'Start the demo here as the CUO: “$7.5M of leakage identified before a single renewal has been worked.”',
  },
  'book.kpis': { title: 'Headline measures', what: 'Renewals analysed, fast-tracked (no material change), accounts with material findings, accounts not yet in the 150-day window, economic leakage identified and the book\'s computed rate change.', fits: 'Fast-tracking 40–50% of renewals is where the handling-time saving comes from; the leakage figure is where the margin comes from.', mode: 'REAL' },
  'book.pipeline': { title: 'Dollar pipeline', what: 'Economic impact of material findings as they move from identified → validated by an underwriter → approved in a quote → actually corrected at bind (the bound terms cure the finding).', fits: 'The product is sold on dollars actually corrected, not dollars flagged. The gap between identified and corrected is the work queue.', how: 'Advance the clock a few weeks and watch the later bars fill as the simulated underwriters bind renewals.', mode: 'REAL' },
  'book.rarc': { title: 'Computed vs reported rate change', what: 'Rate change (RARC) that underwriters report, versus RARC computed by rerunning the pricing model with exposure and terms held constant.', fits: 'Underwriters tend to under-allow for exposure growth, so self-reported rate change overstates the true figure. The computed number is auditable down to each account\'s three model runs.', mode: 'REAL' },
  'book.adequacy': { title: 'Adequacy distribution', what: 'Accounts bucketed by working premium ÷ technical premium. The guideline floor is 95%.', fits: 'Shows how much of the book is being renewed below technical price.', mode: 'REAL' },
  'book.months': { title: 'Renewals by month', what: 'Renewals by expiry month, split into fast-track and action-required.', fits: 'Workload planning: where the underwriting effort will be needed.', mode: 'REAL' },
  'book.actions': { title: 'Recommended actions', what: 'Count of accounts by recommended action (reprice, restructure, condition, refer, data request, non-renew, notice).', fits: 'The platform recommends; the underwriter decides.', mode: 'REAL' },
  'book.families': { title: 'Exceptions by rule family', what: 'Open material findings grouped by the kind of control (pricing, valuation, cat terms, contract integrity, engineering…).', fits: 'Tells the CUO which controls are generating the value — and which rules may be noisy.', how: 'Click a family to open the renewal queue filtered to it.', mode: 'REAL' },
  'book.underwriters': { title: 'By underwriter', what: 'Findings, dollar impact and pricing deviations per underwriter.', fits: 'Portfolio steering and coaching: who is renewing below authority or below technical.', mode: 'REAL' },
  'book.brokers': { title: 'By broker', what: 'Premium, leakage and average rate change per broker.', fits: 'Distribution strategy: which broker relationships carry the most rate erosion.', mode: 'REAL' },
  'book.accumulation': { title: 'Accumulation', what: 'CAT-zone utilisation (1-in-250 PML, carrier share) after renewals, against each zone\'s capacity.', fits: 'Renewals that push a zone over its referral threshold are referred individually — the platform refers the renewal that causes the breach, not the whole zone.', mode: 'REAL' },

  // ------------------------------------------------------------------ renewals
  'renewals.page': { title: 'Renewal queue (underwriter view)', what: 'Every renewal ranked by dollars at stake and how close the statutory notice deadline is, with the recommended actions, integrity score and top findings.', fits: 'This replaces a static renewal list. Work goes only where something changed.', how: 'Filter by status or underwriter, press j/k to move, Enter to open. Fast-track accounts sit in their own lane with one-click confirm.', mode: 'REAL' },
  'renewals.fasttrack': { title: 'Fast-track lane', what: 'Renewals with no material finding. Confirming records that the underwriter reviewed and chose to maintain.', fits: 'Every control still ran; nothing needed a human.', mode: 'REAL' },

  // ------------------------------------------------------------------ account
  'account.page': { title: 'Account integrity record', what: 'Everything about one renewal: the seven deltas, findings with evidence, recommended actions, locations, pricing, contract, CAT, claims and engineering, documents and the audit trail.', fits: 'One record per renewing account — the unit of work for the underwriter and the unit of audit for the carrier.', mode: 'REAL' },
  'account.passes': { title: 'Three passes', what: 'Pass 1 runs at 150 days before expiry on data the carrier already holds. Pass 2 runs when the renewal submission arrives. Pass 3 runs at bind and issuance and checks the contract.', fits: 'Most tools wait for the broker\'s SOV, which often arrives 30 days out. Pass 1 delivers value months earlier.', mode: 'REAL' },
  'account.notice': { title: 'Notice deadline', what: 'For admitted policies, the latest date a non-renewal or conditional-renewal notice can be sent under the state table.', fits: 'Missing the window forces renewal on expiring terms. The table is illustrative — verify with counsel.', mode: 'REAL' },
  'account.integrity': { title: 'Integrity score', what: '100 minus penalties for open findings, weighted by severity and materiality.', fits: 'A quick signal for triage; the findings and dollars are what matter.', mode: 'REAL' },
  'account.deltas': { title: 'Seven deltas', what: 'Exposure, pricing, terms & contract, risk quality, appetite & portfolio, retention & commercial (and net/reinsurance in a later version) — each comparing the bound state with today.', fits: 'The structure of a renewal decision, laid out so nothing is missed.', how: 'Click any metric to open its finding or evidence.', mode: 'REAL' },
  'account.narrative': { title: 'Why this account needs attention', what: 'A written summary of the material findings. Every sentence cites a finding [F] or observation [O]; a critique pass challenges findings that rest on weak evidence.', fits: 'Explains the recommendation in underwriting language, with nothing uncited.', mode: 'REAL' },
  'account.findings': { title: 'Findings', what: 'Every rule that fired: what was observed, what the guideline expects, dollar impact and method, confidence, and status.', fits: 'Underwriters accept, reject or defer each one with a mandatory reason code — that feedback measures each rule\'s precision.', how: 'Click a finding for its evidence; use Accept / Reject / Defer.', mode: 'REAL' },
  'account.actions': { title: 'Recommended actions', what: 'Actions derived from the material findings — reprice, restructure, condition, refer, data request, non-renew, endorsement correction — with owner, due date and dollars.', fits: 'The platform proposes; the underwriter disposes.', mode: 'REAL' },
  'account.locations': { title: 'Location redline', what: 'Each location compared across years: how it was matched, insured value before and after, occupancy and construction changes, valuation versus modelled replacement cost, wind tier, AAL and flags.', fits: 'Values are compared per matched building, never only at account totals, so additions and deletions cannot hide each other.', mode: 'REAL' },
  'account.map': { title: 'Map', what: 'Locations plotted and coloured by the most severe open flag.', fits: 'Geographic context for CAT and accumulation.', mode: 'REAL' },
  'account.model3d': { title: '3D site model', what: 'A 3D model of the buildings with underwriting attributes on hover. For Redline Logistics it shows racks at 28 ft above the 20 ft sprinkler design plane.', fits: 'Makes a physical deficiency obvious to a non-engineer. In production these come from footprint vendors or engineering.', mode: 'MOCK' },
  'account.imagery': { title: 'Aerial imagery before / after', what: 'Two captures of the same site, with a slider.', fits: 'Physical change detection (roof damage, vacancy, new yard storage) feeds the evidence ledger as model-derived observations. Imagery is synthetic in the demo.', mode: 'MOCK' },
  'account.pricing': { title: 'Pricing & real rate change', what: 'The rate-change split. The carrier\'s technical model is rerun three times: expiring exposure & terms, renewal exposure & expiring terms, renewal exposure & proposed terms.', fits: 'Lloyd\'s-style RARC normally relies on underwriters typing in the exposure and terms adjustments. Here they are computed, so the rate change is auditable.', mode: 'MIXED' },
  'account.rarc_runs': { title: 'Three technical-model runs', what: 'Component breakdown (attritional, CAT load, expense, profit) for each run. Only one variable changes between adjacent columns.', fits: 'Exposure factor = run 2 ÷ run 1; terms factor = run 3 ÷ run 2.', mode: 'MOCK', demo: 'The rater is a mock with illustrative parameters; in production this calls the carrier\'s rater or hx.' },
  'account.factor_chain': { title: 'Expected premium chain', what: 'Expiring premium × exposure factor × terms factor = expected premium. RARC = proposed ÷ expected − 1.', fits: 'The headline change can look like an increase while the like-for-like rate is a cut.', mode: 'REAL' },
  'account.whatif': { title: 'What-if', what: 'Change the premium or terms and see RARC, adequacy and required authority recalculate live.', fits: 'Lets an underwriter find terms that are both adequate and within authority before referring.', how: 'Save as a quote version, refer it, or send it to the broker.', mode: 'REAL' },
  'account.drift': { title: 'Model drift', what: 'Technical price at bind (old model version) versus today\'s model on the same exposure.', fits: 'Separates model changes from real rate change so they are not mistaken for each other.', mode: 'REAL' },
  'account.net': { title: 'Gross vs net', what: 'Rate change before and after acquisition cost.', fits: 'A brokerage increase can turn a gross rate increase into a net rate cut.', mode: 'REAL' },
  'account.contract': { title: 'Contract integrity', what: 'The accepted quote, binder, issued policy and endorsed policy side by side, field by field, each value linked to where it was read in the document.', fits: 'Catches terms lost or changed between quote and issuance — a classic source of silent leakage.', how: 'Click any cell to open the document at that value.', mode: 'REAL' },
  'account.subjectivities': { title: 'Subjectivities', what: 'Conditions attached at bind (for example a roof schedule or generator test), their age and status.', fits: 'Open subjectivities are unmanaged risk. They clear when the evidence arrives.', mode: 'REAL' },
  'account.quotes': { title: 'Quote versions', what: 'Every quote version with premium, rate change, adequacy, status and terms hash.', fits: 'Approvals are locked to a terms hash; a new version with different terms invalidates the old approval.', mode: 'BASIC' },
  'account.referrals': { title: 'Referrals', what: 'Referrals raised on this account, the level required, who decided and any conditions or invalidation reason.', fits: 'Authority is enforced on the intended terms.', mode: 'REAL' },
  'account.bind_issue': { title: 'Bind & issue', what: 'Binds the accepted quote (authority re-checked) and issues the policy through the mock policy system, then runs Pass 3.', fits: 'The issuance-error toggle lets you show the contract check catching a keying error.', mode: 'MIXED' },
  'account.cat': { title: 'CAT model', what: 'AAL by peril, OEP/AEP exceedance curves, location contribution, data-quality flags and model-input versus resolved-state mismatches for each run.', fits: 'Checks that the CAT model was run on the risk as it really is. The model itself is a mock (event-based, illustrative) standing in for Moody\'s RMS or Verisk.', mode: 'MIXED' },
  'account.claims': { title: 'Claims & engineering', what: 'Loss history since bind and over five years, the engineering recommendation register, and links between claims and open recommendations.', fits: 'Losses arising from open engineering deficiencies are the strongest renewal signal there is.', mode: 'MIXED' },
  'account.documents': { title: 'Documents', what: 'Every document for the account — SOVs, quotes, binders, policies, emails, engineering, certificates, CAT outputs, imagery, 3D models — in the built-in viewers.', fits: 'One place for all evidence, each linked to the observations extracted from it.', mode: 'MIXED' },
  'account.timeline': { title: 'Timeline & audit trail', what: 'Every document received, engine run, mock-system event and user decision, with the pipeline stage it belongs to.', fits: 'The audit trail regulators, reinsurers and internal audit ask for.', mode: 'REAL' },

  // ------------------------------------------------------------------ other pages
  'referrals.page': { title: 'Referrals inbox', what: 'Referrals waiting for a senior decision, with the evidence memo, the level required and your own level.', fits: 'Senior review focused on the cases that need it, with the evidence already assembled.', how: 'Switch persona to a senior underwriter or the CUO to approve or decline.', mode: 'REAL' },
  'portfolio.page': { title: 'Portfolio & accumulation', what: 'CAT zones on a map with capacity, current and post-renewal utilisation, hazard layers and contributing accounts.', fits: 'Portfolio steering: which renewals are pushing zones over threshold.', mode: 'REAL' },
  'documents.page': { title: 'Document explorer', what: 'All documents across the book, filterable by type, format, source and account.', fits: 'Every document is linked to the observations extracted from it.', mode: 'MIXED' },
  'document.viewer': { title: 'Document viewer', what: 'PDF, Excel, email, 3D model, image, CSV and JSON viewers. The Extracted-fields panel lists what was extracted, with confidence, and highlights each value in place.', fits: 'Shows exactly what the platform read from each document.', mode: 'REAL' },
  'dq.page': { title: 'Data quality', what: 'Extraction volumes and confidence, location matching across years, accounts ranked by data quality (weighted by modelled-loss impact) and the human review queue.', fits: 'If locations cannot be matched across years, every comparison downstream is noise.', how: 'Confirm or reject proposed location matches in the review queue.', mode: 'REAL' },
  'rules.page': { title: 'Rule studio', what: 'The control library: 43 versioned rules (standard controls plus the carrier\'s guidelines as code), with how often each fired and how often underwriters accepted it.', fits: 'Rules are the carrier\'s intellectual property; precision is measured from underwriter dispositions.', mode: 'REAL' },
  'rule.editor': { title: 'Rule editor', what: 'The rule in YAML: scope, condition, outcome, severity, referral level, impact method and guideline citation.', fits: 'Guidelines become executable, versioned and testable.', how: 'Edit, run the tests, backtest against the frozen book, then publish a new version.', mode: 'REAL' },
  'rule.backtest': { title: 'Backtest', what: 'Re-evaluates the whole frozen book with the edited rule and lists findings added and removed.', fits: 'No rule goes live without seeing its effect on the book first.', mode: 'REAL' },
  'pipeline.page': { title: 'Pipeline & mocks', what: 'The 15-stage underwriting lifecycle, each stage marked REAL (our product) or MOCK (stand-in for a carrier or vendor system), with the workflow playbooks that walk accounts through it.', fits: 'Shows the full lifecycle is covered, and exactly which parts are product and which are stand-ins.', how: 'Click a stage to open its system; click a playbook to play or step through it.', mode: 'MIXED' },
  'pipeline.playbooks': { title: 'Workflow playbooks', what: 'Scripted, narrated walks of one account through the pipeline, each showing a different real-life situation.', fits: 'The demo. Every step runs against the real engine and the mocks; nothing is pre-recorded.', mode: 'MIXED' },
  'pipeline.mocks': { title: 'Mock systems console', what: 'The stand-in systems (policy admin, claims, rater, CAT, engineering, vendors, mailbox, broker) and the connector each one plugs into.', fits: 'Replacing a mock with the real system is configuration against the same connector contract.', mode: 'MOCK' },
  'pipeline.outbox': { title: 'Mock outbox', what: 'Everything the platform “sent”: quotes to brokers, data requests, referral notices, non-renewal notices.', fits: 'In production these go by email or broker portal.', mode: 'MOCK' },
  'stage.page': { title: 'Stage workspace', what: 'The system behind one pipeline stage, loaded with a chosen account\'s data: its records, the findings raised there, its documents and its activity.', fits: 'Lets you show what each system holds and does, one stage at a time.', how: 'Pick an account, then Run step to perform that stage for real.', mode: 'MIXED' },
  'player.page': { title: 'Workflow player', what: 'Plays a playbook with narration, captions and a visible cursor, or lets you step through it.', fits: 'The presenter\'s tool: a repeatable, narrated demo that runs the real engine.', how: 'Pick a playbook, read its client brief, press Play. Space pauses and resumes, → steps, Esc stops.', mode: 'MIXED' },
  'player.brief': { title: 'Client brief', what: 'What this workflow shows, why it matters to a carrier, what is real and what is mocked, the live figures from this run, and questions to expect.', fits: 'Share it with the client before or after the demo.', mode: 'MIXED' },
  'sandbox.page': { title: 'Your data (real mode)', what: 'Upload your own statement of values. The real engine parses it, normalises occupancy and construction, checks arithmetic and data quality, flags issues with exact cell anchors and runs the applicable controls.', fits: 'This is the product running on data we have never seen — no mocks involved in the extraction and controls.', how: 'Drop an .xlsx or .csv SOV. Nothing leaves this machine.', mode: 'REAL' },
};

export const HELP: Record<string, HelpEntry> = { ...HELP_RENEWAL, ...HELP_DECISION, ...HELP_DELEGATED };
