import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  useCreditPage,
  useSubmitTopup,
  type LedgerEntry,
  type Topup,
  type TransactionType,
} from '@/data/credit'
import { formatDate, formatDateTime, formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { PhotoInput, type PickedPhoto } from '@/ui/PhotoInput'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * M9 — the balance, where it went, and how to put more in.
 *
 * The screen's one job is to make the delay honest. He transfers money and
 * nothing happens until a person checks a bank statement; a top-up form that
 * implies otherwise produces a tradesman refreshing an unchanged balance and
 * concluding the platform took his money.
 */
export function CreditPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const page = useCreditPage()
  const submit = useSubmitTopup()

  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const [receipt, setReceipt] = useState<PickedPhoto | null>(null)

  if (page.isPending) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-72" />
      </div>
    )
  }

  if (page.isError) {
    return (
      <div className="mx-auto max-w-2xl">
        <ErrorState error={page.error} onRetry={() => void page.refetch()} />
      </div>
    )
  }

  const data = page.data
  const fee = data.default_lead_fee_centimes
  const pending = data.topups.find((topup) => topup.status === 'pending') ?? null
  const lastRejected =
    data.topups.find((topup) => topup.status === 'rejected') ?? null
  const bankReady = data.bank.rib.trim().length > 0

  const centimes = Math.round(Number(amount) * 100)
  const complete =
    Number.isFinite(centimes) && centimes > 0 && reference.trim().length > 0

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('credit.title')}</h1>

      <Card className="mt-6">
        <p className="text-sm text-fg-subtle">{t('credit.balance')}</p>
        <p
          className={cn(
            'numeric mt-1 text-4xl font-bold',
            data.can_take_work ? 'text-fg' : 'text-danger',
          )}
        >
          {formatDirhams(data.balance_centimes, language)}
        </p>
        {fee > 0 && data.balance_centimes > 0 && (
          <p className="mt-1 text-sm text-fg-subtle">
            {t('credit.buysJobs', { count: Math.floor(data.balance_centimes / fee) })}
          </p>
        )}
        {data.free_leads_left > 0 && (
          <Badge tone="success" className="mt-3">
            {t('credit.freeLeads')}: <span className="numeric">{data.free_leads_left}</span>
          </Badge>
        )}
      </Card>

      {pending && (
        <Alert tone="info" className="mt-6">
          <span className="font-semibold">{t('credit.pendingTitle')}</span>{' '}
          {t('credit.pendingBody', {
            amount: formatDirhams(pending.amount_centimes, language),
            reference: pending.reference,
          })}
        </Alert>
      )}

      {!pending && lastRejected?.rejection_reason && (
        <Alert tone="warning" className="mt-6">
          <span className="font-semibold">{t('credit.rejectedTitle')}</span>{' '}
          <span dir="auto">{lastRejected.rejection_reason}</span>
        </Alert>
      )}

      <Card className="mt-6">
        <h2 className="text-lg font-bold text-fg">{t('credit.topUpTitle')}</h2>

        <ol className="mt-4 flex flex-col gap-1.5 text-sm text-fg-muted">
          {['step1', 'step2', 'step3', 'step4'].map((step, index) => (
            <li key={step} className="flex gap-2">
              <span className="numeric font-semibold text-fg-subtle">{index + 1}.</span>
              <span>{t(`credit.${step}`)}</span>
            </li>
          ))}
        </ol>

        {/* The single most important sentence on the screen. */}
        <Alert tone="warning" className="mt-4">
          {t('credit.notYet')}
        </Alert>

        {bankReady ? (
          <div className="mt-6 rounded-md border border-border bg-surface-2 p-5">
            <p className="mb-3 text-sm font-semibold text-fg">{t('credit.bankTitle')}</p>
            <dl className="divide-y divide-border text-sm">
              <BankRow label={t('credit.bankName')} value={data.bank.bank_name} />
              <BankRow label={t('credit.accountHolder')} value={data.bank.account_holder} />
              <BankRow label={t('credit.rib')} value={data.bank.rib} numeric />
            </dl>
            {data.bank.instructions && (
              <p dir="auto" className="mt-3 text-xs text-fg-subtle">
                {data.bank.instructions}
              </p>
            )}
          </div>
        ) : (
          <Alert tone="danger" className="mt-6">
            {t('credit.bankMissing')}
          </Alert>
        )}

        {pending ? (
          <Alert tone="info" className="mt-6">
            {t('credit.onePending')}
          </Alert>
        ) : (
          <div className="mt-6 flex flex-col gap-6">
            <div>
              <p className="mb-3 text-sm font-semibold text-fg">{t('credit.amount')}</p>
              <div className="flex flex-wrap gap-3">
                {data.preset_amounts.map((preset) => {
                  const picked = centimes === preset
                  return (
                    <button
                      key={preset}
                      type="button"
                      aria-pressed={picked}
                      onClick={() => setAmount(String(preset / 100))}
                      className={cn(
                        'min-h-tap-pro rounded-md border-2 px-5 text-start',
                        'transition-colors duration-(--duration-fast)',
                        picked
                          ? 'border-primary bg-primary-soft'
                          : 'border-border bg-surface hover:border-border-strong',
                      )}
                    >
                      <span className="numeric block font-bold text-fg">
                        {formatDirhams(preset, language)}
                      </span>
                      {fee > 0 && (
                        <span className="block text-xs text-fg-subtle">
                          {t('credit.buysJobs', { count: Math.floor(preset / fee) })}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <Field
              label={t('credit.otherAmount')}
              type="number"
              numeric
              min={50}
              prefix="DH"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />

            <div>
              <Field
                label={t('credit.reference')}
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                maxLength={120}
              />
              <p className="mt-2 text-xs text-fg-subtle">{t('credit.referenceHint')}</p>
            </div>

            <PhotoInput
              label={t('credit.receipt')}
              hint={t('credit.receiptHint')}
              purpose="receipt"
              value={receipt}
              onChange={setReceipt}
            />

            {submit.isError && <ErrorState error={submit.error} />}

            <div className="border-t border-border pt-5">
              <Button
                size="pro"
                disabled={!complete || !bankReady}
                loading={submit.isPending}
                onClick={() =>
                  submit.mutate(
                    {
                      amount_centimes: centimes,
                      reference: reference.trim(),
                      receipt_path: receipt?.path ?? null,
                    },
                    {
                      onSuccess: () => {
                        setAmount('')
                        setReference('')
                        setReceipt(null)
                      },
                    },
                  )
                }
              >
                {t('credit.submit')}
              </Button>
            </div>
          </div>
        )}
      </Card>

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-bold text-fg">{t('credit.ledger')}</h2>
        {data.ledger.length === 0 ? (
          <EmptyState title={t('credit.ledgerEmpty')} body={t('credit.ledgerEmptyBody')} />
        ) : (
          <ul className="flex flex-col gap-2">
            {data.ledger.map((entry) => (
              <li key={entry.id}>
                <LedgerRow entry={entry} language={language} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {data.topups.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-4 text-lg font-bold text-fg">{t('credit.topupHistory')}</h2>
          <ul className="flex flex-col gap-2">
            {data.topups.map((topup) => (
              <li key={topup.id}>
                <TopupRow topup={topup} language={language} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function BankRow({
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
      <dd dir="auto" className={cn('text-end font-medium text-fg', numeric && 'numeric')}>
        {value || '—'}
      </dd>
    </div>
  )
}

const TYPE_KEYS: Record<TransactionType, string> = {
  topup: 'credit.typeTopup',
  lead_fee: 'credit.typeLeadFee',
  free_lead: 'credit.typeFreeLead',
  refund: 'credit.typeRefund',
  adjustment: 'credit.typeAdjustment',
}

function LedgerRow({ entry, language }: { entry: LedgerEntry; language: Language }) {
  const { t } = useTranslation()
  const positive = entry.amount_centimes > 0

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div>
        <p className="text-sm font-medium text-fg">{t(TYPE_KEYS[entry.type])}</p>
        <p className="text-xs text-fg-subtle">{formatDateTime(entry.created_at, language)}</p>
      </div>
      <div className="text-end">
        <p
          className={cn(
            'numeric font-semibold',
            entry.amount_centimes === 0
              ? 'text-fg-subtle'
              : positive
                ? 'text-success'
                : 'text-fg',
          )}
        >
          {positive ? '+' : ''}
          {formatDirhams(entry.amount_centimes, language)}
        </p>
        <p className="numeric text-xs text-fg-subtle">
          {t('credit.after')} {formatDirhams(entry.balance_after_centimes, language)}
        </p>
      </div>
    </div>
  )
}

const TOPUP_TONES = { pending: 'brand', approved: 'success', rejected: 'danger' } as const
const TOPUP_KEYS = {
  pending: 'credit.pendingTitle',
  approved: 'credit.typeTopup',
  rejected: 'credit.rejectedTitle',
} as const

function TopupRow({ topup, language }: { topup: Topup; language: Language }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div>
        <p className="numeric text-sm font-semibold text-fg">
          {formatDirhams(topup.amount_centimes, language)}
        </p>
        <p className="text-xs text-fg-subtle">
          {t('credit.submitted')} {formatDate(topup.created_at, language)} ·{' '}
          <span className="numeric">{topup.reference}</span>
        </p>
        {topup.rejection_reason && (
          <p dir="auto" className="mt-1 text-xs text-danger">
            {topup.rejection_reason}
          </p>
        )}
      </div>
      <Badge tone={TOPUP_TONES[topup.status]}>{t(TOPUP_KEYS[topup.status])}</Badge>
    </div>
  )
}
