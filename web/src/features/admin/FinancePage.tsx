import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  useApproveTopup,
  useRejectTopup,
  useTopupQueue,
  type PendingTopup,
} from '@/data/credit'
import { usePrivateImage } from '@/hooks/usePrivateImage'
import { formatDirhams, formatPhone, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * A5 — the transfers waiting to be confirmed.
 *
 * Oldest first, because it is a queue and the person who has waited longest is
 * next. Everything an admin needs to check a claim against a bank statement is
 * on the card: the amount, the reference, and the receipt, which is fetched
 * with his token rather than pointed at — an `<img src>` sends cookies but no
 * Authorization header, and this bucket has no public read.
 */
export function FinancePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const queue = useTopupQueue()

  const items = queue.data?.items ?? []

  return (
    <div className="mx-auto max-w-3xl">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('finance.title')}</h1>
        {items.length > 0 && (
          <p className="text-sm text-fg-muted">
            {items.length === 1
              ? t('finance.waitingOne')
              : t('finance.waiting', { count: items.length })}
          </p>
        )}
      </header>

      <Alert tone="warning" className="mt-5">
        {t('finance.checkFirst')}
      </Alert>

      <div className="mt-6">
        {queue.isPending ? (
          <ul className="flex flex-col gap-5">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-64" />
              </li>
            ))}
          </ul>
        ) : queue.isError ? (
          <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t('finance.empty')} body={t('finance.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-5">
            {items.map((topup) => (
              <li key={topup.id}>
                <TopupCard topup={topup} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function TopupCard({ topup, language }: { topup: PendingTopup; language: Language }) {
  const { t } = useTranslation()
  const approve = useApproveTopup()
  const reject = useRejectTopup()
  const [reason, setReason] = useState('')

  const failed = approve.error ?? reject.error

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-fg-subtle uppercase">
            {t('finance.provider')}
          </p>
          <p dir="auto" className="mt-1 font-bold text-fg">
            {topup.provider.full_name}
          </p>
          <p className="mt-0.5 text-sm text-fg-muted">
            {t('finance.phone')}:{' '}
            <span className="numeric">{formatPhone(topup.provider.phone)}</span>
          </p>
          <p className="mt-0.5 text-sm text-fg-muted">
            {t('finance.currentBalance')}:{' '}
            <span className="numeric">
              {formatDirhams(topup.provider.balance_centimes, language)}
            </span>
          </p>
        </div>

        <div className="text-end">
          <p className="numeric text-3xl font-bold text-fg">
            {formatDirhams(topup.amount_centimes, language)}
          </p>
          <p className="mt-1 text-xs text-fg-subtle">
            {formatRelative(topup.created_at, language)}
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-md bg-surface-2 px-4 py-3">
        <p className="text-xs font-semibold text-fg-subtle uppercase">
          {t('finance.reference')}
        </p>
        {/* What he types into the statement search, so it is selectable and big. */}
        <p className="numeric mt-1 text-lg font-semibold text-fg select-all">
          {topup.reference}
        </p>
      </div>

      <div className="mt-5">
        <p className="mb-2 text-xs font-semibold text-fg-subtle uppercase">
          {t('finance.receipt')}
        </p>
        <Receipt path={topup.receipt_path} />
      </div>

      <footer className="mt-6 border-t border-border pt-5">
        <div className="flex flex-wrap items-start gap-4">
          <ConfirmButton
            label={t('finance.approve')}
            question={t('finance.approveConfirm')}
            confirmLabel={t('finance.approveYes')}
            size="pro"
            loading={approve.isPending}
            onConfirm={() => approve.mutate(topup.id)}
          />

          <ConfirmButton
            label={t('finance.reject')}
            question={t('finance.rejectReason')}
            confirmLabel={t('finance.rejectYes')}
            variant="secondary"
            tone="danger"
            size="pro"
            loading={reject.isPending}
            confirmDisabled={reason.trim().length === 0}
            onConfirm={() => reject.mutate({ topupId: topup.id, reason: reason.trim() })}
          >
            <label className="flex flex-col gap-2">
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
                maxLength={500}
                className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-danger"
              />
              <span className="text-xs text-fg-subtle">{t('finance.rejectReasonHint')}</span>
            </label>
          </ConfirmButton>
        </div>

        {failed && (
          <div className="mt-4">
            <ErrorState error={failed} />
          </div>
        )}
      </footer>
    </Card>
  )
}

function Receipt({ path }: { path: string | null }) {
  const { t } = useTranslation()
  const { url, loading, error } = usePrivateImage(path)

  if (!path) {
    return <p className="text-sm text-fg-subtle">{t('finance.receiptMissing')}</p>
  }
  if (loading) {
    return <Skeleton className="h-48 w-full max-w-sm" />
  }
  if (error || !url) {
    return <p className="text-sm text-danger">{t('finance.receiptFailed')}</p>
  }

  return (
    <img
      src={url}
      alt=""
      className={cn('max-h-72 rounded-md border border-border object-contain')}
    />
  )
}
