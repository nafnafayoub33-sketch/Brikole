import type { TFunction } from 'i18next'

import type { Notification, NotificationKind } from '@/data/notifications'
import { formatDirhams, isolate } from '@/lib/format'
import type { Language } from '@/lib/i18n'

/**
 * What a notification says, and where it goes.
 *
 * The API sends a `kind` and a `payload` of ids and numbers and never a
 * sentence, so the wording is ours — and now two things render it, the bell in
 * the header and C6. Extracted the moment there were two: the fifth copy of a
 * map like this one is how a raw `notify.jobDone` ships in a screenshot.
 */

/** One key per kind. */
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

/**
 * The line, translated and filled in.
 *
 * The interpolated name and price are Latin runs inside a sentence that may be
 * Arabic, so each is wrapped in a directional isolate. Note what is *not* here:
 * `dir="auto"` on the element. It reads the first strong character, which is
 * the name — and that flips the whole Arabic line and scatters it.
 */
export function notificationLine(
  t: TFunction,
  notification: Notification,
  language: Language,
): string {
  const price = number(notification.payload, 'price_centimes')

  return t(LINES[notification.kind], {
    name: isolate(String(notification.payload.provider_name ?? '')),
    price: price === null ? '' : isolate(formatDirhams(price, language)),
  })
}

/**
 * Where a notification points, for the area the reader is in.
 *
 * `area` is `/client` or `/pro`. Only the routes that exist for that area are
 * returned: a client's job has a page of its own and a tradesman's does not, so
 * the same kind is a link for one and plain text for the other. `null` also
 * covers a payload that has lost the id it needs — the line still reads, it
 * just does not go anywhere.
 */
export function destination(notification: Notification, area: string): string | null {
  const { payload } = notification
  const forClient = area === '/client'

  const request = number(payload, 'request_id')
  const job = number(payload, 'job_id')
  const dispute = number(payload, 'dispute_id')

  switch (notification.kind) {
    case 'offer_received':
      return forClient && request !== null ? `/client/requests/${request}` : null
    case 'job_started':
    case 'job_done':
      return forClient && job !== null ? `/client/jobs/${job}` : null
    case 'dispute_update':
      // The one both areas have.
      return dispute === null ? null : `${area}/disputes/${dispute}`
    default:
      return null
  }
}
