import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import {
  NOTIFICATIONS_PER_PAGE,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  type Notification,
  type NotificationKind,
} from '@/data/notifications'
import { formatDirhams, formatRelative, isolate } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Pager } from '@/ui/Pager'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/** One key per kind. The API sends the kind; the wording is ours, in three
 *  languages, and the payload fills its blanks. */
const LINES: Record<NotificationKind, string> = {
  offer_received: 'notify.offerReceived',
  offer_accepted: 'notify.offerAccepted',
  offer_rejected: 'notify.offerRejected',
  job_started: 'notify.jobStarted',
  job_done: 'notify.jobDone',
  review_received: 'notify.reviewReceived',
  provider_approved: 'notify.providerApproved',
  provider_rejected: 'notify.providerRejected',
  topup_approved: 'notify.topupApproved',
  topup_rejected: 'notify.topupRejected',
  dispute_update: 'notify.disputeUpdate',
  credit_low: 'notify.creditLow',
}

function number(payload: Record<string, unknown>, key: string): number | null {
  const value = payload[key]
  return typeof value === 'number' ? value : null
}

/** Where a notification points. `null` when its payload has lost the id it
 *  needs — the line still reads, it just does not go anywhere. */
function destination(notification: Notification): string | null {
  const { payload } = notification

  const request = number(payload, 'request_id')
  const job = number(payload, 'job_id')
  const dispute = number(payload, 'dispute_id')

  switch (notification.kind) {
    case 'offer_received':
      return request === null ? null : `/client/requests/${request}`
    case 'job_started':
    case 'job_done':
      return job === null ? null : `/client/jobs/${job}`
    case 'dispute_update':
      return dispute === null ? null : `/client/disputes/${dispute}`
    default:
      return null
  }
}

/**
 * C6 — what happened while he was not looking.
 *
 * Every line is a thing to go and do, so every line is a link: a notification
 * that only tells you something is a notification you read once and then have
 * to go and find the screen for yourself.
 *
 * Opening one marks it read. The list itself marks nothing — a glance at the
 * bell should not erase what he has not looked at yet — and "mark all read" is
 * there for when he has decided he is done with the lot.
 */
export function NotificationsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const [page, setPage] = useState(1)
  const notifications = useNotifications(page)
  const markRead = useMarkNotificationRead()
  const markAll = useMarkAllNotificationsRead()

  const items = notifications.data?.items ?? []
  const unread = items.filter((item) => item.read_at === null).length
  const pages = notifications.data
    ? Math.max(1, Math.ceil(notifications.data.total / NOTIFICATIONS_PER_PAGE))
    : 1

  const open = (notification: Notification) => {
    if (notification.read_at === null) markRead.mutate({ id: notification.id })
    const to = destination(notification)
    if (to) navigate(to)
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-fg">{t('notify.title')}</h1>
        {unread > 0 && (
          <Button
            variant="secondary"
            size="sm"
            loading={markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            {t('notify.markAll')}
          </Button>
        )}
      </div>

      {notifications.isPending ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-16" />
          ))}
        </div>
      ) : notifications.isError ? (
        <ErrorState
          error={notifications.error}
          onRetry={() => void notifications.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState title={t('notify.empty')} body={t('notify.emptyBody')} />
      ) : (
        <>
          <ul className="flex flex-col gap-2">
            {items.map((notification) => (
              <li key={notification.id}>
                <Row notification={notification} language={language} onOpen={open} />
              </li>
            ))}
          </ul>

          {pages > 1 && (
            <Pager page={page} pages={pages} language={language} onChange={setPage} />
          )}
        </>
      )}
    </div>
  )
}

function Row({
  notification,
  language,
  onOpen,
}: {
  notification: Notification
  language: Language
  onOpen: (notification: Notification) => void
}) {
  const { t } = useTranslation()
  const unread = notification.read_at === null
  const price = number(notification.payload, 'price_centimes')

  return (
    <button
      type="button"
      onClick={() => onOpen(notification)}
      className={cn(
        'flex w-full items-start gap-3 rounded-lg border p-4 text-start shadow-sm',
        'transition-colors duration-(--duration-fast)',
        unread
          ? 'border-primary/30 bg-primary-soft hover:border-primary'
          : 'border-border bg-surface hover:border-border-strong',
      )}
    >
      {/* A dot rather than a word: unread is a state you scan, not read. The
          read rows keep the space so the column of text does not shift. */}
      <span
        aria-hidden
        className={cn(
          'mt-1.5 size-2 shrink-0 rounded-full',
          unread ? 'bg-primary' : 'bg-transparent',
        )}
      />

      <span className="min-w-0 flex-1">
        {/* No `dir="auto"` here. The line is a *translated sentence*, so it
            runs in the interface's direction — and `auto` reads the first
            strong character, which is an interpolated Latin name, so it would
            flip the whole Arabic line and scatter the pieces. The name and the
            price are Latin runs inside it, and `isolate` is what keeps each of
            them together where it belongs. */}
        <span className={cn('block text-sm', unread ? 'font-semibold text-fg' : 'text-fg-muted')}>
          {t(LINES[notification.kind], {
            name: isolate(String(notification.payload.provider_name ?? '')),
            price: price === null ? '' : isolate(formatDirhams(price, language)),
          })}
        </span>
        <span className="numeric mt-1 block text-xs text-fg-subtle">
          {formatRelative(notification.created_at, language)}
        </span>
      </span>

      {unread && <span className="sr-only">{t('notify.unread')}</span>}
    </button>
  )
}
