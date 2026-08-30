import { useTranslation } from 'react-i18next'

import type { JobStatus } from '@/data/jobs'
import { Badge } from '@/ui/Badge'

const TONES = {
  assigned: 'brand',
  in_progress: 'warning',
  done: 'brand',
  confirmed: 'success',
  cancelled: 'neutral',
} as const

const KEYS: Record<JobStatus, string> = {
  assigned: 'job.statusAssigned',
  in_progress: 'job.statusInProgress',
  done: 'job.statusDone',
  confirmed: 'job.statusConfirmed',
  cancelled: 'job.statusCancelled',
}

export function JobStatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const { t } = useTranslation()
  return (
    <Badge tone={TONES[status]} className={className}>
      {t(KEYS[status])}
    </Badge>
  )
}
