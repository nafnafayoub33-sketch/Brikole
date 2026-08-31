import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useAudit, useAuditFilters, type AuditEntry } from '@/data/admin'
import { formatDateTime } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Badge } from '@/ui/Badge'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'

/**
 * A8 — who did what, to whom, and when.
 *
 * Read-only by construction: the API has no write and no delete on this path,
 * so there is nothing for this screen to offer even if somebody wanted it. The
 * filters are built from what the log actually contains, so a choice never
 * returns nothing because the screen invented the option.
 */
export function AuditPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language

  const [action, setAction] = useState<string | null>(null)
  const [targetType, setTargetType] = useState<string | null>(null)

  const filters = useAuditFilters()
  const audit = useAudit({ action, targetType })

  const items = audit.data?.items ?? []

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('audit.title')}</h1>
      <p className="mt-2 text-fg-muted">{t('audit.subtitle')}</p>

      <div className="mt-6 flex flex-wrap gap-3">
        <select
          aria-label={t('audit.allActions')}
          value={action ?? ''}
          onChange={(event) => setAction(event.target.value || null)}
          className="min-h-11 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
        >
          <option value="">{t('audit.allActions')}</option>
          {(filters.data?.actions ?? []).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>

        <select
          aria-label={t('audit.allTargets')}
          value={targetType ?? ''}
          onChange={(event) => setTargetType(event.target.value || null)}
          className="min-h-11 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
        >
          <option value="">{t('audit.allTargets')}</option>
          {(filters.data?.target_types ?? []).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6">
        {audit.isPending ? (
          <ul className="flex flex-col gap-3">
            {[0, 1, 2].map((index) => (
              <li key={index}>
                <Skeleton className="h-20" />
              </li>
            ))}
          </ul>
        ) : audit.isError ? (
          <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t('audit.empty')} body={t('audit.emptyBody')} />
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((entry) => (
              <li key={entry.id}>
                <Entry entry={entry} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function Entry({ entry, language }: { entry: AuditEntry; language: Language }) {
  const { t } = useTranslation()
  const changes = diff(entry.before, entry.after)

  return (
    <div className="rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">{entry.action}</Badge>
          <span className="text-sm text-fg-muted">
            {entry.target_type}
            {entry.target_id !== null && (
              <span className="numeric"> #{entry.target_id}</span>
            )}
          </span>
        </div>
        <span className="text-xs text-fg-subtle">
          {formatDateTime(entry.created_at, language)}
        </span>
      </div>

      <p dir="auto" className="mt-2 text-sm text-fg">
        {/* A deleted actor takes his name, not his record. */}
        {entry.actor_name ?? (
          <span className="text-fg-subtle italic">{t('audit.deletedActor')}</span>
        )}
      </p>

      {changes.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1 text-xs text-fg-muted">
          {changes.map(({ field, from, to }) => (
            <li key={field}>
              <span className="font-medium text-fg-subtle">{field}</span>{' '}
              <span className="numeric">{from}</span> → <span className="numeric">{to}</span>
            </li>
          ))}
        </ul>
      )}

      {/* The note names the key; drop it when the change lines already say so,
          including the `bank_transfer.rib` form. */}
      {entry.note &&
        !changes.some(
          (change) => change.field === entry.note || change.field.startsWith(`${entry.note}.`),
        ) && (
          <p dir="auto" className="mt-2 text-xs text-fg-subtle">
            {entry.note}
          </p>
        )}
    </div>
  )
}

/**
 * The fields that moved, flattened one level.
 *
 * A setting whose value is an object — the bank block — would otherwise render
 * as two JSON blobs side by side, which is unreadable on the one screen whose
 * whole job is being readable. Nested objects are compared key by key and only
 * what actually changed is listed.
 */
function diff(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
): { field: string; from: string; to: string }[] {
  const keys = new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])
  const rows: { field: string; from: string; to: string }[] = []

  for (const field of keys) {
    const from = before?.[field]
    const to = after?.[field]

    if (isPlainObject(from) || isPlainObject(to)) {
      const nested = new Set([
        ...Object.keys(isPlainObject(from) ? from : {}),
        ...Object.keys(isPlainObject(to) ? to : {}),
      ])
      for (const inner of nested) {
        const innerFrom = isPlainObject(from) ? from[inner] : undefined
        const innerTo = isPlainObject(to) ? to[inner] : undefined
        if (show(innerFrom) === show(innerTo)) continue
        rows.push({ field: `${field}.${inner}`, from: show(innerFrom), to: show(innerTo) })
      }
      continue
    }

    rows.push({ field, from: show(from), to: show(to) })
  }

  return rows
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function show(value: unknown): string {
  if (value === undefined || value === null || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
