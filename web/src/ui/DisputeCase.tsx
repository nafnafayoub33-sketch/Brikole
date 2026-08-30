import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  useDisputeMessage,
  type Dispute,
  type DisputeParty,
} from '@/data/disputes'
import { formatDateTime, formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { DisputeStatusBadge, ReasonBadge } from '@/ui/DisputeBadges'
import { VERDICT_KEYS } from '@/ui/disputeLabels'
import { ErrorState } from '@/ui/ErrorState'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * One dispute, as both a party and a moderator read it.
 *
 * Shared because it is one case; what differs is what the reader may do to it,
 * not what it is. The moderator's extras — the lead fee, the internal note
 * toggle, the decision panel — are passed in rather than assumed, so a party's
 * copy cannot grow them by accident.
 */
export function DisputeCase({
  dispute,
  language,
  viewerId,
  moderating = false,
  canWrite,
  footer,
}: {
  dispute: Dispute
  language: Language
  viewerId: number
  moderating?: boolean
  canWrite: boolean
  footer?: React.ReactNode
}) {
  const { t } = useTranslation()
  const message = useDisputeMessage()
  const [body, setBody] = useState('')
  const [internal, setInternal] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 dir="auto" className="text-2xl font-bold text-fg sm:text-3xl">
            {dispute.job.title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ReasonBadge reason={dispute.reason} />
            <DisputeStatusBadge status={dispute.status} />
            {dispute.is_stale && <Badge tone="danger">{t('mod.stale')}</Badge>}
          </div>
        </div>
      </header>

      {dispute.status === 'resolved' && (
        <Alert tone="success">
          <span className="font-semibold">
            {dispute.verdict ? t(VERDICT_KEYS[dispute.verdict]) : ''}
          </span>
          {dispute.resolution_note && (
            <>
              {' — '}
              <span dir="auto">{dispute.resolution_note}</span>
            </>
          )}
          {dispute.lead_fee_refunded && ` · ${t('mod.refunded')}`}
        </Alert>
      )}

      {moderating && dispute.claimed_by_id === null && (
        <Alert tone="info">{t('mod.readOnly')}</Alert>
      )}
      {moderating && dispute.claimed_by_name && dispute.claimed_by_id !== viewerId && (
        <Alert tone="warning">
          {t('mod.claimedBy', { name: dispute.claimed_by_name })}
        </Alert>
      )}

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-fg-subtle uppercase">
          {t('mod.theJob')}
        </h2>
        <dl className="divide-y divide-border text-sm">
          <Row
            label={t('mod.price')}
            value={formatDirhams(dispute.job.agreed_price_centimes, language)}
            numeric
          />
          {/* Shown to a moderator and to nobody else: he can give it back. */}
          {moderating && dispute.job.lead_fee_centimes !== null && (
            <Row
              label={t('mod.leadFee')}
              value={formatDirhams(dispute.job.lead_fee_centimes, language)}
              numeric
            />
          )}
        </dl>
        {moderating && <p className="mt-3 text-xs text-fg-subtle">{t('mod.onlyMoney')}</p>}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <PartyCardView
          party={dispute.opened_by}
          label={t('dispute.openedBy')}
          moderating={moderating}
        />
        <PartyCardView
          party={dispute.against}
          label={t('dispute.against')}
          moderating={moderating}
        />
      </div>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-fg-subtle uppercase">
          {t('dispute.description')}
        </h2>
        <p dir="auto" className="whitespace-pre-line text-fg-muted">
          {dispute.description}
        </p>

        {dispute.evidence.length > 0 && (
          <ul className="mt-5 flex flex-wrap gap-3">
            {dispute.evidence.map((url) => (
              <li key={url}>
                <img
                  src={url}
                  alt=""
                  loading="lazy"
                  className="size-28 rounded-md border border-border object-cover"
                />
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <h2 className="mb-4 text-sm font-semibold text-fg-subtle uppercase">
          {t('dispute.thread')}
        </h2>

        {dispute.messages.filter((entry) => entry.body).length === 0 ? (
          <p className="text-sm text-fg-subtle">{t('dispute.threadEmpty')}</p>
        ) : (
          <ul className="flex flex-col gap-4">
            {dispute.messages
              .filter((entry) => entry.body)
              .map((entry) => (
                <li
                  key={entry.id}
                  className={cn(
                    'rounded-md border px-4 py-3',
                    entry.is_internal
                      ? 'border-warning/30 bg-warning-soft'
                      : entry.author_id === viewerId
                        ? 'border-primary/25 bg-primary-soft'
                        : 'border-border bg-surface-2',
                  )}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span dir="auto" className="text-sm font-semibold text-fg">
                      {entry.author_name}
                    </span>
                    <span className="text-xs text-fg-subtle">
                      {formatDateTime(entry.created_at, language)}
                    </span>
                  </div>
                  {entry.is_internal && (
                    <Badge tone="warning" className="mt-2">
                      {t('dispute.internal')}
                    </Badge>
                  )}
                  <p dir="auto" className="mt-2 text-sm text-fg-muted">
                    {entry.body}
                  </p>
                </li>
              ))}
          </ul>
        )}

        {dispute.status === 'resolved' ? (
          <p className="mt-5 text-sm text-fg-subtle">{t('dispute.closed')}</p>
        ) : canWrite ? (
          <div className="mt-6 flex flex-col gap-3 border-t border-border pt-5">
            <textarea
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder={t('dispute.write')}
              rows={3}
              maxLength={2000}
              className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
            />

            {moderating && (
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={internal}
                  onChange={(event) => setInternal(event.target.checked)}
                  className="mt-1 size-4 accent-[var(--color-primary)]"
                />
                <span>
                  <span className="font-medium text-fg">{t('dispute.internal')}</span>{' '}
                  <span className="text-fg-subtle">{t('dispute.internalHint')}</span>
                </span>
              </label>
            )}

            {message.isError && <ErrorState error={message.error} />}

            <div>
              <Button
                size={moderating ? 'md' : 'md'}
                disabled={body.trim().length === 0}
                loading={message.isPending}
                onClick={() =>
                  message.mutate(
                    { disputeId: dispute.id, body: body.trim(), isInternal: internal },
                    {
                      onSuccess: () => {
                        setBody('')
                        setInternal(false)
                      },
                    },
                  )
                }
              >
                {t('dispute.send')}
              </Button>
            </div>
          </div>
        ) : null}
      </Card>

      {footer}
    </div>
  )
}

function PartyCardView({
  party,
  label,
  moderating,
}: {
  party: DisputeParty
  label: string
  moderating: boolean
}) {
  const { t } = useTranslation()

  return (
    <Card>
      <p className="text-xs font-semibold text-fg-subtle uppercase">{label}</p>
      {party.provider_id && moderating ? (
        <Link
          to={`/m3allem/${party.provider_id}`}
          dir="auto"
          className="mt-1 block font-bold text-fg hover:text-primary hover:underline"
        >
          {party.full_name}
        </Link>
      ) : (
        <p dir="auto" className="mt-1 font-bold text-fg">
          {party.full_name}
        </p>
      )}

      {moderating && (
        <div className="mt-3 flex flex-col gap-1.5 text-sm">
          {party.rating_count !== null && party.rating_count > 0 && (
            <span className="flex items-center gap-2">
              <Stars value={party.rating_avg ?? 0} size="sm" />
              <span className="numeric text-fg">{(party.rating_avg ?? 0).toFixed(1)}</span>
              <span className="text-fg-subtle">
                {t('mod.jobsDone', { count: party.jobs_done ?? 0 })}
              </span>
            </span>
          )}
          {/* One complaint is noise; a pattern is a decision. */}
          <span
            className={cn(
              party.disputes_lost > 0 ? 'font-semibold text-danger' : 'text-fg-subtle',
            )}
          >
            {party.disputes_lost > 0
              ? t('mod.disputesLost', { count: party.disputes_lost })
              : t('mod.noDisputesLost')}
          </span>
        </div>
      )}
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
    <div className="flex items-start justify-between gap-4 py-2.5">
      <dt className="shrink-0 text-fg-subtle">{label}</dt>
      <dd className={cn('text-end font-medium text-fg', numeric && 'numeric')}>{value}</dd>
    </div>
  )
}
