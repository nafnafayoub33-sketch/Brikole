import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  REVIEWS_PER_PAGE,
  useMyReviews,
  useMyReviewsSummary,
  useReplyToReview,
} from '@/data/proReviews'
import { localisedName } from '@/data/types'
import type { Review } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatCount, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Pager } from '@/ui/Pager'
import { RatingBreakdown } from '@/ui/RatingBreakdown'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'

/** What the API accepts. Held here too so the counter and the button agree
 *  with it before a round trip says no. */
const MAX_REPLY = 600

/**
 * M10 — what clients wrote, and his one answer to each.
 *
 * The same reviews the public reads on P3, in the same shape: two versions of
 * a man's reputation is one version too many. Which also means a review D3 has
 * hidden is not here — the platform stopped standing behind it, and putting it
 * back in front of him only sends him to argue about something invisible.
 *
 * The header leads on how many are *unanswered*, not how many exist: "three to
 * answer" is work, "forty-seven reviews" is a fact.
 */
export function ReviewsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language

  const [page, setPage] = useState(1)
  const summary = useMyReviewsSummary()
  const reviews = useMyReviews(page)

  const pages = reviews.data
    ? Math.max(1, Math.ceil(reviews.data.total / REVIEWS_PER_PAGE))
    : 1

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-2xl font-bold text-fg">{t('reviews.title')}</h1>
        {summary.data && summary.data.unanswered > 0 && (
          <span className="text-sm font-semibold text-primary">
            {summary.data.unanswered === 1
              ? t('reviews.waitingOne')
              : t('reviews.waiting', {
                  value: formatCount(summary.data.unanswered, language),
                })}
          </span>
        )}
      </div>

      {summary.isPending ? (
        <Skeleton className="h-32" />
      ) : summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : summary.data.rating_count > 0 ? (
        <RatingBreakdown
          breakdown={summary.data.breakdown}
          total={summary.data.rating_count}
          average={summary.data.rating_avg}
        />
      ) : null}

      {reviews.isPending ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : reviews.isError ? (
        <ErrorState error={reviews.error} onRetry={() => void reviews.refetch()} />
      ) : reviews.data.items.length === 0 ? (
        <EmptyState title={t('reviews.empty')} body={t('reviews.emptyBody')} />
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {reviews.data.items.map((review) => (
              <ReviewCard key={review.id} review={review} language={language} />
            ))}
          </div>

          {pages > 1 && (
            <Pager page={page} pages={pages} language={language} onChange={setPage} />
          )}
        </>
      )}
    </div>
  )
}

function ReviewCard({ review, language }: { review: Review; language: Language }) {
  const { t } = useTranslation()

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span dir="auto" className="text-sm font-semibold text-fg">
          {review.author.display_name}
        </span>
        {review.trade && (
          <span className="text-xs text-fg-subtle">
            {localisedName(review.trade, language)}
          </span>
        )}
        <span className="ms-auto flex items-center gap-2">
          <Stars value={review.rating} size="sm" />
          <span className="numeric text-xs text-fg-subtle">
            {formatRelative(review.created_at, language)}
          </span>
        </span>
      </div>

      {review.comment && (
        <p dir="auto" className="mt-3 text-sm leading-relaxed text-fg">
          {review.comment}
        </p>
      )}

      {review.reply ? (
        <div className="mt-4 rounded-md border-s-2 border-primary bg-surface-2 px-4 py-3">
          <p className="text-xs font-semibold text-primary">{t('reviews.yourReply')}</p>
          <p dir="auto" className="mt-1 text-sm text-fg-muted">
            {review.reply}
          </p>
        </div>
      ) : (
        <ReplyBox reviewId={review.id} />
      )}
    </Card>
  )
}

function ReplyBox({ reviewId }: { reviewId: number }) {
  const { t } = useTranslation()
  const send = useReplyToReview()
  const message = useErrorMessage()

  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')

  const cleaned = text.trim()

  if (!open) {
    return (
      <div className="mt-4">
        <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
          {t('reviews.reply')}
        </Button>
      </div>
    )
  }

  return (
    <div className="mt-4 flex flex-col gap-3">
      {/* The warning comes *before* he writes, not after he presses. Nobody
          should discover "you only get one" by hitting it. */}
      <Alert tone="warning">{t('reviews.onceWarning')}</Alert>

      <label htmlFor={`reply-${reviewId}`} className="sr-only">
        {t('reviews.reply')}
      </label>
      <textarea
        id={`reply-${reviewId}`}
        dir="auto"
        rows={3}
        maxLength={MAX_REPLY}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={t('reviews.replyPlaceholder')}
        className="w-full rounded-md border border-border-strong bg-surface p-3 text-sm text-fg outline-none focus:border-primary"
      />

      {/* `.numeric` on the span, never on the paragraph: it sets
          `direction: ltr`, so on the block it would also drag the counter to
          the opposite side of the composer in Arabic. The digits stay Latin
          and left-to-right; the line stays where the rest of the screen is. */}
      <p className="text-xs text-fg-subtle">
        <span className="numeric">
          {cleaned.length} / {MAX_REPLY}
        </span>
      </p>

      {send.error && <Alert tone="danger">{message(send.error)}</Alert>}

      <div className="flex flex-wrap gap-3">
        <Button
          size="sm"
          loading={send.isPending}
          disabled={cleaned.length === 0}
          onClick={() =>
            send.mutate(
              { id: reviewId, reply: cleaned },
              { onSuccess: () => setOpen(false) },
            )
          }
        >
          {t('reviews.send')}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setOpen(false)
            setText('')
          }}
        >
          {t('job.keep')}
        </Button>
      </div>
    </div>
  )
}
