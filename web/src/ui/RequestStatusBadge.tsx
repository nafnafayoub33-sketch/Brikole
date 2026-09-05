import { useTranslation } from 'react-i18next'

import type { RequestStatus } from '@/data/requests'
import { Badge } from '@/ui/Badge'
import { cn } from '@/ui/cn'

/**
 * What has become of a request.
 *
 * Lived inside C2 until A4 wanted the same badge. Features never import from
 * each other, and copying five statuses into the admin screen is how one of
 * them ends up a different colour there.
 */
const TONES = {
  open: 'brand',
  assigned: 'warning',
  done: 'success',
  cancelled: 'neutral',
  expired: 'neutral',
} as const

const KEYS: Record<RequestStatus, string> = {
  open: 'requests.statusOpen',
  assigned: 'requests.statusAssigned',
  done: 'requests.statusDone',
  cancelled: 'requests.statusCancelled',
  expired: 'requests.statusExpired',
}

export function RequestStatusBadge({
  status,
  className,
}: {
  status: RequestStatus
  className?: string
}) {
  const { t } = useTranslation()
  return (
    <Badge tone={TONES[status]} className={cn('shrink-0', className)}>
      {t(KEYS[status])}
    </Badge>
  )
}
