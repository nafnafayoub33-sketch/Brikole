import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/ui/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'onBrand'
type Size = 'sm' | 'md' | 'lg' | 'pro'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  fullWidth?: boolean
  children: ReactNode
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-primary text-primary-fg shadow-brand hover:bg-primary-hover active:translate-y-px',
  secondary:
    'bg-surface text-fg border border-border-strong shadow-sm hover:border-primary hover:text-primary',
  ghost: 'bg-transparent text-fg-muted hover:bg-surface-2 hover:text-fg',
  danger: 'bg-danger text-white shadow-sm hover:opacity-90',
  onBrand: 'bg-white text-navy-800 shadow-md hover:bg-navy-50',
}

const SIZES: Record<Size, string> = {
  sm: 'min-h-9 px-3.5 text-sm',
  md: 'min-h-tap px-5 text-sm',
  lg: 'min-h-12 px-7 text-base',
  /** For the tradesman's own screens — tapped outdoors, with wet hands. */
  pro: 'min-h-tap-pro px-7 text-base',
}

/**
 * One primary button per screen. If a screen seems to need two, one of them is
 * secondary.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-semibold',
        'transition-all duration-(--duration-fast)',
        'disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none',
        VARIANTS[variant],
        SIZES[size],
        fullWidth && 'w-full',
        className,
      )}
    >
      {loading && <Spinner />}
      {children}
    </button>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}
