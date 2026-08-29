import { cn } from '@/ui/cn'

/**
 * A rating, drawn.
 *
 * Half a star matters: 4.5 shown as four is a tradesman quietly downgraded, and
 * shown as five is a promise the reviews do not keep.
 */
export function Stars({
  value,
  size = 'md',
  className,
}: {
  value: number
  size?: 'sm' | 'md'
  className?: string
}) {
  const pixels = size === 'sm' ? 'size-3.5' : 'size-4'
  const filled = Math.max(0, Math.min(5, value))

  return (
    <span
      className={cn('inline-flex items-center gap-0.5', className)}
      role="img"
      aria-label={`${filled.toFixed(1)} / 5`}
    >
      {[0, 1, 2, 3, 4].map((index) => {
        const portion = Math.max(0, Math.min(1, filled - index))
        return <Star key={index} portion={portion} className={pixels} />
      })}
    </span>
  )
}

const PATH =
  'M10 1.8l2.4 5 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L2.2 7.6l5.4-.8 2.4-5Z'

function Star({ portion, className }: { portion: number; className: string }) {
  return (
    <svg viewBox="0 0 20 20" className={className} aria-hidden>
      <path d={PATH} className="fill-border-strong" />
      {portion > 0 && (
        <>
          <defs>
            <clipPath id={`star-${portion}`} clipPathUnits="objectBoundingBox">
              <rect x="0" y="0" width={portion} height="1" />
            </clipPath>
          </defs>
          <path d={PATH} className="fill-star" clipPath={`url(#star-${portion})`} />
        </>
      )}
    </svg>
  )
}
