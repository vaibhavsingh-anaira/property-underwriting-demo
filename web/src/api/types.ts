// ============================================================================
// API CONTRACT — single source of truth between backend (FastAPI) and web.
// Backend responses MUST match these shapes. All money in USD (number, not
// cents). All dates ISO-8601 strings ("2026-08-01"). Percentages as ratios
// (0.081 = 8.1%) unless the field name ends with `_pct_display`.
// ============================================================================

export type ObsType = 'C' | 'S' | 'N' | 'V' | 'D' | 'M' | 'R';
export const OBS_TYPE_LABEL: Record<ObsType, string> = {
  C: 'Collected', S: 'System', N: 'Normalized', V: 'Verified',
  D: 'Derived', M: 'Model', R: 'Reconciled',
};

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type RuleOutcome =
  | 'PASS' | 'NOT_APPLICABLE' | 'FLAG' | 'REFER' | 'BLOCK'
  | 'CONDITION' | 'PRICE_ADJUST' | 'DATA_REQUEST' | 'TERM_BREACH' | 'DECLINE';
export type ActionType =
  | 'MAINTAIN' | 'REPRICE' | 'RESTRUCTURE' | 'CONDITION' | 'DATA_REQUEST'
  | 'REFER' | 'CONDITIONAL_RENEWAL_NOTICE' | 'NON_RENEW' | 'ENDORSEMENT_CORRECTION';
export type RenewalStatus =
  | 'NOT_STARTED' | 'FAST_TRACK' | 'ACTION_REQUIRED' | 'IN_REVIEW' | 'REFERRED'
  | 'QUOTED' | 'BOUND' | 'ISSUED' | 'NON_RENEWED' | 'LOST';
export type DocFormat =
  | 'pdf' | 'xlsx' | 'eml' | 'glb' | 'png' | 'json' | 'csv' | 'yaml' | 'geojson' | 'txt';
export type PassNo = 0 | 1 | 2 | 3; // 1 = internal drift, 2 = submission delta, 3 = contract integrity

// ---------------------------------------------------------------- evidence --
export interface Anchor {
  doc_id: string | null;           // null for pure system records
  kind: 'pdf' | 'xlsx' | 'eml' | 'system' | 'vendor' | 'glb' | 'image' | 'json' | 'csv' | 'derived';
  page?: number;                   // 1-based
  bbox?: [number, number, number, number]; // PDF points, origin TOP-LEFT: [x0, top, x1, bottom]
  page_size?: [number, number];    // [width, height] in PDF points
  sheet?: string;
  cell?: string;                   // "K14"
  range?: string;                  // "A9:Q9" (row context)
  system?: string;                 // "PAS (mock)", "Claims (mock)"
  record_id?: string;
  path?: string;                   // JSON path for vendor/system payloads
  text?: string;                   // quoted snippet
  node?: string;                   // GLB node name
}

export interface Observation {
  obs_id: string;
  subject_type: 'account' | 'location' | 'building' | 'policy' | 'coverage' | 'claim' | 'recommendation';
  subject_id: string;
  subject_label: string;
  field_code: string;
  field_label: string;
  value: unknown;
  value_display: string;
  unit?: string | null;
  obs_type: ObsType;
  source_family: string;           // 'Broker / insured', 'Carrier systems', 'Engineering', 'External data', 'CAT model', 'Platform'
  source_label: string;            // '2026 renewal SOV', 'Engineering survey 2024-03-15'
  anchor: Anchor | null;
  vendor?: string | null;
  model_version?: string | null;
  confidence: number;              // 0..1
  verification_status: 'UNVERIFIED' | 'VERIFIED' | 'DISPUTED' | 'SUPERSEDED';
  valid_from: string | null;
  recorded_at: string;
  is_resolved: boolean;            // true if this obs is the winner for its field
}

export interface ResolvedField {
  field_code: string;
  label: string;
  value: unknown;
  value_display: string;
  resolved_obs_id: string | null;
  policy: string;                  // resolution policy id, e.g. "roof_year.v3"
  policy_explainer: string;        // "Engineering (V) > permit (S) > imagery (M) > SOV (C)"
  conflict: boolean;
  observations: Observation[];
}

// ---------------------------------------------------------------- people --
export interface User {
  user_id: string;
  name: string;
  role: 'UNDERWRITER' | 'SENIOR_UNDERWRITER' | 'CUO' | 'RISK_ENGINEER' | 'ADMIN';
  authority_level: 1 | 2 | 3 | 4;
  title: string;
  initials: string;
}

// ---------------------------------------------------------------- queue --
export interface FindingBrief { finding_id: string; title: string; severity: Severity; impact_usd: number; }

export interface RenewalQueueItem {
  account_id: string;
  name: string;
  scenario: string | null;         // "S2" for hero accounts
  segment: 'Middle market' | 'Large' | 'E&S';
  occupancy_family: string;
  state: string;
  broker: string;
  underwriter: string;             // user name
  underwriter_id: string;
  expiry: string;
  days_to_expiry: number;
  notice_deadline: string | null;
  days_to_notice: number | null;
  status: RenewalStatus;
  pass: PassNo;
  recommended_actions: ActionType[];
  impact_usd: number;              // sum of material open finding impact
  materiality: Severity;
  integrity_score: number;         // 0..100
  finding_count: number;
  top_findings: FindingBrief[];
  tiv_expiring: number;
  tiv_current: number;
  premium_expiring: number;
  rarc: number | null;
  adequacy: number | null;
  data_gaps: number;
  locations: number;
  families: string[];              // rule families of open material findings
}

// ---------------------------------------------------------------- account --
export interface DeltaMetric {
  label: string;
  before?: string | null;
  after?: string | null;
  display: string;                 // main value, e.g. "+25.8%"
  flag?: 'breach' | 'warn' | 'ok' | 'info';
  note?: string;
  finding_ids?: string[];
  obs_ids?: string[];
}
export interface DeltaCard {
  key: 'exposure' | 'pricing' | 'terms' | 'risk_quality' | 'appetite_portfolio' | 'retention' | 'net';
  title: string;
  status: 'OK' | 'WATCH' | 'ACTION';
  headline: string;
  metrics: DeltaMetric[];
}

export interface Disposition {
  decision: 'ACCEPT' | 'REJECT' | 'DEFER';
  reason_code: 'data_wrong' | 'already_known' | 'commercial_override' | 'immaterial' | 'rule_outdated' | 'agree';
  note: string;
  actor: string;
  at: string;
}

export interface Finding {
  finding_id: string;
  account_id: string;
  subject_type: 'account' | 'location' | 'policy' | 'contract' | 'claim' | 'recommendation' | 'referral';
  subject_id: string;
  subject_label: string;
  rule_id: string;
  rule_version: number;
  family: string;                  // 'cat_terms', 'valuation', 'contract_integrity', ...
  title: string;
  description: string;
  severity: Severity;
  outcome: RuleOutcome;
  observed: string;
  expected: string;
  impact_usd: number;
  impact_method: string;
  confidence: number;
  materiality_score: number;
  material: boolean;
  evidence_obs_ids: string[];
  conflicting_obs_ids: string[];
  status: 'OPEN' | 'ACCEPTED' | 'REJECTED' | 'DEFERRED' | 'RESOLVED';
  disposition: Disposition | null;
  pass: PassNo;
  created_at: string;
  critique: { verdict: 'UPHELD' | 'CHALLENGED'; note: string } | null;
  source: string;                  // guideline citation
}

export interface Action {
  action_id: string;
  account_id: string;
  type: ActionType;
  title: string;
  detail: string;
  finding_ids: string[];
  owner: string;
  due: string | null;
  status: 'PROPOSED' | 'IN_PROGRESS' | 'DONE' | 'DISMISSED';
  impact_usd: number;
}

export interface NoticeInfo {
  required: boolean;
  state: string;
  admitted: boolean;
  days_required: number | null;
  latest_notice_date: string | null;
  days_remaining: number | null;
  rule_ref: string;                // "Demo notice table v1 — illustrative, verify with counsel"
}

export interface LocationFlag { code: string; label: string; severity: Severity; finding_id?: string; }

export interface LocationRow {
  location_uid: string;
  loc_no_prior: string | null;
  loc_no_current: string | null;
  name: string;
  address: string;
  city: string;
  state: string;
  lat: number;
  lon: number;
  match_status: 'MATCHED' | 'NEW' | 'DELETED' | 'SPLIT' | 'MERGED' | 'AMBIGUOUS';
  match_method: string | null;
  match_score: number | null;
  match_confirmed_by: string | null;
  tiv_prior: number | null;
  tiv_current: number | null;
  tiv_change_pct: number | null;
  occupancy: string;
  occupancy_prior: string | null;
  construction: string;
  year_built: number | null;
  stories: number | null;
  sqft: number | null;
  roof_year: number | null;
  sprinkler: string;
  valuation_ratio: number | null;  // reported RC / model RC
  wind_tier: string | null;
  cat_zone: string | null;
  aal: number | null;
  buildings: number;
  flags: LocationFlag[];
  model_doc_id: string | null;     // GLB 3D model
  imagery_doc_ids: string[];       // PNG aerials (sorted by date)
}

export interface TimelineEvent {
  event_id: string;
  date: string;
  kind: 'document' | 'system' | 'engine' | 'user' | 'mock';
  stage: string;                   // pipeline stage code, e.g. '01', '11', '15'
  title: string;
  detail: string;
  actor: string;
  doc_id?: string | null;
  finding_ids?: string[];
}

export interface PolicySummary {
  policy_id: string;
  policy_no: string;
  term_start: string;
  term_end: string;
  carrier_share: number;           // 1.0 = 100%
  layer: string;                   // "Primary $250M loss limit" | "$100M xs $50M"
  limit: number;
  limit_basis: 'blanket' | 'scheduled' | 'loss_limit';
  admitted: boolean;
  premium: number;
  forms: { form_no: string; title: string }[];
}

export interface Narrative {
  text: string;                    // markdown with citation tokens like [F:fnd_123] or [O:obs_456]
  generated_by: 'template' | 'llm';
  model?: string | null;
  critique: { summary: string; upheld: number; challenged: number } | null;
}

export interface AccountDetail {
  account_id: string;
  name: string;
  scenario: string | null;
  scenario_title: string | null;
  segment: string;
  occupancy_family: string;
  broker: string;
  broker_contact: string;
  underwriter: string;
  underwriter_id: string;
  state: string;
  tenure_years: number;
  policy: PolicySummary;
  renewal: {
    expiry: string;
    days_to_expiry: number;
    pass: PassNo;
    status: RenewalStatus;
    integrity_score: number;
    recommended_actions: ActionType[];
    confidence: 'LOW' | 'MEDIUM' | 'HIGH';
    owner: string;
    due: string | null;
    notice: NoticeInfo;
    missing: string[];             // "Updated roof-replacement schedule"
  };
  deltas: DeltaCard[];
  findings: Finding[];
  actions: Action[];
  narrative: Narrative;
  locations: LocationRow[];
  timeline: TimelineEvent[];
  documents: DocumentMeta[];
  site_model_doc_id: string | null; // campus/site GLB
}

// ---------------------------------------------------------------- pricing --
export interface RarcComponentRow { component: string; e0t0: number; e1t0: number; e1t1: number; }
export interface RarcTerms {
  aop_deductible: number;
  named_storm_ded_pct: number | null;
  named_storm_ded_min: number | null;
  wind_hail_ded_pct: number | null;
  bi_sublimit: number | null;
  flood_sublimit: number | null;
  eq_sublimit: number | null;
}
export interface RarcResult {
  account_id: string;
  expiring_premium: number;
  expiring_terms: RarcTerms;
  proposed_terms: RarcTerms;
  tp_e0_t0: number;
  tp_e1_t0: number;
  tp_e1_t1: number;
  exposure_factor: number;
  terms_factor: number;
  expected_premium: number;
  proposed_premium: number;
  headline_change: number;
  rarc: number;
  adequacy: number;
  adequacy_floor: number;
  price_deviation: number;         // proposed / tp - 1
  required_authority_level: 1 | 2 | 3 | 4;
  authority_reasons: string[];
  method: 'model_rerun' | 'elasticity_fallback';
  model_version: string;
  model_drift: { tp_at_bind: number; tp_today_e0t0: number; drift: number };
  net: { brokerage_expiring: number; brokerage_proposed: number; rarc_net: number };
  breakdown: RarcComponentRow[];
  tiv_expiring: number;
  tiv_renewal: number;
}
export interface RarcWhatIfRequest { proposed_premium: number; terms: Partial<RarcTerms>; brokerage?: number; }

// ---------------------------------------------------------------- contract --
export type ContractCol = 'quote' | 'binder' | 'policy' | 'endorsed';
export interface ContractDiffRow {
  field: string;
  label: string;
  group: 'Limits' | 'Deductibles' | 'Sublimits' | 'Forms' | 'Safeguards' | 'Subjectivities' | 'Premium';
  values: Partial<Record<ContractCol, string | null>>;
  anchors: Partial<Record<ContractCol, Anchor | null>>;
  result: 'MATCH' | 'MISMATCH' | 'MISSING' | 'ADDED';
  finding_id: string | null;
}
export interface ContractDiff {
  term: string;                    // "2025–2026"
  quote_version: string;
  rows: ContractDiffRow[];
  endorsements: { endt_id: string; effective: string; type: string; description: string; premium_delta: number; doc_id: string | null }[];
  subjectivities: { text: string; due: string; status: 'OPEN' | 'CLEARED' | 'WAIVED'; age_days: number; finding_id: string | null }[];
  quotes: QuoteVersion[];
  referrals: Referral[];
}

export interface QuoteVersion {
  quote_id: string;
  version: number;
  term: string;
  created_at: string;
  created_by: string;
  premium: number;
  terms: RarcTerms;
  status: 'DRAFT' | 'REFERRED' | 'APPROVED' | 'SENT' | 'ACCEPTED' | 'BOUND' | 'SUPERSEDED';
  terms_hash: string;
  doc_id: string | null;
  rarc: number | null;
  adequacy: number | null;
}

export interface Referral {
  referral_id: string;
  account_id: string;
  account_name: string;
  quote_id: string | null;
  terms_hash: string | null;
  requested_by: string;
  requested_at: string;
  required_level: number;
  reasons: string[];
  memo: string;                    // markdown with citations
  status: 'PENDING' | 'APPROVED' | 'DECLINED' | 'INVALIDATED';
  approver: string | null;
  decided_at: string | null;
  conditions: string | null;
  invalidated_reason: string | null;
}

// ---------------------------------------------------------------- CAT --
export interface CatResult {
  run_id: string;
  account_id: string;
  snapshot: 'AS_BOUND' | 'CURRENT' | 'RENEWAL_PROPOSED';
  vendor: string;                  // "MockCat (stand-in for Moody's RMS / Verisk)"
  model_version: string;
  run_date: string;
  perils: string[];
  basis: string;                   // "Carrier share, net of deductibles"
  aal_total: number;
  aal_by_peril: { peril: string; aal: number }[];
  oep: { rp: number; loss: number }[];
  aep: { rp: number; loss: number }[];
  location_contrib: { location_uid: string; label: string; aal: number; pct: number; tiv: number }[];
  dq_flags: { location_uid: string; label: string; field: string; issue: string; impact: 'LOW' | 'MEDIUM' | 'HIGH' }[];
  input_mismatches: { location_uid: string; field: string; cat_input: string; resolved: string }[];
  exposure_doc_id: string | null;  // OED-style location file (csv)
  elt_doc_id: string | null;       // event loss table (csv)
  ep_doc_id: string | null;        // EP curve json
  compare: { label: string; aal_total: number; oep_100: number; oep_250: number }[]; // prior runs
}

// ---------------------------------------------------------------- claims & engineering --
export interface Claim {
  claim_id: string; location_uid: string | null; location_label: string; date_of_loss: string;
  cause: string; cat_event: string | null; status: 'OPEN' | 'CLOSED';
  paid: number; reserve: number; incurred: number; description: string;
  linked_recommendation: string | null;
}
export interface Recommendation {
  rec_id: string; location_uid: string; location_label: string; raised: string; category: string;
  description: string; severity: Severity; due: string; status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED' | 'VERIFIED_CLOSED';
  bind_condition: boolean; days_overdue: number; completion_evidence: string | null; doc_id: string | null;
}
export interface ClaimsEngineering {
  claims: Claim[];
  summary: { count_5y: number; incurred_5y: number; loss_ratio_5y: number; by_cause: { cause: string; count: number; incurred: number }[] };
  recommendations: Recommendation[];
  surveys: { survey_id: string; location_label: string; date: string; engineer: string; doc_id: string | null }[];
}

// ---------------------------------------------------------------- documents --
export interface DocumentMeta {
  doc_id: string;
  account_id: string | null;
  account_name: string | null;
  doc_type: string;                // 'SOV', 'Loss run', 'Declarations', 'Binder', 'Quote', 'Engineering report', 'Broker email', '3D site model', 'Aerial imagery', 'CAT exposure file', 'CAT event loss table', 'CAT EP curve', 'Guidelines', 'Authority matrix', 'Form', 'Endorsement', 'ACORD 125', 'ACORD 140', 'Appraisal', 'Certificate', 'Vendor payload', 'Rule'
  title: string;
  filename: string;
  format: DocFormat;
  received_at: string;
  source_channel: 'Broker email' | 'Broker portal' | 'PAS (mock)' | 'Claims (mock)' | 'Engineering (mock)' | 'Vendor (mock)' | 'CAT (mock)' | 'Platform' | 'Reference';
  size_bytes: number;
  term: string | null;
  is_sample: boolean;
  extraction: { status: 'EXTRACTED' | 'NOT_APPLICABLE' | 'PENDING'; fields: number; avg_confidence: number | null } | null;
}

export interface XlsxCell { v: string | number | boolean | null; t: 's' | 'n' | 'b' | 'd' | 'f' | 'z'; f?: string; bold?: boolean; fill?: string; num_fmt?: string; }
export interface XlsxSheet {
  name: string;
  hidden: boolean;
  max_row: number;
  max_col: number;
  cells: Record<string, XlsxCell>; // key "A1"
  merges: string[];                // ["A1:D1"]
  hidden_rows: number[];           // 1-based
  hidden_cols: string[];           // ["F"]
  col_widths: Record<string, number>; // chars
  freeze: string | null;
}
export interface XlsxPayload { sheets: XlsxSheet[]; }

export interface EmlPayload {
  from: string; to: string[]; cc: string[]; subject: string; date: string;
  text: string; html: string | null;
  attachments: { filename: string; doc_id: string | null; size_bytes: number; content_type: string }[];
  highlights: { text: string; field_code: string; obs_id: string }[];
}

export interface ExtractionPayload {
  doc_id: string;
  method: string;                  // "SOV parser v2 (header band detection + synonym map)"
  fields: { obs_id: string; field_code: string; label: string; subject_label: string; value_display: string; anchor: Anchor; confidence: number }[];
  issues: { code: string; label: string; anchor: Anchor | null; severity: Severity }[];
}

// ---------------------------------------------------------------- book --
export interface BookSummary {
  as_of: string;
  carrier: string;
  renewals: number;
  locations: number;
  tiv: number;
  premium_expiring: number;
  fast_track: number;
  material_action: number;
  not_started: number;
  pipeline: { identified: number; validated: number; approved: number; corrected: number };
  rarc_reported: number;
  rarc_computed: number;
  adequacy_hist: { bucket: string; count: number; premium: number }[];
  by_family: { family: string; label: string; count: number; impact_usd: number }[];
  by_action: { action: ActionType; count: number; impact_usd: number }[];
  by_underwriter: { user_id: string; name: string; accounts: number; findings: number; impact_usd: number; pricing_deviations: number; avg_rarc: number }[];
  by_broker: { broker: string; accounts: number; premium: number; impact_usd: number; avg_rarc: number }[];
  by_month: { month: string; renewals: number; premium: number; fast_track: number; action: number }[];
  accumulation: AccumulationZone[];
}

export interface AccumulationZone {
  zone_id: string; name: string; peril: string;
  lat: number; lon: number; radius_km: number;
  threshold: number;               // net PML capacity
  current: number;                 // before renewals
  post_renewal: number;            // if all renewals bound as proposed
  utilization: number;             // post_renewal / threshold
  accounts: { account_id: string; name: string; contribution: number }[];
}

// ---------------------------------------------------------------- rules --
export interface RuleTestCase { name: string; fixture: Record<string, unknown>; expect: RuleOutcome | 'NOT_APPLICABLE'; }
export interface Rule {
  rule_id: string;
  product?: string;               // renewal | decision | delegated
  version: number;
  family: string;
  title: string;
  effective_from: string;
  effective_to: string | null;
  scope: Record<string, unknown>;
  applies_to: 'account' | 'location' | 'contract_field' | 'claim_group' | 'recommendation' | 'referral' | 'subjectivity';
  when: string;                    // CEL-style expression
  outcome: RuleOutcome;
  severity: Severity;
  expected: string;
  referral_level: number | null;
  impact_method: string;
  source: string;
  origin: 'standard_library' | 'carrier_guideline';
  tests: RuleTestCase[];
  stats: { fired: number; accepted: number; rejected: number; precision: number | null };
  yaml: string;
}
export interface RuleTestResult { name: string; expected: string; actual: string; pass: boolean; error?: string | null; }
export interface BacktestResult {
  control_set: string; accounts: number;
  before: number; after: number;
  added: { account_id: string; account_name: string; subject_label: string; observed: string }[];
  removed: { account_id: string; account_name: string; subject_label: string; observed: string }[];
  duration_ms: number;
}

// ---------------------------------------------------------------- data quality --
export interface DataQualityAccount {
  account_id: string; name: string; score: number; // 0..100, weighted by modelled-loss impact
  missing_fields: number; low_confidence: number; stale_fields: number; unmatched_locations: number; conflicts: number;
  top_gaps: { location_label: string; field: string; reason: string; impact_rank: number; aal_weight: number }[];
}
export interface DataQualitySummary {
  avg_score: number;
  extraction: { documents: number; fields: number; avg_confidence: number; human_review_queue: number };
  matching: { matched: number; new: number; deleted: number; ambiguous: number; merged: number; split: number };
  accounts: DataQualityAccount[];
  review_queue: { item_id: string; account_id: string; account_name: string; kind: 'LOCATION_MATCH' | 'LOW_CONFIDENCE' | 'MAPPING'; label: string; detail: string; options?: string[] }[];
}

// ---------------------------------------------------------------- pipeline & demo --
export interface PipelineStage {
  code: string;                    // '01'..'15'
  name: string;
  group: string;
  component: string;
  mode: 'REAL' | 'BASIC' | 'MOCK';
  description: string;
  counts: { label: string; value: number }[];
  port: string | null;             // "PolicyAdminPort"
}
export interface DemoState {
  clock: string;
  start: string;
  end: string;
  events_applied: number;
  events_total: number;
  next_events: { date: string; title: string; account_name: string | null }[];
  injections: Record<string, boolean>; // fault-injection toggles
}
export interface AdvanceResult { clock: string; applied: TimelineEvent[]; new_findings: number; }

export interface OutboxMessage {
  message_id: string; at: string; channel: 'email' | 'broker_portal' | 'in_app';
  to: string; subject: string; body: string; account_id: string | null; related: string | null; href?: string; product?: string; }
export interface MockSystem { port: string; name: string; stands_in_for: string; status: 'UP'; records: number; last_sync: string; }

export interface SearchHit { kind: 'account' | 'document' | 'rule' | 'finding'; id: string; title: string; subtitle: string; href: string; }

export interface ObservationDetail { observation: Observation; field: ResolvedField; document: DocumentMeta | null; }
export type GeoFeatureCollection = { type: 'FeatureCollection'; features: { type: 'Feature'; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }[] };

// ---------------------------------------------------------------- pipeline stage workspaces
export type StageStatus = 'DONE' | 'READY' | 'PENDING' | 'NOT_APPLICABLE';
export interface StageColumn { key: string; label: string; kind: 'text' | 'money' | 'date' | 'pct' | 'badge' | 'doc' | 'mono'; }
export interface StageTable { title: string; columns: StageColumn[]; rows: Record<string, unknown>[]; }
export interface StageView {
  code: string; name: string; group: PipelineStage['group']; component: string; mode: PipelineStage['mode']; description: string;
  port: string | null; stands_in_for: string; account: { account_id: string; name: string; scenario: string | null; href?: string }; clock: string;
  status: StageStatus; headline: string; kpis: { label: string; value: string; tone?: 'ok' | 'crit' | 'high' }[];
  tables: StageTable[]; documents: DocumentMeta[]; events: TimelineEvent[]; findings: Finding[];
  next_action: { label: string; description: string } | null;
  product?: string;
}
export interface JourneyStep { code: string; name: string; mode: PipelineStage['mode']; status: StageStatus; headline: string; has_action: boolean; }

// ---------------------------------------------------------------- workflow playbooks
export interface PlaybookStep { index: number; code: string; label: string; action: string; say: string; status: 'DONE' | 'CURRENT' | 'UPCOMING'; result: string | null; then_say: string | null; }
export interface PlaybookBrief { audience?: string; problem?: string; story?: string[]; watch?: string[]; value?: string; questions?: string[]; real: string[]; mocked: string[]; }
export interface Playbook {
  id: string; title: string; account_id: string; account_name: string; scenario: string | null; aspects: string[]; product: string; subject_href?: string;
  intro: string; outro: string; brief: PlaybookBrief; facts: { label: string; value: string }[]; steps: PlaybookStep[]; progress: number; done: boolean; clock: string; message?: string;
}
