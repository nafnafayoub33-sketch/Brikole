/**
 * The mark: a navy tile holding a trowel and a wrench crossed.
 *
 * Simple enough to still read at 24px in a browser tab, which is where a
 * marketplace logo actually earns its keep.
 */
export function LogoMark({ className = 'size-9' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden>
      <rect width="40" height="40" rx="11" fill="currentColor" />
      <g
        stroke="var(--primary-fg)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        <path d="M13.5 26.5 24 16" />
        <path d="M24.8 10.6a4.9 4.9 0 0 1 5.8 5.8l-2.6-2.6-1.2 1.2-2.6-2.6 1.2-1.2Z" />
        <path d="M11.2 24.2 9 26.4a2.4 2.4 0 0 0 3.4 3.4l2.2-2.2" />
        <path d="M17.5 13.5 10 21l3 3 7.5-7.5-3-3Z" />
      </g>
    </svg>
  )
}

export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark className="size-9 text-primary" />
      <span className="text-lg font-bold tracking-tight text-fg">Brikole</span>
    </span>
  )
}

/** For the navy panel, where the mark sits on brand rather than on paper. */
export function LogoOnBrand({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg viewBox="0 0 40 40" className="size-9" aria-hidden>
        <rect width="40" height="40" rx="11" fill="rgb(255 255 255 / 0.14)" />
        <g
          stroke="#fff"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        >
          <path d="M13.5 26.5 24 16" />
          <path d="M24.8 10.6a4.9 4.9 0 0 1 5.8 5.8l-2.6-2.6-1.2 1.2-2.6-2.6 1.2-1.2Z" />
          <path d="M11.2 24.2 9 26.4a2.4 2.4 0 0 0 3.4 3.4l2.2-2.2" />
          <path d="M17.5 13.5 10 21l3 3 7.5-7.5-3-3Z" />
        </g>
      </svg>
      <span className="text-lg font-bold tracking-tight text-white">Brikole</span>
    </span>
  )
}
