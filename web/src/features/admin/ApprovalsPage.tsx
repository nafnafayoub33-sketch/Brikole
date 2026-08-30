import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  useApprove,
  usePendingApplications,
  useReject,
  type Application,
} from '@/data/approvals'
import { ApiError } from '@/data/client'
import { localisedName } from '@/data/types'
import { usePrivateImage } from '@/hooks/usePrivateImage'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatDirhams, formatPhone, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * A2 — the queue, and the decision.
 *
 * Oldest first, because it is a queue: the person who has waited longest is
 * the one to look at next.
 */
export function ApprovalsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const applications = usePendingApplications()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const page = applications.data
  const items = page?.items ?? []
  const selected = items.find((item) => item.id === selectedId) ?? null

  // Acting on one removes it from the queue, so the selection has to move on
  // rather than point at a row that is no longer there. The effect depends on
  // the query's own object — `items` is a new array every render — and updates
  // through the setter so the current selection is not a dependency either.
  useEffect(() => {
    const list = page?.items ?? []
    if (list.length === 0) {
      setSelectedId(null)
      return
    }
    setSelectedId((current) =>
      list.some((item) => item.id === current) ? current : (list[0]?.id ?? null),
    )
  }, [page])

  if (applications.isPending) {
    return (
      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <Skeleton className="h-96" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (applications.isError) {
    return <ErrorState error={applications.error} onRetry={() => void applications.refetch()} />
  }

  const total = applications.data.total

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-baseline gap-x-3">
        <h1 className="text-2xl font-bold text-fg">{t('approvals.title')}</h1>
        {total > 0 && (
          <span className="text-sm font-medium text-fg-muted">
            {total === 1 ? t('approvals.waitingOne') : t('approvals.waiting', { count: total })}
          </span>
        )}
      </div>

      {total === 0 ? (
        <EmptyState title={t('approvals.empty')} body={t('approvals.emptyBody')} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <ul className="flex flex-col gap-2">
            {items.map((item) => (
              <li key={item.id}>
                <QueueRow
                  application={item}
                  language={language}
                  selected={item.id === selectedId}
                  onSelect={() => setSelectedId(item.id)}
                />
              </li>
            ))}
          </ul>

          {selected ? (
            <Detail key={selected.id} application={selected} language={language} />
          ) : (
            <EmptyState title={t('approvals.pick')} />
          )}
        </div>
      )}
    </div>
  )
}

function QueueRow({
  application,
  language,
  selected,
  onSelect,
}: {
  application: Application
  language: Language
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected}
      className={cn(
        'flex w-full items-center gap-3 rounded-md border-2 p-3 text-start',
        'transition-colors duration-(--duration-fast)',
        selected
          ? 'border-primary bg-primary-soft'
          : 'border-border bg-surface hover:border-border-strong',
      )}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-inset text-xs font-bold text-fg-muted">
        {initials(application.full_name)}
      </span>
      <span className="min-w-0 flex-1">
        <span dir="auto" className="block truncate text-sm font-semibold text-fg">
          {application.full_name}
        </span>
        <span className="block truncate text-xs text-fg-subtle">
          {application.trades.map((trade) => localisedName(trade, language)).join(' · ')}
          {' — '}
          {localisedName(application.city, language)}
        </span>
      </span>
      <span className="shrink-0 text-xs text-fg-subtle">
        {formatRelative(application.submitted_at, language)}
      </span>
      <span className="sr-only">{t('approvals.submitted')}</span>
    </button>
  )
}

function Detail({ application, language }: { application: Application; language: Language }) {
  const { t } = useTranslation()
  const approve = useApprove()
  const reject = useReject()
  const message = useErrorMessage()

  const [confirming, setConfirming] = useState<'approve' | 'reject' | null>(null)
  const [reason, setReason] = useState('')

  const error = approve.error ?? reject.error
  const conflict = error instanceof ApiError && error.status === 409

  return (
    <Card className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start gap-4 border-b border-border pb-5">
        <span className="flex size-14 items-center justify-center rounded-full bg-primary text-base font-bold text-primary-fg">
          {initials(application.full_name)}
        </span>
        <div className="min-w-0 flex-1">
          <h2 dir="auto" className="text-lg font-bold text-fg">
            {application.full_name}
          </h2>
          <p className="mt-0.5 text-sm text-fg-muted">
            {localisedName(application.city, language)} ·{' '}
            {t('profile.km', { count: application.radius_km })}
          </p>
          <p className="mt-1 text-sm text-fg-subtle">
            {t('approvals.phone')}:{' '}
            <span className="numeric">{formatPhone(application.phone)}</span>
          </p>
        </div>
        <p className="text-xs text-fg-subtle">
          {t('approvals.submitted')} {formatRelative(application.submitted_at, language)}
        </p>
      </header>

      {conflict && <Alert tone="warning">{t('approvals.handled')}</Alert>}
      {error && !conflict && <Alert tone="danger">{message(error)}</Alert>}

      <section className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-4">
          <Fact label={t('onboarding.headline')} value={application.headline ?? '—'} />
          <div>
            <p className="text-xs font-semibold text-fg-subtle uppercase">
              {t('onboarding.bio')}
            </p>
            <p dir="auto" className="mt-1.5 text-sm leading-relaxed text-fg">
              {application.bio || '—'}
            </p>
          </div>
          <Fact
            label={t('onboarding.trades')}
            value={application.trades.map((trade) => localisedName(trade, language)).join(' · ')}
          />
          <Fact
            label={t('profile.experience')}
            value={t('profile.years', { count: application.years_experience })}
          />
          <Fact
            label={t('onboarding.price')}
            value={
              application.starting_price_centimes === null
                ? t('provider.onQuote')
                : formatDirhams(application.starting_price_centimes, language)
            }
          />
        </div>

        <IdCard path={application.id_card_path} />
      </section>

      <section>
        <p className="mb-2 text-xs font-semibold text-fg-subtle uppercase">
          {t('approvals.portfolio')}
        </p>
        {application.photos.length === 0 ? (
          <p className="text-sm text-fg-subtle">{t('approvals.noPortfolio')}</p>
        ) : (
          <ul className="flex flex-wrap gap-3">
            {application.photos.map((photo) => (
              <li key={photo.id}>
                <img
                  src={photo.url}
                  alt=""
                  className="size-24 rounded-md border border-border object-cover"
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="border-t border-border pt-5">
        {confirming === null && (
          <div className="flex flex-wrap gap-3">
            <Button size="pro" onClick={() => setConfirming('approve')}>
              {t('approvals.approve')}
            </Button>
            <Button size="pro" variant="secondary" onClick={() => setConfirming('reject')}>
              {t('approvals.reject')}
            </Button>
          </div>
        )}

        {confirming === 'approve' && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-fg-muted">{t('approvals.approveConfirm')}</p>
            <div className="flex flex-wrap gap-3">
              <Button
                size="pro"
                loading={approve.isPending}
                onClick={() => approve.mutate(application.id)}
              >
                {t('approvals.approveYes')}
              </Button>
              <Button size="pro" variant="ghost" onClick={() => setConfirming(null)}>
                {t('approvals.cancel')}
              </Button>
            </div>
          </div>
        )}

        {confirming === 'reject' && (
          <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-fg">{t('approvals.rejectReason')}</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
                maxLength={500}
                className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-danger"
              />
              <span className="text-xs text-fg-subtle">{t('approvals.rejectReasonHint')}</span>
            </label>
            <div className="flex flex-wrap gap-3">
              <Button
                size="pro"
                variant="danger"
                disabled={reason.trim().length === 0}
                loading={reject.isPending}
                onClick={() =>
                  reject.mutate({ providerId: application.id, reason: reason.trim() })
                }
              >
                {t('approvals.rejectYes')}
              </Button>
              <Button size="pro" variant="ghost" onClick={() => setConfirming(null)}>
                {t('approvals.cancel')}
              </Button>
            </div>
          </div>
        )}
      </footer>
    </Card>
  )
}

function IdCard({ path }: { path: string | null }) {
  const { t } = useTranslation()
  const { url, loading, error } = usePrivateImage(path)

  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-fg-subtle uppercase">
        {t('approvals.idCard')}
      </p>

      {!path && (
        <p className="rounded-md border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-fg">
          {t('approvals.idCardMissing')}
        </p>
      )}
      {path && loading && <Skeleton className="aspect-[8/5] w-full" />}
      {path && error !== null && (
        <p className="text-sm text-danger">{t('approvals.idCardFailed')}</p>
      )}
      {url && (
        <img
          src={url}
          alt={t('approvals.idCard')}
          className="max-h-80 w-full rounded-md border border-border bg-surface-2 object-contain"
        />
      )}
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold text-fg-subtle uppercase">{label}</p>
      <p dir="auto" className="mt-1 text-sm font-medium text-fg">
        {value}
      </p>
    </div>
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
