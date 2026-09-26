// Formatting helpers. Keep all number formatting here so screens are consistent.
export const usd = (n: number | null | undefined, opts: { compact?: boolean; sign?: boolean } = {}) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const sign = opts.sign && n > 0 ? '+' : '';
  const abs = Math.abs(n);
  if (opts.compact !== false && abs >= 1_000_000_000) return `${sign}${n < 0 ? '−' : ''}$${(abs / 1e9).toFixed(abs >= 1e10 ? 1 : 2)}B`;
  if (opts.compact !== false && abs >= 1_000_000) return `${sign}${n < 0 ? '−' : ''}$${(abs / 1e6).toFixed(abs >= 1e8 ? 0 : 1)}M`;
  if (opts.compact !== false && abs >= 10_000) return `${sign}${n < 0 ? '−' : ''}$${Math.round(abs / 1e3)}K`;
  return `${sign}${n < 0 ? '−' : ''}$${Math.round(abs).toLocaleString('en-US')}`;
};
export const usdFull = (n: number | null | undefined) =>
  n === null || n === undefined ? '—' : `${n < 0 ? '−' : ''}$${Math.round(Math.abs(n)).toLocaleString('en-US')}`;
export const pct = (r: number | null | undefined, digits = 1, sign = false) => {
  if (r === null || r === undefined || Number.isNaN(r)) return '—';
  const v = r * 100;
  const s = sign && v > 0 ? '+' : v < 0 ? '−' : '';
  return `${s}${Math.abs(v).toFixed(digits)}%`;
};
export const num = (n: number | null | undefined) => (n === null || n === undefined ? '—' : n.toLocaleString('en-US'));
export const fmtDate = (d: string | null | undefined, style: 'short' | 'long' = 'short') => {
  if (!d) return '—';
  const dt = new Date(d.length === 10 ? d + 'T00:00:00' : d);
  return dt.toLocaleDateString('en-US', style === 'short' ? { month: 'short', day: 'numeric', year: 'numeric' } : { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric' });
};
export const daysLabel = (d: number | null | undefined) => (d === null || d === undefined ? '—' : d < 0 ? `${-d}d ago` : `${d}d`);
export const bytes = (b: number) => (b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : b > 1e3 ? `${Math.round(b / 1e3)} KB` : `${b} B`);
export const titleCase = (s: string) => s.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export const ACTION_LABEL: Record<string, string> = {
  MAINTAIN: 'Maintain', REPRICE: 'Reprice', RESTRUCTURE: 'Restructure', CONDITION: 'Condition',
  DATA_REQUEST: 'Data request', REFER: 'Refer', CONDITIONAL_RENEWAL_NOTICE: 'Conditional notice',
  NON_RENEW: 'Non-renew', ENDORSEMENT_CORRECTION: 'Endorsement fix',
};
export const STATUS_LABEL: Record<string, string> = {
  NOT_STARTED: 'Not started', FAST_TRACK: 'Fast-track', ACTION_REQUIRED: 'Action required', IN_REVIEW: 'In review',
  REFERRED: 'Referred', QUOTED: 'Quoted', BOUND: 'Bound', ISSUED: 'Issued', NON_RENEWED: 'Non-renewed', LOST: 'Lost',
};
export const PASS_LABEL = ['Not run', 'Pass 1 · internal drift', 'Pass 2 · submission delta', 'Pass 3 · contract integrity'];
