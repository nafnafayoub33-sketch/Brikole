import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useJob, useReviewJob } from '@/data/jobs'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * C5 — the rating.
 *
 * One question, five buttons, and a comment box he can ignore. Every field
 * added here is a percentage point off the number of reviews written, and a
 * marketplace with no reviews is a directory.
 */
export function ReviewPage() {
  const { t } = useTranslation()
  const params = useParams()
  const navigate = useNavigate()

  const jobId = Number(params.id)
  const valid = Number.isInteger(jobId) && jobId > 0

  const job = useJob(valid ? jobId : null)
  const review = useReviewJob()

  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')

  if (!valid) {
    return <EmptyState title={t('job.notFound')} />
  }

  if (job.isPending) {
    return (
      <div className="mx-auto flex max-w-xl flex-col gap-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (job.isError) {
    return (
      <div className="mx-auto max-w-xl">
        <ErrorState error={job.error} onRetry={() => void job.refetch()} />
      </div>
    )
  }

  const data = job.data

  // Rated already: show it rather than letting him write a second one that the
  // API will refuse.
  if (data.review) {
    return (
      <div className="mx-auto max-w-xl">
        <EmptyState
          title={t('job.rateAlready')}
          action={
            <Link to={`/client/jobs/${data.id}`}>
              <Button variant="secondary">{t('job.backToJobs')}</Button>
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('job.rateTitle')}</h1>
      <p className="mt-2 text-fg-muted">{t('job.rateBody')}</p>

      <Card className="mt-8">
        <p dir="auto" className="text-sm text-fg-subtle">
          {data.title}
        </p>
        <p dir="auto" className="mt-1 font-semibold text-fg">
          {data.provider.full_name}
        </p>

        <fieldset className="mt-6">
          <legend className="mb-3 text-sm font-semibold text-fg">{t('job.rateStars')}</legend>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                type="button"
                aria-label={`${value}/5`}
                aria-pressed={rating === value}
                onClick={() => setRating(value)}
                className={cn(
                  'rounded-md border-2 p-2 transition-colors duration-(--duration-fast)',
                  rating === value
                    ? 'border-primary bg-primary-soft'
                    : 'border-border bg-surface hover:border-border-strong',
                )}
              >
                <Stars value={value} />
              </button>
            ))}
          </div>
        </fieldset>

        <label className="mt-6 flex flex-col gap-2">
          <span className="text-sm font-semibold text-fg">{t('job.rateComment')}</span>
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder={t('job.ratePlaceholder')}
            rows={4}
            maxLength={2000}
            className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
          />
        </label>

        {review.isError && (
          <div className="mt-4">
            <ErrorState error={review.error} />
          </div>
        )}

        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-border pt-6">
          <Button
            size="lg"
            disabled={rating === 0}
            loading={review.isPending}
            onClick={() =>
              review.mutate(
                { jobId, rating, comment },
                { onSuccess: () => navigate(`/client/jobs/${jobId}`) },
              )
            }
          >
            {t('job.ratePublish')}
          </Button>
          <Link to={`/client/jobs/${jobId}`}>
            <Button variant="ghost">{t('job.rateSkip')}</Button>
          </Link>
        </div>
      </Card>
    </div>
  )
}
