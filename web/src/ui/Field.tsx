import type { InputHTMLAttributes, ReactNode } from 'react'
import { useId, useState } from 'react'

import { cn } from '@/ui/cn'

// `prefix` is a real HTML attribute typed as a string, so ours has to replace
// it rather than widen it.
interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'prefix'> {
  label: string
  hint?: string
  error?: string | null
  /** Rendered before the input inside the same frame — the `+212` prefix. */
  prefix?: ReactNode
  /** Rendered at the end — a password reveal, a unit. */
  suffix?: ReactNode
  /** Latin digits, left to right, whatever the interface language. */
  numeric?: boolean
}

export function Field({
  label,
  hint,
  error,
  prefix,
  suffix,
  numeric = false,
  className,
  ...rest
}: FieldProps) {
  const id = useId()
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-semibold text-fg">
        {label}
      </label>

      <div
        className={cn(
          'flex items-center overflow-hidden rounded-md border bg-surface',
          'transition-colors duration-(--duration-fast)',
          'focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/12',
          error ? 'border-danger' : 'border-border-strong hover:border-fg-subtle',
        )}
      >
        {prefix && (
          <span className="numeric border-e border-border ps-3.5 pe-3 text-sm font-medium text-fg-muted select-none">
            {prefix}
          </span>
        )}
        <input
          {...rest}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          className={cn(
            'min-h-12 w-full bg-transparent px-3.5 text-fg outline-none',
            'placeholder:text-fg-subtle',
            numeric && 'numeric',
            className,
          )}
        />
        {suffix && <span className="pe-2">{suffix}</span>}
      </div>

      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-fg-subtle">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

/** A password field with a reveal, because a typo on a phone is invisible. */
export function PasswordField({
  revealLabel,
  hideLabel,
  ...props
}: Omit<FieldProps, 'type' | 'suffix'> & { revealLabel: string; hideLabel: string }) {
  const [revealed, setRevealed] = useState(false)

  return (
    <Field
      {...props}
      type={revealed ? 'text' : 'password'}
      suffix={
        <button
          type="button"
          onClick={() => setRevealed((value) => !value)}
          aria-label={revealed ? hideLabel : revealLabel}
          className="rounded-sm px-2 py-2 text-xs font-semibold text-fg-muted hover:text-primary"
        >
          {revealed ? hideLabel : revealLabel}
        </button>
      }
    />
  )
}
