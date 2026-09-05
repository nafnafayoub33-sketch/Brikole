import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { useProvider, useProviderReviews } from '@/data/providers'
import { localisedName, type ProviderProfile, type Review, type Trade } from '@/data/types'
import { formatDate, formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { ReportButton } from '@/ui/ReportButton'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

const REVIEWS_PER_PAGE = 6

/** P3 — one tradesman, and everything a client decides on. */
export function ProviderProfilePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const { id } = useParams<{ id: string }>()
  const providerId = Number(id)
  const valid = Number.isInteger(providerId) && providerId > 0

  const provider = useProvider(valid ? providerId : null)
  const [page, setPage] = useState(1)
  const reviews = useProviderReviews(valid ? providerId : null, {
    page,
    perPage: REVIEWS_PER_PAGE,
  })

  if (!valid || (provider.isError && isNotFound(provider.error))) {
    return (
      <div className="mx-auto max-w-2xl px-5 py-20">
        <EmptyState
          title={t('profile.notFound')}
          body={t('profile.notFoundBody')}
          action={
            <Link to="/services">
              <Button variant="secondary">{t('profile.backToBrowse')}</Button>
            </Link>
          }
        />
      </div>
    )
  }

  if (provider.isError) {
    return (
      <div className="mx-auto max-w-2xl px-5 py-20">
        <ErrorState error={provider.error} onRetry={() => void provider.refetch()} />
      </div>
    )
  }

  if (provider.isPending) return <ProfileSkeleton />

  const person = provider.data
  const totalReviews = reviews.data?.total ?? person.rating_count
  const pages = Math.max(1, Math.ceil(totalReviews / REVIEWS_PER_PAGE))

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[320px_1fr]">
      <aside className="flex flex-col gap-5 lg:sticky lg:top-28 lg:self-start">
        <Card className="flex flex-col items-center gap-3 text-center">
          <Avatar name={person.full_name} />
          <div>
            <h1 dir="auto" className="text-lg font-bold text-fg">
              {person.full_name}
            </h1>
            <p className="mt-0.5 text-sm text-fg-muted">
              {localisedName(person.city, language)}
            </p>
          </div>

          {person.rating_count > 0 ? (
            <span className="flex items-center gap-2">
              <Stars value={person.rating_avg} />
              <span className="numeric text-sm font-bold text-fg">
                {person.rating_avg.toFixed(1)}
              </span>
              <span className="numeric text-sm text-fg-subtle">({person.rating_count})</span>
            </span>
          ) : (
            <span className="text-sm text-fg-subtle">{t('provider.newHere')}</span>
          )}

          {/* A paused tradesman's page still opens — he exists, and the link
              somebody has is worth following. What it must not do is invite a
              request he will not answer, so the button says when he is back
              instead of pretending. */}
          {person.availability.is_available ? (
            <Link to="/client/requests/new" className="w-full">
              <Button fullWidth size="lg">
                {t('profile.contact')}
              </Button>
            </Link>
          ) : (
            <Alert tone="warning" className="w-full">
              {person.availability.back_on
                ? t('profile.awayUntil', {
                    when: formatDate(person.availability.back_on, language),
                  })
                : t('profile.away')}
            </Alert>
          )}

          <dl className="mt-2 w-full divide-y divide-border text-sm">
            <Fact label={t('profile.city')} value={localisedName(person.city, language)} />
            <Fact
              label={t('profile.memberSince')}
              value={formatDate(person.member_since, language)}
            />
            <Fact
              label={t('profile.experience')}
              value={t('profile.years', { count: person.years_experience })}
            />
            <Fact
              label={t('profile.jobsDone')}
              value={String(person.jobs_done)}
              numeric
            />
            <Fact
              label={t('profile.radius')}
              value={t('profile.km', { count: person.radius_km })}
            />
          </dl>
        </Card>

        {person.bio && (
          <Card>
            <h2 dir="auto" className="text-sm font-bold text-fg">
              {t('profile.about', { name: person.full_name })}
            </h2>
            {/* User-authored: let the string pick its own direction. */}
            <p dir="auto" className="mt-2.5 text-sm leading-relaxed text-fg-muted">
              {person.bio}
            </p>
          </Card>
        )}
      </aside>

      <div className="flex flex-col gap-12">
        <section aria-labelledby="services-heading">
          <h2 id="services-heading" dir="auto" className="text-xl font-bold text-fg">
            {t('profile.services', { name: person.full_name })}
          </h2>
          <ul className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {person.trades.map((trade, index) => (
              <li key={trade.id}>
                <ServiceCard
                  trade={trade}
                  person={person}
                  language={language}
                  index={index}
                />
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="reviews-heading">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 id="reviews-heading" className="text-xl font-bold text-fg">
              {t('profile.reviews')}
            </h2>
            {totalReviews > 0 && (
              <span className="text-sm font-medium text-fg-muted">
                {t('profile.reviewsCount', { count: totalReviews })}
              </span>
            )}
          </div>

          {person.rating_count > 0 && (
            <Breakdown
              breakdown={person.rating_breakdown}
              total={person.rating_count}
              average={person.rating_avg}
            />
          )}

          <div className="mt-8">
            {reviews.isPending && (
              <div className="flex flex-col gap-6">
                {Array.from({ length: 3 }, (_, index) => (
                  <Skeleton key={index} className="h-24" />
                ))}
              </div>
            )}
            {reviews.isError && (
              <ErrorState error={reviews.error} onRetry={() => void reviews.refetch()} />
            )}
            {reviews.isSuccess && reviews.data.items.length === 0 && (
              <EmptyState title={t('profile.noReviews')} body={t('profile.noReviewsBody')} />
            )}
            {reviews.isSuccess && reviews.data.items.length > 0 && (
              <ul className="flex flex-col divide-y divide-border">
                {reviews.data.items.map((review) => (
                  <li key={review.id} className="py-6 first:pt-0">
                    <ReviewRow review={review} language={language} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <ReportButton
            targetType="provider_profile"
            targetId={person.id}
            label={t('report.reportProfile')}
            className="mt-8"
          />

          {reviews.isSuccess && pages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((value) => value - 1)}
              >
                {t('browse.previous')}
              </Button>
              <span className="text-sm text-fg-muted">
                {t('browse.pageOf', { page, pages })}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage((value) => value + 1)}
              >
                {t('browse.next')}
              </Button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

const COVERS = [
  'from-navy-700 to-navy-500',
  'from-navy-800 to-navy-600',
  'from-navy-600 to-navy-400',
] as const

function ServiceCard({
  trade,
  person,
  language,
  index,
}: {
  trade: Trade
  person: ProviderProfile
  language: Language
  index: number
}) {
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-sm">
      <div
        className={cn(
          'flex h-28 items-center justify-center bg-gradient-to-br',
          COVERS[index % COVERS.length],
        )}
      >
        <TradeIcon name={trade.icon} className="size-14 text-white/85" />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="text-sm font-semibold text-fg">{localisedName(trade, language)}</h3>
        {person.headline && (
          <p dir="auto" className="line-clamp-2 text-sm text-fg-muted">
            {person.headline}
          </p>
        )}
      </div>
      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        {person.starting_price_centimes !== null ? (
          <span>
            <span className="block text-[10px] font-semibold tracking-wide text-fg-subtle uppercase whitespace-nowrap">
              {t('provider.startingAt')}
            </span>
            <span className="numeric block text-sm font-bold text-fg">
              {formatDirhams(person.starting_price_centimes, language)}
            </span>
          </span>
        ) : (
          <span className="text-xs font-medium text-primary">{t('provider.onQuote')}</span>
        )}
        {/* The card already has the person's availability — a paused
            tradesman keeps his page but must not be asked from it, and one
            gated button beside one that is not is worse than neither. */}
        {person.availability.is_available && (
          <Link to="/client/requests/new" className="shrink-0">
            <Button size="sm" variant="secondary" className="whitespace-nowrap">
              {t('profile.contactShort')}
            </Button>
          </Link>
        )}
      </div>
    </div>
  )
}

function Breakdown({
  breakdown,
  total,
  average,
}: {
  breakdown: Record<string, number>
  total: number
  average: number
}) {
  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-10 gap-y-5 rounded-lg border border-border bg-surface-2 p-5">
      <div className="text-center">
        <p className="numeric text-4xl font-bold text-fg">{average.toFixed(1)}</p>
        <Stars value={average} className="mt-1" />
      </div>

      <ul className="min-w-56 flex-1 space-y-1.5">
        {[5, 4, 3, 2, 1].map((score) => {
          const count = breakdown[String(score)] ?? 0
          const share = total === 0 ? 0 : Math.round((count / total) * 100)
          return (
            <li key={score} className="flex items-center gap-3 text-xs">
              <span className="numeric w-3 text-fg-muted">{score}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-pill bg-surface-inset">
                <span
                  className="block h-full rounded-pill bg-star"
                  style={{ width: `${share}%` }}
                />
              </span>
              <span className="numeric w-8 text-end text-fg-subtle">{count}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ReviewRow({ review, language }: { review: Review; language: Language }) {
  const { t } = useTranslation()

  return (
    <article>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="flex size-9 items-center justify-center rounded-full bg-surface-inset text-xs font-bold text-fg-muted">
          {initials(review.author.display_name)}
        </span>
        <span>
          <span dir="auto" className="block text-sm font-semibold text-fg">
            {review.author.display_name}
          </span>
          {review.author.city && (
            <span className="block text-xs text-fg-subtle">
              {localisedName(review.author.city, language)}
            </span>
          )}
        </span>
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

      {review.trade && (
        <p className="mt-2 text-xs text-fg-subtle">{localisedName(review.trade, language)}</p>
      )}

      {review.reply && (
        <div className="mt-3 rounded-md border-s-2 border-primary bg-surface-2 px-4 py-3">
          <p className="text-xs font-semibold text-primary">{t('profile.replyLabel')}</p>
          <p dir="auto" className="mt-1 text-sm text-fg-muted">
            {review.reply}
          </p>
        </div>
      )}

      <ReportButton
        targetType="review"
        targetId={review.id}
        label={t('report.reportReview')}
        className="mt-3"
      />
    </article>
  )
}

function Fact({
  label,
  value,
  numeric = false,
}: {
  label: string
  value: string
  numeric?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <dt className="text-fg-subtle">{label}</dt>
      <dd className={cn('font-medium text-fg', numeric && 'numeric')}>{value}</dd>
    </div>
  )
}

function Avatar({ name }: { name: string }) {
  return (
    <span className="flex size-20 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-fg">
      {initials(name)}
    </span>
  )
}

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0] ?? '')
      .join('')
      .toUpperCase() || '?'
  )
}

function isNotFound(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'status' in error && error.status === 404
}

function ProfileSkeleton() {
  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[320px_1fr]">
      <Skeleton className="h-96" />
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
        </div>
        <Skeleton className="h-40" />
      </div>
    </div>
  )
}
