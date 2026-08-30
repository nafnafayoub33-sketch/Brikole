import { useTranslation } from 'react-i18next'

import type { DisputeReason, DisputeStatus } from '@/data/disputes'
import { Badge } from '@/ui/Badge'
import { REASON_KEYS, STATUS_KEYS, STATUS_TONES } from '@/ui/disputeLabels'

export function DisputeStatusBadge({
  status,
  className,
}: {
  status: DisputeStatus
  className?: string
}) {
  const { t } = useTranslation()
  return (
    <Badge tone={STATUS_TONES[status]} className={className}>
      {t(STATUS_KEYS[status])}
    </Badge>
  )
}

export function ReasonBadge({ reason }: { reason: DisputeReason }) {
  const { t } = useTranslation()
  return <Badge tone="neutral">{t(REASON_KEYS[reason])}</Badge>
}
