import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useTrades } from '@/data/catalog'
import { useCredit, useFeed, type FeedRequest } from '@/data/offers'
import type { Urgency } from '@/data/requests'
import { localisedName } from '@/data/types'
import { ApiError } from '@/data/client'
import { formatBudget, formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { OutOfCredit } from '@/ui/OutOfCredit'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { cn } from '@/ui/cn'
import { URGENCY_KEYS } from '@/ui/urgencyLabels'

/**
 * M4 — the requests he could take.
 *
 * The whole screen is replaced when his balance is empty: the API answers 402
 * and this renders the top-up call instead of the list. Showing him work he
 * cannot answer, and only refusing once he has written a price, is the version
 * of this screen that loses tradesmen.
 */

const URGENCIES: Urgency[] = ['today', 'this_week', 'flexible']

export function FeedPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language

  const [tradeId, setTradeId] = useState<number | null>(null)
  const [urgency, setUrgency] = useState<Urgency | null>(null)

  const trades = useTrades()
  const credit = useCredit()
  const feed = useFeed({ tradeId, urgency })

  const blocked =
    feed.error instanceof ApiError && feed.error.code === 'insufficient_credit'
  const filtered = tradeId !== null || urgency !== null

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('feed.title')}</h1>
        <p className="mt-2 text-fg-muted">{t('feed.subtitle')}</p>
      </header>

      {credit.data && !blocked && (
        <div className="mt-5 flex flex-wrap items-center gap-3 rounded-md bg-surface-2 px-4 py-3">
          <span className="text-sm text-fg-subtle">{t('feed.balance')}</span>
          <span className="numeric font-bold text-fg">
            {formatDirhams(credit.data.balance_centimes, language)}
          </span>
          {credit.data.free_leads_left > 0 && (
            <Badge tone="success">
              {credit.data.free_leads_left === 1
                ? t('feed.freeLeadsOne')
                : t('feed.freeLeads', { count: credit.data.free_leads_left })}
            </Badge>
          )}
        </div>
      )}

      {blocked ? (
        <div className="mt-8">
          <OutOfCredit
            feeCentimes={credit.data?.default_lead_fee_centimes ?? 0}
            language={language}
          />
        </div>
      ) : (
        <>
          <div className="mt-6 flex flex-wrap gap-3">
            <label className="flex items-center gap-2 text-sm">
              <select
                aria-label={t('feed.allTrades')}
                value={tradeId ?? ''}
                onChange={(event) => setTradeId(Number(event.target.value) || null)}
                className="min-h-11 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
              >
                <option value="">{t('feed.allTrades')}</option>
                {(trades.data ?? []).map((trade) => (
                  <option key={trade.id} value={trade.id}>
                    {localisedName(trade, language)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-2 text-sm">
              <select
                aria-label={t('feed.allUrgency')}
                value={urgency ?? ''}
                onChange={(event) =>
                  setUrgency((event.target.value as Urgency) || null)
                }
                className="min-h-11 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
              >
                <option value="">{t('feed.allUrgency')}</option>
                {URGENCIES.map((option) => (
                  <option key={option} value={option}>
                    {t(URGENCY_KEYS[option])}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-6">
            {feed.isPending ? (
              <ul className="flex flex-col gap-4">
                {[0, 1, 2].map((index) => (
                  <li key={index}>
                    <Skeleton className="h-36" />
                  </li>
                ))}
              </ul>
            ) : feed.isError ? (
              <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />
            ) : (feed.data?.items.length ?? 0) === 0 ? (
              <EmptyState
                title={filtered ? t('feed.emptyFiltered') : t('feed.empty')}
                body={filtered ? undefined : t('feed.emptyBody')}
                action={
                  filtered ? (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setTradeId(null)
                        setUrgency(null)
                      }}
                    >
                      {t('feed.allTrades')}
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              <ul className="flex flex-col gap-4">
                {(feed.data?.items ?? []).map((request) => (
                  <li key={request.id}>
                    <FeedRow request={request} language={language} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function FeedRow({ request, language }: { request: FeedRequest; language: Language }) {
  const { t } = useTranslation()
  const budget = formatBudget(
    request.budget_min_centimes,
    request.budget_max_centimes,
    language,
  )
  const answered = request.my_offer_id !== null

  return (
    <Card className={cn('transition-all duration-(--duration-fast) hover:border-primary/40')}>
      <div className="flex gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-primary-soft">
          <TradeIcon name={request.trade.icon} className="size-6 text-primary" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
            <h2 dir="auto" className="font-bold text-fg">
              {request.title}
            </h2>
            <Badge tone={request.urgency === 'today' ? 'warning' : 'neutral'}>
              {t(URGENCY_KEYS[request.urgency])}
            </Badge>
          </div>

          <p className="mt-1 text-sm text-fg-subtle">
            {localisedName(request.trade, language)} ·{' '}
            {localisedName(request.city, language)} ·{' '}
            {formatRelative(request.created_at, language)}
          </p>

          <p dir="auto" className="mt-3 text-sm text-fg-muted">
            {request.excerpt}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <span className="text-fg-muted">
              {t('feed.budget')}:{' '}
              {budget ? (
                <span className="numeric font-semibold text-fg">{budget}</span>
              ) : (
                <span className="text-fg-subtle">{t('feed.noBudget')}</span>
              )}
            </span>

            {/* How crowded it already is, which is how he decides whether to bother. */}
            {request.offers_count === 0 ? (
              <Badge tone="success">{t('feed.beFirst')}</Badge>
            ) : (
              <span className="text-fg-subtle">
                {request.offers_count === 1
                  ? t('feed.offersOne')
                  : t('feed.offers', { count: request.offers_count })}
              </span>
            )}

            {request.photos_count > 0 && (
              <span className="text-fg-subtle">
                {t('feed.photos', { count: request.photos_count })}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        {answered ? (
          <span className="text-sm font-semibold text-success">
            {t('feed.youOffered', {
              price: formatDirhams(request.my_offer_price_centimes ?? 0, language),
            })}
          </span>
        ) : (
          <span />
        )}
        <Link to={`/pro/requests/${request.id}`}>
          <Button size="pro" variant={answered ? 'secondary' : 'primary'}>
            {t('feed.open')}
          </Button>
        </Link>
      </div>
    </Card>
  )
}
