import type { ReactNode } from 'react'

import { cn } from '@/ui/cn'

export function Card({
  children,
  className,
  interactive = false,
}: {
  children: ReactNode
  className?: string
  interactive?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface p-5 shadow-sm',
        interactive &&
          'transition-all duration-(--duration-fast) hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md',
        className,
      )}
    >
      {children}
    </div>
  )
}
