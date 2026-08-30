import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  useCancelRequest,
  useMyRequests,
  type RequestStatus,
  type ServiceRequest,
} from '@/data/requests'
import { localisedName } from '@/data/types'
import { formatBudget, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { cn } from '@/ui/cn'

/**
 * C2 — his requests, grouped the way he thinks about them.
 *
 * Open first and loudest: those are the ones with a decision waiting in them.
 * Finished work is kept, not hidden, but it is not what the page is about.
 */

const GROUPS: { key: 'open' | 'assigned' | 'closed'; statuses: RequestStatus[] }[] = [
  { key: 'open', statuses: ['open'] },
  { key: 'assigned', statuses: ['assigned'] },
  { key: 'closed', statuses: ['done', 'cancelled', 'expired'] },
]

export function RequestsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const requests = useMyRequests()

  return (
    <div className="mx-auto max-w-4xl">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('requests.title')}</h1>
        <Link to="/client/requests/new">
          <Button>{t('requests.newOne')}</Button>
        </Link>
      </header>

      <div className="mt-8">
        {requests.isPending ? (
          <ul className="flex flex-col gap-4">
            {[0, 1, 2].map((index) => (
              <li key={index}>
                <Skeleton className="h-32" />
              </li>
            ))}
          </ul>
        ) : requests.isError ? (
          <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
        ) : (requests.data?.items.length ?? 0) === 0 ? (
          <EmptyState
            title={t('requests.empty')}
            body={t('requests.emptyBody')}
            action={
              <Link to="/client/requests/new">
                <Button>{t('requests.newOne')}</Button>
              </Link>
            }
          />
        ) : (
          <Groups items={requests.data?.items ?? []} language={language} />
        )}
      </div>
    </div>
  )
}

function Groups({ items, language }: { items: ServiceRequest[]; language: Language }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-10">
      {GROUPS.map((group) => {
        const rows = items.filter((item) => group.statuses.includes(item.status))
        if (rows.length === 0) return null

        return (
          <section key={group.key}>
            <h2 className="mb-4 flex items-baseline gap-2 text-sm font-bold text-fg-subtle uppercase">
              {t(`requests.${group.key}`)}
              <span className="numeric text-fg-subtle">({rows.length})</span>
            </h2>
            <ul className="flex flex-col gap-4">
              {rows.map((request) => (
                <li key={request.id}>
                  <RequestRow request={request} language={language} />
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function RequestRow({ request, language }: { request: ServiceRequest; language: Language }) {
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const cancel = useCancelRequest()

  const budget = formatBudget(
    request.budget_min_centimes,
    request.budget_max_centimes,
    language,
  )

  return (
    <article className="rounded-lg border border-border bg-surface shadow-sm transition-all duration-(--duration-fast) hover:border-primary/40 hover:shadow-md">
      <Link to={`/client/requests/${request.id}`} className="flex gap-4 p-5">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-primary-soft">
          <TradeIcon name={request.trade.icon} className="size-6 text-primary" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
            <h3 dir="auto" className="font-semibold text-fg">
              {request.title}
            </h3>
            <StatusBadge status={request.status} />
          </div>

          <p className="mt-1 text-sm text-fg-muted">
            {localisedName(request.trade, language)} · {localisedName(request.city, language)}
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            {/* The loudest thing on the card: it is the reason to open it. */}
            <OfferCount count={request.offers_count} status={request.status} />
            {budget && (
              <span className="text-fg-muted">
                {t('requests.budget')}: <span className="numeric font-medium">{budget}</span>
              </span>
            )}
            <span className="text-fg-subtle">
              {t('requests.posted')} {formatRelative(request.created_at, language)}
            </span>
          </div>
        </div>
      </Link>

      {request.status === 'open' && (
        <div className="border-t border-border px-5 py-3">
          {confirming ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-fg-muted">{t('requests.cancelConfirm')}</p>
              <Button
                size="sm"
                variant="danger"
                loading={cancel.isPending}
                onClick={() => cancel.mutate({ requestId: request.id })}
              >
                {t('requests.cancelYes')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
                {t('requests.keep')}
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => setConfirming(true)}>
              {t('requests.cancel')}
            </Button>
          )}
        </div>
      )}
    </article>
  )
}

function OfferCount({ count, status }: { count: number; status: RequestStatus }) {
  const { t } = useTranslation()

  if (count === 0) {
    // "Not yet" only means something while it can still happen. A closed
    // request that drew nothing says nothing.
    return status === 'open' ? (
      <span className="text-sm text-fg-subtle">{t('requests.noOffers')}</span>
    ) : null
  }

  const label = count === 1 ? t('requests.offersOne') : t('requests.offers', { count })
  // Loud while he can still act on them; plain once the request is closed.
  return status === 'open' ? (
    <Badge tone="brand" className="text-sm">
      {label}
    </Badge>
  ) : (
    <span className="text-sm text-fg-muted">{label}</span>
  )
}

const STATUS_TONES = {
  open: 'brand',
  assigned: 'success',
  done: 'neutral',
  cancelled: 'neutral',
  expired: 'neutral',
} as const

const STATUS_KEYS: Record<RequestStatus, string> = {
  open: 'requests.statusOpen',
  assigned: 'requests.statusAssigned',
  done: 'requests.statusDone',
  cancelled: 'requests.statusCancelled',
  expired: 'requests.statusExpired',
}

export function StatusBadge({ status, className }: { status: RequestStatus; className?: string }) {
  const { t } = useTranslation()
  return (
    <Badge tone={STATUS_TONES[status]} className={cn('shrink-0', className)}>
      {t(STATUS_KEYS[status])}
    </Badge>
  )
}
