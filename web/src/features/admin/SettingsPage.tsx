import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  useSettings,
  useUpdateSettings,
  type BankValue,
  type Setting,
} from '@/data/admin'
import { ApiError } from '@/data/client'
import { formatDate } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { Skeleton } from '@/ui/Skeleton'

/**
 * A7 — the numbers the platform runs on.
 *
 * It exists because M9 had no way to be filled in: the bank details a tradesman
 * transfers into lived only in whatever somebody had written into the database.
 * Everything here is bounded on the API side, so a mistyped digit is refused
 * rather than quietly making the business free.
 */

const BANK = 'bank_transfer'
const MAINTENANCE = 'maintenance_mode'

/** Money, held in centimes and typed in dirhams. */
const DIRHAMS: { key: string; labelKey: string; hintKey: string }[] = [
  {
    key: 'default_lead_fee_centimes',
    labelKey: 'settings.defaultLeadFee',
    hintKey: 'settings.defaultLeadFeeHint',
  },
  {
    key: 'boost_monthly_centimes',
    labelKey: 'settings.boostMonthly',
    hintKey: 'settings.boostMonthlyHint',
  },
]

const COUNTS: { key: string; labelKey: string; hintKey?: string }[] = [
  { key: 'free_leads_new_provider', labelKey: 'settings.freeLeads', hintKey: 'settings.freeLeadsHint' },
  {
    key: 'max_open_requests_per_client',
    labelKey: 'settings.maxOpenRequests',
    hintKey: 'settings.maxOpenRequestsHint',
  },
  { key: 'offer_expiry_days', labelKey: 'settings.offerExpiry' },
  { key: 'request_expiry_days', labelKey: 'settings.requestExpiry' },
  { key: 'auto_confirm_days', labelKey: 'settings.autoConfirm' },
  { key: 'dispute_window_days', labelKey: 'settings.disputeWindow' },
  { key: 'default_radius_km', labelKey: 'settings.defaultRadius' },
  {
    key: 'contact_flag_threshold',
    labelKey: 'settings.contactFlag',
    hintKey: 'settings.contactFlagHint',
  },
]

const BANK_FIELDS: { field: keyof BankValue; labelKey: string }[] = [
  { field: 'bank_name', labelKey: 'settings.bankName' },
  { field: 'account_holder', labelKey: 'settings.accountHolder' },
  { field: 'rib', labelKey: 'settings.rib' },
]

const EMPTY_BANK: BankValue = { bank_name: '', account_holder: '', rib: '', instructions: '' }

/** Every editable key by its label, so a rejection can name the field in words
 *  rather than handing the admin `boost_monthly_centimes`. */
const LABELS: Record<string, string> = {
  ...Object.fromEntries(DIRHAMS.map(({ key, labelKey }) => [key, labelKey])),
  ...Object.fromEntries(COUNTS.map(({ key, labelKey }) => [key, labelKey])),
  [BANK]: 'settings.bank',
  [MAINTENANCE]: 'settings.maintenance',
}

export function SettingsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const settings = useSettings()
  const update = useUpdateSettings()

  // The API rejects the whole batch and names the key that failed. Passing
  // that to the field it belongs to is the difference between "something is
  // incorrect" and knowing which of eleven numbers to fix.
  const rejected =
    update.error instanceof ApiError && update.error.code === 'validation_failed'
      ? String(update.error.details.field ?? '')
      : null

  const [numbers, setNumbers] = useState<Record<string, string>>({})
  const [bank, setBank] = useState<BankValue>(EMPTY_BANK)
  const [maintenance, setMaintenance] = useState(false)
  const [loaded, setLoaded] = useState(false)

  // Seeded once, then his typing is left alone.
  useEffect(() => {
    if (loaded || !settings.data) return
    const byKey = new Map(settings.data.items.map((item) => [item.key, item]))

    const seeded: Record<string, string> = {}
    for (const { key } of DIRHAMS) {
      seeded[key] = String(Math.round(Number(byKey.get(key)?.value ?? 0) / 100))
    }
    for (const { key } of COUNTS) seeded[key] = String(byKey.get(key)?.value ?? 0)
    setNumbers(seeded)

    setBank({ ...EMPTY_BANK, ...((byKey.get(BANK)?.value as BankValue | undefined) ?? {}) })
    setMaintenance(Boolean(byKey.get(MAINTENANCE)?.value))
    setLoaded(true)
  }, [loaded, settings.data])

  if (settings.isPending) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-72" />
      </div>
    )
  }

  if (settings.isError) {
    return (
      <div className="mx-auto max-w-2xl">
        <ErrorState error={settings.error} onRetry={() => void settings.refetch()} />
      </div>
    )
  }

  const byKey = new Map(settings.data.items.map((item) => [item.key, item]))

  function save() {
    const values: Record<string, unknown> = {}

    // A blank field is a field he cleared to retype, not a zero he meant.
    // `Number('')` is 0, and `free_leads_new_provider` accepts 0 — so reading
    // it literally would take every new tradesman's free jobs away because
    // somebody selected the box and pressed save.
    const typed = (key: string) => {
      const raw = numbers[key]
      return raw !== undefined && raw.trim() !== '' ? Number(raw) : null
    }

    for (const { key } of DIRHAMS) {
      const dirhams = typed(key)
      if (dirhams === null || !Number.isFinite(dirhams)) continue
      const centimes = Math.round(dirhams * 100)
      if (centimes !== byKey.get(key)?.value) values[key] = centimes
    }

    for (const { key } of COUNTS) {
      const parsed = typed(key)
      if (parsed === null || !Number.isInteger(parsed)) continue
      if (parsed !== byKey.get(key)?.value) values[key] = parsed
    }

    const storedBank = { ...EMPTY_BANK, ...((byKey.get(BANK)?.value as BankValue) ?? {}) }
    if (BANK_FIELDS.some(({ field }) => bank[field] !== storedBank[field]) ||
        bank.instructions !== storedBank.instructions) {
      values[BANK] = bank
    }

    if (maintenance !== Boolean(byKey.get(MAINTENANCE)?.value)) values[MAINTENANCE] = maintenance

    // Sending nothing would answer 422 on an empty batch, which is a confusing
    // way to say "you changed nothing".
    if (Object.keys(values).length === 0) return
    update.mutate(values)
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('settings.title')}</h1>
      <p className="mt-2 text-fg-muted">{t('settings.subtitle')}</p>

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('settings.money')}</h2>
        <div className="mt-5 flex flex-col gap-6">
          {DIRHAMS.map(({ key, labelKey, hintKey }) => (
            <div key={key}>
              <Field
                label={t(labelKey)}
                type="number"
                numeric
                min={1}
                prefix="DH"
                error={rejected === key ? t('settings.rejected') : null}
                value={numbers[key] ?? ''}
                onChange={(event) =>
                  setNumbers((n) => ({ ...n, [key]: event.target.value }))
                }
              />
              <p className="mt-2 text-xs text-fg-subtle">{t(hintKey)}</p>
              <Provenance entry={byKey.get(key)} language={language} />
            </div>
          ))}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('settings.limits')}</h2>
        <div className="mt-5 flex flex-col gap-6">
          {COUNTS.map(({ key, labelKey, hintKey }) => (
            <div key={key}>
              <Field
                label={t(labelKey)}
                type="number"
                numeric
                min={0}
                error={rejected === key ? t('settings.rejected') : null}
                value={numbers[key] ?? ''}
                onChange={(event) =>
                  setNumbers((n) => ({ ...n, [key]: event.target.value }))
                }
              />
              {hintKey && <p className="mt-2 text-xs text-fg-subtle">{t(hintKey)}</p>}
              <Provenance entry={byKey.get(key)} language={language} />
            </div>
          ))}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('settings.bank')}</h2>
        <p className="mt-2 text-sm text-fg-muted">{t('settings.bankHint')}</p>
        <div className="mt-5 flex flex-col gap-5">
          {BANK_FIELDS.map(({ field, labelKey }) => (
            <Field
              key={field}
              label={t(labelKey)}
              numeric={field === 'rib'}
              value={bank[field]}
              maxLength={200}
              onChange={(event) => setBank((b) => ({ ...b, [field]: event.target.value }))}
            />
          ))}
          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-fg">{t('settings.instructions')}</span>
            <textarea
              value={bank.instructions}
              onChange={(event) =>
                setBank((b) => ({ ...b, instructions: event.target.value }))
              }
              rows={3}
              maxLength={500}
              className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-primary"
            />
          </label>
          <Provenance entry={byKey.get(BANK)} language={language} />
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('settings.maintenance')}</h2>
        <label className="mt-4 flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={maintenance}
            onChange={(event) => setMaintenance(event.target.checked)}
            className="mt-1 size-4 accent-[var(--color-primary)]"
          />
          <span>
            <span className="font-medium text-fg">{t('settings.maintenanceMode')}</span>
            <span className="block text-xs text-fg-subtle">{t('settings.maintenanceHint')}</span>
          </span>
        </label>
      </Card>

      {update.isError && (
        <div className="mt-6">
          {rejected ? (
            <Alert tone="danger">
              {t('settings.rejectedBatch', { field: t(LABELS[rejected] ?? rejected) })}
            </Alert>
          ) : (
            <ErrorState error={update.error} />
          )}
        </div>
      )}
      {update.isSuccess && !update.isPending && (
        <Alert tone="success" className="mt-6">
          {t('settings.saved')}
        </Alert>
      )}

      <div className="mt-8">
        <Button size="lg" loading={update.isPending} onClick={save}>
          {t('settings.save')}
        </Button>
      </div>
    </div>
  )
}

/** Who last changed it — or that nobody has, and this is the shipped default. */
function Provenance({ entry, language }: { entry: Setting | undefined; language: Language }) {
  const { t } = useTranslation()
  if (!entry) return null

  return (
    <p className="mt-1.5 text-xs text-fg-subtle">
      {entry.updated_by_name && entry.updated_at ? (
        <>
          {t('settings.changedBy', { name: entry.updated_by_name })} ·{' '}
          {formatDate(entry.updated_at, language)}
        </>
      ) : (
        t('settings.default')
      )}
    </p>
  )
}
