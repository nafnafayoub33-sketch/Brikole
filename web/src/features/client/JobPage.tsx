import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useCancelJob, useConfirmJob, useJob } from '@/data/jobs'
import { localisedName } from '@/data/types'
import { formatDate, formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { JobStatusBadge } from '@/ui/JobStatusBadge'
import { JobTimeline } from '@/ui/JobTimeline'
import { PartyCard } from '@/ui/PartyCard'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'

/**
 * C4 — the work, once somebody is doing it.
 *
 * The screen answers three questions in this order: what is happening, who is
 * doing it and how do I reach him, and what do I owe. Confirming is the
 * primary action and only exists once the tradesman says he has finished —
 * offering it earlier invites confirming work that has not happened.
 */
export function JobPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const params = useParams()
  const navigate = useNavigate()

  const jobId = Number(params.id)
  const valid = Number.isInteger(jobId) && jobId > 0

  const job = useJob(valid ? jobId : null)
  const confirm = useConfirmJob()
  const cancel = useCancelJob()
  const [reason, setReason] = useState('')

  if (!valid) {
    return <EmptyState title={t('job.notFound')} action={<BackLink />} />
  }

  if (job.isPending) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-56" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (job.isError) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorState error={job.error} onRetry={() => void job.refetch()} />
        <div className="mt-6 flex justify-center">
          <BackLink />
        </div>
      </div>
    )
  }

  const data = job.data
  const live = data.status !== 'confirmed' && data.status !== 'cancelled'

  return (
    <div className="mx-auto max-w-3xl">
      <BackLink />

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <h1 dir="auto" className="text-2xl font-bold text-fg sm:text-3xl">
          {data.title}
        </h1>
        <JobStatusBadge status={data.status} className="mt-1.5" />
      </header>

      {data.status === 'cancelled' && (
        <Alert tone="warning" className="mt-5">
          {t('job.cancelledBy')}{' '}
          {t(
            data.cancelled_by === 'provider'
              ? 'job.cancelledByProvider'
              : 'job.cancelledByClient',
          )}
          {data.cancel_reason && (
            <>
              {' — '}
              <span dir="auto">
                {t('job.cancelReasonLabel')}: {data.cancel_reason}
              </span>
            </>
          )}
        </Alert>
      )}

      <Card className="mt-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral" className="gap-2">
            <TradeIcon name={data.trade.icon} className="size-4" />
            {localisedName(data.trade, language)}
          </Badge>
          <Badge tone="neutral">{localisedName(data.city, language)}</Badge>
        </div>

        <div className="mt-6 grid gap-8 sm:grid-cols-[1fr_auto]">
          <div>
            <h3 className="mb-3 text-sm font-semibold text-fg-subtle uppercase">
              {t('job.timeline')}
            </h3>
            <JobTimeline job={data} language={language} />
          </div>

          <div className="sm:text-end">
            <p className="text-sm text-fg-subtle">{t('job.price')}</p>
            <p className="numeric mt-1 text-3xl font-bold text-fg">
              {formatDirhams(data.agreed_price_centimes, language)}
            </p>
          </div>
        </div>

        <div className="mt-8 border-t border-border pt-6">
          <PartyCard
            party={data.provider}
            label={t('job.theM3allem')}
            callLabel={t('job.call')}
            profileHref={`/m3allem/${data.provider.id}`}
          />
        </div>

        <div className="mt-6 border-t border-border pt-6">
          <h3 className="mb-2 text-sm font-semibold text-fg-subtle uppercase">
            {t('job.address')}
          </h3>
          <p dir="auto" className="text-fg">
            {data.address}
          </p>
        </div>
      </Card>

      {/* The business model, said plainly on the screen where money comes up. */}
      <Alert tone="info" className="mt-6">
        <span className="font-semibold">{t('job.cashTitle')}</span> {t('job.cashBody')}
      </Alert>

      {data.review ? (
        <Card className="mt-6">
          <h3 className="mb-3 text-sm font-semibold text-fg-subtle uppercase">
            {t('job.yourRating')}
          </h3>
          <div className="flex items-center gap-3">
            <Stars value={data.review.rating} />
            <span className="numeric font-semibold text-fg">{data.review.rating}/5</span>
            <span className="text-sm text-fg-subtle">
              {formatDate(data.review.created_at, language)}
            </span>
          </div>
          {data.review.comment && (
            <p dir="auto" className="mt-3 text-fg-muted">
              {data.review.comment}
            </p>
          )}
        </Card>
      ) : (
        data.status === 'confirmed' && (
          <div className="mt-6">
            <Link to={`/client/jobs/${data.id}/review`}>
              <Button size="lg">{t('job.rate')}</Button>
            </Link>
          </div>
        )
      )}

      {live && (
        <footer className="mt-10 flex flex-col gap-6 border-t border-border pt-6">
          {data.status === 'done' && (
            <div>
              <ConfirmButton
                label={t('job.confirm')}
                question={t('job.confirmConfirm')}
                confirmLabel={t('job.confirmYes')}
                size="lg"
                loading={confirm.isPending}
                onConfirm={() =>
                  confirm.mutate(data.id, {
                    onSuccess: () => navigate(`/client/jobs/${data.id}/review`),
                  })
                }
              />
              <p className="mt-2 text-xs text-fg-subtle">{t('job.confirmHint')}</p>
              {confirm.isError && (
                <div className="mt-3">
                  <ErrorState error={confirm.error} />
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-start gap-4">
            <ConfirmButton
              label={t('job.cancel')}
              question={t('job.cancelConfirmClient')}
              confirmLabel={t('job.cancelYes')}
              variant="ghost"
              tone="danger"
              loading={cancel.isPending}
              onConfirm={() =>
                cancel.mutate(
                  { jobId: data.id, reason },
                  { onSuccess: () => navigate('/client/requests') },
                )
              }
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
              </label>
            </ConfirmButton>

            {/* C8 is not built. Saying so beats a button that goes nowhere. */}
            <p className="self-center text-sm text-fg-subtle">{t('job.disputeSoon')}</p>
          </div>

          {cancel.isError && <ErrorState error={cancel.error} />}
        </footer>
      )}
    </div>
  )
}

function BackLink() {
  const { t } = useTranslation()
  return (
    <Link to="/client/jobs" className="text-sm font-semibold text-primary hover:underline">
      <span aria-hidden className="inline-block rtl:rotate-180">
        &larr;
      </span>{' '}
      {t('job.backToJobs')}
    </Link>
  )
}
