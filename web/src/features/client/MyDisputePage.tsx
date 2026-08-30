import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { useSession } from '@/data/auth'
import { useDispute } from '@/data/disputes'
import type { Language } from '@/lib/i18n'
import { DisputeCase } from '@/ui/DisputeCase'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Skeleton } from '@/ui/Skeleton'

/**
 * A party reading their own case.
 *
 * The same component a moderator uses, without `moderating`: no lead fee, no
 * internal notes, no decision panel. That is a prop rather than a role check
 * inside the component, so this page cannot grow moderator powers by accident.
 */
export function MyDisputePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const params = useParams()

  const disputeId = Number(params.id)
  const valid = Number.isInteger(disputeId) && disputeId > 0

  const session = useSession()
  const dispute = useDispute(valid ? disputeId : null)

  if (!valid) {
    return <EmptyState title={t('dispute.empty')} action={<BackLink />} />
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

  return (
    <div className="mx-auto max-w-3xl">
      <BackLink />
      <div className="mt-4">
        <DisputeCase
          dispute={dispute.data}
          language={language}
          viewerId={session.data?.id ?? 0}
          canWrite={dispute.data.status !== 'resolved'}
        />
      </div>
    </div>
  )
}

function BackLink() {
  const { t } = useTranslation()
  return (
    <Link to="/client/disputes" className="text-sm font-semibold text-primary hover:underline">
      <span aria-hidden className="inline-block rtl:rotate-180">
        &larr;
      </span>{' '}
      {t('dispute.myDisputes')}
    </Link>
  )
}
