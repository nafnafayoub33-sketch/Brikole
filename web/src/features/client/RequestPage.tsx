import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useOpenConversation } from '@/data/chat'
import {
  useCancelRequest,
  useDeclineOffer,
  useMyRequest,
  useRequestOffers,
  type Offer,
  type OfferStatus,
  type ServiceRequest,
} from '@/data/requests'
import { localisedName } from '@/data/types'
import { StatusBadge } from '@/features/client/RequestsPage'
import { formatBudget, formatDate, formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { cn } from '@/ui/cn'

/**
 * C3 — the request as it was published, and what it drew.
 *
 * Everything above the offers exists to answer one question a tradesman's
 * price does not: is this offer for the job I actually described?
 */

type Sort = 'price' | 'rating' | 'soonest'

const SORTS: Sort[] = ['price', 'rating', 'soonest']

const URGENCY_KEYS = {
  today: 'request.urgencyToday',
  this_week: 'request.urgencyWeek',
  flexible: 'request.urgencyFlexible',
} as const

export function RequestPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const params = useParams()
  const navigate = useNavigate()

  const requestId = Number(params.id)
  const valid = Number.isInteger(requestId) && requestId > 0

  const request = useMyRequest(valid ? requestId : null)
  const offers = useRequestOffers(valid ? requestId : null)
  const cancel = useCancelRequest()
  const [confirming, setConfirming] = useState(false)
  const [sort, setSort] = useState<Sort>('price')

  if (!valid) {
    return <EmptyState title={t('requests.notFound')} action={<BackLink />} />
  }

  if (request.isPending) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (request.isError) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorState error={request.error} onRetry={() => void request.refetch()} />
        <div className="mt-6 flex justify-center">
          <BackLink />
        </div>
      </div>
    )
  }

  const data = request.data

  return (
    <div className="mx-auto max-w-3xl">
      <BackLink />

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <h1 dir="auto" className="text-2xl font-bold text-fg sm:text-3xl">
          {data.title}
        </h1>
        <StatusBadge status={data.status} className="mt-1.5" />
      </header>

      {data.status === 'cancelled' && (
        <Alert tone="warning" className="mt-5">
          {t('requests.cancelledBanner')}
          {data.cancel_reason && (
            <>
              {' '}
              <span dir="auto">
                {t('requests.cancelledReason')}: {data.cancel_reason}
              </span>
            </>
          )}
        </Alert>
      )}
      {data.status === 'expired' && (
        <Alert tone="warning" className="mt-5">
          {t('requests.expiredBanner')}
        </Alert>
      )}
      {data.status === 'assigned' && (
        <Alert tone="success" className="mt-5">
          {t('requests.assignedBanner')}
        </Alert>
      )}
      {data.status === 'done' && (
        <Alert tone="success" className="mt-5">
          {t('requests.doneBanner')}
        </Alert>
      )}

      <Details request={data} language={language} />

      <section className="mt-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="flex items-baseline gap-2 text-xl font-bold text-fg">
            {t('requests.offersTitle')}
            {(offers.data?.length ?? 0) > 0 && (
              <span className="numeric text-fg-subtle">({offers.data?.length})</span>
            )}
          </h2>
          {(offers.data?.length ?? 0) > 1 && <SortControl sort={sort} onChange={setSort} />}
        </div>

        <div className="mt-5">
          <Offers
            query={offers}
            language={language}
            sort={sort}
            requestId={requestId}
            readOnly={data.status !== 'open'}
          />
        </div>
      </section>

      {data.status === 'open' && (
        <footer className="mt-10 border-t border-border pt-6">
          {data.offers_count === 0 ? (
            <div className="mb-6">
              <Link to={`/client/requests/${requestId}/edit`}>
                <Button variant="secondary">{t('requests.edit')}</Button>
              </Link>
            </div>
          ) : (
            <p className="mb-6 text-sm text-fg-subtle">{t('requests.editLocked')}</p>
          )}

          {confirming ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-fg-muted">{t('requests.cancelConfirm')}</p>
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="danger"
                  loading={cancel.isPending}
                  onClick={() =>
                    cancel.mutate(
                      { requestId },
                      { onSuccess: () => navigate('/client/requests') },
                    )
                  }
                >
                  {t('requests.cancelYes')}
                </Button>
                <Button variant="ghost" onClick={() => setConfirming(false)}>
                  {t('requests.keep')}
                </Button>
              </div>
              {cancel.isError && <ErrorState error={cancel.error} />}
            </div>
          ) : (
            <Button variant="ghost" onClick={() => setConfirming(true)}>
              {t('requests.cancel')}
            </Button>
          )}
        </footer>
      )}
    </div>
  )
}

function BackLink() {
  const { t } = useTranslation()
  return (
    <Link
      to="/client/requests"
      className="text-sm font-semibold text-primary hover:underline"
    >
      <span aria-hidden className="inline-block rtl:rotate-180">
        &larr;
      </span>{' '}
      {t('requests.backToList')}
    </Link>
  )
}

function Details({ request, language }: { request: ServiceRequest; language: Language }) {
  const { t } = useTranslation()
  const budget = formatBudget(
    request.budget_min_centimes,
    request.budget_max_centimes,
    language,
  )

  return (
    <Card className="mt-6">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral" className="gap-2">
          <TradeIcon name={request.trade.icon} className="size-4" />
          {localisedName(request.trade, language)}
        </Badge>
        <Badge tone="neutral">{localisedName(request.city, language)}</Badge>
        <Badge tone="neutral">{t(URGENCY_KEYS[request.urgency])}</Badge>
      </div>

      <h3 className="mt-6 mb-2 text-sm font-semibold text-fg-subtle uppercase">
        {t('requests.description')}
      </h3>
      <p dir="auto" className="whitespace-pre-line text-fg-muted">
        {request.description}
      </p>

      {request.photos.length > 0 && (
        <>
          <h3 className="mt-6 mb-2 text-sm font-semibold text-fg-subtle uppercase">
            {t('requests.photos')}
          </h3>
          <ul className="flex flex-wrap gap-3">
            {request.photos.map((photo) => (
              <li key={photo.id}>
                <img
                  src={photo.url}
                  alt=""
                  loading="lazy"
                  className="size-28 rounded-md border border-border object-cover"
                />
              </li>
            ))}
          </ul>
        </>
      )}

      <dl className="mt-6 divide-y divide-border border-t border-border text-sm">
        <Row label={t('requests.budget')} value={budget ?? t('requests.noBudget')} numeric={budget !== null} />
        <Row label={t('requests.address')} value={request.address} />
        {/* No `numeric` on a date: it is a number *and* a month name, and
            forcing the line LTR throws the year across the Arabic month. */}
        <Row label={t('requests.posted')} value={formatDate(request.created_at, language)} />
        {request.status === 'open' && request.expires_at && (
          <Row label={t('requests.expires')} value={formatDate(request.expires_at, language)} />
        )}
        {request.cancelled_at && (
          <Row
            label={t('requests.cancelledOn')}
            value={formatDate(request.cancelled_at, language)}
          />
        )}
      </dl>

      <p className="mt-4 text-xs text-fg-subtle">{t('requests.addressHidden')}</p>
    </Card>
  )
}

function Row({
  label,
  value,
  numeric = false,
}: {
  label: string
  value: string
  numeric?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <dt className="shrink-0 text-fg-subtle">{label}</dt>
      <dd dir="auto" className={cn('text-end font-medium text-fg', numeric && 'numeric')}>
        {value}
      </dd>
    </div>
  )
}

const SORT_KEYS: Record<Sort, string> = {
  price: 'requests.sortPrice',
  rating: 'requests.sortRating',
  soonest: 'requests.sortSoonest',
}

function SortControl({ sort, onChange }: { sort: Sort; onChange: (sort: Sort) => void }) {
  const { t } = useTranslation()

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-fg-subtle">{t('requests.sortBy')}</span>
      <select
        aria-label={t('requests.sortBy')}
        value={sort}
        onChange={(event) => onChange(event.target.value as Sort)}
        className="min-h-9 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
      >
        {SORTS.map((option) => (
          <option key={option} value={option}>
            {t(SORT_KEYS[option])}
          </option>
        ))}
      </select>
    </label>
  )
}

function Offers({
  query,
  language,
  sort,
  requestId,
  readOnly,
}: {
  query: ReturnType<typeof useRequestOffers>
  language: Language
  sort: Sort
  requestId: number
  readOnly: boolean
}) {
  const { t } = useTranslation()

  const sorted = useMemo(() => {
    const items = [...(query.data ?? [])]
    return items.sort((a, b) => {
      if (sort === 'price') return a.price_centimes - b.price_centimes
      if (sort === 'rating') return b.provider.rating_avg - a.provider.rating_avg
      // Soonest: an offer with no date said nothing, so it goes last rather
      // than pretending to be available now.
      const left = a.available_from ? new Date(a.available_from).getTime() : Infinity
      const right = b.available_from ? new Date(b.available_from).getTime() : Infinity
      return left - right
    })
  }, [query.data, sort])

  if (query.isPending) {
    return (
      <ul className="flex flex-col gap-4">
        {[0, 1].map((index) => (
          <li key={index}>
            <Skeleton className="h-36" />
          </li>
        ))}
      </ul>
    )
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  }

  if (sorted.length === 0) {
    return <EmptyState title={t('requests.offersEmpty')} body={t('requests.offersEmptyBody')} />
  }

  return (
    <ul className="flex flex-col gap-4">
      {sorted.map((offer) => (
        <li key={offer.id}>
          <OfferCard
            offer={offer}
            language={language}
            requestId={requestId}
            readOnly={readOnly}
          />
        </li>
      ))}
    </ul>
  )
}

function OfferCard({
  offer,
  language,
  requestId,
  readOnly,
}: {
  offer: Offer
  language: Language
  requestId: number
  readOnly: boolean
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const openChat = useOpenConversation()
  const decline = useDeclineOffer()
  const provider = offer.provider

  return (
    <Card className={cn(offer.status !== 'pending' && 'opacity-70')}>
      <div className="flex flex-wrap items-start gap-4">
        <Avatar url={provider.avatar_url} name={provider.full_name} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <Link
              to={`/m3allem/${provider.id}`}
              dir="auto"
              className="font-semibold text-fg hover:text-primary hover:underline"
            >
              {provider.full_name}
            </Link>
            <span className="text-sm text-fg-subtle">
              {localisedName(provider.city, language)}
            </span>
          </div>

          {provider.headline && (
            <p dir="auto" className="mt-0.5 truncate text-sm text-fg-muted">
              {provider.headline}
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg-muted">
            {provider.rating_count > 0 ? (
              <span className="flex items-center gap-1.5">
                <Stars value={provider.rating_avg} size="sm" />
                <span className="numeric font-medium text-fg">
                  {provider.rating_avg.toFixed(1)}
                </span>
                <span className="text-fg-subtle">
                  ({provider.rating_count})
                </span>
              </span>
            ) : (
              <span className="text-fg-subtle">{t('provider.newHere')}</span>
            )}
            <span>{t('provider.jobsDone', { count: provider.jobs_done })}</span>
          </div>
        </div>

        <div className="text-end">
          <p className="numeric text-xl font-bold text-fg">
            {formatDirhams(offer.price_centimes, language)}
          </p>
          <p className="mt-1 text-xs text-fg-subtle">
            {formatRelative(offer.created_at, language)}
          </p>
        </div>
      </div>

      <p dir="auto" className="mt-4 text-sm text-fg-muted">
        {offer.message.trim() || t('requests.noMessage')}
      </p>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <span className="text-sm text-fg-muted">
          {offer.available_from
            ? t('requests.available', { date: formatDate(offer.available_from, language) })
            : t('requests.availableUnknown')}
        </span>

        <div className="flex items-center gap-3">
          <OfferStatusBadge status={offer.status} />
          <Link
            to={`/m3allem/${provider.id}`}
            className="text-sm font-semibold text-primary hover:underline"
          >
            {t('requests.viewProfile')}
          </Link>
        </div>
      </div>

      {offer.status === 'accepted' && (
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
          <span className="text-sm font-semibold text-success">{t('requests.accepted')}</span>
          <Link
            to="/client/jobs"
            className="text-sm font-semibold text-primary hover:underline"
          >
            {t('requests.goToJob')}
          </Link>
        </div>
      )}

      {offer.status === 'rejected' && (
        <div className="mt-4 border-t border-border pt-4">
          <span className="text-sm text-fg-subtle">{t('requests.declined')}</span>
        </div>
      )}

      {!readOnly && offer.status === 'pending' && (
        <div className="mt-4 flex flex-wrap items-start gap-4 border-t border-border pt-4">
          {/* No longer an irreversible press. Opening the chat commits him to
              nothing: he asks his questions, they settle on a price, and the
              job is created only when they have both signed the same one. */}
          <Button
            loading={openChat.isPending}
            onClick={() =>
              openChat.mutate(offer.id, {
                onSuccess: (conversation) =>
                  navigate(`/client/requests/${requestId}/chats/${conversation.id}`),
              })
            }
          >
            {t('requests.talk')}
          </Button>

          {/* Turning one down without choosing another: a tradesman is better
              off knowing now than sitting in a queue that has moved past him. */}
          <ConfirmButton
            label={t('requests.decline')}
            question={t('requests.declineConfirm')}
            confirmLabel={t('requests.declineYes')}
            variant="ghost"
            tone="danger"
            loading={decline.isPending}
            onConfirm={() => decline.mutate({ requestId, offerId: offer.id })}
          />

          {(openChat.isError || decline.isError) && (
            <div className="w-full">
              <ErrorState error={openChat.error ?? decline.error} />
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

const OFFER_TONES = {
  pending: 'brand',
  accepted: 'success',
  rejected: 'neutral',
  withdrawn: 'neutral',
  expired: 'neutral',
} as const

const OFFER_KEYS: Record<OfferStatus, string> = {
  pending: 'requests.offerStatusPending',
  accepted: 'requests.offerStatusAccepted',
  rejected: 'requests.offerStatusRejected',
  withdrawn: 'requests.offerStatusWithdrawn',
  expired: 'requests.offerStatusExpired',
}

function OfferStatusBadge({ status }: { status: OfferStatus }) {
  const { t } = useTranslation()
  return <Badge tone={OFFER_TONES[status]}>{t(OFFER_KEYS[status])}</Badge>
}

function Avatar({ url, name }: { url: string | null; name: string }) {
  if (url) {
    return (
      <img
        src={url}
        alt=""
        className="size-12 shrink-0 rounded-full border border-border object-cover"
      />
    )
  }

  // Initials rather than a grey silhouette: it tells two tradesmen apart.
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')

  return (
    <span
      aria-hidden
      className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary-soft text-base font-bold text-primary"
    >
      {initials}
    </span>
  )
}
