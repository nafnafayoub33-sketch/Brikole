import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/ui/Button'
import { cn } from '@/ui/cn'

/**
 * A destructive or irreversible action, with the question in front of it.
 *
 * The rules say these confirm first; hand-rolling that six times is how one of
 * them ends up not confirming. The question replaces the button rather than
 * covering the screen — a dialog over a job you are reading hides the thing you
 * are deciding about.
 */
export function ConfirmButton({
  label,
  question,
  confirmLabel,
  onConfirm,
  loading = false,
  disabled = false,
  confirmDisabled = false,
  variant = 'primary',
  size = 'md',
  tone = 'primary',
  children,
  className,
}: {
  label: string
  question: string
  confirmLabel: string
  onConfirm: () => void
  loading?: boolean
  disabled?: boolean
  /** Blocks only the confirming press — the field it needs is not filled. */
  confirmDisabled?: boolean
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'pro'
  /** The colour of the *confirming* button, which is often the louder one. */
  tone?: 'primary' | 'danger'
  /** Extra fields the confirmation needs — a reason, usually. */
  children?: ReactNode
  className?: string
}) {
  const { t } = useTranslation()
  const [asking, setAsking] = useState(false)

  if (!asking) {
    return (
      <Button
        variant={variant}
        size={size}
        disabled={disabled}
        className={className}
        onClick={() => setAsking(true)}
      >
        {label}
      </Button>
    )
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <p className="text-sm text-fg-muted">{question}</p>
      {children}
      <div className="flex flex-wrap gap-3">
        <Button
          size={size}
          variant={tone === 'danger' ? 'danger' : 'primary'}
          loading={loading}
          disabled={disabled || confirmDisabled}
          onClick={onConfirm}
        >
          {confirmLabel}
        </Button>
        <Button size={size} variant="ghost" onClick={() => setAsking(false)}>
          {t('job.keep')}
        </Button>
      </div>
    </div>
  )
}
