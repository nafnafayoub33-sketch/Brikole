import { Navigate } from 'react-router-dom'

import { useMyProfile } from '@/data/pro'
import { ErrorState } from '@/ui/ErrorState'
import { NotBuilt } from '@/ui/NotBuilt'
import { Skeleton } from '@/ui/Skeleton'

/**
 * Where `/pro` sends a tradesman, which depends on how far he has got.
 *
 * No application → M1. Waiting or turned down → M2. Approved → his dashboard.
 * The absence of a profile is the signal, so a tradesman who registered and
 * closed the tab lands back on the form rather than on an empty dashboard.
 */
export function ProHome() {
  const profile = useMyProfile()

  if (profile.isPending) {
    return (
      <div className="mx-auto max-w-4xl px-5 py-10">
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

  if (!profile.data) return <Navigate to="/pro/onboarding" replace />
  if (profile.data.status !== 'approved') return <Navigate to="/pro/status" replace />

  return <NotBuilt screen="M3" />
}
