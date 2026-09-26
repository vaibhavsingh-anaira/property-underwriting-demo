import type { RenewalQueueItem } from '@/api/types';

export const FAMILY_LABEL: Record<string, string> = {
  classification: 'Occupancy / COPE drift', data_completeness: 'Data completeness', accumulation: 'Accumulation',
  protective_safeguards: 'Protective safeguards', cat_integrity: 'CAT data integrity', data_integrity: 'Data integrity',
  sov_integrity: 'SOV integrity', exposure: 'Exposure change', fire: 'Fire hazard', vacancy: 'Vacancy', coverage: 'Coverage gap',
  construction: 'Construction / roof',
  pricing: 'Pricing adequacy', valuation: 'Valuation', cat_terms: 'CAT terms', contract_integrity: 'Contract integrity',
  occupancy: 'Occupancy / COPE drift', engineering: 'Engineering recommendations', claims: 'Loss experience',
  cat_data: 'CAT data quality', portfolio: 'Accumulation', appetite: 'Appetite', authority: 'Authority & referral',
  data_quality: 'Data completeness', safeguards: 'Protective safeguards', security: 'Theft & security',
};

// RenewalQueueItem carries no finding families (contract gap), so the book → queue drill-down
// matches on top-finding titles. Replace with a server-side `family` filter when available.
const KEYWORDS: Record<string, RegExp> = {
  pricing: /RARC|adequacy|technical|rate given/i, valuation: /model RC|valu|flat|under-insured/i, cat_terms: /named-storm deductible|deductible .*floor/i,
  contract_integrity: /binder|issued policy|subjectivit|minimum lost|dropped/i, occupancy: /occupancy|vacan/i, engineering: /recommendation|R-\d/i,
  claims: /loss|claim|fire/i, cat_data: /CAT run|CAT model|modifiers|missing/i, portfolio: /zone|accumulation/i, appetite: /appetite|decline/i,
  authority: /approval|notice|authority/i, data_quality: /match|roof year|SOV|blank/i, safeguards: /safeguard|sprinkler|alarm|suppression|hood/i, security: /burglary|crime|stock/i,
};
export const familyMatch = (family: string, i: RenewalQueueItem) => {
  if (i.families) return i.families.includes(family);
  const re = KEYWORDS[family];
  return re ? i.top_findings.some((f) => re.test(f.title)) : true;
};
