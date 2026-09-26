// Coverholder list with scorecards.
import { useNavigate } from 'react-router-dom';
import { Page, Card, Loading, ErrorBox, Badge, cx } from '@/components/ui';
import { pct, usd } from '@/lib/format';
import { Info } from '@/help/Info';
import { useCoverholders } from '../api';
import { Grade, Mini, UtilBar } from '../parts';

export default function Coverholders() {
  const { data, isLoading, error } = useCoverholders();
  const nav = useNavigate();
  return (
    <Page title="Coverholders" subtitle="MGAs and coverholders binding on Northgate paper · scorecard from their own bordereaux" actions={<Info id="delegated.coverholders.page" label="About this page" />}>
      {isLoading ? <Loading /> : error || !data ? <ErrorBox error={error} /> : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {data.map((c) => (
            <Card key={c.id} className="cursor-pointer transition hover:border-line-strong" pad>
              <div onClick={() => nav(`/delegated/coverholders/${c.id}`)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2"><Badge tone="dark">{c.scenario}</Badge><span className="truncate text-[15px] font-semibold text-ink-950">{c.name}</span></div>
                    <div className="mt-0.5 text-[12px] text-ink-500">{c.program} · {c.hq} · {c.agreement} · UMR <span className="mono">{c.umr}</span></div>
                    <div className="mt-1 text-[12.5px] text-ink-700">{c.story}</div>
                  </div>
                  <Grade g={c.grade} score={c.score} />
                </div>
                <div className="mt-3 grid grid-cols-4 gap-2">
                  <Mini label="Within authority" value={pct(c.within_authority, 1)} tone={c.within_authority > 0.995 ? 'ok' : 'high'} />
                  <Mini label="Exception trend" value={<span className={cx('text-[13px]', c.direction === 'deteriorating' ? 'text-crit' : '')}>{c.trend.map((t) => pct(t.rate, 1)).join(' → ')}</span>} />
                  <Mini label="Open · at stake" value={`${c.open_exceptions} · ${usd(c.at_stake)}`} tone={c.open_exceptions ? 'crit' : 'ok'} />
                  <Mini label="DQ · days late" value={`${c.dq_score?.toFixed(0) ?? '—'} · ${c.avg_days_late}`} tone={c.avg_days_late > 0 ? 'high' : undefined} />
                </div>
                {c.top_zone && (
                  <div className="mt-3">
                    <div className="mb-1 flex justify-between text-[11.5px]"><span className="text-ink-600">Top zone · {c.top_zone.name}</span><span className={cx('num font-semibold', c.top_zone.util >= c.top_zone.warn ? 'text-crit' : 'text-ink-700')}>{pct(c.top_zone.util, 1)} · {c.top_zone.status}</span></div>
                    <UtilBar util={c.top_zone.util} warn={c.top_zone.warn} />
                  </div>
                )}
                <div className="mt-2 flex flex-wrap gap-3 text-[11.5px] text-ink-500">
                  <span>Commission {pct(c.commission, 1)}</span><span>Max limit {usd(c.max_limit)}</span><span>Authority v{c.authority_version}</span>
                  <span>Incurred ÷ written {c.loss_ratio != null ? pct(c.loss_ratio, 1) : '—'}</span>{c.rarc?.rarc != null && <span>RARC {c.rarc.quarter} {pct(c.rarc.rarc, 1, true)}</span>}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Page>
  );
}
