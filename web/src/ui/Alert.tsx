import type { ReactNode } from 'react'

import { cn } from '@/ui/cn'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  info: 'bg-primary-soft text-fg border-primary/20',
  success: 'bg-success-soft text-fg border-success/25',
  warning: 'bg-warning-soft text-fg border-warning/25',
  danger: 'bg-danger-soft text-fg border-danger/25',
}

const DOTS: Record<Tone, string> = {
  info: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export function Alert({
  tone = 'info',
  children,
  className,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cn(
        'flex items-start gap-3 rounded-md border px-4 py-3 text-sm',
        TONES[tone],
        className,
      )}
    >
      <span aria-hidden className={cn('mt-1.5 size-2 shrink-0 rounded-full', DOTS[tone])} />
      <span>{children}</span>
    </div>
  )
}
