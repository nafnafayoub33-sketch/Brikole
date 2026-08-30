import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { useSession } from '@/data/auth'
import {
  useClaimDispute,
  useDispute,
  useResolveDispute,
  type DisputeVerdict,
} from '@/data/disputes'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { DisputeCase } from '@/ui/DisputeCase'
import { VERDICT_KEYS } from '@/ui/disputeLabels'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

const VERDICTS: DisputeVerdict[] = ['client_at_fault', 'provider_at_fault', 'no_fault']

/**
 * D2 — the case, and the decision.
 *
 * Read-only until he claims it: two moderators working one argument reach two
 * verdicts. The decision panel only appears once it is his, and the refund
 * only unlocks on the one verdict that permits it — the API refuses the rest,
 * and the screen agrees with the API rather than hiding the disagreement.
 */
export function DisputePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const params = useParams()

  const disputeId = Number(params.id)
  const valid = Number.isInteger(disputeId) && disputeId > 0

  const session = useSession()
  const dispute = useDispute(valid ? disputeId : null)
  const claim = useClaimDispute()
  const resolve = useResolveDispute()

  const [verdict, setVerdict] = useState<DisputeVerdict | null>(null)
  const [note, setNote] = useState('')
  const [refund, setRefund] = useState(false)
  const [suspend, setSuspend] = useState(false)

  if (!valid) {
    return <EmptyState title={t('dispute.myDisputes')} action={<BackLink />} />
  }

  if (dispute.isPending) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-12 w-2/3" />
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (dispute.isError) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorState error={dispute.error} onRetry={() => void dispute.refetch()} />
        <div className="mt-6 flex justify-center">
          <BackLink />
        </div>
      </div>
    )
  }

  const data = dispute.data
  const me = session.data?.id ?? 0
  const mine = data.claimed_by_id === me
  const decided = data.status === 'resolved'

  // The refund is only legal on one verdict; picking another must not leave a
  // stale tick behind that the API would then reject.
  const refundAllowed = verdict === 'client_at_fault'
  const canDecide = mine && !decided && verdict !== null && note.trim().length > 0

  return (
    <div className="mx-auto max-w-3xl">
      <BackLink />

      <div className="mt-4">
        <DisputeCase
          dispute={data}
          language={language}
          viewerId={me}
          moderating
          canWrite={mine && !decided}
          footer={
            decided ? null : !mine ? (
              data.claimed_by_id === null ? (
                <div>
                  <Button
                    size="pro"
                    loading={claim.isPending}
                    onClick={() => claim.mutate(data.id)}
                  >
                    {t('mod.claim')}
                  </Button>
                  {claim.isError && (
                    <div className="mt-3">
                      <ErrorState error={claim.error} />
                    </div>
                  )}
                </div>
              ) : null
            ) : (
              <Card>
                <h2 className="text-lg font-bold text-fg">{t('mod.decide')}</h2>

                <fieldset className="mt-5">
                  <legend className="mb-3 text-sm font-semibold text-fg">
                    {t('dispute.verdict')}
                  </legend>
                  <div className="flex flex-col gap-3">
                    {VERDICTS.map((option) => (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={verdict === option}
                        onClick={() => {
                          setVerdict(option)
                          if (option !== 'client_at_fault') setRefund(false)
                        }}
                        className={cn(
                          'min-h-tap rounded-md border-2 px-4 py-3 text-start text-sm font-medium',
                          'transition-colors duration-(--duration-fast)',
                          verdict === option
                            ? 'border-primary bg-primary-soft text-primary'
                            : 'border-border bg-surface text-fg hover:border-border-strong',
                        )}
                      >
                        {t(VERDICT_KEYS[option])}
                      </button>
                    ))}
                  </div>
                </fieldset>

                <label className="mt-6 flex flex-col gap-2">
                  <span className="text-sm font-semibold text-fg">{t('mod.note')}</span>
                  <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    rows={4}
                    maxLength={2000}
                    className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-primary"
                  />
                  <span className="text-xs text-fg-subtle">{t('mod.noteHint')}</span>
                </label>

                <div className="mt-6 flex flex-col gap-4 border-t border-border pt-5">
                  <label
                    className={cn(
                      'flex items-start gap-3 text-sm',
                      !refundAllowed && 'opacity-50',
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={refund}
                      disabled={!refundAllowed}
                      onChange={(event) => setRefund(event.target.checked)}
                      className="mt-1 size-4 accent-[var(--color-primary)]"
                    />
                    <span>
                      <span className="font-medium text-fg">
                        {t('mod.refund')}
                        {data.job.lead_fee_centimes ? (
                          <>
                            {' — '}
                            <span className="numeric">
                              {formatDirhams(data.job.lead_fee_centimes, language)}
                            </span>
                          </>
                        ) : null}
                      </span>
                      <span className="block text-xs text-fg-subtle">
                        {t('mod.refundOnly')}
                      </span>
                    </span>
                  </label>

                  <label className="flex items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={suspend}
                      onChange={(event) => setSuspend(event.target.checked)}
                      className="mt-1 size-4 accent-[var(--color-primary)]"
                    />
                    <span>
                      <span className="font-medium text-fg">{t('mod.suspend')}</span>
                      <span className="block text-xs text-fg-subtle">
                        {t('mod.suspendedNote')}
                      </span>
                    </span>
                  </label>
                </div>

                {resolve.isError && (
                  <div className="mt-5">
                    <ErrorState error={resolve.error} />
                  </div>
                )}

                <div className="mt-6 border-t border-border pt-5">
                  <ConfirmButton
                    label={t('mod.resolve')}
                    question={t('mod.resolveConfirm')}
                    confirmLabel={t('mod.resolveYes')}
                    size="pro"
                    disabled={!canDecide}
                    loading={resolve.isPending}
                    onConfirm={() =>
                      resolve.mutate({
                        disputeId: data.id,
                        verdict: verdict as DisputeVerdict,
                        note: note.trim(),
                        refund_lead_fee: refund && refundAllowed,
                        suspend_at_fault: suspend,
                      })
                    }
                  />
                </div>
              </Card>
            )
          }
        />
      </div>
    </div>
  )
}

function BackLink() {
  const { t } = useTranslation()
  return (
    <Link to="/mod/disputes" className="text-sm font-semibold text-primary hover:underline">
      <span aria-hidden className="inline-block rtl:rotate-180">
        &larr;
      </span>{' '}
      {t('mod.title')}
    </Link>
  )
}
