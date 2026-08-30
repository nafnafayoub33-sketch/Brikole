import { useTranslation } from 'react-i18next'

import type { Job } from '@/data/jobs'
import { formatDateTime } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'

/**
 * Where the job has got to, and when each step happened.
 *
 * Four steps drawn even when only one has happened: a timeline that grows as
 * it goes tells you nothing about what is still coming, which is the question
 * somebody opening this screen actually has.
 */
export function JobTimeline({ job, language }: { job: Job; language: Language }) {
  const { t } = useTranslation()

  const steps = [
    { key: 'stepAccepted', at: job.created_at },
    { key: 'stepStarted', at: job.started_at },
    { key: 'stepFinished', at: job.finished_at },
    { key: 'stepConfirmed', at: job.confirmed_at },
  ]

  return (
    <ol className="flex flex-col gap-0">
      {steps.map((step, index) => {
        const done = step.at !== null
        const last = index === steps.length - 1
        return (
          <li key={step.key} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'mt-1 flex size-5 shrink-0 items-center justify-center rounded-full border-2',
                  done ? 'border-primary bg-primary' : 'border-border-strong bg-surface',
                )}
              >
                {done && <CheckGlyph />}
              </span>
              {!last && (
                <span
                  className={cn('w-0.5 flex-1', done ? 'bg-primary' : 'bg-border')}
                  aria-hidden
                />
              )}
            </div>

            <div className={cn('pb-6', last && 'pb-0')}>
              <p className={cn('text-sm font-semibold', done ? 'text-fg' : 'text-fg-subtle')}>
                {t(`job.${step.key}`)}
              </p>
              {step.at && (
                <p className="mt-0.5 text-xs text-fg-subtle">
                  {formatDateTime(step.at, language)}
                </p>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function CheckGlyph() {
  return (
    <svg viewBox="0 0 12 12" className="size-3 text-primary-fg" aria-hidden>
      <path
        d="M2.5 6.2 4.7 8.4 9.5 3.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
