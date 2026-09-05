import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '@/data/client'
import {
  useCredit,
  useFeedRequest,
  useSendOffer,
  useWithdrawOffer,
} from '@/data/offers'
import { localisedName } from '@/data/types'
import { formatBudget, formatDate, formatDirhams, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { OutOfCredit } from '@/ui/OutOfCredit'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { URGENCY_KEYS } from '@/ui/urgencyLabels'

/**
 * M5 — the request in full, and the price he puts on it.
 *
 * The address is not on this page. Not blanked, not masked: the API has no
 * field for it until his offer is accepted. What *is* on the page, before he
 * types a number, is exactly what the lead will cost him and exactly when —
 * only if the client accepts.
 */

export function OfferPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const params = useParams()
  const navigate = useNavigate()

  const requestId = Number(params.id)
  const valid = Number.isInteger(requestId) && requestId > 0

  const request = useFeedRequest(valid ? requestId : null)
  const credit = useCredit()
  const send = useSendOffer()
  const withdraw = useWithdrawOffer()

  const [price, setPrice] = useState('')
  const [message, setMessage] = useState('')
  const [available, setAvailable] = useState('')

  // Editing an existing offer starts from what he actually sent.
  const existing = request.data?.my_offer ?? null
  useEffect(() => {
    if (!existing) return
    setPrice(String(Math.round(existing.price_centimes / 100)))
    setMessage(existing.message)
    setAvailable(existing.available_from ? existing.available_from.slice(0, 10) : '')
  }, [existing])

  if (!valid) {
    return <EmptyState title={t('requests.notFound')} action={<BackLink />} />
  }

  if (request.isPending) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-56" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (request.isError) {
    const blocked =
      request.error instanceof ApiError && request.error.code === 'insufficient_credit'
    return (
      <div className="mx-auto max-w-2xl">
        {blocked ? (
          <OutOfCredit
            feeCentimes={credit.data?.default_lead_fee_centimes ?? 0}
            language={language}
          />
        ) : (
          <ErrorState error={request.error} onRetry={() => void request.refetch()} />
        )}
        <div className="mt-6 flex justify-center">
          <BackLink />
        </div>
      </div>
    )
  }

  const data = request.data
  const budget = formatBudget(data.budget_min_centimes, data.budget_max_centimes, language)
  const centimes = Math.round(Number(price) * 100)
  const priced = Number.isFinite(centimes) && centimes > 0
  const freeLead = (credit.data?.free_leads_left ?? 0) > 0

  return (
    <div className="mx-auto max-w-2xl">
      <BackLink />

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <h1 dir="auto" className="text-2xl font-bold text-fg sm:text-3xl">
          {data.title}
        </h1>
        <Badge tone={data.urgency === 'today' ? 'warning' : 'neutral'} className="mt-1.5">
          {t(URGENCY_KEYS[data.urgency])}
        </Badge>
      </header>

      <Card className="mt-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral" className="gap-2">
            <TradeIcon name={data.trade.icon} className="size-4" />
            {localisedName(data.trade, language)}
          </Badge>
          {/* The city, and only the city. */}
          <Badge tone="neutral">{localisedName(data.city, language)}</Badge>
          <span className="text-sm text-fg-subtle">
            {formatRelative(data.created_at, language)}
          </span>
        </div>

        <p dir="auto" className="mt-5 whitespace-pre-line text-fg-muted">
          {data.description}
        </p>

        {data.photos.length > 0 && (
          <ul className="mt-5 flex flex-wrap gap-3">
            {data.photos.map((photo) => (
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
        )}

        <dl className="mt-6 divide-y divide-border border-t border-border text-sm">
          <div className="flex items-start justify-between gap-4 py-3">
            <dt className="text-fg-subtle">{t('feed.budget')}</dt>
            <dd className={budget ? 'numeric font-medium text-fg' : 'text-fg-subtle'}>
              {budget ?? t('feed.noBudget')}
            </dd>
          </div>
          <div className="flex items-start justify-between gap-4 py-3">
            <dt className="text-fg-subtle">{t('requests.offersTitle')}</dt>
            <dd className="numeric font-medium text-fg">{data.offers_count}</dd>
          </div>
        </dl>
      </Card>

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('offer.title')}</h2>

        {existing?.status === 'accepted' ? (
          <Alert tone="success" className="mt-4">
            {t('requests.accepted')}
          </Alert>
        ) : (
          <div className="mt-5 flex flex-col gap-6">
            <div>
              <Field
                label={t('offer.price')}
                type="number"
                numeric
                min={20}
                prefix="DH"
                value={price}
                onChange={(event) => setPrice(event.target.value)}
              />
              <p className="mt-2 text-xs text-fg-subtle">{t('offer.priceHint')}</p>
            </div>

            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-fg">{t('offer.message')}</span>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={t('offer.messagePlaceholder')}
                rows={4}
                maxLength={1000}
                className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
              />
            </label>

            <Field
              label={t('offer.available')}
              type="date"
              numeric
              value={available}
              onChange={(event) => setAvailable(event.target.value)}
            />

            {/* Said before he types a number, not after he presses send. */}
            <Alert tone="info">
              {freeLead
                ? t('offer.feeFree', { count: credit.data?.free_leads_left ?? 0 })
                : t('offer.feeNote', {
                    fee: formatDirhams(data.lead_fee_centimes, language),
                  })}
            </Alert>

            {send.isError && <ErrorState error={send.error} />}

            <div className="flex flex-wrap items-start gap-4 border-t border-border pt-5">
              <ConfirmButton
                label={existing ? t('offer.update') : t('offer.send')}
                question={t('offer.sendConfirm', {
                  fee: formatDirhams(data.lead_fee_centimes, language),
                })}
                confirmLabel={t('offer.sendYes')}
                size="pro"
                disabled={!priced}
                loading={send.isPending}
                onConfirm={() =>
                  send.mutate(
                    {
                      requestId,
                      price_centimes: centimes,
                      message: message.trim() || null,
                      available_from: available ? `${available}T09:00:00` : null,
                    },
                    { onSuccess: () => navigate('/pro/offers') },
                  )
                }
              />

              {existing && existing.status === 'pending' && (
                <ConfirmButton
                  label={t('offer.withdraw')}
                  question={t('offer.withdrawConfirm')}
                  confirmLabel={t('offer.withdrawYes')}
                  variant="ghost"
                  tone="danger"
                  size="pro"
                  loading={withdraw.isPending}
                  onConfirm={() =>
                    withdraw.mutate(existing.id, {
                      onSuccess: () => navigate('/pro/requests'),
                    })
                  }
                />
              )}
            </div>

            {existing && (
              <p className="text-xs text-fg-subtle">
                {t('offer.sentAt')} {formatDate(existing.created_at, language)}
              </p>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

function BackLink() {
  const { t } = useTranslation()
  return (
    <Link to="/pro/requests" className="text-sm font-semibold text-primary hover:underline">
      <span aria-hidden className="inline-block rtl:rotate-180">
        &larr;
      </span>{' '}
      {t('feed.title')}
    </Link>
  )
}
