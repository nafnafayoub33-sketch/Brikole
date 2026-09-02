import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { StatsPlace } from '@/data/admin'
import { useStats } from '@/data/admin'
import { localisedName } from '@/data/types'
import { formatCount, formatDirhams, formatMonth, formatMonthLong } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import type { BarRow } from '@/ui/BarList'
import { BarList, ChartHeader } from '@/ui/BarList'
import { Card } from '@/ui/Card'
import { ColumnChart } from '@/ui/ColumnChart'
import { ErrorState } from '@/ui/ErrorState'
import { Funnel } from '@/ui/Funnel'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/** Past this the panel becomes a scroll, and the tail belongs on A6. */
const PLACES_SHOWN = 8

/**
 * A1 — the whole platform on one screen.
 *
 * One hero figure, a row of stat tiles, then four panels that answer the
 * questions the tiles raise: where the money is, whether it is growing, where
 * the work happens, and whether the marketplace works at all.
 *
 * Numbers wherever a number is the answer, charts only where the shape is.
 * "1 dispute" is a stat tile; thirteen months of revenue is a column chart;
 * twenty cities are a ranked list — past about seven categories colour stops
 * carrying identity and a table is the honest form.
 *
 * Every chart plots one measure in one hue. Nothing here has two y-axes, and
 * no bar is coloured by its own value: length already says how much.
 */
export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const stats = useStats()

  if (stats.isPending) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <Skeleton className="h-40" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4].map((index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (stats.isError) {
    return (
      <div className="mx-auto max-w-5xl">
        <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />
      </div>
    )
  }

  const data = stats.data
  const { money, funnel } = data
  const waiting = data.providers_awaiting_approval
  const disputes = data.disputes_open

  const dh = (centimes: number) => formatDirhams(centimes, language)
  const count = (value: number) => formatCount(value, language)

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('dashboard.title')}</h1>

      {/* The hero figure: exactly one per view, and the one the business is. */}
      <Card>
        <p className="text-sm text-fg-subtle">{t('dashboard.revenue')}</p>
        <p className="mt-1 text-5xl font-bold text-fg">
          {/* The isolate goes on the amount, not on the line: `numeric` turns a
              block LTR, which in Arabic would drag the whole figure over to the
              left edge of a card that reads from the right. */}
          <span className="numeric">{dh(data.leads_value_centimes)}</span>
        </p>
        <p className="mt-2 text-sm text-fg-muted">
          {data.leads_sold === 1
            ? t('dashboard.leadsSoldOne')
            : t('dashboard.leadsSold', { value: count(data.leads_sold) })}
        </p>
        <p className="mt-3 max-w-prose text-xs text-fg-subtle">{t('dashboard.revenueHint')}</p>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Tile
          label={t('dashboard.newUsers')}
          value={count(data.new_users_this_week)}
          footer={t('dashboard.vsLastWeek', { value: count(data.new_users_last_week) })}
        />

        <Tile
          to="/admin/approvals"
          label={t('dashboard.awaitingApproval')}
          value={count(waiting)}
          tone={waiting > 0 ? 'warning' : undefined}
          footer={waiting > 0 ? t('dashboard.needsYou') : t('dashboard.allClear')}
        />

        <Tile
          to="/mod/disputes"
          label={t('dashboard.disputesOpen')}
          value={count(disputes)}
          tone={disputes > 0 ? 'danger' : undefined}
          footer={disputes > 0 ? t('dashboard.needsYou') : t('dashboard.allClear')}
        />

        <Tile label={t('dashboard.openRequests')} value={count(data.open_requests)} />

        <Tile label={t('dashboard.jobsDone')} value={count(data.jobs_done)} />
      </div>

      {/* Money as rows, not as more tiles: every one of these figures needs a
          sentence saying whose money it is, and a tile has no room for one. */}
      <Card>
        <ChartHeader title={t('dashboard.moneyTitle')} />
        <dl className="flex flex-col divide-y divide-border">
          <MoneyRow
            label={t('dashboard.inDispute')}
            value={dh(money.in_dispute_centimes)}
            hint={t('dashboard.inDisputeHint')}
          />
          <MoneyRow
            label={t('dashboard.atRisk')}
            value={dh(money.disputed_lead_fees_centimes)}
            hint={t('dashboard.atRiskHint')}
          />
          <MoneyRow
            label={
              money.topups_waiting === 0
                ? t('dashboard.topupsWaitingNone')
                : money.topups_waiting === 1
                  ? t('dashboard.topupsWaitingOne')
                  : t('dashboard.topupsWaiting', { value: count(money.topups_waiting) })
            }
            value={dh(money.topups_waiting_centimes)}
            hint={t('dashboard.topupsHint')}
            to={money.topups_waiting > 0 ? '/admin/finance' : undefined}
          />
          <MoneyRow
            label={t('dashboard.creditHeld')}
            value={dh(money.credit_held_centimes)}
            hint={t('dashboard.creditHeldHint')}
          />
          <MoneyRow
            label={t('dashboard.creditOwed')}
            value={dh(money.credit_owed_centimes)}
            hint={t('dashboard.creditOwedHint')}
          />
        </dl>
      </Card>

      <Card>
        <ChartHeader title={t('dashboard.trendTitle')} hint={t('dashboard.trendHint')} />
        <ColumnChart
          points={data.months.map((point) => ({
            id: point.month,
            label: formatMonth(point.month, language),
            sublabel: point.month.slice(0, 4),
            value: point.value_centimes,
            detail: t('dashboard.trendTooltip', {
              month: formatMonthLong(point.month, language),
              leads: count(point.leads),
              money: dh(point.value_centimes),
            }),
          }))}
          formatTick={dh}
          emptyLabel={t('dashboard.noTrend')}
        />
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <ChartHeader title={t('dashboard.citiesTitle')} hint={t('dashboard.citiesHint')} />
          <Places
            rows={data.cities}
            language={language}
            dh={dh}
            count={count}
            empty={t('dashboard.noPlaces')}
          />
          <Remainder
            rows={data.cities}
            dh={dh}
            count={count}
            others={(rest) => t('dashboard.others', { value: count(rest) })}
          />
        </Card>

        <Card>
          <ChartHeader title={t('dashboard.tradesTitle')} hint={t('dashboard.tradesHint')} />
          <Places
            rows={data.trades}
            language={language}
            dh={dh}
            count={count}
            empty={t('dashboard.noPlaces')}
          />
          <Remainder
            rows={data.trades}
            dh={dh}
            count={count}
            others={(rest) => t('dashboard.others', { value: count(rest) })}
          />
        </Card>
      </div>

      <Card>
        <ChartHeader title={t('dashboard.funnelTitle')} hint={t('dashboard.funnelHint')} />
        <Funnel
          share={(percent) => t('dashboard.share', { percent })}
          steps={[
            {
              id: 'requests',
              label: t('dashboard.funnelRequests'),
              value: funnel.requests,
              display: count(funnel.requests),
            },
            {
              id: 'offers',
              label: t('dashboard.funnelWithOffer'),
              value: funnel.with_offer,
              display: count(funnel.with_offer),
              lost: unanswered(funnel.requests - funnel.with_offer, t, count),
            },
            {
              id: 'hired',
              label: t('dashboard.funnelHired'),
              value: funnel.hired,
              display: count(funnel.hired),
            },
            {
              id: 'confirmed',
              label: t('dashboard.funnelConfirmed'),
              value: funnel.confirmed,
              display: count(funnel.confirmed),
            },
          ]}
        />
      </Card>
    </div>
  )
}

/** The requests nobody replied to — the number this whole panel is about. */
function unanswered(
  lost: number,
  t: (key: string, options?: Record<string, unknown>) => string,
  count: (value: number) => string,
): string | undefined {
  if (lost <= 0) return undefined
  return lost === 1
    ? t('dashboard.funnelLostOne')
    : t('dashboard.funnelLost', { value: count(lost) })
}

function Places({
  rows,
  language,
  dh,
  count,
  empty,
}: {
  rows: StatsPlace[]
  language: Language
  dh: (centimes: number) => string
  count: (value: number) => string
  empty: string
}) {
  const shown: BarRow[] = rows.slice(0, PLACES_SHOWN).map((row) => ({
    id: row.slug,
    label: localisedName(row, language),
    value: row.jobs,
    display: count(row.jobs),
    note: <span className="numeric">{dh(row.value_centimes)}</span>,
  }))

  return <BarList rows={shown} emptyLabel={empty} />
}

/** Names what the panel is not showing, and what it comes to. A top eight that
 *  quietly drops twelve cities is a chart that lies by omission. */
function Remainder({
  rows,
  dh,
  count,
  others,
}: {
  rows: StatsPlace[]
  dh: (centimes: number) => string
  count: (value: number) => string
  others: (rest: number) => string
}) {
  const rest = rows.slice(PLACES_SHOWN)
  if (rest.length === 0) return null

  const jobs = rest.reduce((total, row) => total + row.jobs, 0)
  const value = rest.reduce((total, row) => total + row.value_centimes, 0)

  return (
    <p className="mt-4 flex items-baseline justify-between gap-3 border-t border-border pt-3 text-xs text-fg-subtle">
      <span>{others(rest.length)}</span>
      <span className="flex items-baseline gap-2">
        <span className="numeric">{count(jobs)}</span>
        <span className="numeric">{dh(value)}</span>
      </span>
    </p>
  )
}

function MoneyRow({
  label,
  value,
  hint,
  to,
}: {
  label: string
  value: string
  hint: string
  to?: string
}) {
  return (
    <div className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
      <div className="min-w-0">
        <dt className="text-sm text-fg">
          {to ? (
            <Link to={to} className="underline-offset-2 hover:underline">
              {label}
            </Link>
          ) : (
            label
          )}
        </dt>
        <p className="mt-0.5 max-w-prose text-xs text-fg-subtle">{hint}</p>
      </div>
      <dd className="numeric shrink-0 text-base font-semibold text-fg">{value}</dd>
    </div>
  )
}

function Tile({
  to,
  label,
  value,
  footer,
  tone,
}: {
  /** Left out when no screen exists yet: a tile that leads to a placeholder
      is worse than a tile that plainly reports a number. A3 and A4 give the
      first two theirs. */
  to?: string
  label: string
  value: string
  footer?: ReactNode
  /** Status only, and only when there is something to act on. */
  tone?: 'warning' | 'danger'
}) {
  const className = cn(
    'block rounded-lg border bg-surface p-5 shadow-sm',
    tone === 'danger'
      ? 'border-danger/40'
      : tone === 'warning'
        ? 'border-warning/40'
        : 'border-border',
    to &&
      'transition-all duration-(--duration-fast) hover:-translate-y-0.5 hover:shadow-md ' +
        (tone === 'danger'
          ? 'hover:border-danger'
          : tone === 'warning'
            ? 'hover:border-warning'
            : 'hover:border-primary/40'),
  )

  const body = (
    <>
      <p className="text-sm text-fg-subtle">{label}</p>
      {/* Proportional figures: a standalone value at this size looks loose with
          tabular digits, which are for columns that must line up. */}
      <p className="mt-1 text-3xl font-bold text-fg">{value}</p>
      {footer && (
        <p className="mt-2 text-xs">
          {tone ? (
            // Never colour alone: the badge carries the words too.
            <Badge tone={tone === 'danger' ? 'danger' : 'warning'}>{footer}</Badge>
          ) : (
            <span className="text-fg-subtle">{footer}</span>
          )}
        </p>
      )}
    </>
  )

  if (!to) {
    return <div className={className}>{body}</div>
  }

  return (
    <Link to={to} className={className}>
      {body}
    </Link>
  )
}
