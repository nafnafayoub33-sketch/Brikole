import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { DISPUTE_REASONS, useOpenDispute, type DisputeReason } from '@/data/disputes'
import { useJob } from '@/data/jobs'
import { Alert } from '@/ui/Alert'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { PhotoGallery, type PickedPhoto } from '@/ui/PhotoInput'
import { REASON_KEYS } from '@/ui/disputeLabels'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

const MIN_DESCRIPTION = 20

/**
 * C8 — opening a dispute.
 *
 * The paragraph that matters most is the one saying this is not a refund
 * request. The platform never held the client's money; somebody arriving here
 * expecting it back leaves angrier than he came, and telling him afterwards is
 * too late.
 */
export function DisputePage() {
  const { t } = useTranslation()
  const params = useParams()
  const navigate = useNavigate()

  const jobId = Number(params.id)
  const valid = Number.isInteger(jobId) && jobId > 0

  const job = useJob(valid ? jobId : null)
  const open = useOpenDispute()

  const [reason, setReason] = useState<DisputeReason | null>(null)
  const [description, setDescription] = useState('')
  const [photos, setPhotos] = useState<PickedPhoto[]>([])

  if (!valid) {
    return <EmptyState title={t('job.notFound')} />
  }

  if (job.isPending) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-72" />
      </div>
    )
  }

  if (job.isError) {
    return (
      <div className="mx-auto max-w-2xl">
        <ErrorState error={job.error} onRetry={() => void job.refetch()} />
      </div>
    )
  }

  const complete = reason !== null && description.trim().length >= MIN_DESCRIPTION

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={`/client/jobs/${jobId}`}
        className="text-sm font-semibold text-primary hover:underline"
      >
        <span aria-hidden className="inline-block rtl:rotate-180">
          &larr;
        </span>{' '}
        {t('job.title')}
      </Link>

      <h1 className="mt-4 text-2xl font-bold text-fg sm:text-3xl">{t('dispute.openTitle')}</h1>
      <p className="mt-2 text-fg-muted">{t('dispute.openBody')}</p>

      {/* Said before anything is filled in, not after it is submitted. */}
      <Alert tone="warning" className="mt-6">
        {t('dispute.noMoney')}
      </Alert>

      <Card className="mt-6">
        <p dir="auto" className="text-sm text-fg-subtle">
          {job.data.title}
        </p>

        <fieldset className="mt-6">
          <legend className="mb-3 text-sm font-semibold text-fg">{t('dispute.reason')}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {DISPUTE_REASONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={reason === option}
                onClick={() => setReason(option)}
                className={cn(
                  'min-h-tap rounded-md border-2 px-4 py-3 text-start text-sm font-medium',
                  'transition-colors duration-(--duration-fast)',
                  reason === option
                    ? 'border-primary bg-primary-soft text-primary'
                    : 'border-border bg-surface text-fg hover:border-border-strong',
                )}
              >
                {t(REASON_KEYS[option])}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="mt-6 flex flex-col gap-2">
          <span className="text-sm font-semibold text-fg">{t('dispute.description')}</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t('dispute.descriptionPlaceholder')}
            rows={6}
            maxLength={2000}
            className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
          />
          <span className="text-xs text-fg-subtle">{t('dispute.descriptionHint')}</span>
        </label>

        <div className="mt-6">
          <PhotoGallery
            label={t('dispute.evidence')}
            hint={t('dispute.evidenceHint')}
            value={photos}
            onChange={setPhotos}
            max={6}
            purpose="request_photo"
          />
        </div>

        {open.isError && (
          <div className="mt-5">
            <ErrorState error={open.error} />
          </div>
        )}

        <div className="mt-8 border-t border-border pt-6">
          <ConfirmButton
            label={t('dispute.submit')}
            question={t('dispute.submitConfirm')}
            confirmLabel={t('dispute.submitYes')}
            size="lg"
            disabled={!complete}
            loading={open.isPending}
            onConfirm={() =>
              open.mutate(
                {
                  jobId,
                  reason: reason as DisputeReason,
                  description: description.trim(),
                  evidence_paths: photos.map((photo) => photo.path),
                },
                { onSuccess: (dispute) => navigate(`/client/disputes/${dispute.id}`) },
              )
            }
          />
        </div>
      </Card>
    </div>
  )
}
