// Book-level reference data: rules, accumulation zones, hazard layers, pipeline, mock systems, reference docs.
import type { DocumentMeta, GeoFeatureCollection, MockSystem, PipelineStage, Rule, RuleOutcome, RuleTestCase, Severity } from '@/api/types';
import { doc } from './util';

// ------------------------------------------------------------------ rules
interface RuleDef {
  id: string; v: number; family: string; title: string; applies: Rule['applies_to']; when: string; outcome: RuleOutcome; sev: Severity; expected: string;
  ref: number | null; impact: string; source: string; origin: Rule['origin']; from: string; states?: string[];
  tests: RuleTestCase[]; stats: [number, number, number];
}
const R = (d: RuleDef) => d;
const RULE_DEFS: RuleDef[] = [
  R({ id: 'CAT.WIND.DED_FLOOR', v: 4, family: 'cat_terms', title: 'Named-storm deductible floor — Tier 1/2 wind', applies: 'location', when: "loc.wind_tier in ['T1','T2'] && loc.named_storm_ded_pct < 0.03", outcome: 'TERM_BREACH', sev: 'HIGH', expected: 'named storm deductible ≥ 3% per location', ref: 3, impact: 'cat_model_delta', source: 'Property UW Guidelines 2026 §7.3, p.41', origin: 'carrier_guideline', from: '2026-07-01', states: ['FL', 'TX', 'LA', 'SC', 'NC', 'GA', 'AL', 'MS'],
    tests: [{ name: 'tampa_2pct', fixture: { loc: { state: 'FL', wind_tier: 'T1', named_storm_ded_pct: 0.02 } }, expect: 'TERM_BREACH' }, { name: 'tampa_3pct', fixture: { loc: { state: 'FL', wind_tier: 'T1', named_storm_ded_pct: 0.03 } }, expect: 'PASS' }, { name: 'ohio_2pct', fixture: { loc: { state: 'OH', wind_tier: null, named_storm_ded_pct: 0.02 } }, expect: 'NOT_APPLICABLE' }, { name: 'houston_t2_25', fixture: { loc: { state: 'TX', wind_tier: 'T2', named_storm_ded_pct: 0.025 } }, expect: 'TERM_BREACH' }],
    stats: [23, 19, 2] }),
  R({ id: 'CAT.INPUT.COMPLETENESS', v: 2, family: 'cat_data', title: 'All renewal locations present in CAT run', applies: 'account', when: 'account.sov_location_count > account.cat_location_count', outcome: 'DATA_REQUEST', sev: 'HIGH', expected: 'Every SOV location modelled before quote', ref: null, impact: 'proxy_aal', source: 'CAT Modelling Standards 2026 §3.1', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'abc_5_vs_4', fixture: { account: { sov_location_count: 5, cat_location_count: 4 } }, expect: 'DATA_REQUEST' }, { name: 'complete', fixture: { account: { sov_location_count: 8, cat_location_count: 8 } }, expect: 'PASS' }], stats: [31, 27, 3] }),
  R({ id: 'CAT.INPUT.SECONDARY_MODS', v: 1, family: 'cat_data', title: 'Secondary modifiers on top-AAL locations', applies: 'location', when: 'loc.aal_rank <= 5 && loc.roof_cover == null', outcome: 'DATA_REQUEST', sev: 'MEDIUM', expected: 'Roof cover / anchorage populated on top-5 AAL locations', ref: null, impact: 'aal_uncertainty', source: 'CAT Modelling Standards 2026 §3.4', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'top_missing', fixture: { loc: { aal_rank: 2, roof_cover: null } }, expect: 'DATA_REQUEST' }, { name: 'tail_missing', fixture: { loc: { aal_rank: 14, roof_cover: null } }, expect: 'PASS' }], stats: [58, 36, 19] }),
  R({ id: 'PRC.RARC.BAND', v: 2, family: 'pricing', title: 'Computed RARC outside L1 band', applies: 'account', when: 'pricing.rarc < -0.05', outcome: 'REFER', sev: 'HIGH', expected: 'RARC ≥ −5% (L1); ≥ −10% (L2)', ref: 2, impact: 'expected_minus_proposed', source: 'Pricing Authority Matrix 2026 §2.1', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'abc_minus_8', fixture: { pricing: { rarc: -0.081 } }, expect: 'REFER' }, { name: 'flat', fixture: { pricing: { rarc: 0.0 } }, expect: 'PASS' }], stats: [41, 33, 6] }),
  R({ id: 'PRC.ADEQ.FLOOR', v: 3, family: 'pricing', title: 'Adequacy floor vs technical premium', applies: 'account', when: 'pricing.adequacy < 0.95', outcome: 'REFER', sev: 'HIGH', expected: 'Proposed ≥ 95% of TP(E1,T1)', ref: 3, impact: 'tp_minus_proposed', source: 'Property UW Guidelines 2026 §4.2, p.18', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'at_953', fixture: { pricing: { adequacy: 0.953 } }, expect: 'PASS' }, { name: 'at_89', fixture: { pricing: { adequacy: 0.89 } }, expect: 'REFER' }], stats: [22, 20, 1] }),
  R({ id: 'VAL.RC.RATIO', v: 3, family: 'valuation', title: 'Reported value vs model replacement cost', applies: 'location', when: 'loc.reported_rc / loc.model_rc < 0.80', outcome: 'PRICE_ADJUST', sev: 'HIGH', expected: 'Reported ≥ 80% of model RC', ref: null, impact: 'rc_gap_x_rol', source: 'Valuation Standards 2026 §1.2', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'dayton_71', fixture: { loc: { reported_rc: 49400000, model_rc: 69600000 } }, expect: 'PRICE_ADJUST' }, { name: 'reno_90', fixture: { loc: { reported_rc: 26000000, model_rc: 28900000 } }, expect: 'PASS' }], stats: [37, 24, 11] }),
  R({ id: 'VAL.FLAT.MULTIYEAR', v: 1, family: 'valuation', title: 'Values flat across 3 renewals', applies: 'location', when: 'loc.tiv_3y_ago == loc.tiv_current', outcome: 'FLAG', sev: 'MEDIUM', expected: 'Values trended at least by construction-cost index', ref: null, impact: 'trend_gap_x_rol', source: 'Valuation Standards 2026 §1.4', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'harborview_flat', fixture: { loc: { tiv_3y_ago: 20600000, tiv_current: 20600000, years_since_appraisal: 5 } }, expect: 'FLAG' }, { name: 'recent_appraisal_flat', fixture: { loc: { tiv_3y_ago: 12000000, tiv_current: 12000000, years_since_appraisal: 1 } }, expect: 'PASS' }, { name: 'trended', fixture: { loc: { tiv_3y_ago: 12000000, tiv_current: 13900000, years_since_appraisal: 4 } }, expect: 'PASS' }], stats: [44, 17, 22] }),
  R({ id: 'CTR.BINDER_POLICY.SUBLIMIT', v: 1, family: 'contract_integrity', title: 'Binder ↔ issued policy — sublimits', applies: 'contract_field', when: 'field.binder != field.policy', outcome: 'TERM_BREACH', sev: 'CRITICAL', expected: 'Issued policy equals binder', ref: null, impact: 'delta_limit_x_p_reach', source: 'Standard library — contract integrity', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'abc_bi', fixture: { field: { binder: 10000000, policy: 15000000 } }, expect: 'TERM_BREACH' }, { name: 'match', fixture: { field: { binder: 5000000, policy: 5000000 } }, expect: 'PASS' }], stats: [12, 12, 0] }),
  R({ id: 'CTR.BINDER_POLICY.DEDUCTIBLE', v: 1, family: 'contract_integrity', title: 'Binder ↔ issued policy — deductibles & minimums', applies: 'contract_field', when: 'field.binder != field.policy', outcome: 'TERM_BREACH', sev: 'HIGH', expected: 'Issued policy equals binder', ref: null, impact: 'delta_aal', source: 'Standard library — contract integrity', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'aurelia_min', fixture: { field: { binder: '5%/250000', policy: '5%/0' } }, expect: 'TERM_BREACH' }], stats: [8, 8, 0] }),
  R({ id: 'CTR.FORMS.SAFEGUARD', v: 1, family: 'contract_integrity', title: 'Protective safeguard endorsement carried to policy', applies: 'contract_field', when: "field.binder == 'Required' && field.policy == null", outcome: 'TERM_BREACH', sev: 'HIGH', expected: 'CP 04 11 attached as bound', ref: null, impact: 'qualitative', source: 'Standard library — contract integrity', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'dropped', fixture: { field: { binder: 'Required', policy: null } }, expect: 'TERM_BREACH' }, { name: 'kept', fixture: { field: { binder: 'Required', policy: 'Required' } }, expect: 'PASS' }], stats: [5, 5, 0] }),
  R({ id: 'CTR.SUBJ.AGING', v: 2, family: 'contract_integrity', title: 'Subjectivity open after bind', applies: 'subjectivity', when: "subj.status == 'OPEN' && subj.age_days > 30", outcome: 'CONDITION', sev: 'MEDIUM', expected: 'Subjectivities cleared ≤ 30 days after bind', ref: null, impact: 'qualitative', source: 'Standard library — subjectivities', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'aurelia_212', fixture: { subj: { status: 'OPEN', age_days: 212 } }, expect: 'CONDITION' }, { name: 'fresh', fixture: { subj: { status: 'OPEN', age_days: 12 } }, expect: 'PASS' }], stats: [14, 11, 2] }),
  R({ id: 'AUTH.APPROVAL.TERMS_HASH', v: 1, family: 'authority', title: 'Approval valid only for the terms it approved', applies: 'referral', when: "referral.status == 'APPROVED' && referral.terms_hash != quote.terms_hash", outcome: 'REFER', sev: 'CRITICAL', expected: 'Bound terms hash equals approved hash', ref: 3, impact: 'control_exposure', source: 'Authority Matrix 2026 §1.4', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'aurelia_v3', fixture: { referral: { status: 'APPROVED', terms_hash: '9f3a17c2' }, quote: { terms_hash: 'c41e08b5' } }, expect: 'REFER' }, { name: 'same_hash', fixture: { referral: { status: 'APPROVED', terms_hash: '9f3a17c2' }, quote: { terms_hash: '9f3a17c2' } }, expect: 'PASS' }], stats: [3, 3, 0] }),
  R({ id: 'NOTICE.LATEST_DATE', v: 1, family: 'authority', title: 'Non-renewal / conditional notice deadline', applies: 'account', when: 'notice.required && notice.days_remaining < 30 && action.requires_notice', outcome: 'BLOCK', sev: 'HIGH', expected: 'Notice issued before latest valid date', ref: null, impact: 'control', source: 'Demo notice table v1 — illustrative, verify with counsel', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'delta_16d', fixture: { notice: { required: true, days_remaining: 16 }, action: { requires_notice: true } }, expect: 'BLOCK' }, { name: 'es_exempt', fixture: { notice: { required: false, days_remaining: 10 }, action: { requires_notice: true } }, expect: 'PASS' }], stats: [6, 6, 0] }),
  R({ id: 'OCC.DRIFT.HAZARD', v: 2, family: 'occupancy', title: 'Occupancy drift to a higher hazard class', applies: 'location', when: 'loc.hazard_rank_now > loc.hazard_rank_rated', outcome: 'CONDITION', sev: 'HIGH', expected: 'Occupancy matches rated class; re-survey if hazard rises', ref: null, impact: 'rate_differential', source: 'Property UW Guidelines 2026 §9.4', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'reno_liion', fixture: { loc: { hazard_rank_now: 5, hazard_rank_rated: 2 } }, expect: 'CONDITION' }, { name: 'same', fixture: { loc: { hazard_rank_now: 2, hazard_rank_rated: 2 } }, expect: 'PASS' }], stats: [19, 15, 2] }),
  R({ id: 'VAC.FIRE.SPRINKLER_OFF', v: 1, family: 'safeguards', title: 'Vacant and sprinkler impaired', applies: 'location', when: "loc.vacancy_pct > 0.5 && loc.sprinkler_status == 'IMPAIRED'", outcome: 'REFER', sev: 'CRITICAL', expected: 'Impairment restored ≤ 10 days or fire watch + referral', ref: 3, impact: 'pml_uplift', source: 'Property UW Guidelines 2026 §8.2 (catalogue §41)', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'pinecrest', fixture: { loc: { vacancy_pct: 0.62, sprinkler_status: 'IMPAIRED' } }, expect: 'REFER' }, { name: 'occupied', fixture: { loc: { vacancy_pct: 0.1, sprinkler_status: 'IMPAIRED' } }, expect: 'PASS' }], stats: [2, 2, 0] }),
  R({ id: 'SPK.ADEQ.HEIGHT', v: 1, family: 'safeguards', title: 'Storage height within sprinkler design', applies: 'location', when: 'loc.storage_height_ft > loc.sprinkler_design_height_ft', outcome: 'BLOCK', sev: 'CRITICAL', expected: 'Storage height ≤ sprinkler design height', ref: null, impact: 'pml_uplift', source: 'Risk Engineering Standards §6 (NFPA 13 / FM DS 8-9)', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'memphis_28_20', fixture: { loc: { storage_height_ft: 28, sprinkler_design_height_ft: 20 } }, expect: 'BLOCK' }, { name: 'ok', fixture: { loc: { storage_height_ft: 18, sprinkler_design_height_ft: 20 } }, expect: 'PASS' }], stats: [6, 5, 0] }),
  R({ id: 'SAFE.CP0411.VERIFIED', v: 2, family: 'safeguards', title: 'Protective safeguard relied on is verified', applies: 'location', when: 'loc.safeguard_required && !loc.safeguard_certificate_current', outcome: 'CONDITION', sev: 'HIGH', expected: 'Current certificate for every CP 04 11 safeguard', ref: null, impact: 'breach_probability', source: 'Theft & Security Guidelines 2026 §40.2', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'lumen_local_bell', fixture: { loc: { safeguard_required: true, safeguard_certificate_current: false } }, expect: 'CONDITION' }], stats: [16, 11, 4] }),
  R({ id: 'SAFE.COOKING.VERIFIED', v: 1, family: 'safeguards', title: 'Cooking suppression & hood cleaning verified', applies: 'location', when: 'loc.cooking && loc.hood_cert_age_days > 180', outcome: 'CONDITION', sev: 'HIGH', expected: 'NFPA 96 certificate ≤ 6 months', ref: null, impact: 'fire_loading', source: 'Occupancy add-on §39 (restaurants)', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'ember_site7', fixture: { loc: { cooking: true, hood_cert_age_days: 410 } }, expect: 'CONDITION' }], stats: [9, 8, 1] }),
  R({ id: 'ENG.REC.OVERDUE', v: 2, family: 'engineering', title: 'Engineering recommendation overdue', applies: 'recommendation', when: "rec.status in ['OPEN','IN_PROGRESS'] && rec.days_overdue > 0", outcome: 'CONDITION', sev: 'MEDIUM', expected: 'Closed with evidence by due date', ref: null, impact: 'attritional_loading', source: 'Risk Engineering Standards §3', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'r114', fixture: { rec: { status: 'OPEN', days_overdue: 94, severity: 'HIGH' } }, expect: 'CONDITION' }, { name: 'low_sev_1d', fixture: { rec: { status: 'OPEN', days_overdue: 1, severity: 'LOW' } }, expect: 'CONDITION' }], stats: [64, 34, 24] }),
  R({ id: 'ENG.REC.UNVERIFIED_CLOSE', v: 1, family: 'engineering', title: 'Bind-condition recommendation closed without evidence', applies: 'recommendation', when: "rec.status == 'CLOSED' && rec.bind_condition && rec.completion_evidence == null", outcome: 'CONDITION', sev: 'CRITICAL', expected: 'VERIFIED_CLOSED with engineer sign-off', ref: 3, impact: 'qualitative', source: 'Risk Engineering Standards §3.4 (catalogue §45)', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'keystone_r088', fixture: { rec: { status: 'CLOSED', bind_condition: true, completion_evidence: null } }, expect: 'CONDITION' }], stats: [7, 7, 0] }),
  R({ id: 'CLM.REPEAT.CAUSE', v: 1, family: 'claims', title: 'Repeat cause at the same building', applies: 'claim_group', when: 'claims.same_cause_same_building_12m >= 2', outcome: 'FLAG', sev: 'MEDIUM', expected: 'No repeat cause within 12 months', ref: null, impact: 'experience_mod', source: 'Property UW Guidelines 2026 §5.1', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'abc_austin_water', fixture: { claims: { same_cause_same_building_12m: 2 } }, expect: 'FLAG' }], stats: [21, 15, 4] }),
  R({ id: 'PORT.ZONE.UTIL', v: 1, family: 'portfolio', title: 'Accumulation zone utilisation after renewal', applies: 'account', when: 'zone.utilization_post > 0.90', outcome: 'REFER', sev: 'HIGH', expected: 'Zone ≤ 90% post-renewal without senior referral', ref: 3, impact: 'control_exposure', source: 'Portfolio Management Guidelines 2026 §2', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'tampa_93', fixture: { zone: { utilization_post: 0.93 } }, expect: 'REFER' }, { name: 'miami_81', fixture: { zone: { utilization_post: 0.81 } }, expect: 'PASS' }], stats: [11, 9, 1] }),
  R({ id: 'APP.CLASS.DECLINE', v: 3, family: 'appetite', title: 'Class out of appetite', applies: 'account', when: "account.occupancy_class in ['3089','5093','2421']", outcome: 'DECLINE', sev: 'CRITICAL', expected: 'Class in appetite under current guideline version', ref: 4, impact: 'premium_at_stake', source: 'Property UW Guidelines 2026 Appendix A, p.72', origin: 'carrier_guideline', from: '2026-07-01',
    tests: [{ name: 'delta_scrap', fixture: { account: { occupancy_class: '3089' } }, expect: 'DECLINE' }, { name: 'office', fixture: { account: { occupancy_class: '1100' } }, expect: 'PASS' }], stats: [3, 3, 0] }),
  R({ id: 'SEC.CRIME.SCORE', v: 1, family: 'security', title: 'High burglary score with high stock values', applies: 'location', when: 'loc.burglary_pctile >= 85 && loc.stock_value > 1000000', outcome: 'REFER', sev: 'HIGH', expected: '< 85th percentile or enhanced security', ref: 3, impact: 'theft_loading', source: 'Theft & Security Guidelines 2026 §40.1', origin: 'carrier_guideline', from: '2026-01-01',
    tests: [{ name: 'lumen_store3', fixture: { loc: { burglary_pctile: 94, stock_value: 3800000 } }, expect: 'REFER' }], stats: [12, 8, 3] }),
  R({ id: 'DQ.CONFLICT.ROOF', v: 1, family: 'data_quality', title: 'Conflicting roof year across sources', applies: 'location', when: 'field.distinct_values > 1', outcome: 'FLAG', sev: 'MEDIUM', expected: 'Single roof year; CAT input uses resolved value', ref: null, impact: 'aal_delta', source: 'Standard library — evidence resolution', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'abc_tampa', fixture: { field: { distinct_values: 3 } }, expect: 'FLAG' }], stats: [29, 12, 14] }),
  R({ id: 'DQ.MATCH.AMBIGUOUS', v: 1, family: 'data_quality', title: 'Location match below confidence threshold', applies: 'location', when: 'loc.match_score < 0.85 && !loc.match_confirmed', outcome: 'DATA_REQUEST', sev: 'MEDIUM', expected: 'Match score ≥ 0.85 or human-confirmed', ref: null, impact: 'qualitative', source: 'Standard library — entity resolution', origin: 'standard_library', from: '2025-01-01',
    tests: [{ name: 'summit_b07', fixture: { loc: { match_score: 0.71, match_confirmed: false } }, expect: 'DATA_REQUEST' }, { name: 'confirmed', fixture: { loc: { match_score: 0.71, match_confirmed: true } }, expect: 'PASS' }], stats: [18, 16, 1] }),
];

export function ruleYaml(d: { id: string; v: number; family: string; title: string; from: string; states?: string[]; applies: string; when: string; outcome: string; sev: string; expected: string; ref: number | null; impact: string; source: string; tests: RuleTestCase[] }) {
  return [
    `id: ${d.id}`, `version: ${d.v}`, `family: ${d.family}`, `title: "${d.title}"`, `effective_from: ${d.from}`, 'scope:', '  lob: commercial_property',
    ...(d.states ? [`  states: [${d.states.join(', ')}]`] : []), '  segment: [middle_market, large]', `applies_to: ${d.applies}`, `when: ${d.when}`, 'outcome:', `  type: ${d.outcome}`, `  severity: ${d.sev.toLowerCase()}`,
    `  expected: "${d.expected}"`, ...(d.ref ? [`  referral_level: ${d.ref}`] : []), '  exception_allowed: true', 'impact:', `  method: ${d.impact}`, `source: "${d.source}"`, 'tests:',
    ...d.tests.flatMap((t) => [`  - name: ${t.name}`, `    fixture: ${JSON.stringify(t.fixture)}`, `    expect: ${t.expect}`]),
  ].join('\n') + '\n';
}

export const RULES: Rule[] = RULE_DEFS.map((d) => ({
  rule_id: d.id, version: d.v, family: d.family, title: d.title, effective_from: d.from, effective_to: null,
  scope: { lob: 'commercial_property', ...(d.states ? { states: d.states } : {}), segment: ['middle_market', 'large'] },
  applies_to: d.applies, when: d.when, outcome: d.outcome, severity: d.sev, expected: d.expected, referral_level: d.ref, impact_method: d.impact, source: d.source, origin: d.origin,
  tests: d.tests, stats: { fired: d.stats[0], accepted: d.stats[1], rejected: d.stats[2], precision: d.stats[1] + d.stats[2] ? d.stats[1] / (d.stats[1] + d.stats[2]) : null },
  yaml: ruleYaml(d),
}));

// ------------------------------------------------------------------ accumulation zones (accounts filled by store)
export const ZONES = [
  { zone_id: 'zn-tampa', name: 'Tampa Bay', peril: 'Named storm', lat: 27.94, lon: -82.46, radius_km: 45, threshold: 350e6, current: 301e6, post_renewal: 325.5e6 },
  { zone_id: 'zn-houston', name: 'Houston–Galveston', peril: 'Named storm', lat: 29.55, lon: -95.2, radius_km: 70, threshold: 380e6, current: 312e6, post_renewal: 334e6 },
  { zone_id: 'zn-miami', name: 'Miami-Dade / Broward', peril: 'Named storm', lat: 25.9, lon: -80.25, radius_km: 50, threshold: 420e6, current: 318e6, post_renewal: 341e6 },
  { zone_id: 'zn-charleston', name: 'Charleston–Low Country', peril: 'Named storm', lat: 32.6, lon: -80.2, radius_km: 80, threshold: 200e6, current: 142e6, post_renewal: 151e6 },
  { zone_id: 'zn-nola', name: 'New Orleans / Gulf LA', peril: 'Named storm', lat: 30.0, lon: -90.6, radius_km: 120, threshold: 220e6, current: 148e6, post_renewal: 158e6 },
  { zone_id: 'zn-la', name: 'Los Angeles Basin', peril: 'Earthquake', lat: 34.05, lon: -118.25, radius_km: 60, threshold: 300e6, current: 214e6, post_renewal: 231e6 },
  { zone_id: 'zn-bay', name: 'San Francisco Bay Area', peril: 'Earthquake', lat: 37.55, lon: -122.05, radius_km: 70, threshold: 260e6, current: 171e6, post_renewal: 179e6 },
  { zone_id: 'zn-madrid', name: 'New Madrid (Memphis)', peril: 'Earthquake', lat: 35.4, lon: -89.9, radius_km: 110, threshold: 180e6, current: 96e6, post_renewal: 104e6 },
  { zone_id: 'zn-reno', name: 'Reno–Carson', peril: 'Earthquake', lat: 39.4, lon: -119.8, radius_km: 60, threshold: 90e6, current: 42e6, post_renewal: 43.5e6 },
  { zone_id: 'zn-nova', name: 'Northern Virginia', peril: 'Terrorism / fire following', lat: 38.95, lon: -77.45, radius_km: 35, threshold: 64e6, current: 39e6, post_renewal: 41e6 },
];

// ------------------------------------------------------------------ hazards
const poly = (layer: string, tier: string, label: string, ring: [number, number][]) => ({ type: 'Feature' as const, geometry: { type: 'Polygon', coordinates: [[...ring, ring[0]]] }, properties: { layer, tier, label } });
export const HAZARDS: GeoFeatureCollection = {
  type: 'FeatureCollection',
  features: [
    poly('wind', 'T1', 'Tier 1 wind — Florida Gulf', [[-87.6, 30.45], [-85.3, 30.2], [-84.2, 30.2], [-83.1, 29.35], [-82.55, 28.0], [-82.0, 26.4], [-81.2, 25.4], [-80.8, 25.2], [-81.3, 25.9], [-82.1, 27.3], [-82.3, 28.3], [-82.8, 29.4], [-84.1, 29.9], [-85.4, 29.95], [-87.6, 30.2]]),
    poly('wind', 'T1', 'Tier 1 wind — Florida Atlantic', [[-80.05, 25.2], [-80.15, 26.8], [-80.45, 27.9], [-80.9, 29.3], [-81.35, 30.7], [-81.75, 30.7], [-81.3, 29.3], [-80.8, 27.9], [-80.55, 26.8], [-80.45, 25.4]]),
    poly('wind', 'T1', 'Tier 1 wind — Texas / Louisiana coast', [[-97.6, 25.9], [-97.2, 27.8], [-96.3, 28.6], [-95.0, 29.2], [-93.8, 29.7], [-92.0, 29.5], [-90.2, 29.0], [-89.2, 29.2], [-89.4, 30.3], [-90.3, 30.2], [-92.0, 29.95], [-93.9, 30.1], [-95.1, 29.7], [-96.4, 29.0], [-97.4, 28.2], [-97.9, 26.1]]),
    poly('wind', 'T1', 'Tier 1 wind — Carolinas / Georgia coast', [[-81.4, 30.8], [-81.0, 31.9], [-80.2, 32.6], [-79.1, 33.4], [-77.9, 33.9], [-76.5, 34.7], [-75.5, 35.3], [-75.8, 36.0], [-76.9, 35.2], [-78.1, 34.3], [-79.3, 33.8], [-80.5, 32.9], [-81.3, 32.1], [-81.7, 30.9]]),
    poly('wind', 'T2', 'Tier 2 wind — Gulf inland band', [[-97.9, 26.1], [-97.4, 28.2], [-96.4, 29.0], [-95.1, 29.7], [-93.9, 30.1], [-92.0, 29.95], [-90.3, 30.2], [-89.4, 30.3], [-87.6, 30.45], [-87.6, 31.1], [-89.5, 31.0], [-91.2, 30.9], [-93.9, 30.8], [-95.4, 30.4], [-96.9, 29.6], [-98.1, 28.3], [-98.4, 26.3]]),
    poly('wind', 'T2', 'Tier 2 wind — Florida interior', [[-82.3, 28.3], [-82.1, 27.3], [-81.3, 25.9], [-80.45, 25.4], [-80.55, 26.8], [-80.8, 27.9], [-81.3, 29.3], [-81.75, 30.7], [-82.4, 30.6], [-82.8, 29.4]]),
    poly('flood', 'A', 'SFHA — Lower Mississippi corridor', [[-91.3, 29.9], [-90.4, 29.7], [-89.9, 30.2], [-90.8, 31.5], [-91.2, 33.0], [-90.7, 34.8], [-89.9, 35.6], [-90.3, 35.8], [-91.4, 34.6], [-91.7, 33.0], [-91.5, 31.4]]),
    poly('flood', 'AE', 'SFHA — Houston bayous', [[-95.8, 29.6], [-95.1, 29.5], [-94.9, 29.85], [-95.4, 30.05], [-95.85, 29.95]]),
    poly('flood', 'AE', 'SFHA — Tampa Bay surge', [[-82.8, 27.55], [-82.4, 27.6], [-82.35, 28.05], [-82.7, 28.1], [-82.85, 27.85]]),
    poly('eq', 'Zone 4', 'High seismic — San Andreas system', [[-124.2, 40.3], [-122.2, 38.9], [-121.1, 36.9], [-119.3, 35.1], [-117.0, 34.0], [-115.4, 32.6], [-116.2, 32.5], [-117.9, 33.6], [-120.1, 35.0], [-121.9, 36.6], [-123.0, 38.2], [-124.4, 39.9]]),
    poly('eq', 'Zone 3', 'Walker Lane — Reno / Carson', [[-120.3, 40.1], [-119.3, 40.0], [-118.8, 38.8], [-119.4, 38.6], [-120.1, 39.2]]),
    poly('eq', 'Zone 3', 'New Madrid Seismic Zone', [[-90.6, 35.0], [-89.2, 35.3], [-88.8, 36.9], [-89.6, 37.3], [-90.5, 36.3]]),
    poly('eq', 'Zone 3', 'Cascadia — Puget Sound', [[-123.2, 46.9], [-121.8, 46.9], [-121.8, 48.4], [-123.0, 48.4]]),
    poly('wildfire', 'Very high', 'WUI — Sierra foothills', [[-121.9, 40.2], [-120.8, 40.3], [-119.4, 37.6], [-118.7, 36.2], [-119.6, 36.1], [-120.6, 37.5], [-121.5, 39.1]]),
    poly('wildfire', 'Very high', 'WUI — Southern California', [[-119.6, 34.7], [-118.0, 34.5], [-116.6, 33.9], [-116.8, 33.2], [-117.9, 34.0], [-119.2, 34.2]]),
    poly('wildfire', 'High', 'WUI — Colorado Front Range', [[-105.6, 40.6], [-105.1, 40.6], [-104.9, 39.0], [-105.4, 38.8], [-105.8, 39.6]]),
  ],
};

// ------------------------------------------------------------------ pipeline
export const PIPELINE: Omit<PipelineStage, 'counts'>[] = [
  { code: '01', name: 'Submission received', group: 'Intake & qualification', component: 'Broker mailbox + portal', mode: 'MOCK', description: 'Scripted broker emails with attachments arrive on demo dates; auto-replies to data requests after N days.', port: 'BrokerMailboxPort' },
  { code: '02', name: 'Clearance', group: 'Intake & qualification', component: 'Clearance service', mode: 'MOCK', description: 'Duplicate check, broker licence table, sanctions fixture list.', port: 'ClearancePort' },
  { code: '03', name: 'Appetite & triage', group: 'Intake & qualification', component: 'Rule engine', mode: 'REAL', description: 'Current guideline version applied; decline or refer with reason and citation.', port: null },
  { code: '04', name: 'Extraction & enrichment', group: 'Intake & qualification', component: 'Ingestion + vendor stubs', mode: 'REAL', description: 'SOV / PDF / email extraction with anchors; geocoder, hazard, crime, valuation, imagery vendor stubs.', port: 'VendorDataPort' },
  { code: '05', name: 'Risk assessment', group: 'Technical decision', component: 'Engineering module', mode: 'MOCK', description: 'Survey ordered → report arrives → recommendation register updates (incl. closed-without-evidence case).', port: 'EngineeringPort' },
  { code: '06', name: 'Pricing & modelling', group: 'Technical decision', component: 'Rater + CAT stubs', mode: 'MOCK', description: 'rater-stub v1.4 and MockCat 23.1, each callable three times for the RARC split.', port: 'RaterPort · CatModelPort' },
  { code: '07', name: 'Authority & portfolio', group: 'Technical decision', component: 'Authority + accumulation', mode: 'REAL', description: 'Authority matrix on intended terms; approvals locked to terms hash; zone-grid accumulation.', port: null },
  { code: '08', name: 'Terms & quote', group: 'Placement & issuance', component: 'Quote builder', mode: 'BASIC', description: 'Terms editor → quote version (hashed) → quote PDF from template.', port: null },
  { code: '09', name: 'Broker negotiation', group: 'Placement & issuance', component: 'Broker bot', mode: 'MOCK', description: 'Scripted counters: accept within X% of target, else counter once, then accept or walk.', port: 'BrokerMailboxPort' },
  { code: '10', name: 'Bind', group: 'Placement & issuance', component: 'Bind flow', mode: 'BASIC', description: 'Binder PDF with subjectivities; authority re-checked on final terms.', port: null },
  { code: '11', name: 'Policy issuance & billing', group: 'Placement & issuance', component: 'Policy admin + billing stubs', mode: 'MOCK', description: 'Stores policy, forms, safeguards; dec page; issuance-error toggle creates S2/S8 mismatches; booked premium.', port: 'PolicyAdminPort · BillingPort' },
  { code: '12', name: 'Mid-term monitoring', group: 'Feedback loop', component: 'PAS endorsements + claims stub', mode: 'MOCK', description: 'Endorsements and FNOL/reserve events on the demo timeline trigger real re-evaluation.', port: 'PolicyAdminPort · ClaimsPort' },
  { code: '13', name: 'Claims & exposure feedback', group: 'Feedback loop', component: 'Outcome capture', mode: 'REAL', description: 'Claims and endorsements feed outcome and risk-quality deltas.', port: null },
  { code: '14', name: 'Portfolio steering', group: 'Feedback loop', component: 'Book view', mode: 'REAL', description: 'CUO view, accumulation, exceptions by underwriter and broker.', port: null },
  { code: '15', name: 'Renewal', group: 'Feedback loop', component: 'Renewal engine', mode: 'REAL', description: 'Passes 1–3; account re-enters stage 03 for the next term.', port: null },
];

export const MOCK_SYSTEMS: MockSystem[] = [
  { port: 'PolicyAdminPort', name: 'PAS stub', stands_in_for: 'Guidewire PolicyCenter / Duck Creek', status: 'UP', records: 1284, last_sync: '2026-08-01T06:00:00Z' },
  { port: 'RaterPort', name: 'rater-stub v1.4', stands_in_for: 'Carrier rater (Excel / hx Renew)', status: 'UP', records: 3462, last_sync: '2026-08-01T06:00:00Z' },
  { port: 'CatModelPort', name: 'MockCat 23.1', stands_in_for: "Moody's RMS / Verisk Touchstone", status: 'UP', records: 318, last_sync: '2026-07-31T22:10:00Z' },
  { port: 'ClaimsPort', name: 'Claims stub', stands_in_for: 'Guidewire ClaimCenter', status: 'UP', records: 612, last_sync: '2026-08-01T06:00:00Z' },
  { port: 'EngineeringPort', name: 'Engineering stub', stands_in_for: 'Risk engineering system (e.g. Riskonnect)', status: 'UP', records: 874, last_sync: '2026-08-01T05:30:00Z' },
  { port: 'BrokerMailboxPort', name: 'Broker mailbox + bot', stands_in_for: 'Underwriting inbox / broker portal', status: 'UP', records: 1906, last_sync: '2026-08-01T07:12:00Z' },
  { port: 'VendorDataPort', name: 'Vendor stubs', stands_in_for: 'Geocoder, hazard, crime, valuation (e.g. e2Value), imagery (e.g. Nearmap)', status: 'UP', records: 4120, last_sync: '2026-08-01T04:00:00Z' },
  { port: 'BillingPort', name: 'Billing stub', stands_in_for: 'Guidewire BillingCenter', status: 'UP', records: 1190, last_sync: '2026-08-01T06:00:00Z' },
  { port: 'ClearancePort', name: 'Clearance stub', stands_in_for: 'Clearance / sanctions (OFAC) service', status: 'UP', records: 120, last_sync: '2026-08-01T06:00:00Z' },
  { port: 'NotificationPort', name: 'Mock outbox', stands_in_for: 'Email / broker portal / in-app notifications', status: 'UP', records: 0, last_sync: '2026-08-01T07:12:00Z' },
  { port: 'WarehousePort', name: 'Warehouse drop', stands_in_for: 'Carrier data warehouse extract (CSV / Parquet)', status: 'UP', records: 2400, last_sync: '2026-07-31T02:00:00Z' },
];

export const REFERENCE_DOCS: DocumentMeta[] = [
  doc({ doc_id: 'ref-guidelines-2026', doc_type: 'Guidelines', title: 'Property Underwriting Guidelines 2026', filename: 'northgate_property_uw_guidelines_2026.pdf', format: 'pdf', received_at: '2026-06-15', source_channel: 'Reference', term: null, size_bytes: 2_840_000, extraction: { status: 'EXTRACTED', fields: 212, avg_confidence: 0.96 } }),
  doc({ doc_id: 'ref-guidelines-2025', doc_type: 'Guidelines', title: 'Property Underwriting Guidelines 2025', filename: 'northgate_property_uw_guidelines_2025.pdf', format: 'pdf', received_at: '2025-06-10', source_channel: 'Reference', term: null, size_bytes: 2_610_000 }),
  doc({ doc_id: 'ref-authority-2026', doc_type: 'Authority matrix', title: 'Authority Matrix 2026', filename: 'northgate_authority_matrix_2026.xlsx', format: 'xlsx', received_at: '2026-06-15', source_channel: 'Reference', term: null, size_bytes: 38_000, extraction: { status: 'EXTRACTED', fields: 64, avg_confidence: 0.99 } }),
  doc({ doc_id: 'ref-forms', doc_type: 'Form', title: 'Form library — commercial property', filename: 'form_library_cp.pdf', format: 'pdf', received_at: '2026-01-05', source_channel: 'Reference', term: null, size_bytes: 1_120_000 }),
  doc({ doc_id: 'ref-notice-table', doc_type: 'Rule', title: 'Notice table v1 (illustrative, verify with counsel)', filename: 'notice_table_v1.yaml', format: 'yaml', received_at: '2026-06-01', source_channel: 'Reference', term: null, size_bytes: 6_200 }),
  doc({ doc_id: 'ref-rule-wind', doc_type: 'Rule', title: 'CAT.WIND.DED_FLOOR v4', filename: 'CAT.WIND.DED_FLOOR.v4.yaml', format: 'yaml', received_at: '2026-07-01', source_channel: 'Platform', term: null, size_bytes: 1_400 }),
  doc({ doc_id: 'ref-hazard-geojson', doc_type: 'Vendor payload', title: 'Hazard layers (wind tiers, SFHA, seismic, WUI)', filename: 'hazard_layers.geojson', format: 'geojson', received_at: '2026-07-15', source_channel: 'Vendor (mock)', term: null, size_bytes: 48_000 }),
];

export const NOTICE_TABLE_YAML = `# Demo notice table v1 — ILLUSTRATIVE ONLY. Verify every entry with counsel.
version: 1
admitted:
  LA: { non_renewal_days: 90, conditional_renewal_days: 90 }
  OH: { non_renewal_days: 45, conditional_renewal_days: 45 }
  TX: { non_renewal_days: 60, conditional_renewal_days: 60 }
  FL: { non_renewal_days: 45, conditional_renewal_days: 45 }
  NY: { non_renewal_days: 60, conditional_renewal_days: 60 }
  IL: { non_renewal_days: 60, conditional_renewal_days: 60 }
  SC: { non_renewal_days: 30, conditional_renewal_days: 30 }
  NC: { non_renewal_days: 45, conditional_renewal_days: 45 }
surplus_lines:
  default: { statutory_notice: false, contractual_days: 30 }
`;
