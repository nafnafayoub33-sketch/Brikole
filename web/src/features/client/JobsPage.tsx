import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useMyJobs, type Job } from '@/data/jobs'
import { localisedName } from '@/data/types'
import { formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { JobStatusBadge } from '@/ui/JobStatusBadge'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'

/** The client's accepted work. C4's list — one row per job, newest first. */
export function JobsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const jobs = useMyJobs()

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('job.myJobs')}</h1>

      <div className="mt-8">
        {jobs.isPending ? (
          <ul className="flex flex-col gap-4">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-28" />
              </li>
            ))}
          </ul>
        ) : jobs.isError ? (
          <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
        ) : (jobs.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title={t('job.empty')}
            body={t('job.emptyBody')}
            action={
              <Link to="/client/requests">
                <Button variant="secondary">{t('requests.title')}</Button>
              </Link>
            }
          />
        ) : (
          <ul className="flex flex-col gap-4">
            {(jobs.data?.items ?? []).map((job) => (
              <li key={job.id}>
                <JobRow job={job} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function JobRow({ job, language }: { job: Job; language: Language }) {
  const { t } = useTranslation()

  return (
    <Link
      to={`/client/jobs/${job.id}`}
      className="flex gap-4 rounded-lg border border-border bg-surface p-5 shadow-sm transition-all duration-(--duration-fast) hover:border-primary/40 hover:shadow-md"
    >
      <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-primary-soft">
        <TradeIcon name={job.trade.icon} className="size-6 text-primary" />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <h2 dir="auto" className="font-semibold text-fg">
            {job.title}
          </h2>
          <JobStatusBadge status={job.status} />
        </div>

        <p dir="auto" className="mt-1 text-sm text-fg-muted">
          {job.provider.full_name} · {localisedName(job.city, language)}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <span className="text-fg-muted">
            {t('job.price')}:{' '}
            <span className="numeric font-semibold text-fg">
              {formatDirhams(job.agreed_price_centimes, language)}
            </span>
          </span>
          <span className="text-fg-subtle">{formatRelative(job.created_at, language)}</span>
        </div>
      </div>
    </Link>
  )
}
