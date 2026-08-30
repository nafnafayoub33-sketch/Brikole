import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'

import { useMyProfile } from '@/data/pro'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'

/** M2 — where an application waits, and where a rejection is explained. */
export function StatusPage() {
  const { t } = useTranslation()
  const profile = useMyProfile()

  if (profile.isPending) {
    return (
      <div className="mx-auto max-w-2xl px-5 py-10">
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (profile.isError) {
    return (
      <div className="mx-auto max-w-2xl px-5 py-10">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    )
  }

  // No application at all: he has not been here yet.
  if (!profile.data) return <Navigate to="/pro/onboarding" replace />

  const status = profile.data.status

  return (
    <div className="mx-auto max-w-2xl px-5 py-14">
      <Card className="flex flex-col items-center gap-4 text-center">
        <Badge status={status} />

        {status === 'pending' && (
          <>
            <h1 className="text-xl font-bold text-fg">{t('status.pendingTitle')}</h1>
            <p className="max-w-prose text-sm text-fg-muted">{t('status.pendingBody')}</p>
          </>
        )}

        {status === 'rejected' && (
          <>
            <h1 className="text-xl font-bold text-fg">{t('status.rejectedTitle')}</h1>
            <p className="max-w-prose text-sm text-fg-muted">{t('status.rejectedBody')}</p>
            {profile.data.rejection_reason && (
              <div className="w-full text-start">
                <Alert tone="warning">
                  <span className="block text-xs font-bold uppercase">
                    {t('status.reasonLabel')}
                  </span>
                  <span dir="auto" className="mt-1 block">
                    {profile.data.rejection_reason}
                  </span>
                </Alert>
              </div>
            )}
            <Link to="/pro/onboarding">
              <Button size="pro">{t('status.edit')}</Button>
            </Link>
          </>
        )}

        {status === 'approved' && (
          <>
            <h1 className="text-xl font-bold text-fg">{t('status.approvedTitle')}</h1>
            <p className="max-w-prose text-sm text-fg-muted">{t('status.approvedBody')}</p>
            <Link to={`/m3allem/${profile.data.id}`}>
              <Button size="pro">{t('status.seeProfile')}</Button>
            </Link>
          </>
        )}

        {status === 'suspended' && (
          <>
            <h1 className="text-xl font-bold text-fg">{t('errors.account_suspended')}</h1>
            {profile.data.rejection_reason && (
              <p dir="auto" className="text-sm text-fg-muted">
                {profile.data.rejection_reason}
              </p>
            )}
          </>
        )}
      </Card>
    </div>
  )
}

function Badge({ status }: { status: string }) {
  const tone =
    status === 'approved'
      ? 'bg-success-soft text-success'
      : status === 'rejected' || status === 'suspended'
        ? 'bg-danger-soft text-danger'
        : 'bg-warning-soft text-warning'

  return (
    <span className={`flex size-14 items-center justify-center rounded-full ${tone}`}>
      {status === 'approved' ? <CheckGlyph /> : status === 'pending' ? <ClockGlyph /> : <AlertGlyph />}
    </span>
  )
}

function ClockGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  )
}

function CheckGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.2 12.4 2.6 2.6 5-5.4" />
    </svg>
  )
}

function AlertGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 8v5M12 16v.5" />
    </svg>
  )
}
