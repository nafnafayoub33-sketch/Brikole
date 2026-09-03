import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useMyOffers, useWithdrawOffer, type MyOffer } from '@/data/offers'
import type { OfferStatus } from '@/data/requests'
import { localisedName } from '@/data/types'
import { formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'

/**
 * M6 — what he has sent and what came of it.
 *
 * Grouped by what he can still do about each: waiting is the group he checks,
 * accepted is the one that became work, and the rest is history.
 */

const GROUPS: { key: 'Pending' | 'Accepted' | 'Closed'; statuses: OfferStatus[] }[] = [
  { key: 'Pending', statuses: ['pending'] },
  { key: 'Accepted', statuses: ['accepted'] },
  { key: 'Closed', statuses: ['rejected', 'withdrawn', 'expired'] },
]

const STATUS_TONES = {
  pending: 'brand',
  accepted: 'success',
  rejected: 'neutral',
  withdrawn: 'neutral',
  expired: 'neutral',
} as const

const STATUS_KEYS: Record<OfferStatus, string> = {
  pending: 'requests.offerStatusPending',
  accepted: 'requests.offerStatusAccepted',
  rejected: 'requests.offerStatusRejected',
  withdrawn: 'requests.offerStatusWithdrawn',
  expired: 'requests.offerStatusExpired',
}

export function MyOffersPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const offers = useMyOffers()

  const items = offers.data?.items ?? []

  return (
    <div className="mx-auto max-w-3xl">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('offer.myOffers')}</h1>
        <Link to="/pro/requests">
          <Button size="pro" variant="secondary">
            {t('feed.title')}
          </Button>
        </Link>
      </header>

      <div className="mt-8">
        {offers.isPending ? (
          <ul className="flex flex-col gap-4">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-28" />
              </li>
            ))}
          </ul>
        ) : offers.isError ? (
          <ErrorState error={offers.error} onRetry={() => void offers.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            title={t('offer.myOffersEmpty')}
            body={t('offer.myOffersEmptyBody')}
            action={
              <Link to="/pro/requests">
                <Button size="pro">{t('feed.title')}</Button>
              </Link>
            }
          />
        ) : (
          <div className="flex flex-col gap-10">
            {GROUPS.map((group) => {
              const rows = items.filter((offer) => group.statuses.includes(offer.status))
              if (rows.length === 0) return null

              return (
                <section key={group.key}>
                  <h2 className="mb-4 flex items-baseline gap-2 text-sm font-bold text-fg-subtle uppercase">
                    {t(`offer.group${group.key}`)}
                    <span className="numeric">({rows.length})</span>
                  </h2>
                  <ul className="flex flex-col gap-4">
                    {rows.map((offer) => (
                      <li key={offer.id}>
                        <OfferRow offer={offer} language={language} />
                      </li>
                    ))}
                  </ul>
                </section>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function OfferRow({ offer, language }: { offer: MyOffer; language: Language }) {
  const { t } = useTranslation()
  const withdraw = useWithdrawOffer()

  return (
    <Card>
      <div className="flex gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-primary-soft">
          <TradeIcon name={offer.trade.icon} className="size-6 text-primary" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
            <h3 dir="auto" className="font-semibold text-fg">
              {offer.request_title}
            </h3>
            <Badge tone={STATUS_TONES[offer.status]}>{t(STATUS_KEYS[offer.status])}</Badge>
          </div>

          <p className="mt-1 text-sm text-fg-subtle">
            {localisedName(offer.city, language)} · {t('offer.sentAt')}{' '}
            {formatRelative(offer.created_at, language)}
          </p>

          {offer.message && (
            <p dir="auto" className="mt-3 text-sm text-fg-muted">
              {offer.message}
            </p>
          )}
        </div>

        <div className="text-end">
          <p className="numeric text-xl font-bold text-fg">
            {formatDirhams(offer.price_centimes, language)}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-end gap-4 border-t border-border pt-4">
        {offer.job_id !== null ? (
          <Link
            to="/pro/jobs"
            className="text-sm font-semibold text-primary hover:underline"
          >
            {t('offer.seeJob')}
          </Link>
        ) : offer.status === 'pending' ? (
          <>
            {/* The thread exists only once the client has opened it. Until
                then there is nothing to link to, and the row says so rather
                than showing a link that 404s. */}
            {offer.conversation_id !== null ? (
              <Link
                to={`/pro/chats/${offer.conversation_id}`}
                className="text-sm font-semibold text-primary hover:underline"
              >
                {t('offer.openChat')}
              </Link>
            ) : (
              <span className="text-sm text-fg-subtle">{t('offer.noReplyYet')}</span>
            )}

            {/* Withdrawing lives here as well as on M5, because M5 closes when
                his balance runs out and an offer he can no longer edit is one
                he must still be able to take back. */}
            <ConfirmButton
              label={t('offer.withdraw')}
              question={t('offer.withdrawConfirm')}
              confirmLabel={t('offer.withdrawYes')}
              variant="ghost"
              tone="danger"
              size="sm"
              loading={withdraw.isPending}
              onConfirm={() => withdraw.mutate(offer.id)}
            />
            <Link
              to={`/pro/requests/${offer.request_id}`}
              className="text-sm font-semibold text-primary hover:underline"
            >
              {t('offer.seeRequest')}
            </Link>
          </>
        ) : null}
      </div>
      {withdraw.isError && (
        <div className="mt-3">
          <ErrorState error={withdraw.error} />
        </div>
      )}
    </Card>
  )
}
