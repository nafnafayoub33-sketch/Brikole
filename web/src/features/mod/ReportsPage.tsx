import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import {
  REPORT_OUTCOMES,
  useHandleReport,
  useReportQueue,
  type Report,
  type ReportOutcome,
  type ReportReason,
} from '@/data/reports'
import { formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * D3 — reported content.
 *
 * The content is quoted on the card, because a moderator judges the thing
 * complained about and not the complaint about it. Anything heavier than a
 * 48-hour suspension is an admin's decision, and there is no control here that
 * reaches it.
 */

const REASON_KEYS: Record<ReportReason, string> = {
  spam: 'report.reasonSpam',
  offensive: 'report.reasonOffensive',
  fake: 'report.reasonFake',
  wrong_info: 'report.reasonWrongInfo',
  other: 'report.reasonOther',
  contact_sharing: 'report.reasonContactSharing',
}

const OUTCOME_KEYS: Record<ReportOutcome, string> = {
  dismissed: 'reports.outcomeDismissed',
  content_hidden: 'reports.outcomeContentHidden',
  warned: 'reports.outcomeWarned',
  suspended: 'reports.outcomeSuspended',
}

const OUTCOME_TONES = {
  dismissed: 'neutral',
  content_hidden: 'warning',
  warned: 'warning',
  suspended: 'danger',
} as const

export function ReportsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const [tab, setTab] = useState<'open' | 'handled'>('open')
  const queue = useReportQueue(tab)

  const items = queue.data?.items ?? []

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('reports.title')}</h1>
      <p className="mt-2 text-fg-muted">{t('reports.subtitle')}</p>

      <div className="mt-6 flex flex-wrap gap-2">
        {(['open', 'handled'] as const).map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={tab === option}
            onClick={() => setTab(option)}
            className={cn(
              'min-h-11 rounded-pill border-2 px-4 text-sm font-semibold',
              'transition-colors duration-(--duration-fast)',
              tab === option
                ? 'border-primary bg-primary-soft text-primary'
                : 'border-border bg-surface text-fg-muted hover:border-border-strong',
            )}
          >
            {t(option === 'open' ? 'reports.tabOpen' : 'reports.tabHandled')}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {queue.isPending ? (
          <ul className="flex flex-col gap-5">
            {[0, 1].map((index) => (
              <li key={index}>
                <Skeleton className="h-56" />
              </li>
            ))}
          </ul>
        ) : queue.isError ? (
          <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t('reports.empty')} body={t('reports.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-5">
            {items.map((report) => (
              <li key={report.id}>
                <ReportCard report={report} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/** The number in a platform flag's description, or null if it is not one. */
function count(description: string | null): number | null {
  const parsed = Number(description)
  return description !== null && description !== '' && Number.isFinite(parsed)
    ? parsed
    : null
}

function ReportCard({ report, language }: { report: Report; language: Language }) {
  const { t } = useTranslation()
  const handle = useHandleReport()

  const [outcome, setOutcome] = useState<ReportOutcome | null>(null)
  const [note, setNote] = useState('')

  const done = report.status === 'handled'
  // Hiding needs something to hide. A profile is not a piece of content.
  const hideable = report.target_type === 'review' && !report.content?.is_hidden
  // The platform's own flag carries a count where a person would have written
  // a sentence. Parsed rather than trusted: `description` is one free-text
  // column shared with every report a human files, and a moderator reading
  // "NaN clients" learns nothing except that the screen is broken.
  const seen = report.reason === 'contact_sharing' ? count(report.description) : null
  const complete = outcome !== null && note.trim().length > 0

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">{t(REASON_KEYS[report.reason])}</Badge>
          {report.also_reported > 0 && (
            <Badge tone="danger">
              {t('reports.alsoReported', { count: report.also_reported })}
            </Badge>
          )}
          {report.content?.is_hidden && <Badge tone="warning">{t('reports.hidden')}</Badge>}
        </div>
        <span className="text-xs text-fg-subtle">
          {formatRelative(report.created_at, language)}
        </span>
      </div>

      {/* An em dash where a name goes reads as missing data. This report has
          no name because nobody made an accusation — the platform counted
          something — and that is worth a sentence, not a placeholder. */}
      <p className="mt-3 text-sm text-fg-muted">
        {report.reporter_id === null ? (
          t('reports.flaggedByThePlatform')
        ) : (
          <>
            {t('reports.reportedBy')}:{' '}
            <span dir="auto" className="font-medium text-fg">
              {report.reporter_name ?? '—'}
            </span>
          </>
        )}
      </p>

      {/* A person's report carries a person's words. The platform's carries a
          number, and the sentence around it is written here — in the language
          the moderator reading it chose, not the one the API was written in. */}
      {seen !== null ? (
        <p className="mt-2 text-sm text-fg-muted">
          {t('reports.contactSharingCount', { count: seen })}
        </p>
      ) : (
        report.description && (
          <p dir="auto" className="mt-2 text-sm text-fg-muted">
            {report.description}
          </p>
        )
      )}

      {/* The thing complained about, quoted. */}
      {report.content && (
        <div className="mt-5 rounded-md border border-border bg-surface-2 p-4">
          <p className="text-xs font-semibold text-fg-subtle uppercase">
            {t('reports.theContent')}
          </p>
          <p dir="auto" className="mt-2 font-semibold text-fg">
            {report.content.title}
          </p>
          {report.content.rating !== null && (
            <div className="mt-1">
              <Stars value={report.content.rating} size="sm" />
            </div>
          )}
          {report.content.body && (
            <p dir="auto" className="mt-2 text-sm text-fg-muted">
              {report.content.body}
            </p>
          )}
          {report.content.provider_id !== null && (
            <Link
              to={`/m3allem/${report.content.provider_id}`}
              className="mt-3 inline-block text-sm font-semibold text-primary hover:underline"
            >
              {t('reports.seeProfile')}
            </Link>
          )}
        </div>
      )}

      {done ? (
        <div className="mt-5 border-t border-border pt-4">
          <div className="flex flex-wrap items-center gap-3">
            {report.outcome && (
              <Badge tone={OUTCOME_TONES[report.outcome]}>
                {t(OUTCOME_KEYS[report.outcome])}
              </Badge>
            )}
            {report.handled_by_name && (
              <span className="text-sm text-fg-subtle">
                {t('reports.handledBy', { name: report.handled_by_name })}
              </span>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-6 border-t border-border pt-5">
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-fg">
              {t('reports.outcome')}
            </legend>
            <div className="flex flex-col gap-2">
              {REPORT_OUTCOMES.map((option) => {
                const blocked = option === 'content_hidden' && !hideable
                return (
                  <button
                    key={option}
                    type="button"
                    disabled={blocked}
                    aria-pressed={outcome === option}
                    onClick={() => setOutcome(option)}
                    className={cn(
                      'min-h-tap rounded-md border-2 px-4 py-3 text-start text-sm font-medium',
                      'transition-colors duration-(--duration-fast)',
                      'disabled:cursor-not-allowed disabled:opacity-50',
                      outcome === option
                        ? 'border-primary bg-primary-soft text-primary'
                        : 'border-border bg-surface text-fg hover:border-border-strong',
                    )}
                  >
                    {t(OUTCOME_KEYS[option])}
                  </button>
                )
              })}
            </div>
            {report.target_type === 'provider_profile' && (
              <p className="mt-2 text-xs text-fg-subtle">{t('reports.hideOnlyReview')}</p>
            )}
          </fieldset>

          {outcome === 'suspended' && (
            <Alert tone="warning" className="mt-4">
              {t('reports.suspendNote')}
            </Alert>
          )}

          <label className="mt-5 flex flex-col gap-2">
            <span className="text-sm font-semibold text-fg">{t('reports.note')}</span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              maxLength={1000}
              className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-primary"
            />
            <span className="text-xs text-fg-subtle">{t('reports.noteHint')}</span>
          </label>

          {handle.isError && (
            <div className="mt-4">
              <ErrorState error={handle.error} />
            </div>
          )}

          <div className="mt-5">
            <ConfirmButton
              label={t('reports.handle')}
              question={t('reports.handleConfirm')}
              confirmLabel={t('reports.handleYes')}
              size="pro"
              disabled={!complete}
              loading={handle.isPending}
              onConfirm={() =>
                handle.mutate({
                  reportId: report.id,
                  outcome: outcome as ReportOutcome,
                  note: note.trim(),
                })
              }
            />
          </div>
        </div>
      )}
    </Card>
  )
}
