import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  useCancelJob,
  useFinishJob,
  useMyJobs,
  useStartJob,
  type Job,
  type JobStatus,
} from '@/data/jobs'
import { localisedName } from '@/data/types'
import { formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { JobStatusBadge } from '@/ui/JobStatusBadge'
import { PartyCard } from '@/ui/PartyCard'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { cn } from '@/ui/cn'

/**
 * M7 — his work.
 *
 * Everything is a full card rather than a list that opens a detail: he is
 * standing outside with one hand free, and the address and the phone number
 * are the two things he needs without another tap. Buttons are `pro`-sized for
 * the same reason.
 */

type Filter = 'all' | 'assigned' | 'active' | 'finished'

const FILTERS: Filter[] = ['all', 'assigned', 'active', 'finished']

const FILTER_KEYS: Record<Filter, string> = {
  all: 'job.proFilterAll',
  assigned: 'job.proFilterAssigned',
  active: 'job.proFilterActive',
  finished: 'job.proFilterFinished',
}

const MATCHES: Record<Filter, JobStatus[]> = {
  all: ['assigned', 'in_progress', 'done', 'confirmed', 'cancelled'],
  assigned: ['assigned'],
  active: ['in_progress'],
  finished: ['done', 'confirmed', 'cancelled'],
}

export function ProJobsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const jobs = useMyJobs()
  const [filter, setFilter] = useState<Filter>('all')

  const items = jobs.data?.items ?? []
  const shown = items.filter((job) => MATCHES[filter].includes(job.status))

  const cancelled = items.filter((job) => job.status === 'cancelled').length
  const rate = items.length > 0 ? Math.round((cancelled / items.length) * 100) : 0

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('job.myJobs')}</h1>

      {/* Shown to him honestly, long before it can ever become a suspension. */}
      {cancelled > 0 && (
        <Alert tone={rate >= 20 ? 'warning' : 'info'} className="mt-5">
          <span className="font-semibold">
            {t('job.cancelRate')}: <span className="numeric">{rate}%</span>
          </span>{' '}
          {t('job.cancelRateBody')}
        </Alert>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        {FILTERS.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={filter === option}
            onClick={() => setFilter(option)}
            className={cn(
              'min-h-11 rounded-pill border-2 px-4 text-sm font-semibold',
              'transition-colors duration-(--duration-fast)',
              filter === option
                ? 'border-primary bg-primary-soft text-primary'
                : 'border-border bg-surface text-fg-muted hover:border-border-strong',
            )}
          >
            {t(FILTER_KEYS[option])}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {jobs.isPending ? (
          <ul className="flex flex-col gap-5">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-64" />
              </li>
            ))}
          </ul>
        ) : jobs.isError ? (
          <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
        ) : shown.length === 0 ? (
          <EmptyState title={t('job.empty')} body={t('job.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-5">
            {shown.map((job) => (
              <li key={job.id}>
                <ProJobCard job={job} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function ProJobCard({ job, language }: { job: Job; language: Language }) {
  const { t } = useTranslation()
  const start = useStartJob()
  const finish = useFinishJob()
  const cancel = useCancelJob()
  const [reason, setReason] = useState('')

  const live = job.status === 'assigned' || job.status === 'in_progress'
  const failed = start.error ?? finish.error ?? cancel.error

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-primary-soft">
            <TradeIcon name={job.trade.icon} className="size-6 text-primary" />
          </span>
          <div className="min-w-0">
            <h2 dir="auto" className="font-bold text-fg">
              {job.title}
            </h2>
            <p className="mt-0.5 text-sm text-fg-subtle">
              {localisedName(job.city, language)} · {formatRelative(job.created_at, language)}
            </p>
          </div>
        </div>
        <JobStatusBadge status={job.status} />
      </div>

      <p dir="auto" className="mt-4 text-sm text-fg-muted">
        {job.description}
      </p>

      <div className="mt-5 flex flex-wrap items-baseline justify-between gap-3 rounded-md bg-surface-2 px-4 py-3">
        <span className="text-sm text-fg-subtle">{t('job.price')}</span>
        <span className="numeric text-2xl font-bold text-fg">
          {formatDirhams(job.agreed_price_centimes, language)}
        </span>
      </div>

      {job.lead_fee_centimes !== null && (
        <p className="mt-2 text-xs text-fg-subtle">
          {job.lead_fee_centimes === 0 ? (
            t('job.leadFeeFree')
          ) : (
            <>
              {t('job.leadFee')}:{' '}
              <span className="numeric">
                {formatDirhams(job.lead_fee_centimes, language)}
              </span>
            </>
          )}
        </p>
      )}

      <div className="mt-6 border-t border-border pt-5">
        <PartyCard
          party={job.client}
          label={t('job.theClient')}
          callLabel={t('job.callClient')}
          size="pro"
        />
      </div>

      <div className="mt-5 border-t border-border pt-5">
        <h3 className="mb-2 text-sm font-semibold text-fg-subtle uppercase">
          {t('job.address')}
        </h3>
        <p dir="auto" className="text-fg">
          {job.address}
        </p>
      </div>

      {job.status === 'cancelled' && job.cancel_reason && (
        <Alert tone="info" className="mt-5">
          <span dir="auto">
            {t('job.cancelReasonLabel')}: {job.cancel_reason}
          </span>
        </Alert>
      )}

      {live && (
        <footer className="mt-6 flex flex-col gap-4 border-t border-border pt-5">
          {job.status === 'assigned' && (
            <ConfirmButton
              label={t('job.start')}
              question={t('job.startConfirm')}
              confirmLabel={t('job.yes')}
              size="pro"
              loading={start.isPending}
              onConfirm={() => start.mutate(job.id)}
            />
          )}

          {job.status === 'in_progress' && (
            <ConfirmButton
              label={t('job.finish')}
              question={t('job.finishConfirm')}
              confirmLabel={t('job.yes')}
              size="pro"
              loading={finish.isPending}
              onConfirm={() => finish.mutate(job.id)}
            />
          )}

          <ConfirmButton
            label={t('job.cancel')}
            question={t('job.cancelConfirmPro')}
            confirmLabel={t('job.cancelYes')}
            variant="ghost"
            tone="danger"
            size="pro"
            loading={cancel.isPending}
            // The API refuses a blank reason. The button refuses it first, so
            // he is not told off after pressing.
            confirmDisabled={reason.trim().length === 0}
            onConfirm={() => cancel.mutate({ jobId: job.id, reason })}
          >
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-fg">{t('job.cancelReason')}</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={2}
                maxLength={500}
                className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-danger"
              />
              <span className="text-xs text-fg-subtle">{t('job.cancelReasonRequired')}</span>
            </label>
          </ConfirmButton>

          {failed && <ErrorState error={failed} />}
        </footer>
      )}
    </Card>
  )
}
