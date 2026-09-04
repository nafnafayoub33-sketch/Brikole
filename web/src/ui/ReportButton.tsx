import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useSession } from '@/data/auth'
import {
  REPORT_REASONS,
  useFileReport,
  type FilableReason,
  type ReportTarget,
} from '@/data/reports'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { ErrorState } from '@/ui/ErrorState'
import { cn } from '@/ui/cn'

const REASON_KEYS: Record<FilableReason, string> = {
  spam: 'report.reasonSpam',
  offensive: 'report.reasonOffensive',
  fake: 'report.reasonFake',
  wrong_info: 'report.reasonWrongInfo',
  other: 'report.reasonOther',
}

/**
 * Flagging a profile or a review, wherever one is shown.
 *
 * Only offered to somebody signed in as a client or a tradesman: a moderator
 * looking at bad content acts on it, he does not queue a complaint for himself,
 * and the API answers 403 to him. A visitor with no account sees nothing rather
 * than a button that sends him to a login he did not ask for.
 */
export function ReportButton({
  targetType,
  targetId,
  label,
  className,
}: {
  targetType: ReportTarget
  targetId: number
  label: string
  className?: string
}) {
  const { t } = useTranslation()
  const session = useSession()
  const file = useFileReport()

  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<FilableReason | null>(null)
  const [description, setDescription] = useState('')

  const role = session.data?.role
  if (role !== 'client' && role !== 'provider') return null

  if (file.isSuccess) {
    return (
      <Alert tone="success" className={className}>
        {t('report.sent')}
      </Alert>
    )
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          'text-xs font-semibold text-fg-subtle hover:text-danger hover:underline',
          className,
        )}
      >
        {label}
      </button>
    )
  }

  // "Other" carries no meaning of its own, so it has to carry a sentence.
  const needsDescription = reason === 'other'
  const complete = reason !== null && (!needsDescription || description.trim().length > 0)

  return (
    <div
      className={cn(
        'rounded-md border border-border-strong bg-surface-2 p-4',
        className,
      )}
    >
      <p className="text-sm font-semibold text-fg">{t('report.title')}</p>
      <p className="mt-1 text-xs text-fg-subtle">{t('report.body')}</p>

      <fieldset className="mt-4">
        <legend className="sr-only">{t('report.reason')}</legend>
        <div className="flex flex-wrap gap-2">
          {REPORT_REASONS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={reason === option}
              onClick={() => setReason(option)}
              className={cn(
                'min-h-9 rounded-pill border-2 px-3 text-xs font-semibold',
                'transition-colors duration-(--duration-fast)',
                reason === option
                  ? 'border-primary bg-primary-soft text-primary'
                  : 'border-border bg-surface text-fg-muted hover:border-border-strong',
              )}
            >
              {t(REASON_KEYS[option])}
            </button>
          ))}
        </div>
      </fieldset>

      <label className="mt-4 flex flex-col gap-2">
        <span className="text-xs font-semibold text-fg">
          {needsDescription ? t('report.descriptionRequired') : t('report.description')}
        </span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder={t('report.descriptionPlaceholder')}
          rows={3}
          maxLength={1000}
          className="rounded-md border border-border-strong bg-surface p-3 text-sm text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
        />
      </label>

      {file.isError && (
        <div className="mt-3">
          <ErrorState error={file.error} />
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <Button
          size="sm"
          variant="danger"
          disabled={!complete}
          loading={file.isPending}
          onClick={() =>
            file.mutate({
              target_type: targetType,
              target_id: targetId,
              reason: reason as FilableReason,
              description: description.trim() || null,
            })
          }
        >
          {t('report.send')}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          {t('report.keep')}
        </Button>
      </div>
    </div>
  )
}
