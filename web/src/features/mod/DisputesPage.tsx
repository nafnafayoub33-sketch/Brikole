import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useDisputeQueue, type DisputeRow, type QueueTab } from '@/data/disputes'
import { formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { Card } from '@/ui/Card'
import { DisputeStatusBadge, ReasonBadge } from '@/ui/DisputeBadges'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * D1 — the cases waiting for a decision.
 *
 * Oldest first, because two people are waiting on every row and neither can do
 * anything until somebody reads it. Anything unclaimed for two days is flagged:
 * a queue where every row looks equally urgent is not a queue.
 */

const TABS: QueueTab[] = ['open', 'mine', 'resolved']

const TAB_KEYS: Record<QueueTab, string> = {
  open: 'mod.tabOpen',
  mine: 'mod.tabMine',
  resolved: 'mod.tabResolved',
}

export function DisputesPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const [tab, setTab] = useState<QueueTab>('open')
  const queue = useDisputeQueue(tab)

  const items = queue.data?.items ?? []

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('mod.title')}</h1>

      <div className="mt-6 flex flex-wrap gap-2">
        {TABS.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={tab === option}
            onClick={() => setTab(option)}
            className={cn(
              'min-h-11 rounded-pill border-2 px-4 text-sm font-semibold',
              'transition-colors duration-(--duration-fast)',
              tab === option
                ? 'border-primary bg-primary-soft text-primary'
                : 'border-border bg-surface text-fg-muted hover:border-border-strong',
            )}
          >
            {t(TAB_KEYS[option])}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {queue.isPending ? (
          <ul className="flex flex-col gap-4">
            {[0, 1, 2].map((index) => (
              <li key={index}>
                <Skeleton className="h-28" />
              </li>
            ))}
          </ul>
        ) : queue.isError ? (
          <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t('mod.empty')} body={t('mod.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-4">
            {items.map((row) => (
              <li key={row.id}>
                <QueueRow row={row} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function QueueRow({ row, language }: { row: DisputeRow; language: Language }) {
  const { t } = useTranslation()

  return (
    <Link to={`/mod/disputes/${row.id}`} className="block">
      <Card
        className={cn(
          'transition-all duration-(--duration-fast) hover:border-primary/40 hover:shadow-md',
          row.is_stale && 'border-danger/40',
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 dir="auto" className="font-semibold text-fg">
            {row.job_title}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            {row.is_stale && <Badge tone="danger">{t('mod.stale')}</Badge>}
            <DisputeStatusBadge status={row.status} />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <ReasonBadge reason={row.reason} />
          <span className="text-sm text-fg-subtle">
            {formatRelative(row.created_at, language)}
          </span>
        </div>

        <p dir="auto" className="mt-3 text-sm text-fg-muted">
          {t('dispute.openedBy')}: {row.opened_by_name} · {t('dispute.against')}:{' '}
          {row.against_name}
        </p>
      </Card>
    </Link>
  )
}
