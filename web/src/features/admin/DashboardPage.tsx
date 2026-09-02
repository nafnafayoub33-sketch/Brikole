import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useStats } from '@/data/admin'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { Card } from '@/ui/Card'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * A1 — the seven numbers the platform is judged on.
 *
 * Stat tiles, not charts: these are headline figures, and a one-bar bar chart
 * of "3 disputes" says less than the number does. One hero figure — what the
 * platform actually took — because a dashboard leads with one number, and this
 * is the one the business lives on.
 *
 * Two tiles carry a status colour, and only when there is something to do: an
 * approval queue and an open dispute are somebody waiting. The colour never
 * carries that alone — each says "waiting on you" in words beside it.
 */
export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const stats = useStats()

  if (stats.isPending) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <Skeleton className="h-40" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      </div>
    )
  }

  if (stats.isError) {
    return (
      <div className="mx-auto max-w-4xl">
        <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />
      </div>
    )
  }

  const data = stats.data
  const waiting = data.providers_awaiting_approval
  const disputes = data.disputes_open

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('dashboard.title')}</h1>

      {/* The hero figure: exactly one per view, and the one the business is. */}
      <Card className="mt-6">
        <p className="text-sm text-fg-subtle">{t('dashboard.revenue')}</p>
        <p className="mt-1 text-5xl font-bold text-fg">
          {/* The isolate goes on the amount, not on the line: `numeric` turns
              a block LTR, which in Arabic would drag the whole figure over to
              the left edge of a card that reads from the right. */}
          <span className="numeric">{formatDirhams(data.leads_value_centimes, language)}</span>
        </p>
        <p className="mt-2 text-sm text-fg-muted">
          {data.leads_sold === 1
            ? t('dashboard.leadsSoldOne')
            : t('dashboard.leadsSold', { count: data.leads_sold })}
        </p>
        <p className="mt-3 max-w-prose text-xs text-fg-subtle">
          {t('dashboard.revenueHint')}
        </p>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Tile
          label={t('dashboard.newUsers')}
          value={data.new_users_this_week}
          footer={t('dashboard.vsLastWeek', { count: data.new_users_last_week })}
        />

        <Tile
          to="/admin/approvals"
          label={t('dashboard.awaitingApproval')}
          value={waiting}
          tone={waiting > 0 ? 'warning' : undefined}
          footer={waiting > 0 ? t('dashboard.needsYou') : t('dashboard.allClear')}
        />

        <Tile
          to="/mod/disputes"
          label={t('dashboard.disputesOpen')}
          value={disputes}
          tone={disputes > 0 ? 'danger' : undefined}
          footer={disputes > 0 ? t('dashboard.needsYou') : t('dashboard.allClear')}
        />

        <Tile label={t('dashboard.openRequests')} value={data.open_requests} />

        <Tile label={t('dashboard.jobsDone')} value={data.jobs_done} />
      </div>
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
  value: number
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
