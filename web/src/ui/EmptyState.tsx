import type { ReactNode } from 'react'

/** The empty state every list screen owes the reader, with a way forward. */
export function EmptyState({
  title,
  body,
  action,
}: {
  title: string
  body?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center">
      <p className="font-medium text-fg">{title}</p>
      {body && <p className="max-w-prose text-sm text-fg-muted">{body}</p>}
      {action}
    </div>
  )
}
