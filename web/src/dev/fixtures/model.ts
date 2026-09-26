// Internal fixture model: one bundle per account + the rater stub used for RARC.
import type {
  AccountDetail, CatResult, ClaimsEngineering, ContractDiff, Observation, RarcComponentRow, RarcResult, RarcTerms,
  XlsxPayload, EmlPayload, ExtractionPayload,
} from '@/api/types';

export interface RarcBase {
  expiring_premium: number;
  proposed_premium: number;
  tp_at_bind: number;
  expiring_terms: RarcTerms;
  proposed_terms: RarcTerms;
  brokerage_expiring: number;
  brokerage_proposed: number;
  tiv_expiring: number;
  tiv_renewal: number;
  adequacy_floor: number;
  method: RarcResult['method'];
  model_version: string;
  /** component → [TP(E0,T0), TP(E1,T0)] on expiring terms */
  components: { component: string; kind: 'aop' | 'bi' | 'wind' | 'flood' | 'eq' | 'other'; e0: number; e1: number }[];
  /** Tier-1/2 wind exposure → named-storm floor applies */
  wind_floor: number | null;
}

export interface AccountBundle {
  detail: AccountDetail;
  rarc: RarcBase | null;
  contract: ContractDiff;
  cat: CatResult[];
  claims: ClaimsEngineering;
  observations: Observation[];
  xlsx: Record<string, XlsxPayload>;
  eml: Record<string, EmlPayload>;
  extraction: Record<string, ExtractionPayload>;
  raw: Record<string, string>;
  premium_expiring: number;
  tiv_expiring: number;
  tiv_current: number;
}

const n = (x: number | null | undefined, d: number) => (x === null || x === undefined ? d : x);

/** Rater stub v1.4 — term sensitivities applied to renewal exposure on expiring terms. */
function termsAdjust(kind: string, v: number, t0: RarcTerms, t1: RarcTerms) {
  switch (kind) {
    case 'wind': {
      if (t0.named_storm_ded_pct === null || t1.named_storm_ded_pct === null) return v;
      const dp = (t1.named_storm_ded_pct - t0.named_storm_ded_pct) / 0.01;
      const dm = (n(t1.named_storm_ded_min, 0) - n(t0.named_storm_ded_min, 0)) / 100_000;
      return v * Math.max(0.45, 1 - 0.112676 * dp) * Math.max(0.8, 1 - 0.015 * dm);
    }
    case 'aop': {
      const r = Math.max(0.1, t1.aop_deductible / Math.max(1, t0.aop_deductible));
      return v * Math.max(0.6, 1 - 0.06 * Math.log2(r));
    }
    case 'bi': {
      if (!t0.bi_sublimit || !t1.bi_sublimit) return v;
      return v * Math.pow(t1.bi_sublimit / t0.bi_sublimit, 0.35);
    }
    case 'flood': {
      if (!t0.flood_sublimit || !t1.flood_sublimit) return v;
      return v * Math.pow(t1.flood_sublimit / t0.flood_sublimit, 0.4);
    }
    case 'eq': {
      if (!t0.eq_sublimit || !t1.eq_sublimit) return v;
      return v * Math.pow(t1.eq_sublimit / t0.eq_sublimit, 0.4);
    }
    default: return v;
  }
}

export function computeRarc(accountId: string, b: RarcBase, proposed_premium = b.proposed_premium, termsIn: Partial<RarcTerms> = {}, brokerage?: number): RarcResult {
  const terms: RarcTerms = { ...b.proposed_terms, ...termsIn };
  const breakdown: RarcComponentRow[] = b.components.map((c) => ({
    component: c.component, e0t0: c.e0, e1t0: c.e1, e1t1: Math.round(termsAdjust(c.kind, c.e1, b.expiring_terms, terms)),
  }));
  const e0 = breakdown.reduce((s, r) => s + r.e0t0, 0);
  const e1 = breakdown.reduce((s, r) => s + r.e1t0, 0);
  const e11 = breakdown.reduce((s, r) => s + r.e1t1, 0);
  const ef = e1 / e0, tf = e11 / e1;
  const expected = b.expiring_premium * ef * tf;
  const rarc = proposed_premium / expected - 1;
  const adequacy = proposed_premium / e11;
  const bp = brokerage ?? b.brokerage_proposed;
  const rarc_net = (proposed_premium * (1 - bp)) / (expected * (1 - b.brokerage_expiring)) - 1;

  const reasons: string[] = [];
  let level: 1 | 2 | 3 | 4 = 1;
  const bump = (l: 1 | 2 | 3 | 4, why: string) => { reasons.push(why); if (l > level) level = l; };
  if (rarc < -0.1) bump(3, `RARC ${fmt(rarc)} beyond −10% (L2 band)`);
  else if (rarc < -0.05) bump(2, `RARC ${fmt(rarc)} beyond −5% (L1 band)`);
  if (adequacy < 0.9) bump(4, `Adequacy ${fmt(adequacy, false)} below 90% — CUO only`);
  else if (adequacy < b.adequacy_floor) bump(3, `Adequacy ${fmt(adequacy, false)} below ${fmt(b.adequacy_floor, false)} floor`);
  else if (adequacy < 1) bump(2, `Adequacy ${fmt(adequacy, false)} below 100% (L1 requires ≥ technical)`);
  if (b.wind_floor !== null && terms.named_storm_ded_pct !== null && terms.named_storm_ded_pct < b.wind_floor - 1e-9)
    bump(3, `Named-storm deductible ${(terms.named_storm_ded_pct * 100).toFixed(1)}% below ${(b.wind_floor * 100).toFixed(0)}% floor — guideline exception (§7.3)`);
  if (b.expiring_terms.bi_sublimit && terms.bi_sublimit && terms.bi_sublimit > b.expiring_terms.bi_sublimit * 1.25)
    bump(2, `BI sublimit increase > 25% over expiring`);
  if (reasons.length === 0) reasons.push('Within L1 authority: RARC ≥ −5%, adequacy ≥ 100%, terms at or above guideline');

  return {
    account_id: accountId,
    expiring_premium: b.expiring_premium,
    expiring_terms: b.expiring_terms,
    proposed_terms: terms,
    tp_e0_t0: e0, tp_e1_t0: e1, tp_e1_t1: e11,
    exposure_factor: ef, terms_factor: tf,
    expected_premium: expected,
    proposed_premium,
    headline_change: proposed_premium / b.expiring_premium - 1,
    rarc, adequacy, adequacy_floor: b.adequacy_floor,
    price_deviation: proposed_premium / e11 - 1,
    required_authority_level: level,
    authority_reasons: reasons,
    method: b.method,
    model_version: b.model_version,
    model_drift: { tp_at_bind: b.tp_at_bind, tp_today_e0t0: e0, drift: e0 / b.tp_at_bind - 1 },
    net: { brokerage_expiring: b.brokerage_expiring, brokerage_proposed: bp, rarc_net },
    breakdown,
    tiv_expiring: b.tiv_expiring,
    tiv_renewal: b.tiv_renewal,
  };
}

function fmt(r: number, sign = true) {
  const v = r * 100;
  return `${sign && v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}%`;
}
