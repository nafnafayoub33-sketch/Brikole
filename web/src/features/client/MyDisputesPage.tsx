import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useMyDisputes, type DisputeRow } from '@/data/disputes'
import { formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Card } from '@/ui/Card'
import { DisputeStatusBadge, ReasonBadge } from '@/ui/DisputeBadges'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'

/** The arguments he is a party to, whichever side he opened from. */
export function MyDisputesPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const disputes = useMyDisputes()

  const items = disputes.data?.items ?? []

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('dispute.myDisputes')}</h1>

      <div className="mt-8">
        {disputes.isPending ? (
          <ul className="flex flex-col gap-4">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-28" />
              </li>
            ))}
          </ul>
        ) : disputes.isError ? (
          <ErrorState error={disputes.error} onRetry={() => void disputes.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t('dispute.empty')} body={t('dispute.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-4">
            {items.map((row) => (
              <li key={row.id}>
                <DisputeRowCard row={row} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function DisputeRowCard({ row, language }: { row: DisputeRow; language: Language }) {
  const { t } = useTranslation()

  return (
    <Link to={`/client/disputes/${row.id}`} className="block">
      <Card className="transition-all duration-(--duration-fast) hover:border-primary/40 hover:shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 dir="auto" className="font-semibold text-fg">
            {row.job_title}
          </h2>
          <DisputeStatusBadge status={row.status} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <ReasonBadge reason={row.reason} />
          <span className="text-sm text-fg-subtle">
            {formatRelative(row.created_at, language)}
          </span>
        </div>
        <p dir="auto" className="mt-2 text-sm text-fg-muted">
          {t('dispute.against')}: {row.against_name}
        </p>
      </Card>
    </Link>
  )
}
